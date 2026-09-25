from __future__ import annotations
from importlib.resources import files
from pathlib import Path
from calendar import monthrange
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
import yaml
from .util import digest, utcnow


def publication_window(config: dict, as_of: str | None = None) -> tuple[str, str] | None:
    months=config.get("publication_window_months")
    days=config.get("publication_window_days")
    if months is None and days is None:return None
    if months is not None and days is not None:
        raise ValueError("Set one publication window: days or months")
    value=days if days is not None else months
    if type(value) is not int or value < 1:
        raise ValueError("The publication window must be a positive integer")
    value=as_of or utcnow()
    end=(date.fromisoformat(value) if len(value)==10 else
         datetime.fromisoformat(value.replace("Z","+00:00")).astimezone(ZoneInfo(config["timezone"])).date())
    if days is not None:
        start=end-timedelta(days=days-1)
    else:
        year,month=divmod(end.year*12+end.month-1-months,12)
        start=date(year,month+1,min(end.day,monthrange(year,month+1)[1]))
    return start.isoformat(),end.isoformat()


def in_publication_window(document: dict, window: tuple[str,str] | None) -> bool:
    published=document.get("published_at")
    return window is None or bool(published and window[0] <= published[:10] <= window[1])


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
    publication_window(data)
    for s in data["sources"]:
        if s["adapter"] not in {"who_odata","rss_discovery","html_index","sitemap","static","manual"}:
            raise ValueError("Unknown source adapter")
        if not s.get("allowed_hosts"):
            raise ValueError(f"{s['id']} requires an explicit host allowlist")
    return data


def vocabulary() -> dict:
    return yaml.safe_load(assets("vocabulary.yaml"))


def config_hash(data: dict) -> str:
    return digest(data)
