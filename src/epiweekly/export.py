"""Deterministic documented JSON/CSV bundles and content approval manifests."""
from __future__ import annotations
import csv
import io
import json
import zipfile
from pathlib import Path
from .models import Status
from .render import render_markdown, render_html
from .tables import TABLES, dictionary, fields_for, complete_row
from .util import canonical, digest, write_json, atomic_write, read_json

DATASET_GUIDE="""# EpiWeekly dataset\n\n
This bundle is a frozen knowledge-time snapshot. `report.json` is the canonical structured representation.
CSV files use the same tables and fixed column order. `data_dictionary.json` and `DATA_DICTIONARY.md` describe every column.
`report.schema.json` defines the machine-readable table contracts. `checksums.sha256` verifies bundle members.

## Units of analysis
`events` contains current reviewed event views. `updates` links accepted report mentions to those events.
`observations` contains individual source assertions, including explicit supersessions. `event_metrics` gives selected current
measurements or a conflicting missingness status. Equal measurements in multiple reports are corroborating claims and share
one selected representative; they remain separate observation rows. Sources may share one originating authority.
`event_history` retains prior weekly event views. Compare archived bundles for historical measurements and editorial decisions.
`relationships` distinguishes editorial identity decisions, source-reported links, and analyst hypotheses.
`opportunities` contains persistent research proposals and source-reported calls, labeled by basis.
`source_coverage` records scope, gaps, failures, and adapter limits. Report counts describe captured evidence, rather than global burden.

## Missing data
JSON uses null plus an explicit `_status`. CSV uses the literal `N/A` plus the same status column.
`reported` accompanies an available value, including 0. `not_reported` means the source is silent;
`unknown` means explicitly unknown; `not_applicable` means structurally inapplicable; `pending_verification` means unresolved;
`conflicting` preserves disagreement; `not_extracted` describes extraction state; `not_comparable` marks unsupported comparisons;
`access_restricted` describes a documented access limitation. Code NA denotes Namibia and is an ordinary country value.

## Dates and changes
`known_at` and `knowledge_cutoff` use UTC RFC 3339. Source publication timestamps retain their precision.
Measurement intervals and `as_of` are ISO 8601 dates. Period dates refer to the declared `date_basis`.
`change_in_reported_cumulative` is a reporting-total difference across compatible weekly snapshots; revisions can make it negative.
Incident counts are stored with `count_kind=interval` and the source reporting interval. Overlapping population and geographic
scopes remain separate series. The source case classification, denominator, host, and stratum are measurement context.

## Text and CSV
CSV uses UTF-8, comma separators, LF newlines, JSON strings for array cells, and true/false booleans.
String cells beginning with =, +, -, @, tab, or carriage return receive a leading apostrophe in CSV for spreadsheet import.
JSON preserves original strings. Numeric negatives remain numeric. The accompanying Python and R examples preserve NA country codes.

## Provenance and reuse
Source landing URLs, content URLs, publication dates, first capture times, and content hashes accompany the data.
Full source bytes, long excerpts, model requests, API credentials, and private editorial rationale remain in the deployment state.
Software and documentation licensing is recorded in the repository. Source-specific rights and attribution remain attached to source content.
A release approval identifies the exact checksummed bundle and its editor. `draft` and `approved` are editorial release states.
"""


def metadata_schema() -> dict:
    strings=["report_id","report_date","knowledge_cutoff","timezone","release_status","dataset_mode","software_version",
        "schema_version","template_version","config_sha256","ledger_head_sha256","prompt_sha256","extraction_schema_sha256","vocabulary_sha256"]
    props={k:{"type":"string"} for k in strings}
    props["report_date"]["format"]="date";props["knowledge_cutoff"]["format"]="date-time"
    props.update(previous_report_id={"type":["string","null"]},previous_report_id_status={"enum":["reported","not_applicable"]},
                 build_fingerprint={"type":"object"},research_profile={"type":"object"})
    integers=["pending_review_mentions","evidence_flagged_mentions","captured_documents","documents_with_some_extraction",
              "documents_awaiting_extraction","conflicting_current_series"]
    quality={k:{"type":"integer","minimum":0} for k in integers}
    quality.update(future_dated_candidates_excluded={"type":"array","items":{"type":"string"}},
        core_source_gaps={"type":"array","items":{"type":"string"}},latest_extraction_check={"type":["object","null"]})
    props["quality"]={"type":"object","required":list(quality),"properties":quality,"additionalProperties":False}
    return {"type":"object","required":list(props),"properties":props,"additionalProperties":False}


