from faster_whisper import WhisperModel

model = WhisperModel(
    "base",
    device="cpu",
    compute_type="int8"
)

def transcribe_audio(audio_path: str) -> str:
    try:
        segments, _ = model.transcribe(audio_path, beam_size=1)

        full_text = ""
        for segment in segments:
            full_text += segment.text + " "

        return full_text.strip()

    except Exception as e:
        print("Whisper Error:", e)
        return ""