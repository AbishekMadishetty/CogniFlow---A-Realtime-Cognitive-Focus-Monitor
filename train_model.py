"""
CogniFlow — Machine Learning Validation Layer
Trains a Random Forest classifier on the logged session data.
Matches the hyperparameters and feature importance metrics from the research paper.
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score, classification_report
import joblib
import os

CSV_FILE = "cogniflow_log.csv"

def main():
    if not os.path.exists(CSV_FILE):
        print(f"Error: {CSV_FILE} not found. Run the engine first to generate data.")
        return

    print("Loading session data...")
    df = pd.read_csv(CSV_FILE)

    # Filter out session start markers to only train on actual data frames
    df = df[df['Type'] == 'DATA'].copy()
    
    if len(df) < 50:
        print(f"Not enough data to train. Current samples: {len(df)}. Let the engine run longer.")
        return

    print(f"Total training samples available: {len(df)}")

    # ── Feature Engineering ───────────────────────────────────────────────────
    # Encode categorical text into a "context category index"
    le_state = LabelEncoder()
    le_activity = LabelEncoder()

    df['State_Idx'] = le_state.fit_transform(df['State'].astype(str))
    df['Activity_Idx'] = le_activity.fit_transform(df['Activity'].astype(str))

    # Map the features available in the CSV to those described in the model
    # Note: Mouse displacement is captured implicitly via 'Activity' and 'State' updates
    features = ['EAR', 'Yawns', 'Variance', 'Activity_Idx', 'State_Idx', 'EyeCloses']
    
    # Target variable is the 6-class focus label
    X = df[features]
    y = df['Label'] 

    # ── Model Training ────────────────────────────────────────────────────────
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    print("Training Random Forest Classifier...")
    # Initializing with the exact hyperparameters from Table 1
    rf_model = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1
    )

    rf_model.fit(X_train, y_train)
    y_pred = rf_model.predict(X_test)

    # ── Evaluation ────────────────────────────────────────────────────────────
    test_accuracy = accuracy_score(y_test, y_pred)
    
    print("\n" + "="*40)
    print("  COGNIFLOW MODEL EVALUATION")
    print("="*40)
    print(f"Test accuracy:              {test_accuracy * 100:.1f}%")

    print("Calculating 5-fold cross-validation...")
    cv_scores = cross_val_score(rf_model, X, y, cv=5)
    print(f"5-fold cross-val. accuracy: {cv_scores.mean() * 100:.1f}%")

    print("\n" + "="*40)
    print("  FEATURE IMPORTANCES")
    print("="*40)
    
    # Extract and sort feature importances
    importances = rf_model.feature_importances_
    feature_imp_df = pd.DataFrame({'Feature': features, 'Importance': importances})
    feature_imp_df = feature_imp_df.sort_values(by='Importance', ascending=False)
    
    for _, row in feature_imp_df.iterrows():
        print(f"{row['Feature']:<25} {row['Importance'] * 100:.1f}%")

    # ── Save Model ────────────────────────────────────────────────────────────
    joblib.dump(rf_model, 'cogniflow_rf_model.pkl')
    joblib.dump(le_state, 'le_state.pkl')
    joblib.dump(le_activity, 'le_activity.pkl')
    print("\nModel and encoders successfully saved to disk (.pkl).")

if __name__ == "__main__":
    main()  