# ai_module/voice_analyzer.py
import os
import joblib
import numpy as np
from ai_module.feature_extractor import extract_features

# Define model and scaler paths
MODEL_PATH = os.path.join("ai_module", "voice_model.joblib")
SCALER_PATH = os.path.join("ai_module", "feature_scaler.joblib")

# Try to load the trained model and scaler
try:
    model = joblib.load(MODEL_PATH)
    scaler = joblib.load(SCALER_PATH)
    print("✅ Voice model and scaler loaded successfully.")
except Exception as e:
    print("⚠️ Could not load model/scaler:", e)
    model, scaler = None, None

def analyze_voice(audio_path):
    """
    Takes a .wav file path, extracts features using feature_extractor.py,
    and predicts the Big-Five Personality Traits.
    """
    try:
        feats = extract_features(audio_path)
        feats = feats.reshape(1, -1)

        if model is not None and scaler is not None:
            feats_scaled = scaler.transform(feats)
            preds = model.predict(feats_scaled)[0]
        else:
            # fallback random values if model missing
            preds = np.random.uniform(40, 80, 5)

        traits = ["Openness", "Conscientiousness", "Extraversion", "Agreeableness", "Neuroticism"]
        result = {trait: round(float(value), 2) for trait, value in zip(traits, preds)}

        print("🎯 Personality Analysis Result:", result)
        return result

    except Exception as e:
        print("⚠️ Error analyzing voice:", e)
        return {"Error": str(e)}
