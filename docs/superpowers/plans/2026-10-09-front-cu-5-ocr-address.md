# `front_cu_5` OCR Address Fix Plan

> **For agentic workers:** Use `superpowers:executing-plans` to implement this plan task by task. Check each item as it is completed.

**Goal:** Read both address fields on `image/front_cu_5.jpg` from front-side OCR without degrading other front images.

**Architecture:** Keep the current DBNet18 pass (`width_ths=0.75`) as the default. Recover a failed residence row with a conditional, local second detection pass (`width_ths=0.3`), and re-read split address lines from image pixels to recover characters between boxes. Stop the parser from inventing a residence from an unanchored province-name substring.

**Tech Stack:** Python, EasyOCR DBNet18, VietOCR VGG seq2seq, pytest.

**Spec:** Scope and acceptance criteria below.

## Scope and acceptance criteria

- Use only front-side OCR; no MRZ or QR value may supply either address.
- Expected `origin`: `Bình Hưng Hòa A, Bình Tân, TP. Hồ Chí Minh`.
- Expected `residence`: `24/12/29 LK 2-10, Kp 18, Bình Hưng Hòa A, Bình Tân, TP.HCM` (allow one consistent space after `TP.` if the repository normalizes that abbreviation).
- Preserve the existing passing OCR assertions for `front_cu.jpg` and `front_cu_4.jpg`, including address punctuation.
- If the residence label and address cannot be recovered, return `None` rather than a province guessed from unrelated text.
- Keep the primary detector settings and all back-side OCR paths unchanged.

## Measured cause

The checked-in snapshot `output/front_cu_5_ocr_no_qr/ocr.json` came from OCR with QR decoding/masking and MRZ recognition disabled. It contains `Bình Hưng Hòa Bình Tân` twice and no residence label or first residence line.

Both inputs are aligned to 1000×630, but their source detail is very different: `front_cu.jpg` is 2524×1650 and its detected card spans about 2218 pixels across; `front_cu_5.jpg` is 683×452 and its detected card spans about 602 pixels across. The aligner downsamples the first card and upsamples the second. It normalizes the outer card boundary, not the amount of readable text detail or the internal spacing of DBNet polygons. The origin label also starts at y=477 in the first aligned image versus y=487 in the second, so field rows do not land at identical pixel positions.

Reproduction used the checked-in `aligned.png`, Python 3.12, EasyOCR 1.7.2 DBNet18, and VietOCR `vgg_seq2seq.pth`. The actual detector's `width_ths=0.75` box `[95, 935, 543, 598]` spans the residence row and part of the lower row. VietOCR returned repeated digits with confidence `0.278`, below the engine's `0.35` acceptance threshold, so the whole box was discarded. At `width_ths=0.3`, DBNet18 instead returned `[273, 451, 546, 577]` (`Nơi thường trú`, `0.833`) and `[458, 934, 544, 589]` (`Place of residence: 24/12/29 LK 2-10`, `0.885`).

For the origin line, the primary detector split `[279, 512, 509, 548]` and `[549, 963, 507, 550]`, leaving `A,` in the gap. VietOCR on a single crop `[279, 505, 963, 553]` returned the complete expected origin with confidence `0.855`. On the lower residence line, the full crop recovered `A,` but changed `Tân` to `Tần`; a crop through the gap, `[274, 571, 655, 628]`, returned `Kp 18, Bình Hưng Hòa A,` with confidence `0.890`, while the original right box correctly read `Bình Tân, TP.HCM`.

Changing `width_ths` globally to `0.3` is rejected by the experiment: it removed address commas on `front_cu.jpg` and degraded `front_cu_4.jpg`. The parser's province fallback separately matches `Hoà Bình` as a substring across `Hòa Bình Tân` and assigns it to `residence` at `vn_id/parser/front.py:154-177`.

## Review focus

- A merged low-confidence box must not make a recoverable residence disappear.
- Re-reading a line must preserve existing words and diacritics; in particular, reject `Tần` when a box already says `Tân`.
- A missing residence anchor must not cause origin text to become residence.
- A second pass must not alter a clean front image or run on the back-side path.
- Crop geometry must stay within image bounds and work after the aligner produces a 1000×630 image.
- Test on both the high-resolution source (`front_cu.jpg`) and the low-resolution source (`front_cu_5.jpg`); alignment does not make their text quality equivalent.

## Tasks

### 1. Pin the failure and the regression set

**Files:** `tests/test_user_image_e2e.py`, `tests/test_front_rules.py`.

