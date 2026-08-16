# Local OCR Pipeline — Test Results (2026-06-18, updated 2026-07-08)

## Test Environment
- Hardware: Apple M5 Mac (arm64), macOS 25.5.0
- OCR Backend: Apple Vision (Core ML ANE-accelerated), VNRecognizeTextRequestRevision3
- Preprocessing: CIDocumentEnhancer (amount=3.0) + CIColorControls (contrast=1.15) + CISharpenLuminance (sharpness=0.3)

## Test Corpus

**Important**: These results are spot-tests on a small corpus (3 PDFs). Not a systematic benchmark. Error rates vary significantly by print quality, font, language, and DPI. Use as rough guidance.

| Document | Language | Pages | PDF Type | Notes |
|----------|----------|-------|----------|-------|
| Eudora Welty Collected Stories | English | 728 | Image with embedded OCR layer | Internet Archive scan |
| 俞军产品方法论 | Chinese | 317 | Text-based | Calibre-generated e-book |
| 失落的一代 | Chinese | 466 | Pure image (scanned book) | 200 DPI, 10-workers OCR |

## PDF Detection Results
- Eudora Welty: correctly identified as having extractable text (embedded OCR layer from Internet Archive)
- 俞军产品方法论: correctly identified as text-based (Calibre-generated)
- 失落的一代: correctly identified as pure image (no extractable text layer)

## OCR Quality (Observed)

| Language | Approximate Error Rate | Common Errors |
|----------|----------------------|---------------|
| English (clean print) | <1% | Fused adjacent words, signature/image misreads |
| Chinese (clean print) | 3-5% | Dropped particles (的/了/是), visually similar characters |

## Pipeline Performance (Measured)

| PDF Type | 300 pages | Bottleneck |
|----------|-----------|------------|
| Text-based | ~5 seconds | pdftotext is near-instant |
| Image with OCR layer | ~5 seconds | Same (uses pdftotext) |
| Pure image (serial OCR) | ~12 minutes | ~2.4s per page OCR |
| Pure image (10-workers) | ~3 minutes | ANE-bound |

Actual benchmark: 失落的一代 (466 pages) processed in ~3 minutes with 10 workers at 200 DPI.

## txt_to_md.py Post-Processing (rewritten 2026-07-08)

- **Auto-detect repeating headers**: Statistical detection of lines that repeat across page boundaries. Removes duplicates beyond first occurrence.
- **Paragraph merging**: "Short last line" heuristic — computes median content-line length per document; lines <75% of median are paragraph-ending lines.
- **Configurable**: Optional YAML config for document-specific section headers, running header pairs, OCR corrections.
- **Language-aware**: Adapts sentence-ending punctuation detection to the target language.

## Conclusions
1. Always prefer pdftotext when available — 100× faster than re-OCR
2. 200 DPI is the sweet spot for OCR quality vs speed  
3. Apple Vision with preprocessing is competitive with embedded OCR (Internet Archive)
4. Minimize LLM calls — local extraction handles 95% of cases
5. The auto-detect running header feature works best with 10+ pages of consistent headers
