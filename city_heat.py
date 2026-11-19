"""Read Iloilo City CDRRMO heat index advisories (text) and keep them in city_heat.json.

Usage: python3 city_heat.py [saved_page.html]
Without an argument it downloads the page. Exits 0 even when nothing parses,
so a layout change on the city site never turns the whole run red.
"""
import json, re, sys, unicodedata, urllib.request
from html.parser import HTMLParser
from pathlib import Path

URL = "https://cdrrmo.iloilocity.gov.ph/fb-updates/heat-index-updates/"
OUT = Path("city_heat.json")
KEEP = 60


class Text(HTMLParser):
    def __init__(self):
        super().__init__(); self.out = []; self.skip = 0
    def handle_starttag(self, t, a):
        if t in ("script", "style"): self.skip += 1
        if t in ("br", "p", "div", "li", "article", "h1", "h2", "h3", "h4"): self.out.append("\n")
    def handle_endtag(self, t):
        if t in ("script", "style") and self.skip: self.skip -= 1
    def handle_data(self, d):
        if not self.skip: self.out.append(d)


def page_text(html):
    p = Text(); p.feed(html)
    # NFKC turns the bold Unicode letters used in the posts into plain letters
    return re.sub(r"[ \t ]+", " ", unicodedata.normalize("NFKC", "".join(p.out)))


def num(rx, s):
    m = re.search(rx, s, re.I)
    return float(m.group(1)) if m else None


def parse(text):
    heads = list(re.finditer(r"(\d{2})-(\d{2})-(20\d{2})", text))
    found = {}
    for i, h in enumerate(heads):
        chunk = text[h.start(): heads[i + 1].start() if i + 1 < len(heads) else len(text)]
        low = chunk.lower()
        if "heat index advisory" not in low:
            continue
        t = re.search(r"as of\s*(\d{1,2})(?::(\d{2}))?\s*(a\.?m|p\.?m|nn|noon)", chunk, re.I)
        hi = re.search(r"heat\s*index\D{0,20}?(\d{2})\s*°", chunk, re.I)
        if not (t and hi):
            continue
        hr, mn, ap = int(t.group(1)), int(t.group(2) or 0), t.group(3).lower().replace(".", "")
        if ap in ("nn", "noon"): hr = 12
        elif ap == "pm" and hr < 12: hr += 12
        elif ap == "am" and hr == 12: hr = 0
        mm, dd, yy = h.group(1), h.group(2), h.group(3)
        src = re.search(r"(weatherlink|accuweather|pagasa)", chunk, re.I)
        key = f"{yy}-{mm}-{dd}T{hr:02d}:{mn:02d}"
        found[key] = {
            "at": key,
            "hi": int(hi.group(1)),
            "temp": num(r"temp\w*\D{0,20}?(\d{2}(?:\.\d)?)\s*°", chunk),
            "rh": num(r"humidity\D{0,20}?(\d{1,3})\s*%", chunk),
            "uv": num(r"uv\s*(?:index)?\D{0,20}?(\d{1,2}(?:\.\d)?)", chunk),
            "src": src.group(1) if src else None,
        }
    return found


def main():
    if len(sys.argv) > 1:
        html = Path(sys.argv[1]).read_text(errors="ignore")
    else:
        req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
        html = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore")
    new = parse(page_text(html))
    print(f"parsed {len(new)} advisories")
    if not new:
        return 0
    old = json.loads(OUT.read_text()) if OUT.exists() else {"readings": []}
    merged = {r["at"]: r for r in old["readings"]}
    merged.update(new)
    readings = [merged[k] for k in sorted(merged)][-KEEP:]
    if readings != old["readings"]:
        OUT.write_text(json.dumps({"readings": readings}, indent=1))
        print("saved; latest", readings[-1])
    return 0


if __name__ == "__main__":
    sys.exit(main())
