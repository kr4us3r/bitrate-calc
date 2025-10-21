import os
import mimetypes
from moviepy import VideoFileClip
from pydub import AudioSegment
import ffmpeg

def calculate_bitrate(file_path, temp_audio_base="temp_audio"):
    """
    Calculate audio bitrate for audio/video files and video bitrate
    for videos. Uses ffmpeg-python for metadata if available,
    else pydub/moviepy for calculation. Returns a dict with 'audio' as list of
    dicts and optionally 'video' bitrate in kbps.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    bitrates = {}
    mime_type, _ = mimetypes.guess_type(file_path)
    is_video = mime_type and mime_type.startswith("video")
    temps_created = []

    try:
        # Try metadata extraction with ffmpeg
        probe_success = False
        audio_list = []
        video_bitrate = None
        duration_seconds = None
        audio_streams = []
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
                name = title or (f"{i+1} ({lang.upper()})" if len(lang) == 3 else f"{i+1} ({lang})" if lang else f"{i+1}")
                bitrate = int(stream["bit_rate"]) / 1000 if "bit_rate" in stream else None
                audio_list.append({"name": name, "bitrate": bitrate})

            # video bitrate
            if video_streams:
                vstream = video_streams[0]
                video_bitrate = int(vstream["bit_rate"]) / 1000 if "bit_rate" in vstream else None

            # return early if all bitrates present
            need_fallback = any(a["bitrate"] is None for a in audio_list) or (is_video and video_bitrate is None)
            if not need_fallback and audio_list:
                bitrates["audio"] = audio_list
                if is_video:
                    bitrates["video"] = video_bitrate
                return bitrates
        except ffmpeg.Error:
            probe_success = False

        if not audio_list:
            raise ValueError("No audio stream found")

        # partial fallback
        if probe_success and duration_seconds is not None:
            total_audio_size_bits = 0
            codec_to_ext = {
                "aac": ".m4a", "mp3": ".mp3", "opus": ".opus", "vorbis": ".ogg",
                "flac": ".flac", "ac3": ".ac3", "aiff": ".aiff", "alac": ".m4a",
                "wma": ".wma",
            }
            for i, astream in enumerate(audio_streams):
                if audio_list[i]["bitrate"] is not None:
                    total_audio_size_bits += (audio_list[i]["bitrate"] * 1000 * duration_seconds) / 8
                    continue

                codec = astream.get("codec_name", "pcm_s16le").lower()
                ext = codec_to_ext.get(codec, ".wav")
                temp_audio = f"{temp_audio_base}_{i}{ext}"
                temps_created.append(temp_audio)

                extracted = False
                try:
                    # extract without re-encoding
                    stream_in = ffmpeg.input(file_path)
                    out = ffmpeg.output(stream_in, temp_audio, c="copy", map=f"0:a:{i}", loglevel="quiet")
                    ffmpeg.run(out, overwrite_output=True, quiet=True, capture_stdout=True, capture_stderr=True)
                    extracted = True
                except ffmpeg.Error:
                    pass

                if not extracted:
                    # transcode to WAV
                    wav_temp = f"{temp_audio_base}_{i}.wav"
                    temps_created.append(wav_temp)
                    try:
                        stream_in = ffmpeg.input(file_path)
                        out = ffmpeg.output(
                            stream_in, wav_temp, acodec="pcm_s16le", ar=44100, map=f"0:a:{i}",
                            loglevel="quiet"
                        )
                        ffmpeg.run(out, overwrite_output=True, quiet=True, capture_stdout=True, capture_stderr=True)
                        temp_audio = wav_temp
                        extracted = True
                    except ffmpeg.Error:
                        raise ValueError(f"Failed to extract audio stream {i} (codec: {codec})")

                if not os.path.exists(temp_audio) or os.path.getsize(temp_audio) == 0:
                    raise ValueError(f"Extracted audio stream {i} is empty or missing")

                audio_size_bits = os.path.getsize(temp_audio) * 8
                audio_bitrate_kbps = (audio_size_bits / duration_seconds) / 1000
                audio_list[i]["bitrate"] = round(audio_bitrate_kbps, 2)
                total_audio_size_bits += audio_size_bits

            bitrates["audio"] = audio_list

            if is_video and video_bitrate is None:
                container_size_bits = os.path.getsize(file_path) * 8
                video_size_bits = container_size_bits - total_audio_size_bits
                if video_size_bits > 0:
                    bitrates["video"] = round((video_size_bits / duration_seconds) / 1000, 2)
                else:
                    bitrates["video"] = 0.0

            return bitrates

        # full fallback
        print("FFmpeg probe failed. Processing only the first/default audio track.")
        temp_audio = None
        if is_video:
            temp_audio = temp_audio_base + ".wav"
            temps_created.append(temp_audio)
            video = VideoFileClip(file_path)
            duration_seconds = video.duration
            video.audio.write_audiofile(temp_audio, verbose=False, logger=None)
            video.close()
        else:
            temp_audio = file_path
            duration_seconds = AudioSegment.from_file(file_path).duration_seconds

        if not os.path.exists(temp_audio) or os.path.getsize(temp_audio) == 0:
            raise ValueError("Failed to load audio data")

        audio_size_bits = os.path.getsize(temp_audio) * 8
        audio_bitrate_kbps = (audio_size_bits / duration_seconds) / 1000
        bitrates["audio"] = [{"name": "Audio Track", "bitrate": round(audio_bitrate_kbps, 2)}]

        if is_video:
            container_size_bits = os.path.getsize(file_path) * 8
            video_size_bits = container_size_bits - audio_size_bits
            if video_size_bits > 0:
                bitrates["video"] = round((video_size_bits / duration_seconds) / 1000, 2)
            else:
                bitrates["video"] = 0.0

        return bitrates

    finally:
        for temp in temps_created:
            if os.path.exists(temp):
                os.remove(temp)