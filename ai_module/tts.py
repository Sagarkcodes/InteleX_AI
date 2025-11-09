# ai_module/tts.py
import os
import traceback

# Where to save generated speech
OUTPUT_DIR = os.path.join("static", "audio")
os.makedirs(OUTPUT_DIR, exist_ok=True)

def say_text_to_file(text, filename="inteleX_speech.wav", voice_name=None):
    """
    Generate speech to WAV file. Returns full path to WAV file.
    Tries Coqui TTS first (higher-quality). If TTS is not available or fails,
    falls back to pyttsx3 local TTS.
    """
    out_path = os.path.join(OUTPUT_DIR, filename)

    # Try high-quality Coqui TTS
    try:
        from TTS.api import TTS
        # Default: use the first available model if no voice_name specified
        # Example model name that generally exists: "tts_models/en/vctk/vits"
        model_name = voice_name if voice_name else "tts_models/en/vctk/vits"
        tts = TTS(model_name)
        # generate and save
        tts.tts_to_file(text=text, file_path=out_path, speaker="p239")


        return out_path
    except Exception as e:
        print("Coqui TTS not available or failed:", str(e))
        # print stack for debugging
        traceback.print_exc()

    # Fallback: pyttsx3 (local)
    try:
        import pyttsx3
        engine = pyttsx3.init()
        # set properties if you want (rate, volume, voice)
        try:
            engine.setProperty('rate', 160)  # speaking rate
            engine.setProperty('volume', 1.0)  # 0..1
        except Exception:
            pass
        # pyttsx3 can save directly on some platforms via .save_to_file
        engine.save_to_file(text, out_path)
        engine.runAndWait()
        return out_path
    except Exception as e:
        print("pyttsx3 fallback failed:", e)
        traceback.print_exc()

    raise RuntimeError("No TTS engine available on this machine.")
