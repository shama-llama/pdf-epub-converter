import pandas as pd
from typing import List, Dict, Any

def featurize(elements: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Converts a list of text elements into a pandas DataFrame of features.

    Args:
        elements: A list of dictionaries, where each dictionary represents
                  a text element with properties like 'text', 'bbox', etc.

    Returns:
        A pandas DataFrame where each row corresponds to an element and
        each column is a feature.
    """
    features = []
    for el in elements:
        bbox = el["bbox"]
        text = el.get("text", "")
        
        # Bbox features
        x0, y0, x1, y1 = bbox
        width = x1 - x0
        height = y1 - y0
        
        # Normalize position by page height, with a fallback
        page_height = el.get("page_height", 1)
        if page_height == 0:
            page_height = 1
        rel_y0 = y0 / page_height
        
        # Text features
        text_len = len(text)
        word_count = len(text.split())
        
        # Ratio of uppercase characters
        cap_ratio = sum(1 for c in text if c.isupper()) / (text_len + 1e-5)
        
        features.append({
            "width": width,
            "height": height,
            "x0": x0,
            "rel_y0": rel_y0,
            "text_len": text_len,
            "word_count": word_count,
            "cap_ratio": cap_ratio,
            "label": el.get("type", "") # Include label for training
        })
    return pd.DataFrame(features) 