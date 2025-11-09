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
