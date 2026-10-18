"""Duration contract: full source stays, an explicit target stays, frames match."""
import pytest

from backend.director_v3 import duration_contract, frame_seconds, output_seconds


def _assert_aligned(contract):
    fps = contract["fps"]
    frames = contract["durationInFrames"]
    target = contract["targetSeconds"]
    assert frames == int(round(target * fps))
    assert target == pytest.approx(frames / fps)
    assert target <= contract["sourceSeconds"] + 1e-6


def test_explicit_20_and_60_stay_on_the_frame_grid():
    short = duration_contract(20, 85.5)
    minute = duration_contract(60, 85.5)
    assert short["mode"] == "target"
    assert short["targetSeconds"] == 20
    assert short["durationInFrames"] == 600
    assert minute["mode"] == "target"
    assert minute["targetSeconds"] == 60
    assert minute["durationInFrames"] == 1800
    assert minute["sourceSeconds"] == 85.5
    _assert_aligned(short)
    _assert_aligned(minute)


def test_full_source_85_5_is_not_truncated_to_85():
    contract = duration_contract(None, 85.5)
    assert contract["mode"] == "full_source"
    assert contract["targetSeconds"] == pytest.approx(85.5)
    assert contract["durationInFrames"] == 2565
    assert output_seconds(85.5, 85.5) == pytest.approx(85.5)
    assert frame_seconds(85.5, 85.5) == pytest.approx(85.5)
    _assert_aligned(contract)


def test_full_source_151_1_is_not_truncated_to_151():
    contract = duration_contract(None, 151.1)
    assert contract["mode"] == "full_source"
    assert contract["targetSeconds"] == pytest.approx(151.1)
    assert contract["durationInFrames"] == 4533
    assert duration_contract(60, 151.1)["targetSeconds"] == 60
    _assert_aligned(contract)


def test_timeline_audio_and_frames_name_the_same_target():
    """The three clocks the render uses. AAC padding is not a fourth clock."""
    for requested, source, frames in (
        (20, 85.5, 600),
        (60, 85.5, 1800),
        (None, 85.5, 2565),
        (None, 151.1, 4533),
    ):
        contract = duration_contract(requested, source)
        timeline = [0.0, contract["targetSeconds"]]
        audio_end = contract["targetSeconds"]
        assert contract["durationInFrames"] == frames
        assert timeline[1] == audio_end
        assert audio_end == pytest.approx(frames / 30)
