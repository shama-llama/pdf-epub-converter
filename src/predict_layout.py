import json
import pandas as pd
import joblib
import os
import fitz # PyMuPDF

from features import featurize
from src import config

def get_page_dimensions(pdf_path):
    doc = fitz.open(pdf_path)
    dims = [(p.rect.width, p.rect.height) for p in doc]
    doc.close()
    return dims

def process_raw_blocks(raw_path, page_dims):
    elements = []
    with open(raw_path, "r", encoding="utf-8") as f:
        for line in f:
            page_data = json.loads(line)
            if page_data.get("type") != "page":
                continue
            
            page_num = page_data["meta"]["number"]
            width, height = page_dims[page_num - 1] if page_num <= len(page_dims) else (1, 1)
            
            for run in page_data.get("text_runs", []):
                elements.append({
                    "id": f"p{page_num}_b{len(elements)}",
                    "type": "", # To be predicted
                    "text": run["text"],
                    "bbox": run["bbox"],
                    "page_width": width,
                    "page_height": height,
                    "doc_name": os.path.basename(config.PDF_PATH)
                })
    return elements

def main():
    print("[INFO] Loading model and scaler...")
    model = joblib.load(config.MODEL_OUTPUT_PATH)
    scaler = joblib.load(config.SCALER_OUTPUT_PATH)

    print(f"[INFO] Getting page dimensions from {config.PDF_PATH}...")
    page_dims = get_page_dimensions(config.PDF_PATH)

    print(f"[INFO] Processing raw blocks from {config.RAW_EXTRACTION_PATH}...")
    elements = process_raw_blocks(config.RAW_EXTRACTION_PATH, page_dims)
    
    if not elements:
        print("[ERROR] No elements found to predict. Aborting.")
        return

    print(f"[INFO] Generating features for {len(elements)} blocks...")
    df = featurize(elements)
    
    # We only need the feature columns, not the label
    features = df.drop("label", axis=1)
    
    print("[INFO] Scaling features...")
    features_scaled = scaler.transform(features)
    
    print("[INFO] Predicting labels...")
    predictions = model.predict(features_scaled)
    
    print("[INFO] Saving predictions...")
    with open(config.PREDICTED_LAYOUT_PATH, "w", encoding="utf-8") as f:
        for i, element in enumerate(elements):
            element["type"] = predictions[i]
            # Clean up for final output
            del element["page_width"]
            del element["page_height"]
            del element["doc_name"]
            f.write(json.dumps(element) + '\n')
            
    print(f"[INFO] Predictions saved to {config.PREDICTED_LAYOUT_PATH}")

if __name__ == "__main__":
    main() 