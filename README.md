# Bitrate Calculator

A CLI tool to calculate audio bitrate for video/audio files and video bitrate (excluding audio) for video files. Uses FFmpeg metadata when available, falling back to manual calculation.

## Installation

1. Clone the repo:
```bash
git clone https://github.com/yourusername/bitrate-calculator.git
cd bitrate-calculator
```

2. Create a virtual environment (optional but recommended):
```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
.\venv\Scripts\activate   # Windows
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Install FFmpeg:
- Linux: `sudo apt install ffmpeg`
- macOS: `brew install ffmpeg`
- Windows: Download from ffmpeg.org and add to PATH.

5. (Optional) Install as a global tool:
```bash
pip install .
```

## Usage

Run with a file path:

```bash
python -m bitrate_calc.cli path/to/file.mp4
# Or, if installed globally:
bitrate-calc path/to/file.mp3
```

### Example Output

For a video file:

```
Audio bitrate: 128.45 kbps
Video bitrate (excluding audio): 1500.67 kbps
```

For an audio file:

```
Audio bitrate: 256.32 kbps
```

## Supported Formats

- Video: MP4, MKV, AVI, MOV, etc
- Audio: MP3, OGG, WAV, AAC, FLAC, etc

## Notes

- Requires FFmpeg for audio/video processing.
- Uses metadata if available; otherwise, calculates video bitrate by subtracting audio size from container size, which may include minor overhead.
- Install globally with `pip install .` to use `bitrate-calc` command.