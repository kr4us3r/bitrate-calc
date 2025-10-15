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
    temps_created = []

    try:
        # try metadata extraction with ffmpeg
        probe_success = False
        audio_list = []
        video_bitrate = None
        duration_seconds = None
        try:
            probe = ffmpeg.probe(file_path, loglevel="quiet")
            probe_success = True
            streams = probe["streams"]
            duration_seconds = float(probe["format"]["duration"])

            audio_streams = [s for s in streams if s["codec_type"] == "audio"]
            video_streams = [s for s in streams if s["codec_type"] == "video"]

            # create audio list with metadata
            for i, stream in enumerate(audio_streams):
                tags = stream.get("tags", {})
                lang = tags.get("language", "")
                title = tags.get("title", "")
                name = title if title else (f"{i+1} ({lang.upper()})" if len(lang) == 3 else f"{i+1} ({lang})") if lang else f"{i+1}"
                bitrate = int(stream["bit_rate"]) / 1000 if "bit_rate" in stream else None
                audio_list.append({"name": name, "bitrate": bitrate})

            # video bitrate
            if video_streams:
                stream = video_streams[0]
                bitrate = int(stream["bit_rate"]) / 1000 if "bit_rate" in stream else None

            # return early if all bitrates present
            need_fallback = any(a["bitrate"] is None for a in audio_list) or (is_video and video_bitrate is None)
            if not need_fallback and audio_list:
                bitrates["audio"] = audio_list
                if is_video and video_bitrate is not None:
                    bitrates["video"] = video_bitrate
                return bitrates

        except ffmpeg.Error:
            probe_success = False
        
        if not audio_list:
            raise ValueError("No audio stream found")

        # partial fallback to extract missing bitrates
        if probe_success and duration_seconds is not None:
            total_audio_size_bits = 0
            for i, stream in enumerate(audio_streams):
                codec = stream.get("codec_name", "wav").lower()
                temp_audio = f"{temp_audio_base}_{i}.{codec}"
                temps_created.append(temp_audio)

                try:
                    # extract without re-encoding
                    stream = ffmpeg.input(file_path)
                    out = ffmpeg.output(stream, temp_audio, c='copy',map=f'0:a:{i}', loglevel='quiet')
                    ffmpeg.run(out, overwrite_output=True, quiet=True)
                except ffmpeg.Error:
                    if is_video:
                        video = VideoFileClip(file_path)
                        audio_clip = video.audio.subclipped()
                        audio_clip.write_audiofile(temp_audio, verbose=False, logger=None)
                        audio_clip.close()
                        video.close()
                    else:
                        raise ValueError("Failed to extract")
                    
                    audio_size_bits = os.path.getsize(temp_audio) * 8
                    audio_bitrate_kbps = (audio_size_bits / duration_seconds) / 1000
                    audio_list[i]["bitrate"] = audio_bitrate_kbps
                    total_audio_size_bits += audio_size_bits
                
                bitrates["audio"] = audio_list

            if is_video and video_bitrate is None:
                container_size_bits = os.path.getsize(file_path) * 8
                video_size_bits = container_size_bits - total_audio_size_bits
                if video_size_bits > 0:
                    bitrates["video"] = (video_size_bits / duration_seconds) / 1000
            
            return bitrates

        # full fallback
        if is_video:
            temp_audio = temp_audio_base + ".wav"
            temps_created.append(temp_audio)
            video = VideoFileClip(file_path)
            duration_seconds = video.duration
            video.audio.write_audiofile(temp_audio, verbose=False, logger=None)
            video.close()
        else:
            temp_audio = file_path
            duration_seconds = AudioSegment.from_file(file_path).duration

        audio_size_bits = os.path.getsize(temp_audio) * 8
        audio_bitrate_kbps = (audio_size_bits / duration_seconds) / 1000
        bitrates["audio"] = [{"name": "Audio track", "bitrate": audio_bitrate_kbps}]

        if is_video:
            container_size_bits = os.path.getsize(file_path) * 8
            video_bitrate = container_size_bits - audio_size_bits
            if video_size_bits > 0:
                bitrates["video"] = (video_size_bits / duration_seconds) / 1000

        return bitrates

    finally:
        for temp in temps_created:
            if os.path.exists(temp):
                os.remove(temp)
            