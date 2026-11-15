"""Read the PAGASA heat index image and merge each station's values into history.json.

Usage: python3 update.py HeatIndexObserved.png
Stations that cannot be read are skipped (their old data is kept) and the run exits
non-zero, so the scheduled run fails visibly and GitHub emails you.
"""
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from extract import STATIONS, extract

HISTORY = Path("history.json")
OFFSETS = {"d-4": -4, "d-3": -3, "d-2": -2, "d-1": -1, "d0": 0, "fc+1": 1, "fc+2": 2}


def load():
    h = json.loads(HISTORY.read_text()) if HISTORY.exists() else {}
    if "stations" not in h and "days" in h:  # old single-station format
        h = {"stations": {"iloilo": {"days": h["days"]}}, "as_of": h.get("as_of")}
    h.setdefault("stations", {})
    return h


def main(path):
    res = extract(path)
    if not res["as_of"]:
        print("Could not read the issue date:", res)
        return 1
    base = datetime.strptime(res["as_of"], "%d %B %Y").date()
    hist = load()
    failed = []
    for st in STATIONS:
        items = res["stations"].get(st["id"])
        vals = [i["hi_c"] for i in items] if items else []
        if not items or not all(15 <= v <= 60 for v in vals):
            print(f"{st['name']}: could not read a plausible row {vals}, skipped")
            failed.append(st["id"])
            continue
        rec = hist["stations"].setdefault(st["id"], {"days": {}})
        rec["name"], rec["station"] = st["name"], st["station"]
        for item in items:
            day = (base + timedelta(days=OFFSETS[item["slot"]])).isoformat()
            r = rec["days"].setdefault(day, {})
            if item["slot"].startswith("fc"):
                if "observed" not in r:
                    r["forecast"] = item["hi_c"]
            else:
                r["observed"] = item["hi_c"]
                r.pop("forecast", None)
        rec["days"] = dict(sorted(rec["days"].items()))
        print(f"{st['name']}: saved {base} {vals}")
    if len(failed) < len(STATIONS):
        hist["as_of"] = base.isoformat()
        hist["updated"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        HISTORY.write_text(json.dumps(hist, indent=1))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
