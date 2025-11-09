# scripts/prepare_ravdess_dataset.py
import os, csv, random

# Folder where your extracted dataset is stored
root = "dataset/archive"
out_csv = "dataset/dataset.csv"

print("🔍 Scanning for audio files...")
audio_files = []
for path, _, files in os.walk(root):
    for file in files:
        if file.lower().endswith(".wav"):
            audio_files.append(os.path.join(path, file).replace("\\", "/"))

print(f"🎵 Found {len(audio_files)} audio files.")

# Create dataset.csv with random Big-Five personality traits (0–100 scale)
print("🧠 Creating dataset.csv with sample Big-Five scores...")
with open(out_csv, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["filepath", "openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"])
    for file in audio_files:
        writer.writerow([
            file,
            random.uniform(40, 90),  # openness
            random.uniform(40, 90),  # conscientiousness
            random.uniform(40, 90),  # extraversion
            random.uniform(40, 90),  # agreeableness
            random.uniform(40, 90)   # neuroticism
        ])

print(f"✅ dataset.csv created successfully with {len(audio_files)} entries.")
