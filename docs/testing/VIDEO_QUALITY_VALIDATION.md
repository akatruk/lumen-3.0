# Video quality validation

`backend/video_quality.validate_plan` checks a plan dict:

- A scene marked `NO_MATCH` must not keep an `assetId`.
- A caption string longer than 12 characters that is absent from the transcript is reported.
- The result always sets `humanReviewRequired=true`.

It does not open an MP4. It does not measure overflow, PIP overlap, black frames, or whether a shot feels directed.

Those checks need a rendered file and a person. None were produced in this pass. Create Video was not clicked. original1 and original4 were not rendered again.

A green unit test is not a quality sign-off.
