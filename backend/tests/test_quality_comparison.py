from backend.quality_comparison import compare,CATEGORIES,RUBRIC

def result(value=70,**kw):
    return {'render_id':'a'*32,'quality_model':'test','quality_rubric':RUBRIC,'qa':{'scores':[{'category':c,'value':value} for c in CATEGORIES]}}|kw

def test_delta_and_regressions_do_not_hide_weakness():
    a=result(70);b=result(80)
    b['qa']['scores'][-1]['value']=60
    report=compare(a,b)
    assert report['comparable'] and report['delta']==6
    assert report['regressions']==['audio']
    assert 'passed' not in report

def test_missing_legacy_or_different_models_are_not_comparable():
    assert compare(None,result()) is None
    assert not compare(result(qa=None),result())['comparable']
    assert not compare(result(quality_model='other'),result())['comparable']
    assert not compare(result(quality_rubric=None),result())['comparable']
    a=result();a['qa']['scores'][0]['value']=float('nan')
    assert not compare(a,result())['comparable']


def test_malformed_legacy_scores_never_break_render_completion():
    for malformed in [None, 'bad', {'scores':None}, {'scores':['bad']}, {'scores':[{'category':c,'value':True} for c in CATEGORIES]}]:
        assert not compare(result(qa=malformed),result())['comparable']
