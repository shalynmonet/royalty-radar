import sys

import detect
from outreach import SENDERS


def scan_all(urls, mock=None, sender="artist"):
    """Scan each URL and return (url, verdict, confidence, output_type) rows.

    One failing URL is reported in the table and does not stop the batch.
    """
    rows = []
    for url in urls:
        try:
            job_id = detect.submit_track(url, mock=mock)
            result = detect.poll_job(job_id)
            output_type, _ = detect.handle_result(url, result, sender=sender, job_id=job_id)
            rows.append((url, result.get("verdict"), result.get("confidence"), output_type))
        except Exception as e:  # network, auth, job failure, timeout
            rows.append((url, "error", None, f"failed: {e}"))
    return rows


def print_table(rows):
    print(f"\n{'VERDICT':<12}{'CONF':>7}  {'OUTPUT':<12}SOURCE")
    for url, verdict, confidence, output_type in rows:
        conf = f"{confidence * 100:.1f}%" if confidence is not None else "-"
        print(f"{str(verdict):<12}{conf:>7}  {output_type:<12}{url}")


def take_option(args, name):
    """Remove `name value` from args and return value, or None if absent."""
    if name not in args:
        return None
    i = args.index(name)
    if i + 1 >= len(args) or args[i + 1].startswith("--"):
        print(f"{name} needs a value")
        sys.exit(1)
    value = args[i + 1]
    del args[i:i + 2]
    return value


if __name__ == "__main__":
    args = sys.argv[1:]
    mock = take_option(args, "--mock")
    sender = take_option(args, "--sender") or "artist"
    if sender not in SENDERS:
        print(f"--sender must be one of: {', '.join(SENDERS)}")
        sys.exit(1)
    if not args:
        print("Usage: python scan_batch.py [--mock scenario] [--sender artist|label] <source> [<source> ...]")
        sys.exit(1)
    print_table(scan_all(args, mock=mock, sender=sender))
