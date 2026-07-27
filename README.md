# apply-track

A local, single-user web app for tracking job applications and building a
tailored resume for each one.

Two flows:

1. **Parse a base resume** (once per resume). Upload a PDF or DOCX; its text is
   sent to the Claude Code CLI, which extracts the sections into JSON. You review
   and correct the result before anything is saved. This is the only fuzzy step.
2. **Compose a tailored resume** (the main flow, once per application). Fork a
   base resume into a variant, then switch bullets and sections off, reorder
   them, reword them, and add capstone projects or one-off items. Export a PDF.
   Rendering JSON to a resume is fully deterministic — one template, same output
   every time.

Runs on macOS and Windows.

## Requirements

- **Python 3.11+**
- **Node 18+**
- **Claude Code CLI**, installed and logged in. Run `claude` once interactively
  to authenticate. Parsing uses your existing subscription, so no
  `ANTHROPIC_API_KEY` is needed.

## Install

```sh
git clone git@github.com:humzaahmad906/apply-track.git
cd apply-track
python install.py
```

On Windows use `python` (or `py`) in PowerShell; the script handles the
platform differences itself.

`install.py` creates the API venv, installs Python and npm dependencies, and
downloads the Chromium build used for PDF export (~130 MB). If that last
download fails, everything else still works — see
[PDF export](#pdf-export) below.

## Run

```sh
python dev.py
```

- web: <http://localhost:5173>
- api: <http://127.0.0.1:8000> (docs at `/docs`)

Or start the two halves yourself:

```sh
# macOS / Linux
cd api && .venv/bin/python -m uvicorn apply_track.main:app --reload --port 8000
cd web && npm run dev

# Windows (PowerShell)
cd api; .venv\Scripts\python -m uvicorn apply_track.main:app --reload --port 8000
cd web; npm run dev
```

Data lives in `data/` at the repo root: `apply_track.db` (SQLite), plus
`uploads/` and `exports/`. It is gitignored. Back it up by copying the folder.

## How it works

```
resume.pdf ──> text ──> claude -p ──> ResumeJSON ──> you review ──> Resume (base)
                        (fuzzy)                                        │
                                                                  fork │ snapshot
                                                                       ▼
Application ─────────────────────────────────────────────────────> Variant
                                                                       │
                                             toggles / reorder / capstones
                                                                       ▼
                                              one Jinja template ──> HTML ──> PDF
                                                    (deterministic)
```

**Fuzzy in, deterministic out.** The model only ever extracts sections into
JSON. Everything after that — resolving which items are switched on, ordering,
layout, the PDF — is plain code, so the same JSON always produces the same
resume.

**A variant is a snapshot, not a diff.** Forking copies the whole base resume
into the variant. Editing a base resume afterwards does *not* rewrite variants
you already sent, and deleting a base resume leaves them intact. The trade-off
is deliberate: a resume you have already sent must not change under you.

**The preview cannot drift from the PDF.** `GET /api/variants/{id}/preview`
returns the exact HTML the PDF is rendered from, and the composer displays that
in an iframe. One template feeds both.

**Nothing on argv.** The whole prompt, resume text included, goes to
`claude -p` over stdin. That keeps content off the command line, which also
means the Windows `cmd /c` shim for npm-installed `claude.cmd` has nothing to
mis-quote.

## PDF export

PDF export uses the Chromium that ships with Playwright, so output is the same
on macOS and Windows rather than depending on system fonts and libraries.

If Chromium is missing, `Export PDF` returns a 503 with instructions and the app
tells you so in the header. You can still open the preview in a new tab and
print to PDF from the browser. To install it later:

```sh
# macOS / Linux
cd api && .venv/bin/python -m playwright install chromium
# Windows
cd api; .venv\Scripts\python -m playwright install chromium
```

## Configuration

Environment variables, all optional:

| Variable | Default | Purpose |
| --- | --- | --- |
| `APPLY_TRACK_MODEL` | `claude-opus-5` | Model used for extraction |
| `APPLY_TRACK_CLAUDE_BIN` | *(found on PATH)* | Full path to the `claude` binary |
| `APPLY_TRACK_PARSE_TIMEOUT` | `240` | Seconds to allow one parse |
| `APPLY_TRACK_DATA` | `./data` | Where the DB, uploads and exports live |

## Tests

```sh
# macOS / Linux
cd api && .venv/bin/python -m pytest -q
# Windows
cd api; .venv\Scripts\python -m pytest -q
```

The CLI is stubbed in tests, so they are offline and deterministic — no model
calls, no network.

## Notes and limits

- **No auth, single user.** Bind it to localhost. Do not expose it to a network.
- **Parse cost.** Each parse sends the Claude Code system prompt plus your
  resume, so a call reports a few cents of notional usage and takes a few
  seconds. Fine for personal use; not built for multi-tenant volume.
- **Reordering uses up/down buttons**, not drag and drop.
- **The section-kind list is fixed** (`experience`, `projects`, `education`,
  `skills`, `certifications`, `awards`, `publications`, `custom`). Anything else
  the model returns is mapped to `custom` rather than failing the parse.
- **Fonts** are limited to families present on both macOS and Windows (Georgia,
  Arial) so a variant renders the same on either machine.
