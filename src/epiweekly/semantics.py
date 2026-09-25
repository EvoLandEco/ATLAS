"""Deterministic terminology mapping, evidence checks, and comparability rules."""
from __future__ import annotations
import re
from datetime import date
import unicodedata
from copy import deepcopy
from .models import Mention
from .util import canonical_url


def norm(text: str) -> str:
    return " ".join(unicodedata.normalize("NFKC",text).split()).casefold()


def normalize_mention(mention: Mention, vocabulary: dict) -> Mention:
    data = mention.model_dump(mode="json")
    for field in ("disease", "pathogen", "host"):
        val = data[field]["value"]
        if val:
            aliases = vocabulary.get(field,{})
            data[field]["value"] = aliases.get(norm(val),val.strip())
    if data["country_code"]["value"]:
        data["country_code"]["value"] = data["country_code"]["value"].upper()
    data["tags"] = sorted(set(data["tags"]))
    return Mention.model_validate(data)


def evidence_errors(mention: Mention, source_text: str) -> list[str]:
    errors = []
    haystack = norm(source_text)
    for ev in mention.evidence + [o.evidence for o in mention.observations] + [r.evidence for r in mention.resources]:
        if norm(ev.quote) not in haystack:
            errors.append(f"Evidence text absent: {ev.field}")
    # Anchoring is a mechanical prerequisite; semantic accuracy is an editorial decision.
    for obs in mention.observations:
        if obs.value is not None:
            quote = norm(obs.evidence.quote).replace(",", "").replace("\u202f", " ")
            numeric_quote = re.sub(r"(?<=\d)\s+(?=\d{3}(?:\D|$))", "", quote)
            number = str(int(obs.value)) if obs.value.is_integer() else str(obs.value)
            tokens = re.findall(r"\d+(?:\.\d+)?", numeric_quote)
            # Number words and locale-specific decimal notation are explicitly reviewed.
            if number not in tokens:
                errors.append(f"Numeric evidence needs review: {obs.metric}={number}")
    for resource in mention.resources:
        try:
            canonical_url(resource.url)
        except ValueError:
            errors.append("Resource URL is invalid")
        if resource.url not in source_text:
            errors.append("Resource URL absent from captured source")
    return sorted(set(errors))


def identity_signature(m: dict) -> tuple:
    return (m["disease"]["value"],m["host"]["value"],m["country_code"]["value"],
            m["location"]["value"], m["geographic_scope"],m["kind"])


def series_key(m: dict, o: dict) -> tuple:
    """Measurement context; end date is a time coordinate, not a series key."""
    interval_days=None
    if o["count_kind"]=="interval" and o["period_start"]["value"] and o["period_end"]["value"]:
        interval_days=(date.fromisoformat(o["period_end"]["value"])-date.fromisoformat(o["period_start"]["value"])).days+1
    return (m["disease"]["value"], m["host"]["value"], m["country_code"]["value"],
            m["location"]["value"],m["geographic_scope"],o["metric"],o["unit"],o["count_kind"],
            o["case_class"],o["case_definition"]["value"],o["date_basis"],o["population"]["value"],o["stratum"]["value"],
            o["period_start"]["value"] if o["count_kind"] == "cumulative" else None,
            interval_days,o["denominator"],o["denominator_status"],o["qualifier"])


def cumulative_change(current: dict, previous: dict | None) -> tuple[float | None,str]:
    if previous is None:
        return None,"not_comparable"
    required = ["series_id","origin_authority","period_start","period_end","date_basis","case_class","case_definition","population"]
    if any(current.get(k) in (None,"unknown") or previous.get(k) in (None,"unknown") for k in required):
        return None,"not_comparable"
    if current["count_kind"] != "cumulative" or previous["count_kind"] != "cumulative":
        return None,"not_comparable"
    if current.get("value_status") != "reported" or previous.get("value_status") != "reported":
        return None,"not_comparable"
    if current["series_id"] != previous["series_id"] or current["origin_authority"] != previous["origin_authority"]:
        return None,"not_comparable"
    if current["period_end"] < previous["period_end"]:
        return None,"not_comparable"
    if current.get("qualifier")!="exact" or previous.get("qualifier")!="exact":
        return None,"not_comparable"
    change = current["value"] - previous["value"]
    # This label remains a reporting change even when positive.
    return change, "reported"
