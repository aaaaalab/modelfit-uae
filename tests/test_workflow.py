import os
os.environ['DATABASE_URL']='sqlite:///./test-modelfit.db'
from copy import deepcopy
from fastapi.testclient import TestClient
from backend.main import app,Base,engine,Workspace
from backend.seed import seed
from backend.rules import gate,apply_change
from sqlalchemy.orm import Session
import pytest
@pytest.fixture
def client():
 Base.metadata.drop_all(engine)
 with TestClient(app) as c:
  c.get('/api/state');yield c

def state(c):return c.get('/api/state').json()
def post(c,path,data=None,role='evaluator'):return c.post('/api/'+path,json=data or {},headers={'X-Demo-Role':role})
def complete(c):
 aid=state(c)['active_assessment']
 assert post(c,f'assessments/{aid}/reuse',{'evidence_id':'E2','decision':'applicable','rationale':'Same public dataset, task, language, configuration and oversight; does not prove performance.'}).status_code==200
 assert post(c,f'assessments/{aid}/evaluate',{'confirm_simulated':True}).status_code==200
 return aid

def decision(c,aid,kind='approve'):
 return post(c,f'assessments/{aid}/decision',{'decision':kind,'rationale':'All applicable mandatory demonstration checks reviewed; public-only scope and human oversight.','review_date':'2099-01-01','conditions':'Review optional latency weekly.','owner':'Mariam Al Noor','deadline':'2098-12-01'},'approver')

def test_mandatory_failure_overrides_performance():
 s=seed();a=s['assessments'][0]
 a['findings'][0]['state']='fail';a['findings'][-1]['value']=1
 assert not gate(s,a)['eligible']
def test_missing_evidence_blocks_submit_and_approval(client):
 assert post(client,'assessments/AS-001/submit').status_code==409
 assert decision(client,'AS-001').status_code==409

def test_conditional_cannot_bypass_mandatory(client):
 aid=complete(client);assert post(client,f'assessments/{aid}/submit').status_code==200
 with Session(engine) as db,db.begin():
  row=db.query(Workspace).first();s=deepcopy(row.data);s['assessments'][0]['findings'][0]['state']='fail';row.data=s
 assert decision(client,aid,'approve_with_conditions').status_code==409

def test_reuse_requires_rationale_and_matching_dependencies(client):
 assert post(client,'assessments/AS-001/reuse',{'evidence_id':'E2','decision':'applicable','rationale':''}).status_code==422
 assert post(client,'assessments/AS-001/changes',{'kind':'deployment','new_value':'retrieval-v2','requirement_id':'R3'},'owner').status_code==200
 aid=state(client)['active_assessment']
 assert post(client,f'assessments/{aid}/reuse',{'evidence_id':'E2','decision':'applicable','rationale':'I would like to reuse the previous configuration review.'}).status_code==409

def test_full_journey_and_change_preserves_decision(client):
 aid=complete(client);assert state(client)['assessments'][0]['gate']['coverage']==100
 assert post(client,f'assessments/{aid}/submit').status_code==200
 assert decision(client,aid).status_code==200
 before=deepcopy(state(client)['approvals'][0])
 assert post(client,f'assessments/{aid}/changes',{'kind':'model','new_value':'1.1','requirement_id':'R3'},'owner').status_code==200
 s=state(client);a=s['assessments'][-1]
 assert a['model_version']=='1.1' and a['status']=='draft' and not a['gate']['eligible']
 assert len(a['tasks'])==6
 assert next(x for x in s['events'][-1]['impacts'] if x['requirement_id']=='R6')['classification']=='retained'
 assert s['approvals'][0]==before and before['snapshot']['model_version']=='1.0'
 assert post(client,f'assessments/{a["id"]}/evaluate',{'confirm_simulated':True}).status_code==409

def test_persistence_and_isolation(client):
 complete(client);cookie=client.cookies.get('modelfit_workspace')
 with TestClient(app) as other:
  assert state(other)['assessments'][0]['gate']['coverage']==67
  other.cookies.set('modelfit_workspace',cookie)
  assert state(other)['assessments'][0]['gate']['coverage']==100

def test_roles_and_reset_confirmation(client):
 assert post(client,'assessments/AS-001/evaluate',{'confirm_simulated':True},'owner').status_code==403
 assert post(client,'demo/reset?confirm=true',role='auditor').status_code==403
 assert post(client,'demo/reset',role='owner').status_code==400
 complete(client)
 assert post(client,'demo/reset?confirm=true',role='owner').status_code==200
 assert state(client)['assessments'][0]['gate']['coverage']==67

def test_frozen_assessment_cannot_be_edited(client):
 aid=complete(client);post(client,f'assessments/{aid}/submit')
 assert post(client,f'assessments/{aid}/evaluate',{'confirm_simulated':True}).status_code==409

def test_all_change_triggers_have_traceable_impact():
 for kind,new in [('model','1.1'),('requirement','0.95'),('deployment','retrieval-v2'),('data','Sensitive'),('expiry','Review period elapsed'),('incident','New limitation')]:
  s=seed();old=deepcopy(s['assessments'][0]);b,e=apply_change(s,s['assessments'][0],kind,new,'R3')
  assert s['assessments'][0]==old and e['tasks_created']>0
  assert e['previous'] is not None and e['new']==new and all(i['reason'] for i in e['impacts'])

def test_claim_review_preserves_provenance(client):
 r=post(client,'evidence/E5/review');assert r.status_code==200
 e=next(e for e in r.json()['evidence'] if e['id']=='E5')
 assert e['type']=='Supplier claim' and e['verification']=='Reviewed claim; not independently verified'

def test_expired_evidence_blocks_gate():
 s=seed();s['evidence'][0]['review_date']='2000-01-01'
 assert 'R1' in gate(s,s['assessments'][0])['blocked']

def test_request_size_and_origin(client):
 assert client.post('/api/evidence',content='x'*100001).status_code==413
 assert client.post('/api/demo/reset?confirm=true',headers={'Origin':'https://evil.example','X-Demo-Role':'owner'}).status_code==403
