import importlib.util
from pathlib import Path
import pytest
spec=importlib.util.spec_from_file_location('digest_trial',Path('scripts/digest_trial.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def test_compact_evidence_references():
    raw={'outcome':'extracted','quotes':['Three confirmed cases.'],'items':[{'title':'Outbreak','kind':'outbreak','claims':[{'text':'Three confirmed cases.','evidence':[0]}],'urls':[]}],'omitted_detail':[]}
    result=m.Digest.model_validate(raw)
    assert not m.validate_evidence(result,'Three confirmed cases.')
    assert m.validate_evidence(result,'Different source.')
    raw['items'][0]['claims'][0]['evidence']=[1]
    with pytest.raises(ValueError):m.Digest.model_validate(raw)

def test_document_url_is_valid_input_evidence():
    raw={'outcome':'extracted','quotes':['A source fact.'],'items':[{'title':'Topic','kind':'research','claims':[{'text':'A source fact.','evidence':[0]}],'urls':['https://example.org/source']}],'omitted_detail':[]}
    result=m.Digest.model_validate(raw)
    assert not m.validate_evidence(result,'A source fact.','https://example.org/source')
    assert m.validate_evidence(result,'A source fact.','https://example.org/other')
