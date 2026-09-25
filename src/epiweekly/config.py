from __future__ import annotations
from importlib.resources import files
from pathlib import Path
import yaml
from .util import digest


def assets(name: str) -> str:
    return files("epiweekly").joinpath("assets",name).read_text(encoding="utf-8")


def load_config(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    required = {"timezone","sources","limits","research_profile"}
    if not isinstance(data,dict) or not required.issubset(data):
        raise ValueError(f"Configuration requires {sorted(required)}")
    ids = [s["id"] for s in data["sources"]]
    if len(ids) != len(set(ids)):
        raise ValueError("Source IDs must be unique")
    for s in data["sources"]:
        if s["adapter"] not in {"who_odata","rss_discovery","html_index","static","manual"}:
            raise ValueError("Unknown source adapter")
        if not s.get("allowed_hosts"):
            raise ValueError(f"{s['id']} requires an explicit host allowlist")
    return data


def vocabulary() -> dict:
    return yaml.safe_load(assets("vocabulary.yaml"))


def config_hash(data: dict) -> str:
    return digest(data)
