import os
import time
from datetime import datetime

# Try importing Coqui
try:
    from TTS.api import TTS
    coqui_available = True
except ImportError:
    coqui_available = False
    print("⚠️ Coqui TTS not installed. Run: pip install TTS")

UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Preload Coqui model once (faster, consistent)
tts_model = None
if coqui_available:
    try:
        print("🔄 Loading Coqui model (vctk/vits, speaker p251)...")
        tts_model = TTS("tts_models/en/vctk/vits")
        print("✅ Coqui model loaded successfully.")
    except Exception as e:
        print(f"⚠️ Could not load Coqui model: {e}")
        tts_model = None


def say_text_to_file(text: str, filename="intelx_voice.wav"):
    """
    Generate natural human-like voice (p251) for all project pages.
    """
    base, _ = os.path.splitext(filename)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    final_name = f"{base}_{timestamp}.wav"
    save_path = os.path.join(UPLOAD_FOLDER, final_name)

    # Preferred: Coqui
    if coqui_available and tts_model is not None:
        try:
            tts_model.tts_to_file(
                text=text,
                speaker="p251",
                speed=0.9,  # calm HR pace
                file_path=save_path
            )
            # Ensure file flush
            time.sleep(0.4)
            print(f"✅ Coqui voice generated (p251): {save_path}")
            return save_path
        except Exception as e:
            print(f"⚠️ Coqui generation failed: {e}")

    # Fallback: pyttsx3 if Coqui unavailable
    try:
        import pyttsx3
        engine = pyttsx3.init()
        engine.setProperty("rate", 160)
        engine.save_to_file(text, save_path)
        engine.runAndWait()
        print(f"⚠️ Used fallback pyttsx3 voice: {save_path}")
        return save_path
    except Exception as e:
        print(f"❌ Fallback TTS failed: {e}")
        # create silent file placeholder
        with open(save_path, "wb") as f:
            f.write(b"")
        return save_path
