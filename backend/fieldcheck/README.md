# fieldcheck

Dev-only tool to run the real eKYC AI pipeline against **your own real evidence**
(e.g. your own CCCD photo and a selfie video) and see what every capability
actually says - both as a one-off ad-hoc check and as a batch run over many
real entries with aggregate stats.

This is **not** `backend/benchmark/`. `benchmark/` is the M4-scoped, governed
benchmark over licensed/approved *distributable* datasets, gated by
`benchmark/datasets/registry.json`. `fieldcheck` is for a developer's own
consented, non-distributable evidence, run locally. Nothing here goes through
that dataset-approval gate, and nothing here should ever be committed.

It is a thin CLI around the same production code the real API uses -
`app.adapters.ekyc_providers.build_capability_registry` and
`app.adapters.analyzer.OfflineModelAnalyzer` - so results are exactly what the
real pipeline would produce, with no DB/HTTP/session involved.

## At a glance

```
fieldcheck/
├── local_cases/                <- evidence goes IN here (gitignored)
│   ├── my-cccd/                   one case = one subdirectory,
│   │   ├── document_front.jpg        however many files inside it
│   │   ├── document_back.jpg
│   │   └── selfie_video.mp4       (optional)
│   └── another-person/            a second case = another subdirectory
│       ├── document_front.jpg
│       └── document_back.jpg
└── local_runs/                 <- results come OUT here (gitignored)
    ├── adhoc-my-cccd-<timestamp>.json
    └── <timestamp>/summary.json
```

- **One case folder** (however many files are inside it) -> `adhoc --case
  fieldcheck/local_cases/my-cccd`: runs that one case, prints/saves one
  result.
- **Multiple case folders** -> `batch --cases-root fieldcheck/local_cases`:
  discovers and runs every subdirectory found under the root, writes one
  aggregated summary. There's no separate "bulk" location - it's the same
  `local_cases/` tree, `batch` just points at the parent instead of one leaf.

Everything below fills in the exact rules (recognized filenames, `case.json`,
flags) - the tree above is the shape to hold in your head first.

## Handling real evidence safely

- `local_cases/` and `local_runs/` are both gitignored (only `.gitkeep` is
  committed). Drop your case directories under `local_cases/`; run output
  defaults to `local_runs/`.
- `--out`/`--out-dir` refuse to write anywhere else inside the repo unless you
  pass `--force`. Prefer pointing them outside the repo entirely if you want
  to keep results longer-term.
- Never commit a case directory, a run's JSON output, or share it outside
  people authorized to see your real evidence.

## Case directory layout

One case = one directory. Recognized filenames (case-insensitive stem match,
suffix picks the content type):

| file | evidence_type | suffixes |
|---|---|---|
| `document_front.*` | `DOCUMENT_FRONT` | `.jpg` `.jpeg` `.png` `.webp` |
| `document_back.*` | `DOCUMENT_BACK` | `.jpg` `.jpeg` `.png` `.webp` |
| `passport_page.*` | `PASSPORT_PAGE` | `.jpg` `.jpeg` `.png` `.webp` |
| `selfie_video.*` | `SELFIE_VIDEO` | `.mp4` `.webm` `.mov` |

`document_type` is auto-detected: `passport_page` present -> `PASSPORT_TD3`;
`document_front`/`document_back` present -> `CCCD`. Having both is ambiguous
and requires an explicit override.

`selfie_video` is optional. If it's absent, `fieldcheck` runs OCR/layout/MRZ
only (`analyze_document()`) instead of the full 13-capability pipeline
(`analyze()`) - useful for a quick "just check my ID photo" case.

`backend/benchmark/`'s `voice_challenge` and `lip_sync` runners
(`python -m benchmark.cli run --capability voice_challenge|lip_sync`) reuse
this same `local_cases/` directory - one real-evidence source for both
tools, not two. See those runners' module docstrings for details.

The selfie video's own audio track is what the voice-challenge check
transcribes - there's no separate audio evidence type. Record what digits you
actually said and put them in `case.json`'s `voice_challenge` (or pass
`--voice-challenge` on `adhoc`), otherwise it will just report a mismatch.

