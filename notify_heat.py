"""Send a phone alert (ntfy) when PAGASA's heat index data moves to a new day.

Usage: python3 notify_heat.py OLD_AS_OF
Needs the NTFY_TOPIC secret. Without it, it only prints the message.
"""
import json, os, sys, urllib.request

def cpu(v):
    if v >= 42: return "RED: face-to-face classes suspended, online"
    if v >= 40: return "YELLOW: adjusted class schedule"
    return "GREEN: regular classes"

def main(old):
    h = json.load(open("history.json"))
    if h["as_of"] == old:
        print("no new day; no alert"); return 0
    asof = h["as_of"]
    lines = []
    for sid, label in (("iloilo", "Iloilo City"), ("lacarlota", "La Carlota")):
        days = h["stations"].get(sid, {}).get("days", {})
        parts = []
        for d, r in days.items():
            if d < asof: continue
            v = r.get("observed", r.get("forecast"))
            if v is not None:
                parts.append(f"{d[5:]} {v}C" + ("" if "observed" in r else "f"))
        if parts: lines.append(f"{label}: " + ", ".join(parts))
    il = h["stations"].get("iloilo", {}).get("days", {})
    today = il.get(asof, {}).get("observed")
    nxt = il.get(sorted(d for d in il if d > asof)[0], {}).get("forecast") if any(d > asof for d in il) else None
    body = "\n".join(lines)
    if today is not None: body += f"\nCPU today: {cpu(today)}"
    if nxt is not None: body += f"\nCPU tomorrow (forecast): {cpu(nxt)}"
    print(body)
    topic = os.environ.get("NTFY_TOPIC", "").strip()
    if not topic:
        print("no NTFY_TOPIC set; not sent"); return 0
    req = urllib.request.Request(f"https://ntfy.sh/{topic}", data=body.encode("utf-8"),
        headers={"Title": f"New PAGASA heat index for {asof}", "Priority": "high" if (today or 0) >= 42 or (nxt or 0) >= 42 else "default", "Tags": "thermometer"})
    urllib.request.urlopen(req, timeout=20); print("sent"); return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
