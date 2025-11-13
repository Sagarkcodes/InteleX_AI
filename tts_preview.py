from TTS.api import TTS
import os

# Ensure uploads folder exists
os.makedirs("static/uploads", exist_ok=True)

# Load the model
model_name = "tts_models/en/vctk/vits"
tts = TTS(model_name)

# Print all speakers
print("\n🎙️ Available Speakers:\n", tts.speakers, "\n")

# Test text
test_text = "Hello, I am your InteleX AI interviewer. Let's begin your voice personality test."

# Try some different speakers (these are names, not numeric indexes)
test_speakers = ["p231", "p238", "p239", "p240", "p245", "p248", "p251", "p260", "p273", "p283", "p303", "p307"]

for speaker in test_speakers:
    output_file = f"static/uploads/test_voice_{speaker}.wav"
    print(f"🎧 Generating voice for speaker '{speaker}' -> {output_file}")
    tts.tts_to_file(text=test_text, speaker=speaker, file_path=output_file)

print("\n✅ All test voices generated! Check your static/uploads folder.\n")