- [x] Add an OCR-only real-model fixture using `OCREngine` with a no-op `mask_qr_regions`, and skip clearly if DBNet18/VietOCR weights are absent. Do not require QReader or QR weights.
- [x] Add a failing real-image test for `front_cu_5.jpg`: align, recognize as front, parse `ocr.full_text`, then assert both exact address values above and that the source is front OCR.
- [x] Add a parser test using the checked-in failing `ocr.json`: `FrontRuleExtractor.extract_raw(full_text)` must leave `residence` absent instead of returning `Hoà Bình`.
- [x] Run each test and record the expected failure before changing product code.

### 2. Recover the merged residence row

**Files:** `vn_id/ocr/engine.py`, `tests/test_ocr_engine.py`, `tests/test_user_image_e2e.py`.

- [x] Add a small unit test with fake detector/recognizer results: a low-confidence front box spanning two address rows causes a second detect call with `width_ths=0.3`; valid right-column boxes from that pass are added, and unrelated boxes stay from the first pass. No second call for clean front or back input.
- [x] In `OCREngine.recognize`, retain the ordinary first-pass boxes. When an old front card has an origin anchor but no residence anchor and a rejected, oversized box in the lower right address region, run the second detect pass. Recognize only its boxes in that region and merge accepted results before sorting. Keep the existing `0.35` text threshold.
- [x] Run the unit test and the real-image test. The residence first line must now begin `24/12/29 LK 2-10`; the remaining missing `A,` is handled in Task 3.

### 3. Recover text omitted between adjacent address boxes

**Files:** `vn_id/ocr/engine.py`, `tests/test_ocr_engine.py`, `tests/test_user_image_e2e.py`.

- [x] Add a unit test for adjacent address boxes with a gap: accept a line re-read only when every existing word remains in order with the same spelling; an inserted `A,` may be accepted, while a changed existing word such as `Tân` → `Tần` must be rejected.
- [x] For front address value rows with multiple boxes, re-read the pixel crop spanning the row, with vertical padding. Prefer that result when it passes the preservation check and confidence is at least `0.8`.
- [x] If the full-row result conflicts with an existing box, re-read only across the gap through a few pixels of the next box; use its recovered left text with the original right box when the preservation check passes. The target image was recovered by the second full-row crop, and the gap fallback is covered by a unit test.
- [x] Run the `front_cu_5.jpg`, `front_cu.jpg`, and `front_cu_4.jpg` real-image OCR tests. Assert the exact `origin` and `residence` for the target and existing punctuation for the controls.

### 4. Remove the false residence guess and verify end to end

**Files:** `vn_id/parser/front.py`, `tests/test_front_rules.py`.

- [x] Remove the branch that fills missing `residence` from `found_locs[-1]` or duplicates a single unanchored province into both addresses. Preserve extraction from explicit residence labels.
- [x] Confirm the checked-in failing OCR text now yields `residence is None`, while the repaired OCR text yields the full address.
- [x] Run `pytest tests/test_front_rules.py tests/test_ocr_engine.py tests/test_user_image_e2e.py -q` in an environment with OCR models, then run the relevant front-side pipeline test with QR decoding disabled. Record the before/after OCR boxes and parsed JSON in a new ignored output directory.
- [x] Review the diff for changes outside the planned files and document any remaining recognition uncertainty.

## Reproduction notes

- The local diagnostic environment is `/tmp/vn-id-ocr-diag` (Python 3.12). DBNet18 weights are in `.easyocr_models/model/pretrained_ic15_res18.pt`; VietOCR weights are in `.easyocr_models/model/vgg_seq2seq.pth`. Both paths are ignored by Git.
- Put `/tmp/vn-id-ocr-diag/bin` on `PATH` so EasyOCR can compile its CPU deformable-convolution extension with `ninja`.
- VietOCR's constructor otherwise downloads an additional 548 MB VGG backbone before loading the local full checkpoint. The implementation now sets `config['cnn']['pretrained'] = False` when that checkpoint exists, so the ordinary product path skips the redundant download.

## Implementation result (2026-10-10)

- The target real-image test and control tests for `front_cu.jpg` and `front_cu_4.jpg` pass using the product OCR code without a model-loading workaround.
- The front-side pipeline with QR decoding disabled returns both expected addresses with `field_sources.origin` and `field_sources.residence` equal to `front_rules`.
- Full suite: `104 passed, 18 skipped, 16 warnings` using the Python 3.12 diagnostic environment. The skipped tests depend on optional models or packages absent from that environment.
- Before/after OCR and parsed JSON are in `output/front_cu_5_ocr_no_qr/` and `.superpowers/diagnostics/front_cu_5_ocr_fix/` respectively.
- Review found that the first acceptance check could change existing separators; a red regression test exposed it, and the final code preserves each recognized fragment exactly. Unmeasured accuracy on other card layouts remains the normal limit of this image-based fix.
