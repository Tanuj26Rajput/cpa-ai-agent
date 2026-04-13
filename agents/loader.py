from pathlib import Path

import pdfplumber


def load_document(file_path):
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Document not found: {file_path}")

    suffix = path.suffix.lower()

    if suffix == ".pdf":
        text = ""
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                text += page_text + "\n"

        if not text.strip():
            raise ValueError("No readable text found in the PDF")

        return text

    if suffix in {".txt", ".md"}:
        text = path.read_text(encoding="utf-8")
        if not text.strip():
            raise ValueError(f"No readable text found in {path.name}")
        return text

    raise ValueError(f"Unsupported file type: {suffix}")


def load_pdf(file_path):
    return load_document(file_path)
