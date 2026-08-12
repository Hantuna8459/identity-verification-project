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

```
python -m fieldcheck.cli adhoc --case backend/fieldcheck/local_cases/my-test \
    [--model-dir PATH] [--profile technical_demo] \
    [--document-type CCCD] [--voice-challenge "1 2 3 4 5 6"] \
    [--out PATH] [--json]

python -m fieldcheck.cli batch --cases-root backend/fieldcheck/local_cases \
    [--model-dir PATH] [--profile technical_demo] [--pattern 'my-*'] \
    [--fail-fast] [--out-dir PATH] [--save-per-case] [--force]
```

Both subcommands print `.readiness()` first, so you know upfront which
capabilities will actually run vs. report `UNAVAILABLE` for this
`--model-dir`/`--profile`.

`batch`'s summary report walks every result's normalized contract shape
generically (any dict carrying an `execution_status` key becomes a "signal"),
so it covers whatever capabilities/sub-signals a case's evidence exercised -
including nested ones like `ocr.documents.document_front.mrz_validation` -
without hardcoding a capability list that could drift from the real contract.
