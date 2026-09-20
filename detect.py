import os
import sys
import time
import json
import tempfile
import requests
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

import extract_audio
from outreach import generate_outreach_email, usable_origin

load_dotenv()

BASE_URL = "https://app.jobsbyhumans.com"
API_KEY = os.environ["HUMANSTANDARD_API_KEY"]
HEADERS = {"Authorization": f"Bearer {API_KEY}"}
LOG_FILE = Path(__file__).resolve().parent / "results_log.jsonl"

# Outreach is only drafted for an "ai" verdict at or above this confidence. Anything
# lower goes to a person: an email accusing someone must not rest on a shaky verdict.
AI_OUTREACH_MIN_CONFIDENCE = 0.80


def submit_track(source, mock=None):
    """Submit a public audio URL, or a local file path (uploaded directly).

    A local video file has its audio extracted first (needs ffmpeg).
    """
    if os.path.isfile(source) and extract_audio.is_video(source):
        with tempfile.TemporaryDirectory() as tmp:
            wav = os.path.join(tmp, Path(source).stem + ".wav")
            extract_audio.extract_audio(source, wav)
            return submit_track(wav, mock=mock)

    params = {"mock": mock} if mock else {}
    if os.path.isfile(source):
        with open(source, "rb") as f:
            response = requests.post(
                f"{BASE_URL}/api/analyze",
                headers=HEADERS,
                params=params,
                files={"file": (os.path.basename(source), f)},
                timeout=300,
            )
    else:
        response = requests.post(
            f"{BASE_URL}/api/analyze",
            headers=HEADERS,
            params=params,
            json={"url": source},
            timeout=60,
        )
    response.raise_for_status()
    return response.json()["job_id"]


def poll_job(job_id, timeout=180, interval=3):
    start = time.time()
    while time.time() - start < timeout:
        try:
            response = requests.get(
                f"{BASE_URL}/api/jobs/{job_id}/status",
                headers=HEADERS,
                timeout=30
            )
            if response.status_code < 500:
                response.raise_for_status()  # 4xx (bad key, unknown job) is not transient
                data = response.json()
            else:
                data = {"status": f"server error {response.status_code}"}
        except (requests.ConnectionError, requests.Timeout):
            data = {"status": "network error"}
        status = data.get("status")
        if status == "complete":
            return data["result"]
        elif status == "failed":
            raise RuntimeError(f"Job failed: {data}")
        print(f"Status: {status}, waiting...")
        time.sleep(interval)
    raise TimeoutError(f"Job {job_id} did not complete within {timeout}s")


def generate_certificate(result):
    summary = (result.get("origin_map") or {}).get("summary_line")
    evidence = summary or (
        "No reference-recording evidence returned. Based on full-mix analysis only; "
        "this does not confirm the track contains vocals or verify authorship."
    )
    return (
        f"CERTIFICATE OF HUMAN AUTHORSHIP\n"
        f"Verdict: {str(result.get('verdict')).upper()} ({(result.get('confidence') or 0)*100:.1f}% confidence)\n"
        f"Evidence: {evidence}\n"
        f"Model: {result.get('model_version')}\n"
        f"Processed: {result.get('processed_at')}"
    )


def generate_review_flag(result):
    verdict = str(result.get("verdict")).upper()
    confidence = (result.get("confidence") or 0) * 100
    origin = usable_origin(result)
    origin_line = f" Possible origin: {origin}." if origin else ""
    if result.get("verdict") == "ai":
        headline = (
            f"VERDICT 'AI' AT LOW CONFIDENCE ({confidence:.1f}%): flagged for manual review. "
            f"The detector labeled this AI but is not confident, so no outreach was drafted."
        )
    else:
        headline = f"VERDICT '{verdict}': flagged for manual review, not a confirmed AI claim."
    return (
        f"{headline}\n"
        f"Confidence: {confidence:.1f}%.{origin_line}\n"
        f"This result is not a clear human or AI call and should be reviewed by a person "
        f"before any outreach or action is taken."
    )


def handle_result(source_file, result, sender="artist", job_id=None):
    verdict = result.get("verdict")
    confident_ai = verdict == "ai" and (result.get("confidence") or 0) >= AI_OUTREACH_MIN_CONFIDENCE
    if verdict == "human":
        output_type = "certificate"
        content = generate_certificate(result)
    elif confident_ai:
        output_type = "outreach"
        content = generate_outreach_email(result, sender=sender)
    else:
        # uncertain, suspicious, no_vocal, a low-confidence "ai", or anything unexpected:
        # never guess, and never accuse anyone on a shaky verdict.
        output_type = "review"
        content = generate_review_flag(result)

    print("\n" + "=" * 50)
    print(content)
    print("=" * 50 + "\n")

    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source_file": source_file,
        "verdict": verdict,
        "confidence": result.get("confidence"),
        "origin": result.get("origin"),
        "job_id": job_id,
        "ai_probability": result.get("ai_probability"),
        "confidence_full_mix": result.get("confidence_full_mix"),
        "output_type": output_type,
        "sender": sender if output_type == "outreach" else None,
        "content": content,
    }
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry) + "\n")

    return output_type, content


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python detect.py <public_file_url> [mock_scenario]")
        sys.exit(1)

    file_url = sys.argv[1]
    mock_scenario = sys.argv[2] if len(sys.argv) > 2 else None

    job_id = submit_track(file_url, mock=mock_scenario)
    print(f"Job submitted: {job_id}")
    result = poll_job(job_id)
    handle_result(file_url, result, job_id=job_id)
