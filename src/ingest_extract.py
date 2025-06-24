import sys
import os
import fitz
import json

from src import config


def ensure_output_dir():
    if not os.path.exists(config.OUTPUT_DIR):
        os.makedirs(config.OUTPUT_DIR)
        print(f"[INFO] Created output directory: {config.OUTPUT_DIR}")
    else:
        print(f"[INFO] Output directory already exists: {config.OUTPUT_DIR}")

def extract_with_pymupdf(pdf_path):
    print("[INFO] Extracting with PyMuPDF...")
    try:
        doc = fitz.open(pdf_path)
        
        # First, yield the outline
        outline = doc.get_toc()
        yield {"type": "outline", "data": outline}
        print(f"[INFO] PDF outline/bookmarks: {len(outline)} entries")

        # Then, yield each page's data
        for page_num, page in enumerate(doc, 1):
            text_dict = page.get_text("dict")
            page_meta = {
                "number": page_num,
                "width": page.rect.width,
                "height": page.rect.height,
                "rotation": page.rotation,
            }
            page_data = {
                "type": "page",
                "meta": page_meta,
                "text_runs": [],
                "images": []
            }
            # Text runs
            for block in text_dict["blocks"]:
                if block["type"] == 0:  # text
                    for line in block["lines"]:
                        for span in line["spans"]:
                            run = {
                                "text": span["text"],
                                "font": span["font"],
                                "size": span["size"],
                                "bbox": span["bbox"]
                            }
                            page_data["text_runs"].append(run)
                            print(f"  [TEXT] '{span['text'][:40]}' (font: {span['font']}, size: {span['size']}, bbox: {span['bbox']})")
            # Image extraction
            images = page.get_images(full=True)
            for img_idx, img in enumerate(images):
                xref = img[0]
                try:
                    img_info = doc.extract_image(xref)
                    if not img_info:
                        print(f"  [WARNING] Could not extract image xref {xref} on page {page_num}. Skipping.")
                        continue
                    img_bytes = img_info["image"]
                    ext = img_info.get("ext", "png")
                    img_path = os.path.join(config.OUTPUT_DIR, f"page{page_num}_img{img_idx}_xref{xref}.{ext}")
                    with open(img_path, "wb") as f:
                        f.write(img_bytes)
                    img_record = {
                        "xref": xref,
                        "path": img_path,
                        "width": img_info.get("width"),
                        "height": img_info.get("height"),
                        "ext": ext
                    }
                    page_data["images"].append(img_record)
                    print(f"  [IMAGE] Saved image to {img_path}")
                except Exception as img_e:
                    print(f"  [ERROR] Failed to extract image xref {xref} on page {page_num}: {img_e}")
            
            yield page_data
        
        print("[INFO] PyMuPDF extraction complete.")
        
    except Exception as e:
        print(f"[ERROR] PyMuPDF extraction failed: {e}")

def main():
    ensure_output_dir()
    if not os.path.exists(config.PDF_PATH):
        print(f"[ERROR] PDF file not found: {config.PDF_PATH}")
        sys.exit(1)

    with open(config.RAW_EXTRACTION_PATH, "w", encoding="utf-8") as f_jsonl:
        for item in extract_with_pymupdf(config.PDF_PATH):
            if item.get("type") == "outline":
                with open(config.OUTLINE_PATH, "w", encoding="utf-8") as f_outline:
                    json.dump(item["data"], f_outline, ensure_ascii=False, indent=2)
                print(f"[INFO] Saved outline data to {config.OUTLINE_PATH}")
            elif item.get("type") == "page":
                f_jsonl.write(json.dumps(item, ensure_ascii=False) + '\n')
    
    print(f"[INFO] Saved page-by-page extraction data to {config.RAW_EXTRACTION_PATH}")

if __name__ == "__main__":
    main() 