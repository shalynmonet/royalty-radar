# Royalty Radar: agent instructions

Scans audio for AI-generated music or cloned vocals (via the HumanStandard API)
and acts on the verdict. The user is an independent artist, label or manager.

## Running scans

- Single track: `python detect.py <public_audio_url>`
- Several tracks: `python scan_batch.py <url> [<url> ...]`
- Free test run, no credits spent: add a mock scenario, one of
  `human`, `ai`, `suspicious`, `no_vocal` (`python detect.py <url> ai`,
  `python scan_batch.py --mock ai <url>`)
- Sources can be a public audio URL or a local file path (uploaded directly).
  Streaming-service page links (Spotify, YouTube) are not audio files and will
  not work.
- Video source: `python extract_audio.py <video> out.wav`, then scan the WAV

Real scans cost 1 credit each from a shared pool of 200. Use mock scenarios
unless the user asks for a real scan, and never rescan a URL that already has an
entry in `results_log.jsonl` without asking.

## Verdict rules (do not change)

- `human` -> certificate of authorship
- `ai` -> drafted consent-and-revenue-share outreach email
- anything else (`uncertain`, `suspicious`, `no_vocal`, unexpected) -> flag for
  manual review. Never send or draft outreach on these, and never describe them
  as confirmed AI.

Outreach is only ever drafted, never sent.

## Reporting back

For each track say the verdict, confidence, what was produced, and why. Be plain
about uncertainty.

## Secrets

`HUMANSTANDARD_API_KEY` lives in `.env` (gitignored). Never print it, commit it,
or paste it into output.
