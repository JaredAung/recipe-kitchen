# Experiment: on-screen text OCR for recipe videos

## Objective

Select an OCR engine for extracting on-screen text (titles, ingredient overlays, captions) from cooking videos. Two engines were compared: **Tesseract** and **PaddleOCR**.

## Preliminary finding: Burmese video overlays

Burmese recipe videos (`tests/test1.mp4`, `tests/test2.mp4`) were tried first. Overlay OCR failed: the readable on-screen text is almost always subtitles that restated the narration, so the signal duplicated speech-to-text rather than adding ingredients or steps.

**Scope for this experiment:** English on-screen text only, until a Burmese video is found where overlays carry information that is not in the audio.

## Setup

Both engines ran in a single pass on the same raw stills. No engine-specific preprocess, upsample, threshold, page-segmentation search, or confidence cutoff.

| Item | Value |
|---|---|
| Language | English |
| Inputs | `benchmark/OCR/test_images/c.png`, `d.png` |
| Preprocess | None (raw PNG) |
| Passes | One per image |
| Post-filter | Drop lines with fewer than two Latin letters |
| Outputs | `benchmark/OCR/transcripts/{stem}_{engine}.txt` |

### Tesseract (`tesseract.py`)

- Binary: system Tesseract 5.5.3, `-l eng --psm 3` (default fully automatic page segmentation)

### PaddleOCR (`paddleOCR.py`)

- Runtime: local Python 3.13 venv, CPU, ONNX Runtime
- Model: PP-OCRv5 mobile detector (`PP-OCRv5_mobile_det`) then English recognizer (`en_PP-OCRv5_mobile_rec`)
- Document orientation, unwarping, and text-line orientation off

The remaining difference is architectural: PaddleOCR detects text regions before recognition; Tesseract OCRs the full page. That is part of each engine, not extra pipeline help.

## Result

| Image | Ground-truth text | Tesseract | PaddleOCR |
|---|---|---|---|
| `c.png` (tight crop) | Capsicum | `‘Capsicum` | `Capsicum` |
| `d.png` (full frame) | NOT A COOK; Capsicum | empty | `NOT A COOK` / `Capsicum` |

PaddleOCR read both frames cleanly. Tesseract nearly got the cropped overlay and returned nothing on the full cooking frame.

## Decision

Use **PaddleOCR** for English on-screen text. Revisit Burmese OCR only if a test video has overlays that are not redundant with narration.
