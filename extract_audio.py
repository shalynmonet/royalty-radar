import os
import shutil
import subprocess
import sys
from pathlib import Path

VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v"}


def is_video(path):
    return Path(path).suffix.lower() in VIDEO_EXTS


def extract_audio(video_path, output_path="extracted_audio.wav"):
    """Pull the audio track out of a video file as WAV using ffmpeg."""
    ffmpeg = os.environ.get("FFMPEG_PATH") or shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError(
            "ffmpeg not found. Install it (winget install ffmpeg, apt install ffmpeg, "
            "brew install ffmpeg), reopen your terminal, or set FFMPEG_PATH."
        )
    try:
        subprocess.run(
            [
                ffmpeg, "-y",
                "-i", video_path,
                "-vn",                    # drop the video stream
                "-acodec", "pcm_s16le",   # uncompressed 16-bit WAV
                output_path,
            ],
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as e:
        tail = e.stderr.decode(errors="replace").strip().splitlines()[-1:]
        raise RuntimeError(
            f"Could not extract audio from {Path(video_path).name} "
            f"(does it have an audio track?): {' '.join(tail)}"
        ) from e
    return output_path


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python extract_audio.py <video_file> [output.wav]")
        sys.exit(1)

    out = sys.argv[2] if len(sys.argv) > 2 else "extracted_audio.wav"
    try:
        print(f"Wrote {extract_audio(sys.argv[1], out)}")
    except RuntimeError as e:
        print(e)
        sys.exit(1)
