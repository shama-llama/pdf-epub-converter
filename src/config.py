from pathlib import Path

# Base directory for the project
BASE_DIR = Path(__file__).resolve().parent.parent

# Data directories
DATA_DIR = BASE_DIR / "data"
INPUT_DIR = DATA_DIR / "input"
OUTPUT_DIR = DATA_DIR / "output"

# Input files
PDF_PATH = INPUT_DIR / "China's Revolution and the Quest for a Socialist Future.pdf"
LABELED_DATA_PATH = DATA_DIR / "labeled_document_data.json"

# Output files
RAW_EXTRACTION_PATH = OUTPUT_DIR / "raw_extraction.jsonl"
OUTLINE_PATH = OUTPUT_DIR / "outline.json"
PREDICTED_LAYOUT_PATH = OUTPUT_DIR / "predicted_layout.jsonl"
AST_PATH = OUTPUT_DIR / "ast.json"
EPUB_PATH = OUTPUT_DIR / "book.epub"

# Model files
MODEL_OUTPUT_PATH = OUTPUT_DIR / "layout_model.joblib"
SCALER_OUTPUT_PATH = OUTPUT_DIR / "scaler.joblib"

# Template files
TEMPLATE_DIR = BASE_DIR / "templates"
CSS_STYLE_PATH = TEMPLATE_DIR / "style.css"
MAIN_TEMPLATE_PATH = TEMPLATE_DIR / "main.xhtml.j2" 