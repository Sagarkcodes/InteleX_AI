# ai_module/tts_test.py
from TTS.api import TTS

tts = TTS("tts_models/en/vctk/vits")
print(tts.speakers)

from ai_module.tts import say_text_to_file

text = "Hello! I am InteleX, your interview assistant. Let's test my voice."

try:
    path = say_text_to_file(text, filename="intelex_test.wav")
    print("✅ Speech file created successfully!")
    print(f"👉 Saved at: {path}")
    print("Now, play the file in your file explorer or visit it through Flask later.")
except Exception as e:
    print("❌ Error during TTS test:", e)
