import os
import json

from src import config

# Helper: map outline entries to page ranges
def outline_to_ranges(outline, total_pages):
    # outline: list of [level, title, page_num]
    toc = []
    chapter_ranges = []
    for i, entry in enumerate(outline):
        level, title, page_num = entry
        start = page_num - 1  # 0-based
        if i + 1 < len(outline):
            end = outline[i+1][2] - 2  # up to the page before next
        else:
            end = total_pages - 1
        toc.append({"title": title, "level": level, "start": start, "end": end})
        chapter_ranges.append((title, start, end))
    return toc, chapter_ranges

def main():
    # Load outline and count total pages
    try:
        with open(config.OUTLINE_PATH, "r", encoding="utf-8") as f:
            outline = json.load(f)
    except FileNotFoundError:
        print(f"[ERROR] Outline file not found at {config.OUTLINE_PATH}. Aborting.")
        return
        
    try:
        with open(config.RAW_EXTRACTION_PATH, "r", encoding="utf-8") as f:
            # We need to count only page entries
            total_pages = sum(1 for line in f if '"type": "page"' in line)
    except FileNotFoundError:
        print(f"[ERROR] Raw pages file not found at {config.RAW_EXTRACTION_PATH}. Aborting.")
        return

    # Load predicted layout elements
    elements = []
    try:
        with open(config.PREDICTED_LAYOUT_PATH, "r", encoding="utf-8") as f:
            for line in f:
                elements.append(json.loads(line))
    except FileNotFoundError:
        print(f"[ERROR] Predicted layout file not found at {config.PREDICTED_LAYOUT_PATH}. Aborting.")
        return

    # Assign page numbers to each element from its ID
    for el in elements:
        try:
            # ID is like "p12_b345"
            el['page_number'] = int(el['id'].split('_')[0][1:])
        except (ValueError, IndexError):
            el['page_number'] = 0 # Default if ID is malformed
            
    toc, chapter_ranges = outline_to_ranges(outline, total_pages)
    
    # Heuristic for metadata - we can get some from the raw pages if needed
    # For now, we'll keep it simple as it wasn't well-defined before.
    metadata = {
        "page_size": None, # Could be extracted from raw file if needed
        "rotation": None,
        "total_pages": total_pages
    }
    
    # Group elements into chapters
    frontmatter = []
    chapters = []
    backmatter = []
    
    for idx, (title, start, end) in enumerate(chapter_ranges):
        # page numbers are 1-based, start/end are 0-based
        chapter_elements = [el for el in elements if start < el.get("page_number", 0) <= end + 1]
        
        # Merge consecutive paragraph blocks
        merged_elements = []
        current_paragraph = ""
        for i, el in enumerate(chapter_elements):
            el_type = el.get("type")
            
            is_paragraph = el_type == "paragraph"
            is_last_element = i == len(chapter_elements) - 1
            next_el_is_paragraph = not is_last_element and chapter_elements[i+1].get("type") == "paragraph"

            if is_paragraph:
                # Append text to the current paragraph
                current_paragraph += el.get("text", "") + " "
                # If the next element is not a paragraph, or it's the last element,
                # finalize the current paragraph.
                if not next_el_is_paragraph or is_last_element:
                    merged_elements.append({
                        "type": "paragraph", 
                        "text": current_paragraph.strip(),
                        "page_number": el.get("page_number") # Use page number of last run
                    })
                    current_paragraph = "" # Reset
            else:
                # If there was a pending paragraph, add it first.
                if current_paragraph:
                    merged_elements.append({
                        "type": "paragraph", 
                        "text": current_paragraph.strip(),
                         # This page number might be slightly off, but it's an approximation
                        "page_number": el.get("page_number")
                    })
                    current_paragraph = ""

                # Add the non-paragraph element directly
                merged_elements.append(el)
        
        # If the last element was a paragraph, ensure it's added
        if current_paragraph:
             merged_elements.append({
                "type": "paragraph", 
                "text": current_paragraph.strip(),
                "page_number": chapter_elements[-1].get("page_number")
            })

        # Filter and transform elements for the AST
        processed_elements = []
        for el in merged_elements:
            el_type = el.get("type")
            
            # Skip elements that shouldn't be in the main content flow
            if el_type in ["running_header", "page_number", "header", "footer"]:
                continue
            
            # Map predicted types to a structured AST
            if el_type == "main_title":
                processed_elements.append({"type": "heading", "level": 1, "text": el.get("text"), "page_number": el.get("page_number")})

            elif "heading" in el_type:
                 # e.g., "heading_1" -> 1, "sub_heading" -> 2
                level = 1
                if "_" in el_type:
                    try:
                        level = int(el_type.split('_')[1])
                    except ValueError:
                        level = 2 # Default for sub_heading etc.
                elif el_type == "sub_heading":
                    level = 2

                processed_elements.append({"type": "heading", "level": level, "text": el.get("text"), "page_number": el.get("page_number")})
            
            elif el_type == "paragraph":
                processed_elements.append({"type": "paragraph", "text": el.get("text"), "page_number": el.get("page_number")})
            
            elif el_type == "list_item":
                # If the previous element was not a list, create a new one
                if not processed_elements or processed_elements[-1]["type"] != "list":
                    processed_elements.append({"type": "list", "items": [], "ordered": False, "page_number": el.get("page_number")})
                # Add the item to the last list
                processed_elements[-1]["items"].append(el.get("text"))

            elif el_type == "blockquote":
                 processed_elements.append({"type": "blockquote", "text": el.get("text"), "page_number": el.get("page_number")})

            elif el_type == "figure":
                processed_elements.append({"type": "figure", "src": el.get("src"), "caption": el.get("caption", ""), "page_number": el.get("page_number")})

            elif el_type == "caption":
                # Try to associate with the last figure
                if processed_elements and processed_elements[-1]["type"] == "figure":
                    processed_elements[-1]["caption"] = el.get("text")
                else: # Orphan caption, treat as a small paragraph
                    processed_elements.append({"type": "paragraph", "style": "caption", "text": el.get("text"), "page_number": el.get("page_number")})
            
            # Add other mappings from your taxonomy here...
            else:
                print(f"[WARN] Unhandled element type: '{el_type}'. Skipping.")

            
        chapter = {
            "title": title,
            "elements": processed_elements
        }
        
        # Assign to frontmatter, backmatter, or chapters
        if idx == 0 or title.lower() in ["cover", "copyright", "contents"]:
            frontmatter.append(chapter)
        elif title.lower() in ["index", "endnotes", "glossary of names", "bibliography"] or idx == len(chapter_ranges) - 1:
            backmatter.append(chapter)
        else:
            chapters.append(chapter)

    # Build final AST
    ast = {
        "metadata": metadata,
        "toc": toc,
        "frontmatter": frontmatter,
        "chapters": chapters,
        "backmatter": backmatter,
        "footnotes": [] # Footnote detection would need a separate model/logic
    }
    
    with open(config.AST_PATH, "w", encoding="utf-8") as f:
        json.dump(ast, f, ensure_ascii=False, indent=2)

    print(f"[INFO] Saved AST to {config.AST_PATH}")

if __name__ == "__main__":
    main() 