"""Royalty Radar dashboard. Run with: streamlit run app.py"""
import json
import os
import tempfile
from pathlib import Path

import streamlit as st

try:
    import detect
    DETECT_ERROR = None
except KeyError as e:  # HUMANSTANDARD_API_KEY not set
    detect = None
    DETECT_ERROR = f"{e.args[0]} is not set. Scanning is disabled; the results view still works."

LOG_FILE = Path(__file__).parent / "results_log.jsonl"
AUDIO_TYPES = ["mp3", "wav", "m4a", "flac", "ogg", "aac"]
VIDEO_TYPES = ["mp4", "mov", "mkv", "webm", "avi", "m4v"]
MOCKS = ["Real scan (1 credit)", "human", "ai", "suspicious", "no_vocal"]

OUTPUTS = {
    "certificate": ("Certificate of human authorship", "green"),
    "outreach": ("Outreach draft (not sent)", "orange"),
    "review": ("Manual review", "red"),
}

st.set_page_config(page_title="Royalty Radar", layout="wide")
st.title("Royalty Radar")
st.caption(
    "Scans audio for AI-generated music and cloned vocals. "
    "Human gets a certificate, AI gets a drafted outreach email, anything unsure goes to a person."
)


def load_log():
    if not LOG_FILE.exists():
        return []
    rows = []
    for line in LOG_FILE.read_text(encoding="utf-8").splitlines():
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return list(reversed(rows))  # newest first


def show_output(entry):
    label, color = OUTPUTS.get(entry["output_type"], (entry["output_type"], "gray"))
    conf = entry.get("confidence")
    st.markdown(f"### :{color}[{label}]")
    cols = st.columns(3)
    cols[0].metric("Verdict", str(entry.get("verdict")).upper())
    cols[1].metric("Confidence", f"{conf * 100:.1f}%" if conf is not None else "n/a")
    cols[2].metric("Possible origin", entry.get("origin") or "none")
    st.code(entry["content"], language=None, wrap_lines=True)


def source_name(source):
    return Path(source).name if "://" not in source else source.rsplit("/", 1)[-1] or source


def run_scan(source, display, mock, video=False):
    """Submit, poll, log and show one scan."""
    try:
        with st.status("Scanning. The first real scan can take 20-30 seconds...") as status:
            if video:
                status.update(label="Extracting audio from the video, then submitting...")
            job_id = detect.submit_track(source, mock=mock)
            status.update(label=f"Job {job_id} submitted, waiting for the verdict...")
            result = detect.poll_job(job_id)
            detect.handle_result(display, result)
            status.update(label="Done", state="complete")
        show_output(load_log()[0])
    except Exception as e:
        st.error(f"Scan failed: {e}")


def scan_upload(upload, mock):
    """Write an uploaded or recorded file to disk, scan it, clean up."""
    suffix = Path(upload.name).suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(upload.getvalue())
        tmp_path = tmp.name
    try:
        run_scan(tmp_path, upload.name, mock, video=suffix.lower().lstrip(".") in VIDEO_TYPES)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


if DETECT_ERROR:
    st.error(DETECT_ERROR)
mode = st.selectbox(
    "Scan mode",
    MOCKS,
    help="Mock scenarios return canned results, ignore the audio, and cost no credits.",
)
mock = None if mode == MOCKS[0] else mode
if mock:
    st.info(f"Mock scenario '{mock}': canned result, no credits spent.")

scan_tab, listen_tab, results_tab = st.tabs(["Check a track", "Listen", "Results"])

with scan_tab:
    upload = st.file_uploader(
        "Audio or video file",
        type=AUDIO_TYPES + VIDEO_TYPES,
        help="For a video, the audio track is extracted with ffmpeg before scanning.",
    )
    url = st.text_input("...or a public audio URL")

    if st.button("Scan", type="primary", disabled=DETECT_ERROR is not None):
        if upload:
            scan_upload(upload, mock)
        elif url.strip():
            run_scan(url.strip(), url.strip(), mock)
        else:
            st.warning("Choose a file or paste a URL first.")

with listen_tab:
    st.write(
        "Play music near your device's microphone, record 15-30 seconds, then scan it. "
        "Room noise lowers accuracy, so treat a result here as a first look."
    )
    recording = st.audio_input("Record what's playing")
    if recording is not None:
        if st.button("Scan recording", type="primary", disabled=DETECT_ERROR is not None):
            scan_upload(recording, mock)

with results_tab:
    rows = load_log()
    if st.button("Refresh"):
        st.rerun()
    if not rows:
        st.info("No results yet. Scan a track, or ask the agent to run scan_batch.py.")
    else:
        counts = {k: sum(1 for r in rows if r["output_type"] == k) for k in OUTPUTS}
        cols = st.columns(len(OUTPUTS) + 1)
        cols[0].metric("Scanned", len(rows))
        for col, (key, (label, _)) in zip(cols[1:], OUTPUTS.items()):
            col.metric(label.split(" (")[0], counts[key])

        for r in rows:
            label, color = OUTPUTS.get(r["output_type"], (r["output_type"], "gray"))
            conf = r.get("confidence")
            conf_txt = f"{conf * 100:.1f}%" if conf is not None else "n/a"
            title = f":{color}[{label.split(' (')[0]}] {source_name(r['source_file'])} ({conf_txt})"
            with st.expander(title):
                st.caption(r.get("timestamp", ""))
                show_output(r)
