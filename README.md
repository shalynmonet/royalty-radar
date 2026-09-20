# Royalty Radar

A self-serve tool for independent artists, labels and managers. It scans the audio
of content in the wild (UGC and ad audio, not just DSP catalogs) for AI-generated
music or vocals that may be cloned from a real artist's style, then acts on the
verdict:

| Verdict | Output |
|---|---|
| `human` | Certificate of human authorship |
| `ai` at 80%+ confidence | Drafted consent-and-revenue-share outreach email to whoever posted it, written as an independent artist or as a label representative (`--sender artist` or `--sender label`, or the dropdown in the dashboard) |
| anything else (`uncertain`, `suspicious`, `no_vocal`, unexpected, or `ai` below 80% confidence) | Flagged for manual review. Never guessed on. |

Detection is done by the [HumanStandard](https://app.jobsbyhumans.com) API. Every
processed result is appended to `results_log.jsonl`.

## Setup

**Prerequisites:** Python 3.12+, and [ffmpeg](https://ffmpeg.org) if you want to
extract audio from video.

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt   # Windows
# .venv/bin/pip install -r requirements.txt     # macOS/Linux
```

Create a `.env` file (it is gitignored, never commit it):

```
HUMANSTANDARD_API_KEY=your_key_here
```

## Usage

```bash
# scan a local audio or video file. Video audio is extracted with ffmpeg first.
python detect.py path/to/song.mp3
python detect.py path/to/clip.mp4

# or a public URL
# (if you need one for a local file, serve it and tunnel it, e.g. with cloudflared)
python detect.py https://<your-tunnel>.trycloudflare.com/extracted_audio.wav

# several at once, one summary table
python scan_batch.py path/to/a.mp3 https://example.com/b.wav

# free test run against the API's mock scenarios (human, ai, suspicious, no_vocal)
python detect.py https://example.com/any.wav suspicious

# check a job without resubmitting
python check_job.py <job_id>
```

The first real scan has a ~20-30s cold start; polling times out after 180s.

## Dashboard

```bash
pip install -r requirements-ui.txt   # adds Streamlit; the core tool doesn't need it
streamlit run app.py
```

Views: **Check a track** (upload a file or paste a URL, with a mock mode that
costs no credits) **Listen** (record from the microphone and scan; the recorder sends audio over Streamlit's own connection instead of a separate upload request, which is meant to help behind cloud proxies that block uploads), and **Results** (everything in `results_log.jsonl`, including
scans run by an agent through `scan_batch.py`).

## Files

```
detect.py         submit, poll, branch on verdict, log
extract_audio.py  ffmpeg wrapper: video -> WAV (used automatically for video files)
check_job.py      look up an existing job_id
scan_batch.py     scan several sources, print one verdict table
test_routing.py   unit tests (standard library only)
outreach.py       outreach email drafts: independent artist or label representative
app.py            optional Streamlit dashboard
```

## Tests

```bash
python -m unittest -v   # routing, email drafts, polling, video detection; no network, no credits
```

## Honesty about uncertainty

The tool only drafts outreach on a confident `ai` verdict (`AI_OUTREACH_MIN_CONFIDENCE`, 80%). Mid-confidence and
unrecognised verdicts are routed to a person, and the review note says so rather
than implying an AI claim.

## License

MIT. See [LICENSE](LICENSE).