def report_schema() -> dict:
    type_map={"string":"string","number":"number","integer":"integer","boolean":"boolean","date":"string","datetime":"string","array":"array"}
    table_props={}
    for name in TABLES:
        props={}
        for field in fields_for(name):
            typ=type_map[field["type"]]
            schema={"type":[typ,"null"] if field["nullable"] else typ,"description":field["description"]}
            if typ=="array":schema["items"]={"type":"string"}
            if field["type"]=="date":schema["format"]="date"
            if field["type"]=="datetime":schema["format"]="date-time"
            if field["name"].endswith("_status") and field["name"] not in {"lifecycle_status","freshness_status"}:
                # Only generated missingness-status fields get this enum.
                if any(f[0]+"_status"==field["name"] and f[3] for f in TABLES[name]):
                    schema["enum"]=[s.value for s in Status]
            props[field["name"]]=schema
        table_props[name]={"type":"array","items":{"type":"object","properties":props,"required":list(props),"additionalProperties":False}}
    return {"$schema":"https://json-schema.org/draft/2020-12/schema","title":"EpiWeekly report 0.1.0",
            "type":"object","required":["metadata","tables"],"additionalProperties":False,
            "properties":{"metadata":metadata_schema(),"tables":{"type":"object","properties":table_props,
                "required":list(TABLES),"additionalProperties":False}}}


def validate_snapshot(snapshot: dict) -> dict:
    if set(snapshot)!={"metadata","tables"} or set(snapshot["tables"])!=set(TABLES):
        raise ValueError("Report top-level or table contract differs from the schema")
    import jsonschema
    jsonschema.Draft202012Validator(report_schema(),format_checker=jsonschema.FormatChecker()).validate(snapshot)
    for name,rows in snapshot["tables"].items():
        for row in rows:
            if complete_row(name,row)!=row:
                raise ValueError("Export has unexpected or omitted columns")
            for field in fields_for(name):
                value=row[field["name"]]
                if value is None:continue
                typ=field["type"]
                valid=(isinstance(value,str) if typ in {"string","date","datetime"} else
                       isinstance(value,bool) if typ=="boolean" else
                       isinstance(value,int) and not isinstance(value,bool) if typ=="integer" else
                       isinstance(value,(int,float)) and not isinstance(value,bool) if typ=="number" else
                       isinstance(value,list) and all(isinstance(v,str) for v in value))
                if not valid:raise ValueError(f"Invalid type: {name}.{field['name']}")
                if field["name"].endswith("_status") and any(f[0]+"_status"==field["name"] and f[3] for f in TABLES[name]):
                    Status(value)
    identities={r["event_id"] for r in snapshot["tables"]["event_identities"]}
    for name in ["events","updates","observations","event_metrics","opportunities","event_history"]:
        if any(r["event_id"] not in identities for r in snapshot["tables"][name]):
            raise ValueError("Historical or current event identity foreign key is missing")
    for relation in snapshot["tables"]["relationships"]:
        if not {relation["from_event_id"],relation["to_event_id"]}<=identities:
            raise ValueError("Relationship endpoint identity is missing")
    docs={r["document_id"] for r in snapshot["tables"]["documents"]}
    updates={r["candidate_id"] for r in snapshot["tables"]["updates"]}
    for obs in snapshot["tables"]["observations"]:
        if obs["document_id"] not in docs or obs["candidate_id"] not in updates:
            raise ValueError("Observation provenance foreign key is missing")
    obs_ids={r["observation_id"] for r in snapshot["tables"]["observations"]}
    for metric in snapshot["tables"]["event_metrics"]:
        if not set(metric["supporting_observation_ids"])<=obs_ids:
            raise ValueError("Current measurement evidence foreign key is missing")
    return {"valid":True,"tables":len(TABLES),"rows":sum(len(r) for r in snapshot["tables"].values())}


def csv_bytes(name: str, rows: list[dict]) -> bytes:
    buffer=io.StringIO(newline="")
    fieldnames=[f["name"] for f in fields_for(name)]
    writer=csv.DictWriter(buffer,fieldnames=fieldnames,lineterminator="\n")
    writer.writeheader()
    for row in rows:
        values={}
        for key in fieldnames:
            value=row[key]
            if value is None:value="N/A"
            elif isinstance(value,(list,dict)):value=canonical(value)
            elif isinstance(value,bool):value="true" if value else "false"
            elif isinstance(value,str) and value.startswith(("=","+","-","@","\t","\r")):value="'"+value
            values[key]=value
        writer.writerow(values)
    return buffer.getvalue().encode("utf-8")


