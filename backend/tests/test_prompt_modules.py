"""Hypit prompt module assembly: main body + localization + versions."""
from backend.prompt_modules import assemble_hypit_prompt, main_prompt_version
from backend.prompt_modules.localization import VERSION as LOC_VERSION
from backend.hypit_prompt import assemble_illustration, illustration_request


def test_main_prompt_version_is_stable_hash():
    a = main_prompt_version()
    b = main_prompt_version()
    assert a == b and a.startswith('assembly:') and len(a) > 12


def test_assembly_without_language_has_editing_but_no_localization():
    bundle = assemble_hypit_prompt({'card_motion': 60})
    assert [m['id'] for m in bundle.modules] == ['editing_controls']
    assert '--- PROMPT MODULES ---' in bundle.text
    assert 'editing_controls@' in bundle.text or 'editing_controls @' in bundle.text or 'MODULE: editing_controls' in bundle.text
    assert 'MODULE LOCALIZATION RULES' not in bundle.text
    assert 'MODULE EDITING CONTROLS RULES' in bundle.text
    assert bundle.conflicts == []
    assert bundle.run_params['mainPromptVersion'] == bundle.main_prompt_version
    assert bundle.run_params['editingControls']['preset'] == 'balanced'


def test_localization_module_attaches_for_ru_en_zh():
    for code, locale in (('ru', 'ru-RU'), ('en', 'en-US'), ('zh', 'zh-CN')):
        bundle = assemble_illustration({'language': code, 'card_motion': 60})
        ids = [m['id'] for m in bundle.modules]
        assert ids[0] == 'editing_controls'
        assert any(m['id'] == 'localization' and m['version'] == LOC_VERSION for m in bundle.modules)
        assert bundle.run_params['targetLocale'] == locale
        assert 'MODULE LOCALIZATION RULES' in bundle.text
        assert 'MODULE EDITING CONTROLS RULES' in bundle.text
        assert f'"locale": "{locale}"' in bundle.text or f'locale: {locale}' in bundle.text
        assert '--- RUN PARAMS ---' in bundle.text
        assert '--- USER CONTENT ---' in bundle.text
        assert 'VOICE_SETUP_REQUIRED' in bundle.text  # hard-error rule stated
        meta = bundle.job_fields()['promptAssembly']
        assert meta['mainPromptVersion'] == bundle.main_prompt_version
        assert {m['id'] for m in meta['modules']} >= {'editing_controls', 'localization'}


def test_illustration_request_keeps_main_body_and_avoids_transcript_dump():
    bare = {
        'clips': [{'start': 0, 'end': 40}],
        'captions': [{
            'start': 0, 'end': 6,
            'original': 'Планируете переезд',
            'ru': 'Планируете переезд',
            'en': 'Are you planning a move',
            'zh': '您是否正在计划移居',
        }],
        'card_motion': 60,
        'language': 'ru',
    }
    text = illustration_request(bare)
    assert 'FINAL REVIEW BEFORE DELIVERY' in text or 'FACE PROTECTION' in text
    # Target-language transcript is filled into SOURCE MATERIAL (not a 3-language dump).
    assert 'Transcript with target-language timing:' in text
    assert 'Планируете переезд' in text
    assert 'русский:' not in text and 'English:' not in text and '中文:' not in text
    assert 'localization@' in text or 'localization @' in text or 'MODULE: localization' in text


def test_save_video_language_helper_only_persists_locale():
    """Language switch must not enqueue render / paid ops (studio.save_video_language)."""
    import inspect
    from backend import studio
    src = inspect.getsource(studio.save_video_language)
    assert 'enqueue' not in src
    assert '_remember_language' in src
