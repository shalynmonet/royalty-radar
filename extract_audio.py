import subprocess
import sys


def extract_audio(video_path, output_path="extracted_audio.wav"):
    """Pull the audio track out of a video file as WAV using ffmpeg."""
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-i", video_path,
            "-vn",                    # drop the video stream
            "-acodec", "pcm_s16le",   # uncompressed 16-bit WAV
            output_path,
        ],
        check=True,
        capture_output=True,
    )
    return output_path


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python extract_audio.py <video_file> [output.wav]")
        sys.exit(1)

    out = sys.argv[2] if len(sys.argv) > 2 else "extracted_audio.wav"
    try:
        print(f"Wrote {extract_audio(sys.argv[1], out)}")
    except FileNotFoundError:
        print("ffmpeg not found. Install it and reopen your terminal (winget install ffmpeg).")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(e.stderr.decode(errors="replace"))
        sys.exit(1)
