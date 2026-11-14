"""Read the Iloilo City row from PAGASA's HeatIndexObserved.png.

Usage: python3 -I extract.py <image.png>
Step 1: find the "Iloilo City, Iloilo" row by OCR of the station column.
Step 2: OCR each of the 7 value cells on its own (digits only).
Layout is measured in fractions of image width/height so a rescaled image still works.
"""
import json
import re
import sys

import pytesseract
from PIL import Image

STATION = "Iloilo City"
LEVELS = [(52, "Extreme Danger"), (42, "Danger"), (33, "Extreme Caution"),
          (27, "Caution"), (0, "Not classified")]
SLOTS = ["d-4", "d-3", "d-2", "d-1", "d0", "fc+1", "fc+2"]

# Column edges as fractions of image width (measured on the 1442px-wide image)
X0, STEP = 735 / 1442, 99.4 / 1442
STATION_X = (326 / 1442, 735 / 1442)


def level(v):
    return next(n for lo, n in LEVELS if v >= lo)


def find_row(img):
    """Return (center_y, row_height) in pixels of the Iloilo City row."""
    W, H = img.size
    y0 = int(H * 0.12)
    crop = img.crop((int(W * STATION_X[0]), y0, int(W * STATION_X[1]), int(H * 0.97)))
    s = 3
    crop = crop.resize((crop.width * s, crop.height * s), Image.LANCZOS).convert("L")
    crop = crop.point(lambda p: 255 if p > 140 else 0)
    d = pytesseract.image_to_data(crop, config="--psm 6",
                                  output_type=pytesseract.Output.DICT)
    for i, t in enumerate(d["text"]):
        if re.fullmatch(r"[Il1|]lo[il1|]lo,?", t.strip(), re.I) or t.strip().lower().startswith("iloilo"):
            # require "City" on the same line to skip Dumangas / "Iloilo" in other places
            ln = (d["block_num"][i], d["par_num"][i], d["line_num"][i])
            same = [d["text"][j].lower() for j in range(len(d["text"]))
                    if (d["block_num"][j], d["par_num"][j], d["line_num"][j]) == ln]
            if any(w.startswith("city") for w in same):
                top = d["top"][i] / s + y0
                h = d["height"][i] / s
                return top + h / 2, h
    return None


def read_cell(img, x0, x1, yc, rh):
    box = (int(x0), int(yc - rh * 0.55), int(x1), int(yc + rh * 0.55))
    c = img.crop(box).convert("L")
    c = c.resize((c.width * 5, c.height * 5), Image.LANCZOS)
    # text is dark on a light/orange/yellow fill: threshold well below fill brightness
    c = c.point(lambda p: 255 if p > 90 else 0)
    pad = Image.new("L", (c.width + 60, c.height + 60), 255)
    pad.paste(c, (30, 30))
    txt = pytesseract.image_to_string(
        pad, config="--psm 7 -c tessedit_char_whitelist=0123456789")
    m = re.search(r"\d{2}", txt)
    return int(m.group()) if m else None


def extract(path):
    img = Image.open(path).convert("RGB")
    W, H = img.size
    head = pytesseract.image_to_string(
        img.crop((0, 0, W, int(H * 0.08))).resize((W * 2, int(H * 0.08) * 2)),
        config="--psm 6")
    m = re.search(r"As of\s+(\d{1,2}\s+\w+\s+\d{4})", head)
    out = {"as_of": m.group(1) if m else None, "station": STATION, "values": None}

    row = find_row(img)
    if row:
        yc, rh = row
        vals = []
        for k in range(7):
            x0 = (X0 + k * STEP) * W + 6
            x1 = (X0 + (k + 1) * STEP) * W - 6
            vals.append(read_cell(img, x0, x1, yc, rh))
        out["row_y"] = round(yc)
        if all(v is not None for v in vals):
            out["values"] = [{"slot": s, "hi_c": v, "level": level(v)}
                             for s, v in zip(SLOTS, vals)]
        else:
            out["raw"] = vals
    return out


if __name__ == "__main__":
    res = extract(sys.argv[1])
    print(json.dumps(res, indent=2))
    sys.exit(0 if res["values"] else 1)
