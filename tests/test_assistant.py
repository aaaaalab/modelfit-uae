import json
import httpx
import pytest
from backend.assistant import EvidenceAssistant,AssistantUnavailable
from backend.seed import seed

def test_no_key_is_explicitly_simulated(monkeypatch):
 monkeypatch.delenv('OPENAI_API_KEY',raising=False)
 assert EvidenceAssistant().summarize(seed()['evidence'][0])['live'] is False

def test_live_summary_is_bounded_source_linked_and_cached(monkeypatch):
 monkeypatch.setenv('OPENAI_API_KEY','test-placeholder')
 calls=[]
 def post(self,url,**kwargs):
  calls.append(kwargs);return httpx.Response(200,json={'output':[{'content':[{'type':'output_text','text':json.dumps({'summary':'[E1] Simulated evidence needs human review.','references':['E1']})}]}]})
 monkeypatch.setattr(httpx.Client,'post',post)
 a=EvidenceAssistant();e=seed()['evidence'][0];r=a.summarize(e)
 assert r['live'] and r['references']==['E1'] and r['requires_human_confirmation']
 assert a.summarize(e)['cached'] and len(calls)==1
 assert calls[0]['json']['store'] is False and 'tools' not in calls[0]['json']
 assert 'secret' not in r['text']

def test_provider_error_never_masquerades_as_live_success(monkeypatch):
 monkeypatch.setenv('OPENAI_API_KEY','test-placeholder')
 monkeypatch.setattr(httpx.Client,'post',lambda *a,**k:httpx.Response(401,text='sensitive upstream body'))
 with pytest.raises(AssistantUnavailable,match='Check OPENAI_API_KEY'):EvidenceAssistant().summarize(seed()['evidence'][0])
