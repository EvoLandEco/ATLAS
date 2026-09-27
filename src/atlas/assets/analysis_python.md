"""Run from the extracted dataset directory: python analysis.py"""
import csv
import json
from pathlib import Path

root = Path(__file__).resolve().parent
snapshot = json.loads((root / "report.json").read_text(encoding="utf-8"))
metrics = snapshot["tables"]["event_metrics"]
for row in metrics:
    if row["metric"] == "cases" and row["value_status"] == "reported":
        print(row["event_id"], row["count_kind"], row["value"], row["unit"], row["period_end"])

# The canonical JSON keeps numeric nulls and missingness reasons separate.
# For pandas: pip install pandas, then use:
# pd.read_csv(root / "observations.csv", keep_default_na=False, na_values=["N/A"])
# Read arrays with json.loads. Preserve ISO country code NA (Namibia).
# Analyze selected compatible series; inspect superseded and conflicting source claims explicitly.
