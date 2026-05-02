"""
OCR scanned PDFs in a folder using EasyOCR (Russian + English).
Writes results into a single text file with per-file sections.

Usage: python ocr_pdfs.py <folder_or_list_of_files> <output.txt>
       The first argument can be either a folder (recursive scan for PDFs)
       or a glob/list of pdf files.
"""
import sys
import os
from pathlib import Path
import pypdfium2 as pdfium

def needs_ocr(path):
    """Return True if PDF has effectively no extractable text."""
    try:
        pdf = pdfium.PdfDocument(str(path))
        for i in range(len(pdf)):
            page = pdf.get_page(i)
            text = page.get_textpage().get_text_range()
            if len(text.strip()) > 50:
                return False
        return True
    except Exception:
        return True

def render_page(pdf, idx, scale=2.0):
    """Return a PIL Image of page idx at given scale."""
    page = pdf.get_page(idx)
    pil_img = page.render(scale=scale).to_pil()
    return pil_img

def ocr_pdf(reader, path):
    """OCR a single PDF, return text."""
    pdf = pdfium.PdfDocument(str(path))
    parts = []
    for i in range(len(pdf)):
        img = render_page(pdf, i)
        # easyocr.readtext returns list of (bbox, text, confidence)
        results = reader.readtext(
            img.tobytes() if False else __import__('numpy').array(img),
            paragraph=True,
            detail=0,
        )
        page_text = "\n".join(results) if results else ""
        parts.append(f"\n--- Page {i+1} ---\n{page_text}")
        print(f"  page {i+1}/{len(pdf)} done", file=sys.stderr)
    return "\n".join(parts)

def main():
    if len(sys.argv) < 3:
        print("usage: ocr_pdfs.py <folder> <output.txt>")
        sys.exit(1)
    target = Path(sys.argv[1])
    output = Path(sys.argv[2])

    if target.is_dir():
        files = sorted(target.rglob("*.pdf"))
    else:
        files = [target]

    files = [f for f in files if needs_ocr(f)]
    print(f"will OCR {len(files)} files", file=sys.stderr)
    if not files:
        print("nothing to OCR", file=sys.stderr)
        return

    print("loading easyocr (Russian + English)...", file=sys.stderr)
    import easyocr
    reader = easyocr.Reader(["ru", "en"], gpu=False)
    print("ready", file=sys.stderr)

    with open(output, "w", encoding="utf-8") as f:
        for path in files:
            rel = path.name
            try:
                rel = path.relative_to(target if target.is_dir() else target.parent)
            except ValueError:
                pass
            f.write(f"\n\n{'#'*80}\n# OCR FILE: {rel}\n{'#'*80}\n\n")
            print(f"OCR: {rel}", file=sys.stderr)
            try:
                text = ocr_pdf(reader, path)
                f.write(text)
            except Exception as e:
                f.write(f"[ERROR: {e}]")
                print(f"  error: {e}", file=sys.stderr)
            f.flush()
    print(f"done -> {output}", file=sys.stderr)

if __name__ == "__main__":
    main()
