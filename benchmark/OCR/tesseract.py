"""Run English OCR on test images with Tesseract."""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
IMAGE_DIR = SCRIPT_DIR / "test_images"
OUTPUT_DIR = SCRIPT_DIR / "transcripts"
LANG = "eng"
PSM = 3  # Tesseract default: fully automatic page segmentation
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".webp", ".bmp"}
LETTER_RE = re.compile(r"[A-Za-z]")


def require_bin(name: str, hint: str) -> str:
    path = shutil.which(name)
    if path is None:
        sys.exit(f"{name} not found. Install it first, e.g. `{hint}`.")
    return path


def list_images(image_dir: Path) -> list[Path]:
    images = sorted(
        path
        for path in image_dir.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
    )
    if not images:
        sys.exit(f"No images found in {image_dir}")
    return images


def ocr_image(tesseract: str, image_path: Path) -> str:
    result = subprocess.run(
        [
            tesseract,
            str(image_path),
            "stdout",
            "-l",
            LANG,
            "--psm",
            str(PSM),
        ],
        capture_output=True,
    )
    if result.returncode != 0:
        return ""
    return result.stdout.decode("utf-8")


def clean_text(text: str) -> str:
    lines: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if len(LETTER_RE.findall(line)) >= 2:
            lines.append(line)
    return "\n".join(lines).strip()


def main() -> None:
    extra = [Path(arg) for arg in sys.argv[1:]]
    images = extra if extra else list_images(IMAGE_DIR)
    for image_path in images:
        if not image_path.is_file():
            sys.exit(f"Image not found: {image_path}")

    tesseract = require_bin("tesseract", "brew install tesseract")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for image_path in images:
        print(f"OCR {image_path.name} with {LANG}...")
        text = clean_text(ocr_image(tesseract, image_path))
        output_path = OUTPUT_DIR / f"{image_path.stem}_tesseract.txt"
        output_path.write_text((text + "\n") if text else "", encoding="utf-8")
        print("\n--- text ---")
        print(text or "(empty)")
        print(f"\nSaved {output_path}\n")


if __name__ == "__main__":
    main()
