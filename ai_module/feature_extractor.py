# ai_module/feature_extractor.py
import librosa
import numpy as np

def extract_features(audio_path):
    """
    Extracts meaningful audio features from a given .wav file.
    Returns a 1D NumPy array (feature vector).
    """
    try:
        # Load the audio file
        y, sr = librosa.load(audio_path, sr=22050)

        # Compute features
        mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
        chroma = librosa.feature.chroma_stft(y=y, sr=sr)
        spectral_contrast = librosa.feature.spectral_contrast(y=y, sr=sr)
        tonnetz = librosa.feature.tonnetz(y=librosa.effects.harmonic(y), sr=sr)

        # Mean values across time
        features = np.hstack([
            np.mean(mfcc, axis=1),
            np.mean(chroma, axis=1),
            np.mean(spectral_contrast, axis=1),
            np.mean(tonnetz, axis=1)
        ])

        return features

    except Exception as e:
        print(f"⚠️ Error processing {audio_path}: {e}")
        return np.zeros(39)  # Return empty vector if error occurs


def score_audio(audio_path):
    """
    Computes real confidence, clarity, and communication scores (0–100)
    from audio signal features using librosa. No trained model needed.

    - Confidence  → RMS energy (how loud/assertive the speaker is)
    - Clarity     → Spectral rolloff (articulation / brightness of speech)
    - Communication → Zero-crossing rate (rhythm and fluency of speech)
    - Overall     → Weighted average of all three, scaled to 0–10
    """
    try:
        y, sr = librosa.load(audio_path, sr=22050)

        # --- Confidence: RMS energy ---
        rms = librosa.feature.rms(y=y)[0]
        avg_rms = float(np.mean(rms))
        # Typical RMS for speech: 0.01–0.25. Scale to 0–100.
        confidence = round(min(100.0, max(0.0, avg_rms * 400)), 1)

        # --- Clarity: Spectral rolloff (brightness / articulation) ---
        rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr)[0]
        avg_rolloff = float(np.mean(rolloff))
        # Typical rolloff for speech: 1000–8000 Hz. Normalize to 0–100.
        clarity = round(min(100.0, max(0.0, (avg_rolloff - 500) / 75)), 1)

        # --- Communication: Zero-crossing rate (rhythm / fluency) ---
        zcr = librosa.feature.zero_crossing_rate(y)[0]
        avg_zcr = float(np.mean(zcr))
        # Typical ZCR for speech: 0.02–0.12. Scale to 0–100.
        communication = round(min(100.0, max(0.0, avg_zcr * 800)), 1)

        # --- Overall score (out of 10, weighted) ---
        overall = round(
            (confidence * 0.4 + clarity * 0.3 + communication * 0.3) / 10, 2
        )
        overall = min(10.0, overall)

        print(f"🎙️ Audio Scores → Confidence: {confidence}, Clarity: {clarity}, Communication: {communication}, Overall: {overall}")

        return {
            "confidence": confidence,
            "clarity": clarity,
            "communication": communication,
            "overall": overall
        }

    except Exception as e:
        print(f"⚠️ score_audio error for {audio_path}: {e}")
        # Safe fallback — neutral scores
        return {
            "confidence": 60.0,
            "clarity": 60.0,
            "communication": 60.0,
            "overall": 6.0
        }
