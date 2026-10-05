"""Build docs/flow.html: inline the two architecture SVGs into flow_template.html (self-contained, no network).
Run after re-rendering the diagrams:  python3 docs/build_flow.py"""
import os, re

D = os.path.dirname(os.path.abspath(__file__))


def inline(name):
    s = open(os.path.join(D, name), encoding="utf-8").read()
    s = re.sub(r"<\?xml[^>]*\?>", "", s)
    s = re.sub(r"<!--.*?-->", "", s, flags=re.S)
    s = re.sub(r'\scontent="[^"]*"', "", s, count=1)  # drop the embedded draw.io payload (not needed to display)
    return s.strip()


html = open(os.path.join(D, "flow_template.html"), encoding="utf-8").read()
html = html.replace("__SVG_OBO__", inline("architecture.svg")).replace("__SVG_OAUTH__", inline("architecture-2lo-3lo.svg"))
open(os.path.join(D, "flow.html"), "w", encoding="utf-8").write(html)
print(f"wrote flow.html ({len(html)//1024} KB)")
