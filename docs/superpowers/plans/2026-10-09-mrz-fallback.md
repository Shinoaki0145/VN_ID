# MRZ fallback and back-card OCR implementation plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan task by task. Keep changes uncommitted for the user's review, as in the preceding fix.

**Goal:** Read issue date and issuer reliably on outputs 8–11, and fill missing identity/expiry fields from MRZ while reporting disagreements.

**Architecture:** Detect a plausible card quadrilateral before resizing. Read MRZ lines with the existing Latin recognizer alongside VietOCR, parse fixed positions with field checksums, then fuse validated candidates after QR and printed text.

**Tech Stack:** Python, OpenCV, EasyOCR, VietOCR, Pydantic, pytest; existing local models only.

**Spec:** User request and clarification: fill missing fields and cross-check existing values. CCCD ID is line 1 positions 16–27; DOB is line 2 positions 1–6; gender position 8; expiry positions 9–14 (one-based).

## Global Constraints

- Updated user scope: allow MRZ gender independently of a verified ID; leave DOB null when birth century is unavailable. Preserve QR/front priority and existing gender consistency checks when ID is available.
- Updated user scope: remove the separate personal-number checksum and warnings about an unchecked province prefix when the MRZ tail is incomplete; retain independent field checks and cross-checks with QR/front data.
- Preserve QR/front priority and report disagreements; never silently replace existing fields.
- MRZ supplies no issue date, issuer, or accented name.
- Reject failed checksums and impossible calendar dates; derive DOB century from verified CCCD ID.
- Preserve ordinary OCR when optional Latin recognition fails and log the failure; provision the required Latin weights when missing, including on fresh Colab deployments.
- Save fresh outputs separately from the original output snapshots.

## Review Focus

- Partial MRZ filler: independent field checks remain usable; unavailable composite check stays null.
- Conflicting valid OCR candidates: abstain rather than choose an arbitrary identity.
- Wrong DOB century and expiry beyond 2050: use CCCD century and a 2000-based expiry.
- Background resembling a card: conservative shape checks and resize fallback.
- Existing 2024 address extraction and old issuer recognition must remain correct.

### Task 1: Validated MRZ parsing and fusion

**Files:** `vn_id/parser/mrz.py`, `vn_id/parser/back.py`, `vn_id/core/schemas.py`, `vn_id/validator/fusion.py`, `tests/test_mrz.py`.

**Interfaces:** `parse_mrz(text: str, alternate_text: str | None = None) -> MRZResult | None`; `BackRuleExtractor.extract(text, mrz_text=None)`; nested `BackSideResult.mrz`; `ValidationReport.mrz_checks` and `mrz_checksums`.

- [x] Write tests for the four image transcripts, missing-field filling, disagreements, bad checksums, invalid dates, ambiguous candidates, partial lines and numeric OCR substitutions.
- [x] Run `.venv/bin/python -m pytest tests/test_mrz.py -q` and verify failures expose missing behavior.
- [x] Implement fixed-position parsing with weights 7/3/1 and optional composite verification; integrate fallback before gender deduction and compare independently sourced fields.
- [x] Run parser/fusion regression tests and confirm they pass.

### Task 2: Card alignment and dedicated MRZ OCR

**Files:** `vn_id/aligner/detector.py`, `vn_id/ocr/engine.py`, `vn_id/pipeline.py`, `tests/test_aligner.py`, `tests/test_ocr_engine.py`.

**Interfaces:** Existing `align(image, corners=None)` auto-detects conservative four-corner candidates; additive `OCRResult.mrz_text` is passed by both pipeline paths to the back parser.

- [x] Add failing tests for a card surrounded by background, blank-image fallback, whole-line MRZ grouping and optional-recognizer failure.
- [x] Implement edge/color contour detection; read lower-card MRZ using the installed Latin model with restricted characters and merged line boxes.
- [x] Run alignment/OCR/pipeline regression tests.

### Task 3: Real-image verification

**Files:** `tests/test_user_image_e2e.py`, `output/mrz_fix/`.

- [x] Add expected identity, dates and issuer assertions for back_cu_8, 14, 16 and 18.
- [x] Run the complete pytest suite, including earlier 2024-address regressions.
- [x] Generate separate result/OCR/aligned-image artifacts for outputs 8–11 and review the final diff.
