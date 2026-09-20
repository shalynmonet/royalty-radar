import os
import sys
import time
import json
import requests
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://app.jobsbyhumans.com"
API_KEY = os.environ["HUMANSTANDARD_API_KEY"]
HEADERS = {"Authorization": f"Bearer {API_KEY}"}
LOG_FILE = "results_log.jsonl"


def submit_track(source, mock=None):
    """Submit a public audio URL, or a local file path (uploaded directly)."""
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
        response = requests.get(
            f"{BASE_URL}/api/jobs/{job_id}/status",
            headers=HEADERS,
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        status = data.get("status")
        if status == "complete":
            return data["result"]
        elif status == "failed":
            raise RuntimeError(f"Job failed: {data}")
        print(f"Status: {status}, waiting...")
        time.sleep(interval)
    raise TimeoutError(f"Job {job_id} did not complete within {timeout}s")


def generate_certificate(result):
    evidence = result.get("origin_map", {}).get("summary_line", "No detailed evidence available.")
    return (
        f"CERTIFICATE OF HUMAN AUTHORSHIP\n"
        f"Verdict: {result['verdict'].upper()} ({result['confidence']*100:.1f}% confidence)\n"
        f"Evidence: {evidence}\n"
        f"Model: {result.get('model_version')}\n"
        f"Processed: {result.get('processed_at')}"
    )


def generate_review_flag(result):
    confidence = result.get("confidence", 0) * 100
    origin = result.get("origin")
    origin_line = f" Possible origin: {origin}." if origin else ""
    return (
        f"VERDICT '{str(result.get('verdict')).upper()}': flagged for manual review, "
        f"not a confirmed AI claim.\n"
        f"Confidence: {confidence:.1f}%.{origin_line}\n"
        f"This result is not a clear human or AI call and should be reviewed by a person "
        f"before any outreach or action is taken."
    )


def generate_outreach_email(result):
    origin = result.get("origin", "an AI model")
    confidence = result.get("confidence", 0) * 100
    return (
        f"Hi, I'm reaching out because a recent scan flagged a track you posted as likely "
        f"AI-generated (possible origin: {origin}, {confidence:.0f}% confidence). "
        f"If it was trained on or styled after an artist's work, I'd rather turn this into a "
        f"conversation about fair credit, consent and revenue share than a dispute. "
        f"Would you be open to connecting so we can find a fair path forward?"
    )


def handle_result(source_file, result):
    verdict = result.get("verdict")
    if verdict == "human":
        output_type = "certificate"
        content = generate_certificate(result)
    elif verdict == "ai":
        output_type = "outreach"
        content = generate_outreach_email(result)
    else:
        # uncertain, suspicious, no_vocal, or anything unexpected: never guess
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
        "output_type": output_type,
        "content": content,
    }
    with open(LOG_FILE, "a") as f:
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
    handle_result(file_url, result)
