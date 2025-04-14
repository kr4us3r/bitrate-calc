import os
import mimetypes
from moviepy import VideoFileClip
from pydub import AudioSegment
import ffmpeg

def calculate_bitrate(file_path, temp_audio="temp_audio.wav"):
    """
    Calculate audio bitrate for audio/video files and video bitrate
    excluding audio for videos. Uses ffmpeg-python for metadata if available,
    else pydub/moviepy for calculation. Returns a dict with 'audio' and
    optionally 'video' bitrates in kpbs.
    """
    bitrates = {}
    mime_type, _ = mimetypes.guess_type(file_path)
    is_video = mime_type and mime_type.startswith("video")

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
            # Exctract audio from video
            video = VideoFileClip(file_path)
            duration_seconds = video.duration
            video.audio.write_audiofile(temp_audio)
            video.close()
        else:
            # Use audio file directly
            temp_audio = file_path
            duration_seconds = AudioSegment.from_file(file_path).duration_seconds

        audio = AudioSegment.from_file(temp_audio)
        audio_size_bits = os.path.getsize(temp_audio) * 8
        audio_bitrate_kpbs = (audio_size_bits / duration_seconds) / 1000
        bitrates["audio"] = audio_bitrate_kpbs

        if is_video:
            container_size_bits = os.path.getsize(file_path) * 8
            video_size_bits = container_size_bits - audio_size_bits
            video_bitrate_kpbs = (video_size_bits / duration_seconds) / 1000
            bitrates["video"] = video_bitrate_kpbs
            os.remove(temp_audio)

        return bitrates

    except Exception as e:
        raise Exception(f"Failed to calculate bitrate: {str(e)}")


