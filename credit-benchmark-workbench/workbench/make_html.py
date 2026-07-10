"""Generate a standalone workbench.html from the (baked) JSX artifact.

The HTML loads React 18 UMD and Babel standalone from CDN (network needed
when the file is opened) and inlines the same JSX source, so the .html and
.jsx artifacts cannot drift: re-run this after every re-bake.
"""

from pathlib import Path

HERE = Path(__file__).parent
JSX = HERE / "CreditBenchmarkWorkbench.jsx"
OUT = HERE / "workbench.html"

src = JSX.read_text()
src = src.replace('import React, { useMemo, useState } from "react";',
                  "const { useMemo, useState } = React;")
src = src.replace("export default function CreditBenchmarkWorkbench",
                  "function CreditBenchmarkWorkbench")
assert "</script" not in src.lower(), "JSX would break the inline script tag"

html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Commercial Credit Benchmark Workbench</title>
<script crossorigin src="https://unpkg.com/react@18/umd/react.production.min.js"></script>
<script crossorigin src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js"></script>
<script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
<style>body {{ margin: 0; }}</style>
</head>
<body>
<div id="root"></div>
<script type="text/babel" data-presets="react">
{src}
ReactDOM.createRoot(document.getElementById("root")).render(<CreditBenchmarkWorkbench />);
</script>
</body>
</html>
"""
OUT.write_text(html)
print(f"wrote {OUT} ({OUT.stat().st_size / 1024:.0f} KB)")
