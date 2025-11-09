# ai_module/train_voice_model.py
import os
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.multioutput import MultiOutputRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score
from ai_module.feature_extractor import extract_features

# Paths
CSV_PATH = "dataset/dataset.csv"
MODEL_PATH = "ai_module/voice_model.joblib"
SCALER_PATH = "ai_module/feature_scaler.joblib"

def load_data():
    df = pd.read_csv(CSV_PATH)
    X = []
    y = []

    print("🔍 Extracting features from audio files...")
    for i, row in df.iterrows():
        path = row["filepath"]
        if os.path.exists(path):
            features = extract_features(path)
            X.append(features)
            y.append([
                row["openness"],
                row["conscientiousness"],
                row["extraversion"],
                row["agreeableness"],
                row["neuroticism"]
            ])
        else:
            print(f"⚠️ Missing file: {path}")

    X = np.array(X)
    y = np.array(y)
    print(f"✅ Extracted {len(X)} samples.")
    return X, y

def main():
    X, y = load_data()

    # Standardize features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Split data for training/testing
    X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, random_state=42)

    print("🧠 Training Random Forest model...")
    model = MultiOutputRegressor(RandomForestRegressor(n_estimators=200, random_state=42))
    model.fit(X_train, y_train)

    # Evaluate
    preds = model.predict(X_test)
    mse = mean_squared_error(y_test, preds)
    r2 = r2_score(y_test, preds)
    print(f"📊 Mean Squared Error: {mse:.2f}")
    print(f"📈 R² Score: {r2:.2f}")

    # Save model and scaler
    joblib.dump(model, MODEL_PATH)
    joblib.dump(scaler, SCALER_PATH)
    print("💾 Model saved to:", MODEL_PATH)
    print("💾 Scaler saved to:", SCALER_PATH)

if __name__ == "__main__":
    main()
