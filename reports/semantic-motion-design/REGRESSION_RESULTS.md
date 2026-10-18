# Regression

`node --import tsx --test src/semantic/motionDesign.test.ts src/semantic/numericRange.test.ts src/semantic/layouts.test.ts`

- timeline keeps 2–5 labels and does not add 步骤
- one label does not grow a second row
- column fits 952 and 504
- Chinese keeps 偶、 with the preceding character; English wraps to 2 lines; the long Russian word stays one token and scales to the split label width at fitScale ≥ 0.75
- range motion is low, then stem, then high, and the same frame returns the same values
- range kind labels unchanged
- layout safety tests, 8 passed

`pytest` `test_visual_treatment_ranking.py` `test_visual_quality_optimizer.py` `test_director_v14.py` `test_semantic_motion_profile.py`: 56 passed.

No failures suppressed.