### `case.json` (optional)

```json
{
  "document_type": "CCCD",
  "voice_challenge": "1 2 3 4 5 6",
  "expected": {
    "face_match": "SCORE_AVAILABLE",
    "liveness": "SCORE_AVAILABLE"
  },
  "notes": "free text, ignored by the tool"
}
```

`expected` is optional and only used for informational scoring in `batch`
reports (see below) - never a pass/fail gate, since no capability in this
pipeline has an approved decision threshold yet.

## Usage

Both subcommands must be run from `backend/` - `fieldcheck` and its `.venv`
live there, and `--model-dir`/`--cases-root` default to paths relative to it.

### `adhoc`: run one case

`adhoc` runs a single case directory through the pipeline and prints/saves
one result.

```
cd backend
uv run python -m fieldcheck.cli adhoc --case fieldcheck/local_cases/<case-name> --model-dir ../models
```

`--case` is the case directory to run (see "At a glance" above for the
expected layout); `--model-dir` is the path to this project's model
artifacts, constant across runs. The result prints to stdout and is also
saved as a timestamped file under `local_runs/`.

### `batch`: run every case under a directory

`batch` discovers every case directory under `--cases-root` and runs them
all, then writes one summary aggregated across every case.

```
cd backend
uv run python -m fieldcheck.cli batch --cases-root fieldcheck/local_cases --model-dir ../models
```

`--cases-root` takes the *parent* directory containing case directories,
not a single case directory.

Running `batch` against an empty `local_cases/` also doubles as a
standalone readiness check, with no evidence required - it prints the
model-readiness table before it looks for any cases. A `--cases-root` that
doesn't exist at all isn't handled cleanly yet: it prints a raw traceback
after the readiness table instead of an error message.

### Flag reference

Every flag `adhoc` and `batch` accept, and what each does.

**`adhoc`**

| flag | default | description |
|---|---|---|
| `--case <path>` | required | The case directory to run. |
| `--model-dir <path>` | `../models` | Path to the model artifacts directory. |
| `--profile <name>` | `technical_demo` | Deployment profile controlling provider/model gating - `technical_demo` is the only profile this project currently defines. |
| `--document-type <type>` | auto-detected | Overrides the document type detected from the case's evidence files (`CCCD` or `PASSPORT_TD3`). Required when a case ambiguously contains both a passport page and CCCD front/back; otherwise only needed to override `case.json`. |
| `--voice-challenge <digits>` | from `case.json` | Overrides `case.json`'s `voice_challenge` field - the digits actually spoken in the selfie video. Without a correct value here, the `voice_challenge` capability reports a mismatch regardless of what the video contains. |
| `--out <path>` | timestamped file under `local_runs/` | Where to write the result JSON. |
| `--json` | off | Also print the full result JSON to stdout, in addition to the summary. |
| `--force` | off | Allow writing output inside the git repository, outside `local_runs/`. See "Handling real evidence safely" above for why this is guarded. |

**`batch`**

| flag | default | description |
|---|---|---|
| `--cases-root <path>` | `local_cases/` | The directory containing one subdirectory per case. |
| `--pattern <glob>` | `*` | Restricts which case directories are picked up, matched against each directory's name (e.g. `'my-*'`). |
| `--fail-fast` | off | Stop after the first case that fails to load or run, instead of continuing through the rest. |
| `--out-dir <path>` | timestamped directory under `local_runs/` | Where to write the summary, and (with `--save-per-case`) each case's individual result. |
| `--save-per-case` | off | Also write each case's full result JSON, not just the aggregated summary. |
| `--model-dir`, `--profile`, `--force` | same as `adhoc` | See above. |

`batch`'s summary report walks every result's normalized contract shape
generically (any dict carrying an `execution_status` key becomes a "signal"),
so it covers whatever capabilities/sub-signals a case's evidence exercised -
including nested ones like `ocr.documents.document_front.mrz_validation` -
without hardcoding a capability list that could drift from the real contract.
