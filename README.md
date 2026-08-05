# apply-track

A local, single-user job hunt: one dashboard that shows where every application
stands and what needs you today, and a tailored resume behind each one.

**The dashboard is the app.** It answers three questions without you asking:

- **What needs me?** One action per job, most urgent first, each with a single
  button that resolves it — follow up, mark applied, export and send, add a job
  description. A job you have nothing to do about does not appear.
- **Where is everything?** A board with a column per stage. Drag a card to move
  it; the date it moved is recorded, so "twelve days in this stage" is real
  rather than remembered.
- **Is it working?** Applied, replies and reply rate across everything tracked.

Behind that:

1. **Parse a base resume** (once per resume). Upload a PDF or DOCX; its text is
   sent to the Claude Code CLI, which extracts the sections into JSON. You review
   and correct the result before anything is saved. This is the only fuzzy step.
2. **Compose a tailored resume** (once per job). Fork a base resume, then switch
   bullets and sections off, reorder them, reword them, and add capstone projects
   or one-off items. Export a PDF. Rendering JSON to a resume is fully
   deterministic — one template, same output every time.
3. **Prep, a project and an interview bank**, per job. See below.

Nothing here is a background job you have to manage. The analysis schedules
itself, the lesson catalogue refreshes itself, and the only page that mentions
any of it is Settings.

Runs on macOS and Windows.

## Pages

| Route | What it is |
| --- | --- |
| `/` | Dashboard — what needs you, the board, the numbers |
| `/jobs/:id` | One job: stage timeline, next step, description, prep, project, interview |
| `/jobs/:id/resume` | The composer, editor beside a live preview |
| `/material` | Base resumes and reusable items |
| `/settings` | CLI, model, Chromium, lesson catalogue, where the data lives |

## Prep

