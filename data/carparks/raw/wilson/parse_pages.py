"""Parse cached Wilson location detail pages into intermediate structured blocks."""
import json, os, re, sys
from bs4 import BeautifulSoup

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fetch  # cache-only use here (pages already cached)

P = "https://www.wilsonparking.com.au"


def clean(s):
    return re.sub(r"\s+", " ", (s or "").replace("\xa0", " ")).strip()


def parse_blocks(s):
    out = []
    for it in s.select(".accordionBlock-item"):
        name = it.select_one(".item-name")
        if not name:
            continue
        content = it.select_one(".accordionBlock-item-content")
        hdr, rows, notes = [], [], []
        if content:
            for d in content.find_all("div", recursive=False):
                cls = d.get("class") or []
                if "parkingServiceBlock-timelist" in cls:
                    for r in d.find_all("div", recursive=False):
                        lab = r.select_one(".flex-1")
                        vals = [clean(v.get_text()) for v in r.select(".cell-w")]
                        rows.append([clean(lab.get_text()) if lab else "", vals])
                elif "d-flex" in cls and not hdr and not rows:
                    hdr = [clean(v.get_text()) for v in d.select(".cell-w")]
                else:
                    n = clean(d.get_text(" "))
                    if n:
                        notes.append(n)
        summ = it.select_one(".accordionBlock-item-summary")
        out.append(dict(name=clean(name.get_text()), summary=clean(summ.get_text()) if summ else None,
                        hdr=hdr, rows=rows, notes=" ".join(notes)))
    return out


def parse_page(html):
    s = BeautifulSoup(html, "lxml")
    d = {"blocks": parse_blocks(s)}
    txt = clean(s.get_text(" "))
    m = re.search(r"Entry:\s*(.{0,160}?)\s*(?:gallery|Get Directions)", txt)
    d["entry_text"] = m.group(1) if m else None
    m = re.search(r"Online from:\s*\$([\d.,]+)", txt)
    d["online_from"] = float(m.group(1).replace(",", "")) if m else None
    # monthly products
    mp = []
    for m in re.finditer(r"(Unreserved parking|Reserved parking)\s+(.{0,60}?)\s+(\$[\d.,]+/day\*?)?\s*(\$[\d.,]+/month)?", txt):
        if m.group(3) or m.group(4):
            mp.append({"product": m.group(1), "per_day": m.group(3), "per_month": m.group(4)})
    d["monthly"] = mp
    # capacity / spaces mentions
    caps = re.findall(r"(\d[\d,]*)\s*(?:car\s*)?(?:parking\s*)?(?:spaces|bays|car parks)\b", txt, flags=re.I)
    d["capacity_mentions"] = caps
    d["ev_mentions"] = re.findall(r".{0,80}(?:EV charg|electric vehicle).{0,80}", txt, flags=re.I)
    d["accessible_mentions"] = re.findall(r".{0,60}(?:disabled|accessible|PWD).{0,60}", txt, flags=re.I)
    return d


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    cps = json.load(open(os.path.join(here, "api_bne_subset.json")))
    out = {}
    for c in cps:
        h = fetch.fetch(P + c["url"])
        out[c["url"]] = parse_page(h) if h else None
    json.dump(out, open(os.path.join(here, "parsed_pages.json"), "w"), indent=1)
    print(len(out))
