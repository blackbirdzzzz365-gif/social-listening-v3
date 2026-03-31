# Vision Validation Scenarios - Phase 9
## Production-Safe Answer Delivery

**Purpose:** define repeatable image-bearing cases that prove OCR / vision fallback adds value before wider rollout  
**Updated:** 2026-03-31

---

## Why This Exists

Phase 8 introduced conditional OCR / image understanding.

Phase 9 needs proof that:

- the trigger conditions are narrow enough
- the extra model call changes or confirms a decision for the right reason
- the product can report when image understanding mattered

---

## Scenario Matrix

| Scenario ID | Use case | Typical evidence | Why text-only is weak | Expected image signal | Expected outcome |
|---|---|---|---|---|---|
| VV-01 | Skincare before/after review | before-after selfie, caption ngắn | post text rất ngắn hoặc chỉ nói "đỡ rồi" | OCR or alt text mentions timeline, irritation, acne, redness | `UNCERTAIN -> ACCEPTED` |
| VV-02 | Scam / fraud screenshot | screenshot chat hoặc payment | text body có thể chỉ là "mọi người cẩn thận" | screenshot chứa transfer proof, warning, account name | `UNCERTAIN -> ACCEPTED` |
| VV-03 | Pricing / fee table screenshot | image chụp hợp đồng, bảng phí, lãi suất | caption không đủ nêu chi tiết phí | OCR đọc fee/interest rows | `UNCERTAIN -> ACCEPTED` hoặc confirm reject |
| VV-04 | Packaging / authenticity proof | ảnh bao bì, tem, nhãn | text body chỉ nói "hàng fake" | visual summary nhắc serial, label mismatch, expired package | confirm trust-risk signal |

---

## Trigger Rules To Validate

Vision fallback should only run when at least one of the following is true:

- text judge returned `UNCERTAIN`
- text is too weak or too short
- the record has `image_urls`, `image_ocr_text`, `image_alt_text`, or precomputed `image_summary`
- the research objective cares about visual proof, screenshots, contracts, packaging, or before-after evidence

It should not run for:

- clearly promotional posts already rejected by hard filter
- strong accepted posts whose text already satisfies the research objective
- image-bearing posts where the image adds no new evidence

---

## Metrics To Capture

- `judge_used_image_understanding`
- count of records that triggered image fallback
- count of records that changed from `UNCERTAIN` to `ACCEPTED` after image evidence
- count of records that stayed `REJECTED` after image evidence
- sample audited cases with `image_summary` and final `reason_codes`

---

## Minimum Validation Standard

Phase 9 should not consider vision validated until all of the following are true:

1. there is at least one repeatable scenario for each major image-bearing pattern
2. at least one scenario proves image fallback can change the final decision
3. the system can explain in audit output that image evidence was used
4. the trigger does not fire on every image post by default

---

## Current Phase 9 Validation Stance

- local/unit validation should prove the fallback path works deterministically
- production smoke should try at least one image-bearing case
- if production smoke does not hit image evidence, the report must say so explicitly instead of pretending the capability is proven
