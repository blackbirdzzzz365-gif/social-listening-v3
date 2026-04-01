# Phase 10 Vision Validation Scenarios

Phase 10 does not broaden vision scope.
It only defines how to validate it honestly after the control layer is fixed.

## Scenario A - Before/after skincare review

Goal:

- find posts where the text alone is weak, but the image or OCR adds evidence

Signals:

- before/after captions
- OCR text on screenshots or collage images
- short text plus visual proof

Success:

- image-bearing evidence is found and audited clearly
- or the run finishes with a documented reason why no such evidence was found

## Scenario B - Screenshot-based complaint proof

Goal:

- detect screenshots containing fees, chat logs, or service issues

Signals:

- OCR text from screenshots
- posts where the main evidence is inside the image, not the body text

## Minimum proof bar

Phase 10 may only claim vision validation if one of these is true:

1. `judge_used_image_understanding > 0` on a real production run
2. the run completes and the final audit clearly explains why no image-bearing evidence was actually found

Anything weaker means vision is still unproven.