Lessons are indexed from a GitHub repo laid out as `content/<course>/NN-slug.md`
— by default [`applied-ml-academy`](https://github.com/humzaahmad906/applied-ml-academy),
changeable with `APPLY_TRACK_COURSE_REPO`. Only the repo's tree listing is
fetched, never the lesson files, and the index is cached in `data/courses.json`.
It refreshes itself on startup when it is missing or a fortnight old.

**There is no button.** Saving a job description or editing a tailored resume
schedules the comparison, and it runs about thirty seconds after you stop
typing. The composer autosaves every 1.2 seconds, so that quiet period is the
whole reason a long tailoring session costs one CLI call instead of hundreds;
each save pushes the deadline out rather than starting more work. A run is also
skipped outright when neither document has actually changed.

One call receives the JD, the resume being sent and the whole lesson catalogue.
**Every requirement the job states gets reading**, including the ones your
resume already proves — an interviewer goes deeper than a bullet does. The three
buckets say how well the resume answers each requirement, not who gets lessons:

- **Learn this** — the job wants it and the resume shows nothing.
- **Revise this** — the job wants it and the resume proves it, with the role or
  project named. Doubles as your list of bullets to switch on, and the lessons
  here are picked to go deeper than what you already demonstrated.
- **Foundations** — assumed for the role. Still worth a refresher before a call.

Two deliberate constraints:

- **The reading list never reaches the PDF.** It is a list of things you cannot
  yet claim; printing that would work against you.
- **Lesson titles and URLs come from the local index, never the model.** Cited
  paths are checked against the real catalogue and anything invented is dropped,
  so a hallucinated path cannot become a dead link.

Results are saved per application, so reopening a job is instant and free.

## A project worth building

For any job with a description and a tailored resume, **Project to build**
designs one. It first checks what you have already built: if something covers
most of the stack it produces a sharper angle on that (`reframe`), and if
nothing is close it specifies a new one (`design`).

Either way the output is a build plan, not resume copy — the problem stated in
that company's own domain, the architecture, an explicit map from every
requirement in the job description to the component that exercises it,
milestones sized in evenings and weekends, and what "done" looks like.

The resume bullets come last and carry placeholders like `<throughput>` where a
real measurement belongs. **A project can only be added to the resume once you
mark it built.** That is not bookkeeping: the interview bank below will drill
into anything on that resume, and a project you have not built has no second
answer in it.

## Interview prep

Generated from exactly two documents — the resume variant you actually sent and
the job description — because those are the two the interviewer has read.

- **Your resume**: every metric, benchmark and "led" claim, with the line it
  came from quoted back at you.
- **The stack**: one question per technology the job asks for.
- **System design** and **behavioural**, scoped to your seniority and drawn
  from situations your resume implies really happened.
- **Where you are exposed**: the handful of places this resume is weakest
  against this job. Blunt on purpose.
- **Ask them**: questions worth asking back, specific to the role.

Each question says what it is really testing and what a strong answer needs —
the shape of one, not words to recite. Editing the resume marks the bank out of
date, because it is then asking about a document you are no longer sending.

Both of these are buttons rather than background work: you build one project in
ten applications and you only prep for an interview you actually have.

## Portfolio

Once a project is marked built it can also go on
[the site](https://humzaahmad906.github.io/projects/). It writes one card into
`projects.html` in the same markup the page already uses, under Featured or
Earlier work, and **leaves it uncommitted** so the diff gets read before
anything is public.

Title, tags and description are all editable first, because the generated
wording is sized for a resume bullet rather than a portfolio card — and because
a card is public writing. Two guards:

- **Unfilled placeholders are refused.** `<throughput>` is a useful reminder on
  a resume and an embarrassment on a public page.
- **Tags do not default to the company you are applying to.** Tagging a
  personal project "Northbay" would imply the work was done for them; add the
  real organisation yourself when it belongs to a job.

Point `APPLY_TRACK_SITE` at the checkout; it defaults to
`~/humzaahmad906.github.io`.

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

To run a second copy against a throwaway database while the real one is up,
give the API its own port and data directory and point the web server at it:

```sh
cd api && APPLY_TRACK_DATA=/tmp/scratch .venv/bin/python -m uvicorn \
  apply_track.main:app --port 8011
cd web && APPLY_TRACK_API=http://127.0.0.1:8011 npm run dev -- --port 5199
```

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

**Status is a history, not a field.** An application stores where it is now;
every change also writes a `StageEvent`. That is where the timeline, days in
stage, reply rate and the follow-up rule all come from — none of it can be
reconstructed from a single current value. `applied_at` is stamped only on
reaching applied, screen, interview or offer, because being rejected off the
wishlist is not applying.

**One action per job.** The dashboard rules run in priority order and stop at
the first hit, so a job contributes at most one line to the queue. A queue
listing three things per job is a queue nobody reads. Snoozing a job silences
it entirely until the date passes.

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
| `APPLY_TRACK_COURSE_REPO` | `humzaahmad906/applied-ml-academy` | Repo the reading recommendations come from |
| `APPLY_TRACK_COURSE_BRANCH` | `main` | Branch to index |
| `APPLY_TRACK_GAP_TIMEOUT` | `420` | Seconds to allow one gap analysis |
| `APPLY_TRACK_AUTO_ANALYSE` | `1` | Set to `0` to make prep a manual step again |
| `APPLY_TRACK_ANALYSE_DELAY` | `30` | Quiet period, in seconds, before an edit triggers prep |
| `APPLY_TRACK_COURSE_MAX_AGE_DAYS` | `14` | How stale the lesson catalogue may get |
| `APPLY_TRACK_SITE` | `~/humzaahmad906.github.io` | Portfolio checkout a built project can be published into |

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
- **Reordering resume sections uses up/down buttons**, not drag and drop. The
  dashboard board does use drag; every card also has a `⋯` menu that moves it
  without one.
- **One tailored resume per job.** Two competing angles on the same posting
  would need two jobs.
- **Prep spends a CLI call** whenever a job description or resume genuinely
  changes. Set `APPLY_TRACK_AUTO_ANALYSE=0` to go back to pressing a button.
- **The section-kind list is fixed** (`experience`, `projects`, `education`,
  `skills`, `certifications`, `awards`, `publications`, `custom`). Anything else
  the model returns is mapped to `custom` rather than failing the parse.
- **Fonts** are limited to families present on both macOS and Windows (Georgia,
  Arial) so a variant renders the same on either machine.
- **Light by default**, with a dark toggle in the top bar. It follows your
  system preference the first time and remembers the choice after that.
- **A project only reaches the resume once you mark it built.**
