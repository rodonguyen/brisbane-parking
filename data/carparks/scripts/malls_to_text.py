#!/usr/bin/env python3
"""Convert cached raw mall pages to plain text (for manual/assisted extraction).
Output: $OUT (default ../raw/malls_text/) <id>__<n>.txt
"""
import os, sys, glob, subprocess
from bs4 import BeautifulSoup

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.normpath(os.path.join(HERE, "..", "raw", "malls"))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.normpath(os.path.join(HERE, "..", "raw", "malls_text"))
os.makedirs(OUT, exist_ok=True)


def totext(p):
    b = open(p, "rb").read()
    if b[:4] == b"%PDF":
        r = subprocess.run(["pdftotext", "-layout", p, "-"], capture_output=True, text=True)
        return r.stdout
    s = BeautifulSoup(b, "lxml")
    for t in s(["script", "style", "noscript", "svg"]):
        t.decompose()
    out, prev = [], None
    for l in s.get_text("\n").split("\n"):
        l = " ".join(l.split())
        if l and l != prev:
            out.append(l)
        prev = l
    return "\n".join(out)


for p in sorted(glob.glob(RAW + "/*.html")):
    t = totext(p)
    open(os.path.join(OUT, os.path.basename(p)[:-5] + ".txt"), "w").write(t)
    print(os.path.basename(p), len(t))
