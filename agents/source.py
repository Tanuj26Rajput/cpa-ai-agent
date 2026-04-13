import os
from email import policy
from email.parser import BytesParser
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
EMAIL_ATTACHMENT_DIR = DATA_DIR / "email_attachments"
SUPPORTED_SUFFIXES = {".pdf", ".txt", ".md", ".eml"}


def _latest_supported_file(directory):
    candidates = [
        path
        for path in directory.iterdir()
        if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES
    ]
    if not candidates:
        raise FileNotFoundError(f"No supported files found in {directory}")
    return max(candidates, key=lambda path: path.stat().st_mtime)


def _extract_first_attachment_from_eml(eml_path):
    EMAIL_ATTACHMENT_DIR.mkdir(parents=True, exist_ok=True)
    with eml_path.open("rb") as handle:
        message = BytesParser(policy=policy.default).parse(handle)

    for part in message.iter_attachments():
        filename = part.get_filename()
        if not filename:
            continue
        suffix = Path(filename).suffix.lower()
        if suffix not in {".pdf", ".txt", ".md"}:
            continue

        target = EMAIL_ATTACHMENT_DIR / filename
        payload = part.get_payload(decode=True)
        target.write_bytes(payload or b"")
        return target

    raise FileNotFoundError(f"No supported attachment found in {eml_path}")


def resolve_input(source_type="auto", location=None):
    if source_type == "auto":
        source_type = "local"

    if source_type == "local":
        if location is None:
            for candidate in (
                DATA_DIR / "order_10248.pdf",
                DATA_DIR / "order_10264.pdf",
                DATA_DIR / "sample.txt",
            ):
                if candidate.exists():
                    return {
                        "source_type": "local",
                        "source_label": "Local workspace file",
                        "document_path": candidate,
                    }
            raise FileNotFoundError("No default local input file found in data/")

        path = Path(location)
        if path.is_dir():
            path = _latest_supported_file(path)
        if not path.exists():
            raise FileNotFoundError(f"Input file not found: {path}")

        if path.suffix.lower() == ".eml":
            attachment_path = _extract_first_attachment_from_eml(path)
            return {
                "source_type": "email",
                "source_label": f"Email attachment from {path.name}",
                "document_path": attachment_path,
            }

        return {
            "source_type": "local",
            "source_label": "Local workspace file",
            "document_path": path,
        }

    if source_type == "gdrive":
        base_dir = Path(location or os.getenv("GDRIVE_DROP_DIR", DATA_DIR))
        file_path = _latest_supported_file(base_dir)
        return {
            "source_type": "gdrive",
            "source_label": f"GDrive sync folder: {base_dir}",
            "document_path": file_path,
        }

    if source_type == "email":
        base_path = Path(location or os.getenv("EMAIL_DROP_DIR", DATA_DIR))
        eml_path = base_path if base_path.is_file() else _latest_supported_file(base_path)
        if eml_path.suffix.lower() != ".eml":
            return {
                "source_type": "email",
                "source_label": f"Email drop folder: {base_path}",
                "document_path": eml_path,
            }
        attachment_path = _extract_first_attachment_from_eml(eml_path)
        return {
            "source_type": "email",
            "source_label": f"Email attachment from {eml_path.name}",
            "document_path": attachment_path,
        }

    raise ValueError(f"Unsupported source type: {source_type}")
