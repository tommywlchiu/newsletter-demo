# brand/

The KittyNews identity. **`brand.json` is the single source of truth** — the logo, this
sheet, every infographic and the email shell all render from it. Nothing hardcodes a colour.

## Files

| File | What it is |
| --- | --- |
| `brand.json` | Palette, type, layout, chart ramp, voice. Edit this, never the PNGs. |
| `_mark.svg.j2` | The cat mark geometry, as a Jinja macro. Imported by everything that draws it — never copy the paths. |
| `logo.html.j2` | The lockup. `variant`: `primary` \| `dark` \| `mark`. |
| `guidelines.html.j2` | The brand board. |
| `*.png` | **Generated.** Never hand-edit — your change is lost on the next render. |

## Regenerating

After any change to `brand.json` or a template, re-run all four:

```bash
PY=.venv/Scripts/python.exe   # Windows; use .venv/bin/python elsewhere

$PY tools/render_png.py --template brand/logo.html.j2 --out brand/logo.png       --data '{"variant":"primary"}' --scale 3
$PY tools/render_png.py --template brand/logo.html.j2 --out brand/logo-dark.png  --data '{"variant":"dark"}'    --scale 3
$PY tools/render_png.py --template brand/logo.html.j2 --out brand/logo-mark.png  --data '{"variant":"mark"}'    --scale 3
$PY tools/render_png.py --template brand/guidelines.html.j2 --out brand/guidelines.png --scale 2 --width 1100 --colors 128 --opaque
```

## Rules worth not relearning

- **`marmalade` (#E8743B) is barred from text.** It measures 2.91:1 on paper — below even
  the 3:1 large-text bar. Use `marmalade_deep` (#A8481A, 5.63:1) for any accent that is
  text. This is enforced by nothing but attention, so check it.
- **Charts must label values directly.** Slot 1 sits at 2.55:1 on sand, which is legal only
  with a relief channel. Direct labels are that channel.
- **Assets are PNG, never SVG.** Outlook for Windows renders no SVG at all.
- **Dark mode doesn't touch the graphics.** Gmail and Outlook invert HTML backgrounds but
  not images, so the ramp only ever meets the sand ground baked into each PNG. That is why
  it is validated in light mode alone.
- **The palette is derived, not chosen.** It came out of a brute-force search scored by the
  `dataviz` skill's `validate_palette.js`. Before changing any chart colour, re-run:

  ```bash
  node <dataviz-skill>/scripts/validate_palette.js \
    "#E8743B,#149184,#C0453A,#3D7AB8,#4E7A2F" --mode light --surface "#F5EBDF"
  ```

  See `_provenance` in `brand.json` for the full record.
