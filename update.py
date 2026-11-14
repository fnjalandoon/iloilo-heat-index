"""Read the PAGASA heat index image and merge Iloilo City values into history.json.

Usage: python3 update.py HeatIndexObserved.png
Exits non-zero if the row cannot be read, so the scheduled run fails visibly.
"""
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from extract import extract

HISTORY = Path("history.json")
OFFSETS = {"d-4": -4, "d-3": -3, "d-2": -2, "d-1": -1, "d0": 0, "fc+1": 1, "fc+2": 2}


def main(path):
    res = extract(path)
    if not res["values"] or not res["as_of"]:
        print("Could not read Iloilo City row or issue date:", res)
        return 1
    vals = [v["hi_c"] for v in res["values"]]
    if not all(15 <= v <= 60 for v in vals):
        print("Implausible values, refusing to save:", vals)
        return 1

    base = datetime.strptime(res["as_of"], "%d %B %Y").date()
    hist = (json.loads(HISTORY.read_text()) if HISTORY.exists()
            else {"station": "Iloilo City, Iloilo", "days": {}})
    for item in res["values"]:
        day = (base + timedelta(days=OFFSETS[item["slot"]])).isoformat()
        rec = hist["days"].setdefault(day, {})
        if item["slot"].startswith("fc"):
            if "observed" not in rec:
                rec["forecast"] = item["hi_c"]
        else:
            rec["observed"] = item["hi_c"]
            rec.pop("forecast", None)
    hist["as_of"] = base.isoformat()
    hist["updated"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    hist["days"] = dict(sorted(hist["days"].items()))
    HISTORY.write_text(json.dumps(hist, indent=1))
    print("Saved", base, vals)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
