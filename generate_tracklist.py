#!/usr/bin/env python3
"""Generate a printable HTML track list from music_mappings.json.
Edit HEADING below, then run:  python3 generate_tracklist.py"""

import json
from pathlib import Path

# ── Customise here ───────────────────────────────────────────────────────────
HEADING = "Newton's Jukebox"
OUTPUT_FILE = "tracklist.html"
# ─────────────────────────────────────────────────────────────────────────────

script_dir = Path(__file__).parent

with open(script_dir / "music_mappings.json") as f:
    music_map = json.load(f)

with open(script_dir / "config_sonos.json") as f:
    config = json.load(f)

sorted_entries = sorted(music_map.items(), key=lambda x: int(x[0]))

key_bindings = config.get("key_bindings", {})
controls_html = "  ".join(
    f"<span><strong>{key.replace('KEY_', '')}</strong> = {action.capitalize()}</span>"
    for key, action in key_bindings.items()
)

cards = []
for number, entry in sorted_entries:
    title = entry.get("title", "")
    filename = entry.get("filename", "")
    img_tag = (
        f'<img src="trackart/{filename}" alt="{title}">'
        if filename
        else '<div class="no-art"></div>'
    )
    cards.append(f"""
    <div class="card">
      <div class="number">{number}</div>
      {img_tag}
      <div class="title">{title}</div>
    </div>""")

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{HEADING}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}

  body {{
    font-family: 'Helvetica Neue', Arial, sans-serif;
    background: #f5f5f5;
    padding: 24px;
  }}

  h1 {{
    text-align: center;
    font-size: 2rem;
    margin-bottom: 28px;
    color: #1a1a1a;
  }}

  .grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
    gap: 16px;
    max-width: 1000px;
    margin: 0 auto;
  }}

  .card {{
    background: white;
    border-radius: 10px;
    padding: 16px;
    text-align: center;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 10px;
  }}

  .number {{
    background: #1DB954;
    color: white;
    font-size: 1.5rem;
    font-weight: 700;
    width: 48px;
    height: 48px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }}

  .card img {{
    width: 148px;
    height: 148px;
    object-fit: cover;
    border-radius: 6px;
  }}

  .no-art {{
    width: 148px;
    height: 148px;
    background: #eee;
    border-radius: 6px;
  }}

  .title {{
    font-size: 0.85rem;
    color: #333;
    line-height: 1.4;
  }}

  .controls {{
    text-align: center;
    margin: 0 auto 28px;
    max-width: 1000px;
    padding: 12px 20px;
    background: white;
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    font-size: 0.95rem;
    color: #555;
    display: flex;
    justify-content: center;
    flex-wrap: wrap;
    gap: 16px;
  }}

  .controls strong {{
    color: #1DB954;
    font-size: 1rem;
  }}

  @media print {{
    body {{ background: white; padding: 8px; }}
    .card {{ box-shadow: none; border: 1px solid #ddd; break-inside: avoid; }}
    .controls {{ box-shadow: none; border: 1px solid #ddd; }}
  }}
</style>
</head>
<body>
<h1>{HEADING}</h1>
<div class="controls">{controls_html}</div>
<div class="grid">{''.join(cards)}
</div>
</body>
</html>"""

output_path = script_dir / OUTPUT_FILE
output_path.write_text(html, encoding="utf-8")
print(f"Generated {OUTPUT_FILE} with {len(sorted_entries)} tracks.")
print(f"Open in a browser, or print to PDF via File → Print.")
