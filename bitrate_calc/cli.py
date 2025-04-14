import argparse
from .main import calculate_bitrate

def main():
    parser = argparse.ArgumentParser(
        description="Calculate audio and video bitrates for media files."
    )
    parser.add_argument(
        "file_path",
        help="Path to video (e.g., .mkv, .mp4) or audio (e.g., .mp3, .ogg) file"
    )
    args = parser.parse_args()

    try:
        bitrates = calculate_bitrate(args.file_path)
        print(f"Audio bitrate: {bitrates["audio"]:.0f} kbps")
        if "video" in bitrates:
            print(f"Video bitrate: {bitrates["video"]:.0f} kbps")
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()