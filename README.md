# Royalty Radar

A self-serve tool for independent artists, labels and managers. It scans the audio
of content in the wild (UGC and ad audio, not just DSP catalogs) for AI-generated
music or vocals that may be cloned from a real artist's style, then acts on the
verdict:

| Verdict | Output |
|---|---|
| `human` | Certificate of human authorship |
| `ai` | Drafted consent-and-revenue-share outreach email to whoever posted it |
| anything else (`uncertain`, `suspicious`, `no_vocal`, unexpected) | Flagged for manual review. Never guessed on. |

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
# 1. (optional) pull audio out of a video
python extract_audio.py clip.mp4 extracted_audio.wav

# 2. the API needs a publicly reachable URL, not a local path. Serve the folder
#    and tunnel it, e.g. with cloudflared:
python -m http.server 8000
cloudflared tunnel --url http://localhost:8000

# 3. scan it
python detect.py https://<your-tunnel>.trycloudflare.com/extracted_audio.wav

# free test run against the API's mock scenarios (human, ai, suspicious, no_vocal)
python detect.py https://example.com/any.wav suspicious

# check a job without resubmitting
python check_job.py <job_id>
```

The first real scan has a ~20-30s cold start; polling times out after 180s.

## Files

```
detect.py         submit, poll, branch on verdict, log
extract_audio.py  ffmpeg wrapper: video -> WAV
check_job.py      look up an existing job_id
```

## Honesty about uncertainty

The tool only drafts outreach on a clear `ai` verdict. Mid-confidence and
unrecognised verdicts are routed to a person, and the review note says so rather
than implying an AI claim.
