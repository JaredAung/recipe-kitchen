"""Detect and recognize English text with PaddleOCR."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
VENV_PYTHON = SCRIPT_DIR / ".venv" / "bin" / "python"
if VENV_PYTHON.exists() and Path(sys.executable).resolve() != VENV_PYTHON.resolve():
    os.execv(str(VENV_PYTHON), [str(VENV_PYTHON), *sys.argv])
os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")

ROOT = SCRIPT_DIR.parents[1]
IMAGE_DIR = SCRIPT_DIR / "test_images"
OUTPUT_DIR = SCRIPT_DIR / "transcripts"
FRAME_FPS = 1
LETTER_RE = re.compile(r"[A-Za-z]")
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".webp", ".bmp"}
VIDEO_SUFFIXES = {".mp4", ".mov", ".mkv", ".webm"}


def require_bin(name: str, hint: str) -> str:
    path = shutil.which(name)
    if path is None:
        sys.exit(f"{name} not found. Install it first, e.g. `{hint}`.")
    return path


def require_ocr():
    try:
        from paddleocr import PaddleOCR
    except ImportError:
        sys.exit(
            "paddleocr is missing. Create a 3.13 venv in this folder and install it:\n"
            "  uv venv --python 3.13 --no-project benchmark/OCR/.venv\n"
            "  uv pip install --python benchmark/OCR/.venv/bin/python paddleocr onnxruntime pillow"
        )
    kwargs = {
        "lang": "en",
        "ocr_version": "PP-OCRv5",
        "text_detection_model_name": "PP-OCRv5_mobile_det",
        "text_recognition_model_name": "en_PP-OCRv5_mobile_rec",
        "device": "cpu",
        "use_doc_orientation_classify": False,
        "use_doc_unwarping": False,
        "use_textline_orientation": False,
    }
    try:
        return PaddleOCR(engine="onnxruntime", **kwargs)
    except Exception:
        return PaddleOCR(**kwargs)


def list_images(image_dir: Path) -> list[Path]:
    images = sorted(
        path
        for path in image_dir.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
    )
    if not images:
        sys.exit(f"No images found in {image_dir}")
    return images


def extract_frames(ffmpeg: str, video_path: Path, frame_dir: Path) -> list[Path]:
    frame_dir.mkdir(parents=True, exist_ok=True)
    pattern = frame_dir / f"{video_path.stem}_%03d.png"
    result = subprocess.run(
        [
            ffmpeg,
            "-nostdin",
            "-y",
            "-i",
            str(video_path),
            "-vf",
            f"fps={FRAME_FPS}",
            str(pattern),
        ],
        capture_output=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"ffmpeg failed for {video_path.name}:\n{result.stderr.decode().strip()}"
        )
    return sorted(frame_dir.glob(f"{video_path.stem}_*.png"))


def result_payload(result) -> dict:
    if isinstance(result, dict):
        return result.get("res", result)
    json_data = getattr(result, "json", None)
    if callable(json_data):
        json_data = json_data()
    if isinstance(json_data, dict):
        return json_data.get("res", json_data)
    return {
        "rec_texts": getattr(result, "rec_texts", []),
        "rec_scores": getattr(result, "rec_scores", []),
        "rec_boxes": getattr(result, "rec_boxes", []),
        "rec_polys": getattr(result, "rec_polys", []),
    }


def as_list(value) -> list:
    if value is None:
        return []
    if hasattr(value, "tolist"):
        value = value.tolist()
    return list(value)


def poly_box(poly) -> tuple[int, int, int, int]:
    xs = [int(point[0]) for point in poly]
    ys = [int(point[1]) for point in poly]
    return min(xs), min(ys), max(xs), max(ys)


def line_box(box, poly) -> tuple[int, int, int, int]:
    if box is not None and len(box) >= 4:
        x0, y0, x1, y1 = (int(v) for v in box[:4])
        return x0, y0, x1, y1
    if poly is not None:
        return poly_box(poly)
    return 0, 0, 0, 0


def iter_lines(result) -> list[tuple[str, float, tuple[int, int, int, int]]]:
    payload = result_payload(result)
    texts = as_list(payload.get("rec_texts"))
    scores = as_list(payload.get("rec_scores"))
    boxes = as_list(payload.get("rec_boxes"))
    polys = as_list(payload.get("rec_polys"))
    lines: list[tuple[str, float, tuple[int, int, int, int]]] = []
    for index, raw in enumerate(texts):
        text = str(raw).strip()
        score = float(scores[index]) if index < len(scores) else 1.0
        if len(LETTER_RE.findall(text)) < 2:
            continue
        box = boxes[index] if index < len(boxes) else None
        poly = polys[index] if index < len(polys) else None
        lines.append((text, score, line_box(box, poly)))
    return sorted(lines, key=lambda item: (item[2][1], item[2][0]))


def ocr_image(ocr, image_path: Path) -> str:
    outputs = ocr.predict(str(image_path))
    if not outputs:
        return ""
    lines = iter_lines(outputs[0])
    return "\n".join(text for text, _score, _box in lines).strip()


def save_transcript(stem: str, text: str) -> Path:
    output_path = OUTPUT_DIR / f"{stem}_paddleocr.txt"
    output_path.write_text((text + "\n") if text else "", encoding="utf-8")
    return output_path


def process_image(ocr, image_path: Path) -> None:
    print(f"OCR {image_path.name} with en...")
    text = ocr_image(ocr, image_path)
    output_path = save_transcript(image_path.stem, text)
    print("\n--- text ---")
    print(text or "(empty)")
    print(f"\nSaved {output_path}\n")


def process_video(ocr, ffmpeg: str, video_path: Path, work_dir: Path) -> None:
    print(f"Extracting {FRAME_FPS} fps from {video_path.name}...")
    frames = extract_frames(ffmpeg, video_path, work_dir)
    for frame_path in frames:
        process_image(ocr, frame_path)


def main() -> None:
    extra = [Path(arg) for arg in sys.argv[1:]]
    inputs = extra if extra else list_images(IMAGE_DIR)
    for path in inputs:
        if not path.is_file():
            sys.exit(f"File not found: {path}")
        suffix = path.suffix.lower()
        if suffix not in IMAGE_SUFFIXES and suffix not in VIDEO_SUFFIXES:
            sys.exit(f"Unsupported file type: {path}")

    ocr = require_ocr()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    needs_ffmpeg = any(path.suffix.lower() in VIDEO_SUFFIXES for path in inputs)
    ffmpeg = require_bin("ffmpeg", "brew install ffmpeg") if needs_ffmpeg else ""

    with tempfile.TemporaryDirectory(dir=SCRIPT_DIR, prefix=".ocr_frames_") as tmp:
        work_dir = Path(tmp)
        for path in inputs:
            if path.suffix.lower() in VIDEO_SUFFIXES:
                process_video(ocr, ffmpeg, path, work_dir)
            else:
                process_image(ocr, path)


if __name__ == "__main__":
    main()
