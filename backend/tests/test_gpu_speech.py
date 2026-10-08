"""Speech is recorded on lumen-web-gpu. OpenRouter is not an audio endpoint."""
from backend.dubbing_audio import SPEECH_MODEL, VOICES, synthesize


def test_speech_is_recorded_on_the_gpu(monkeypatch, tmp_path):
    calls = []

    def speak_lines(jobs):
        calls.append(jobs)
        for _text, _voice, dest in jobs:
            dest.write_bytes(b'gpu-mp3')

    monkeypatch.setattr('backend.gpu_speech.speak_lines', speak_lines)
    monkeypatch.setattr(
        'backend.dubbing_audio.httpx.Client',
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError('openrouter')),
    )
    destination = tmp_path / 'line.mp3'
    synthesize('Hello there.', 'en-male', destination, 'minimax/speech-2.8-hd')
    assert calls == [[('Hello there.', 'en-male', destination)]]
    assert destination.read_bytes() == b'gpu-mp3'
    assert VOICES['en-male']['speaker'] == 'Ryan'
    assert VOICES['zh-female']['qwen_language'] == 'Chinese'
    assert SPEECH_MODEL.startswith('lumen-web-gpu/')
