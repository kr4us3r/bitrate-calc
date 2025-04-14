import os
import mimetypes
from moviepy import VideoFileClip
from pydub import AudioSegment
import ffmpeg

def calculate_bitrate(file_path, temp_audio_base="temp_audio"):
    """
    Calculate audio bitrate for audio/video files and video bitrate
    excluding audio for videos. Uses ffmpeg-python for metadata if available,
    else pydub/moviepy for calculation. Returns a dict with 'audio' and
    optionally 'video' bitrates in kpbs.
    """
    bitrates = {}
    mime_type, _ = mimetypes.guess_type(file_path)
    is_video = mime_type and mime_type.startswith("video")
    temp_file_created = False

    try:
        # Try metadata extraction with ffmpeg
        try:
            probe = ffmpeg.probe(file_path, loglevel="quiet")
            streams = probe["streams"]
            duration_seconds = float(probe["format"]["duration"])

            for stream in streams:
                if stream["codec_type"] == "audio" and "bit_rate" in stream:
                    bitrates["audio"] = int(stream["bit_rate"]) / 1000
                elif is_video and stream["codec_type"] == "video" and "bit_rate" in stream:
                    bitrates["video"] = int(stream["bit_rate"]) / 1000
            
            if (is_video and "audio" in bitrates and "video" in bitrates) or (not is_video and "audio" in bitrates):
                return bitrates
        except ffmpeg.Error:
            pass
        
        # Manual calculation
        if is_video:
            try:
                # Get audio codec to choose extension
                probe = ffmpeg.probe(file_path)
                audio_stream = next((s for s in probe["streams"] if s["codec_type"] == "audio"), None)
                if not audio_stream:
                    raise ValueError("No audio stream found in video")
                codec = audio_stream.get("codec_name", "aac").lower()
                codec_to_ext = {
                    "aac": ".aac",
                    "mp3": ".mp3",
                    "opus": ".opus",
                    "vorbis": ".vorbis",
                    "flac": ".flac",
                    "ac3": ".ac3",
                    "aiff": ".aiff",
                    "m4a": ".m4a",
                    "wav": ".wav",
                    "alac": ".alac",
                    "wma": ".wma",
                }
                ext = codec_to_ext.get(codec)
                temp_audio = temp_audio_base + ext

                # Exctract without re-encoding
                stream = ffmpeg.input(file_path)
                stream = ffmpeg.output(stream, temp_audio, c='copy', map='0:a:0', loglevel='verbose')
                ffmpeg.run(stream)
                duration_seconds = float(probe["format"]["duration"])
            except (ffmpeg.Error, ValueError):
                print(f"Native audio exctraction failed. Falling back to WAV.")
                temp_audio = temp_audio_base + ".wav"
                video = VideoFileClip(file_path)
                duration_seconds = video.duration
                video.audio.write_audiofile(temp_audio)
                video.close()
            temp_file_created = True
        else:
            # Use audio file directly
            temp_audio = file_path
            duration_seconds = AudioSegment.from_file(file_path).duration_seconds

        audio_size_bits = os.path.getsize(temp_audio) * 8
        audio_bitrate_kpbs = (audio_size_bits / duration_seconds) / 1000
        bitrates["audio"] = audio_bitrate_kpbs

        if is_video:
            container_size_bits = os.path.getsize(file_path) * 8
            video_size_bits = container_size_bits - audio_size_bits
            video_bitrate_kpbs = (video_size_bits / duration_seconds) / 1000
            bitrates["video"] = video_bitrate_kpbs
        return bitrates
   
    finally:
        if temp_file_created and os.path.exists(temp_audio):
            os.remove(temp_audio)