def dictionary_markdown() -> str:
    parts=["# EpiWeekly data dictionary","Schema version: 0.1.0. Nullable fields have an explicit reason column."]
    for name in TABLES:
        parts.extend(["## "+name,"| Field | Type | Meaning |","| --- | --- | --- |"])
        for f in fields_for(name):
            parts.append(f"| `{f['name']}` | {f['type']}{' / null' if f['nullable'] else ''} | {f['description']} |")
    return "\n".join(parts)+"\n"


def reproducible_zip(directory: Path, target: Path) -> None:
    with zipfile.ZipFile(target,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for path in sorted(directory.rglob("*")):
            if path.is_file() and path.resolve()!=target.resolve():
                info=zipfile.ZipInfo(path.relative_to(directory).as_posix(),date_time=(1980,1,1,0,0,0))
                info.compress_type=zipfile.ZIP_DEFLATED
                info.external_attr=0o100644<<16
                z.writestr(info,path.read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)


def export_snapshot(snapshot: dict, out: Path) -> dict:
    validate_snapshot(snapshot)
    out.mkdir(parents=True,exist_ok=True)
    if any(out.iterdir()):
        raise ValueError("Export target must be empty so each bundle contains exactly one frozen snapshot")
    write_json(out/"report.json",snapshot)
    atomic_write(out/"report.md",render_markdown(snapshot))
    atomic_write(out/"report.html",render_html(snapshot))
    import jsonschema
    jsonschema.Draft202012Validator(report_schema(),format_checker=jsonschema.FormatChecker()).validate(snapshot)
    for name,rows in snapshot["tables"].items():
        atomic_write(out/(name+".csv"),csv_bytes(name,rows))
    write_json(out/"data_dictionary.json",dictionary())
    write_json(out/"report.schema.json",report_schema())
    atomic_write(out/"DATA_DICTIONARY.md",dictionary_markdown())
    atomic_write(out/"DATASET_README.md",DATASET_GUIDE)
    from .config import assets
    atomic_write(out/"analysis.py",assets("analysis_python.md"))
    atomic_write(out/"analysis.R",assets("analysis_r.md"))
    resources=[]
    for name in TABLES:
        fields=[]
        for f in fields_for(name):
            field={"name":f["name"],"type":f["type"],"description":f["description"]}
            if f["type"]=="datetime":field["format"]="any"
            fields.append(field)
        resources.append({"name":name,"path":name+".csv","profile":"tabular-data-resource",
            "format":"csv","encoding":"utf-8","schema":{"fields":fields,"missingValues":["N/A"]}})
    write_json(out/"datapackage.json",{"profile":"tabular-data-package","name":"epiweekly-"+snapshot["metadata"]["report_id"],
                                     "resources":resources})
    write_json(out/"run_manifest.json",snapshot["metadata"])
    checksums={p.name:digest(p.read_bytes()) for p in sorted(out.iterdir()) if p.is_file()}
    atomic_write(out/"checksums.sha256","".join(f"{sha}  {name}\n" for name,sha in checksums.items()))
    reproducible_zip(out,out/"dataset.zip")
    return {"path":str(out),"bundle_sha256":digest((out/"dataset.zip").read_bytes()),"files":len(list(out.iterdir()))}


def verify_bundle(out: Path) -> dict:
    expected={}
    for line in (out/"checksums.sha256").read_text().splitlines():
        sha,name=line.split("  ",1)
        if Path(name).name!=name:raise ValueError("Bundle member path must be local")
        expected[name]=sha
        if digest((out/name).read_bytes())!=sha:raise ValueError("Checksum mismatch: "+name)
    result=validate_snapshot(read_json(out/"report.json"))
    if (out/"dataset.zip").exists():
        with zipfile.ZipFile(out/"dataset.zip") as z:
            if set(z.namelist())!=set(expected)|{"checksums.sha256"}:raise ValueError("ZIP membership differs from manifest")
            if z.read("checksums.sha256")!=(out/"checksums.sha256").read_bytes():raise ValueError("ZIP checksum manifest differs")
            for name,sha in expected.items():
                if digest(z.read(name))!=sha:raise ValueError("ZIP member mismatch: "+name)
    return {**result,"checksummed_files":len(expected)}
