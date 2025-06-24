import json
import os
from jinja2 import Environment, FileSystemLoader
from ebooklib import epub, ITEM_DOCUMENT
from pathlib import Path

from src import config

def load_ast(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def render_chapter(env, chapter_data):
    template = env.get_template("main.xhtml.j2")
    return template.render(chapter=chapter_data)

def main():
    print("[INFO] Loading AST...")
    ast = load_ast(config.AST_PATH)
    
    # Create output dir if it doesn't exist
    Path(config.OUTPUT_DIR).mkdir(exist_ok=True)

    # Setup Jinja2
    env = Environment(loader=FileSystemLoader(config.TEMPLATE_DIR))

    # Create a new EPUB book
    book = epub.EpubBook()
    book.set_identifier("id123456")
    book.set_title(ast.get("metadata", {}).get("title", "Untitled Book"))
    book.set_language("en")

    # Add author if available
    author = ast.get("metadata", {}).get("author")
    if author:
        book.add_author(author)

    # Add CSS stylesheet
    style_content = ""  # Default to empty string
    if os.path.exists(config.CSS_STYLE_PATH):
        with open(config.CSS_STYLE_PATH, "r", encoding="utf-8") as f:
            style_content = f.read()
    
    style_item = epub.EpubItem(
        uid="style_main",
        file_name="style/main.css",
        media_type="text/css",
        content=style_content,
    )
    book.add_item(style_item)

    # Process and add chapters
    chapters_to_add = []
    all_sections = ast.get("frontmatter", []) + ast.get("chapters", []) + ast.get("backmatter", [])

    for i, chapter_data in enumerate(all_sections):
        # Skip empty chapters
        if not chapter_data.get("elements"):
            print(f"[WARN] Skipping empty chapter: {chapter_data.get('title', 'Untitled')}")
            continue

        html_content = render_chapter(env, chapter_data)
        
        # Another check to ensure we don't add empty content
        if not html_content.strip():
            print(f"[WARN] Skipping chapter with empty rendered content: {chapter_data.get('title', 'Untitled')}")
            continue
            
        file_name = f"chapter_{i}.xhtml"
        
        epub_chapter = epub.EpubHtml(
            title=chapter_data["title"],
            file_name=file_name,
            content=html_content,
            lang="en"
        )
        epub_chapter.add_item(style_item)
        book.add_item(epub_chapter)
        chapters_to_add.append(epub_chapter)

    if not chapters_to_add:
        print("[ERROR] No content to add to the EPUB. Aborting.")
        return

    # Define the book spine
    book.spine = chapters_to_add

    # Define the TOC from the chapters we are actually adding
    book.toc = tuple(epub.Link(chapter.file_name, chapter.title, f'chapter-{i}') for i, chapter in enumerate(chapters_to_add))

    # Add default NCX and Nav file
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    # Write the EPUB file
    print("[INFO] Writing EPUB file...")
    epub.write_epub(config.EPUB_PATH, book, {"epub3_pages": False})
    
    print(f"[INFO] EPUB saved to {config.EPUB_PATH}")

if __name__ == "__main__":
    main() 