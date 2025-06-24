import json
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report
from sklearn.preprocessing import StandardScaler
import joblib
import numpy as np

from features import featurize
from src import config

def load_and_flatten_data(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    all_elements = []
    for doc_name, content in data.items():
        for page in content["document_analysis"]["pages"]:
            page_height = max(el["bbox"][3] for el in page["elements"]) if page["elements"] else 1
            page_width = max(el["bbox"][2] for el in page["elements"]) if page["elements"] else 1
            
            for element in page["elements"]:
                element_data = {
                    "id": element["id"],
                    "type": element["type"],
                    "text": element.get("text", ""),
                    "bbox": element["bbox"],
                    "page_width": page_width,
                    "page_height": page_height,
                    "doc_name": doc_name
                }
                all_elements.append(element_data)
    return all_elements

def main():
    print("[INFO] Loading and flattening data...")
    elements = load_and_flatten_data(config.LABELED_DATA_PATH)
    
    print("[INFO] Generating features...")
    df = featurize(elements)
    
    # Exclude rare classes for more stable training
    label_counts = df['label'].value_counts()
    to_keep = label_counts[label_counts > 1].index
    df = df[df['label'].isin(to_keep)]
    
    if df.empty:
        print("[ERROR] No data left after filtering rare classes. Aborting.")
        return

    print(f"[INFO] Training on {len(df)} samples.")
    print(f"[INFO] Label distribution:\n{df['label'].value_counts()}")

    X = df.drop("label", axis=1)
    y = df["label"]
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y
    )
    
    # Scale features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    print("[INFO] Training RandomForestClassifier...")
    model = RandomForestClassifier(n_estimators=100, random_state=42, class_weight='balanced')
    model.fit(X_train_scaled, y_train)
    
    print("[INFO] Evaluating model...")
    y_pred = model.predict(X_test_scaled)
    print(classification_report(y_test, y_pred))
    
    print(f"[INFO] Saving model to {config.MODEL_OUTPUT_PATH}")
    joblib.dump(model, config.MODEL_OUTPUT_PATH)
    joblib.dump(scaler, config.SCALER_OUTPUT_PATH)
    
    print("[INFO] Training complete.")

if __name__ == "__main__":
    main() 