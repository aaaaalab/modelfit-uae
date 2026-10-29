import os,json,uuid,re,time,threading
from copy import deepcopy
from pathlib import Path
from datetime import date
from contextlib import asynccontextmanager
from typing import Literal
from urllib.parse import urlparse
from fastapi import FastAPI,Request,HTTPException,Response,Header
from fastapi.responses import FileResponse,JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel,Field,ConfigDict,field_validator
from sqlalchemy import create_engine,Column,String,JSON,select,text
from sqlalchemy.orm import DeclarativeBase,Session
from .seed import seed,now,PERSONAS,future
from .rules import gate,check_findings,reuse_compatibility,apply_change,apply_service_revision
from .assistant import assistant

url=os.environ.get('DATABASE_URL','sqlite:///./modelfit.db')
if url.startswith('mysql://'):url=url.replace('mysql://','mysql+pymysql://',1)
engine=create_engine(url,pool_pre_ping=True,**({'connect_args':{'check_same_thread':False}} if url.startswith('sqlite') else {'pool_recycle':280}))
class Base(DeclarativeBase):pass
class Workspace(Base):
    __tablename__='demo_workspaces'
    id=Column(String(36),primary_key=True)
    data=Column(JSON,nullable=False)
lock=threading.RLock()
@asynccontextmanager
async def lifespan(app):
    for attempt in range(20):
        try:Base.metadata.create_all(engine);break
        except Exception:
            if attempt==19:raise
            time.sleep(2)
    yield
app=FastAPI(title='ModelFit demonstration API',lifespan=lifespan,docs_url='/api/docs',redoc_url=None)

@app.middleware('http')
async def safeguards(request,call_next):
    try: declared_length=int(request.headers.get('content-length','0') or 0)
    except ValueError:return JSONResponse({'detail':'Invalid request length.'},400)
    if declared_length>100_000:return JSONResponse({'detail':'Request limit is 100 KB. Use public or synthetic text only.'},413)
    if request.method not in ('GET','HEAD','OPTIONS') and len(await request.body())>100_000:return JSONResponse({'detail':'Request limit is 100 KB.'},413)
    if request.method not in ('GET','HEAD','OPTIONS'):
        origin=request.headers.get('origin')
        if origin and urlparse(origin).netloc!=request.headers.get('host') and origin not in ('http://localhost:5173','http://127.0.0.1:5173'):
            return JSONResponse({'detail':'Cross-origin changes are not allowed.'},403)
    try:response=await call_next(request)
    except Exception:return JSONResponse({'detail':'The operation could not complete. Please retry; no partial decision was saved.'},500)
    response.headers['X-Content-Type-Options']='nosniff';response.headers['Referrer-Policy']='strict-origin-when-cross-origin'
    response.headers['X-Frame-Options']='DENY'
    response.headers['Content-Security-Policy']="default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; script-src 'self'; connect-src 'self'"
    if request.url.path.startswith('/api/'):response.headers['Cache-Control']='no-store'
    return response

def role_check(role,allowed):
    if role not in allowed:raise HTTPException(403,'This action requires '+', '.join(allowed)+'. Demo role selection is not authentication.')
def find(items,id):
    item=next((i for i in items if i['id']==id),None)
    if item is None:raise HTTPException(404,'Record not found')
    return item

def audit(s,role,action,record,detail=''):
    s['audit'].append({'id':'AUD-'+uuid.uuid4().hex[:10],'at':now(),'actor':PERSONAS.get(role,'Demo user'),'role':role,'action':action,'record':record,'detail':detail})

def workspace_id(request,response):
    wid=request.cookies.get('modelfit_workspace','')
    if not re.fullmatch('[a-f0-9-]{36}',wid):
        wid=str(uuid.uuid4());response.set_cookie('modelfit_workspace',wid,max_age=60*60*24*30,httponly=True,samesite='lax',secure=request.url.scheme=='https')
    return wid

def transact(request,response,fn):
    wid=workspace_id(request,response)
    with lock,Session(engine) as db,db.begin():
        row=db.execute(select(Workspace).where(Workspace.id==wid).with_for_update()).scalar_one_or_none()
        if row is None:row=Workspace(id=wid,data=seed());db.add(row)
        s=deepcopy(row.data);result=fn(s);row.data=s
        return result

def view(s):
    out=deepcopy(s)
    for a in out['assessments']:a['gate']=gate(out,a)
    active=find(out['assessments'],out['active_assessment'])
    comparisons=[]
    for model in out['models']:
        matches=[a for a in out['assessments'] if a['model_id']==model['id'] and a['model_version']==model['version'] and a['usecase_id']==active['usecase_id'] and a['usecase_version']==active['usecase_version'] and a['context']==active['context']]
        ca=matches[-1] if matches else {'requirements':active['requirements'],'findings':[],'model_id':model['id'],'model_version':model['version'],'context':active['context']}
        cg=gate(out,ca)
        status='fail' if any(r['mandatory'] and r['state']=='fail' for r in cg['checks']) else 'eligible' if cg['eligible'] else 'blocked'
        latency=next((r['finding']['value'] for r in cg['checks'] if r['id']=='R7' and r['state']=='pass'),None)
        comparisons.append({'model_id':model['id'],'status':status,'gate':cg,'latency':latency,'rank':None,'assessment_id':ca.get('id')})
    ranked=sorted([c for c in comparisons if c['status']=='eligible' and c['latency'] is not None],key=lambda c:(c['latency'],c['model_id']))
    for index,c in enumerate(ranked,1):c['rank']=index
    out['comparisons']=comparisons
    out['decision_applicability']={}
    for p in out['approvals']:
        reason='Applicable only to the recorded demonstration context.'
        status='recorded_context'
        if not p['decision'].startswith('approve'):status='not_approval';reason='This record is not an approval.'
        elif any(e['from_assessment']==p['assessment_id'] for e in out['events']) or find(out['usecases'],p['snapshot']['usecase_id'])['version']!=p['snapshot']['usecase_version']:status='reassessment';reason='Historical decision — changed context requires reassessment.'
        elif p['review_date']<=date.today().isoformat():status='review_overdue';reason='Decision review date reached; human review is required.'
        elif not gate(out,p['snapshot'])['eligible']:status='evidence_review';reason='Supporting mandatory evidence is no longer valid; reassessment required.'
        elif any(c['decision_id']==p['id'] and c['status']=='open' and c['deadline']<=date.today().isoformat() for c in out['conditions']):status='condition_overdue';reason='An owned condition is overdue; review applicability before use.'
        out['decision_applicability'][p['id']]={'status':status,'reason':reason}
    return out

def editable(a):
    if a['status']!='draft':raise HTTPException(409,'This assessment is frozen. Request changes or create a reassessment to edit findings.')

class Strict(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    @field_validator('review_date','deadline',check_fields=False)
    @classmethod
    def iso_date(cls,value):
        if value:
            try:date.fromisoformat(value)
            except ValueError:raise ValueError('Use a valid YYYY-MM-DD date.')
        return value
class AssessmentInput(Strict):
    usecase_id:str
    model_id:str='M1'
class ReuseInput(Strict):
    evidence_id:str
    rationale:str=Field(min_length=15,max_length=3000)
    decision:Literal['applicable','inappropriate']='applicable'
class EvalInput(Strict):
    confirm_simulated:bool
class DecisionInput(Strict):
    decision:Literal['approve','approve_with_conditions','request_changes','reject']
    rationale:str=Field(min_length=15,max_length=3000)
    conditions:str=Field(default='',max_length=3000)
    owner:str=Field(default='',max_length=150)
    deadline:str=Field(default='')
    review_date:str
class ChangeInput(Strict):
    kind:Literal['model','requirement','deployment','data','expiry','incident']
    new_value:str=Field(min_length=1,max_length=500)
    requirement_id:str='R3'
class FindingInput(Strict):
    state:Literal['pass','fail','missing','needs_review','not_applicable']
    evidence_ids:list[str]=Field(max_length=10)
    rationale:str=Field(min_length=15,max_length=3000)
    value:float=Field(ge=0,le=1000000)
class UsecaseInput(Strict):
    id:str|None=None
    name:str=Field(min_length=3,max_length=150)
    description:str=Field(min_length=10,max_length=2000)
    owner:str=Field(min_length=3,max_length=150)
    task:str=Field(min_length=3,max_length=500)
    exclusions:str=Field(min_length=5,max_length=2000)
    users:str=Field(min_length=3,max_length=1000)
    accessibility:str=Field(min_length=5,max_length=2000)
    data_sources:str=Field(min_length=3,max_length=1000)
    sensitivity:str=Field(min_length=3,max_length=150)
    languages:list[str]=Field(min_length=1,max_length=5)
    consequences:str=Field(min_length=5,max_length=2000)
    autonomy:str=Field(min_length=3,max_length=1000)
    oversight:str=Field(min_length=5,max_length=2000)
    deployment:str=Field(min_length=3,max_length=1000)
    constraints:str=Field(min_length=3,max_length=1000)
    risk:Literal['Low','Moderate','High']
    risk_rationale:str=Field(min_length=5,max_length=2000)
    thresholds:dict[str,float]=Field(default_factory=dict)
    mandatory:dict[str,bool]=Field(default_factory=dict)
class EvidenceInput(Strict):
    title:str=Field(min_length=3,max_length=200)
    type:Literal['Verified source evidence','Supplier claim','Measured evaluation result','Demonstration data']
    reference:str=Field(min_length=3,max_length=1000)
    issuer:str=Field(min_length=3,max_length=200)
    model_version:str=Field(min_length=1,max_length=100)
    requirements:list[str]=Field(min_length=1,max_length=7)
    method:str=Field(min_length=3,max_length=1000)
    conditions:str=Field(min_length=3,max_length=2000)
    limitations:str=Field(min_length=3,max_length=2000)
    result:str=Field(min_length=3,max_length=2000)
    sample_size:int=Field(ge=1,le=1000000)
    units:str=Field(min_length=1,max_length=100)
    review_date:str
    expiry_rationale:str=Field(min_length=5,max_length=1000)
    published_at:str='Unknown'
    evaluated_at:str='Unknown'

@app.get('/api/health')
def health():
    with engine.connect() as db:db.execute(text('SELECT 1'))
    return {'status':'ok','database':'MySQL' if url.startswith('mysql') else 'SQLite','demo':True,'ai':'simulated'}
@app.get('/api/state')
def state(request:Request,response:Response):return transact(request,response,view)
@app.post('/api/demo/reset')
def reset(request:Request,response:Response,confirm:bool=False,x_demo_role:str=Header('owner')):
    role_check(x_demo_role,['owner'])
    if not confirm:raise HTTPException(400,'Confirm reset of your demo workspace.')
    def run(s):s.clear();s.update(seed());return view(s)
    return transact(request,response,run)
@app.post('/api/usecases')
def save_uc(body:UsecaseInput,request:Request,response:Response,x_demo_role:str=Header('owner')):
    role_check(x_demo_role,['owner'])
    def run(s):
        data=body.model_dump();id=data.pop('id');thresholds=data.pop('thresholds');mandatory=data.pop('mandatory')
        if any(v<0 or v>1000000 for v in thresholds.values()):raise HTTPException(422,'Thresholds must be between 0 and 1,000,000.')
        old=find(s['usecases'],id) if id else None
        previous=deepcopy(old) if old else None
        reqs=deepcopy(old['requirements'] if old else s['usecases'][0]['requirements'])
        for r in reqs:
            r['threshold']=thresholds.get(r['id'],r['threshold']);r['mandatory']=mandatory.get(r['id'],r['mandatory'])
            if r['unit']=='fraction' and r['threshold']>1:raise HTTPException(422,'Fraction thresholds must be between 0 and 1.')
        data.update({'id':id or 'UC-'+str(len(s['usecases'])+1).zfill(3),'version':old['version']+1 if old else 1,'requirements':reqs,'draft':False,'created_at':now(),'context':{**deepcopy(s['usecases'][0]['context']),**{k:data[k] for k in ['task','languages','sensitivity','deployment']},'dataset':old['context']['dataset'] if old and old['data_sources']==data['data_sources'] else data['data_sources']}})
        data['versions']=deepcopy(old['versions']) if old else []
        data['versions'].append({'version':data['version'],'created_at':now(),'snapshot':{k:deepcopy(v) for k,v in data.items() if k!='versions'}})
        if old:
            prior_assessments=[x for x in s['assessments'] if x['usecase_id']==old['id'] and x['usecase_version']==previous['version']]
            old.clear();old.update(data)
            if prior_assessments:
                source=next((x for x in prior_assessments if x['id']==s['active_assessment']),prior_assessments[-1])
                apply_service_revision(s,source,old,previous)
            audit(s,x_demo_role,'Service version created',data['id'],f"Version {data['version']}; earlier assessments retain their recorded requirement snapshot.")
        else:s['usecases'].append(data);audit(s,x_demo_role,'Service created',data['id'])
        return view(s)
    return transact(request,response,run)
@app.post('/api/assessments')
def start(body:AssessmentInput,request:Request,response:Response,x_demo_role:str=Header('owner')):
    role_check(x_demo_role,['owner','evaluator'])
    def run(s):
        u=find(s['usecases'],body.usecase_id);m=find(s['models'],body.model_id)
        existing=next((a for a in s['assessments'] if a['usecase_id']==u['id'] and a['usecase_version']==u['version'] and a['model_id']==m['id'] and a['status']=='draft'),None)
        if existing:s['active_assessment']=existing['id'];return view(s)
        a={'id':'AS-'+str(len(s['assessments'])+1).zfill(3),'usecase_id':u['id'],'usecase_version':u['version'],'model_id':m['id'],'model_version':m['version'],'requirements':deepcopy(u['requirements']),'context':deepcopy(u['context']),'status':'draft','created_at':now(),'started_at':now(),'reuse':[],'tasks':[],'findings':[]}
        if m['id']=='M2':a['findings']=[{'id':'F-R3','requirement_id':'R3','state':'fail','value':0.5,'evidence_ids':[],'rationale':'Synthetic Arabic fixture fails 1 of 2 language cases; confirmed demonstration failure.','reviewer':PERSONAS['evaluator'],'dependencies':['model','languages'],'context':a['context'],'model_version':m['version']}]
        s['assessments'].append(a);s['active_assessment']=a['id'];audit(s,x_demo_role,'Assessment started',a['id']);return view(s)
    return transact(request,response,run)
@app.post('/api/assessments/{aid}/reuse')
def reuse(aid:str,body:ReuseInput,request:Request,response:Response,x_demo_role:str=Header('evaluator')):
    role_check(x_demo_role,['evaluator'])
    def run(s):
        a=find(s['assessments'],aid);editable(a);e=find(s['evidence'],body.evidence_id);checks=reuse_compatibility(e,a)
        if body.decision=='applicable' and not all(c['matches'] for c in checks):raise HTTPException(409,'Dependencies differ or evidence is expired. Record inappropriate reuse and retest.')
        decision={'id':'REUSE-'+uuid.uuid4().hex[:8],'evidence_id':e['id'],'decision':body.decision,'rationale':body.rationale,'reviewer':PERSONAS[x_demo_role],'at':now(),'dependencies':checks}
        a['reuse'].append(decision)
        if body.decision=='applicable':
            for rid in e['requirements']:
                f=next((f for f in a['findings'] if f['requirement_id']==rid),None)
                if f and rid=='R6':f.update({'state':'pass','value':1,'evidence_ids':[e['id']],'rationale':body.rationale,'reviewer':PERSONAS[x_demo_role],'impact':'retained'})
        if body.decision=='inappropriate':
            for f in a['findings']:
                if e['id'] in f['evidence_ids']:
                    f.update({'state':'needs_review','rationale':'Reuse declined: '+body.rationale,'reviewer':PERSONAS[x_demo_role]})
        audit(s,x_demo_role,'Evidence reuse '+body.decision,aid,e['id']+': '+body.rationale);return view(s)
    return transact(request,response,run)
@app.post('/api/assessments/{aid}/evaluate')
def evaluate(aid:str,body:EvalInput,request:Request,response:Response,x_demo_role:str=Header('evaluator')):
    role_check(x_demo_role,['evaluator'])
    if not body.confirm_simulated:raise HTTPException(422,'Confirm these are simulated outputs, not real model measurements.')
    def run(s):
        a=find(s['assessments'],aid);editable(a)
        if a['model_id']!='M1' or a['model_version']!='1.0':raise HTTPException(409,'This fixture supports Noor Atlas 1.0 only. New versions require new outputs and human review.')
        if a['context']!=s['assessments'][0]['context']:raise HTTPException(409,'Changed configuration is outside the fixed fixture scope. Attach new evidence and findings.')
        e=deepcopy(find(s['evidence'],'E1'));e.update({'id':'E-'+uuid.uuid4().hex[:8],'title':'Confirmed bilingual simulation run','requirements':['R1','R2','R3','R4','R5'],'evaluated_at':now(),'reviewer':PERSONAS[x_demo_role],'result':'6/6 deterministic simulated cases meet their human-authored rubrics. No real model tested.'});s['evidence'].append(e)
        for rid in e['requirements']:
            f=next((f for f in a['findings'] if f['requirement_id']==rid),None)
            if f:f.update({'state':'pass','value':1,'evidence_ids':[e['id']],'rationale':'Human confirmed simulated outputs and source-linked rubric; 6/6 examples.','reviewer':PERSONAS[x_demo_role],'impact':'retained'})
        a['evaluation_run']={'at':now(),'sample_size':6,'type':'simulation','results':deepcopy(s['examples'])}
        for t in a['tasks']:
            if t['requirement_id'] in e['requirements']:t['status']='complete'
        audit(s,x_demo_role,'Demonstration evaluation confirmed',aid,e['id']+'; 6 simulated examples');return view(s)
    return transact(request,response,run)
@app.post('/api/assessments/{aid}/findings/{rid}')
def finding(aid:str,rid:str,body:FindingInput,request:Request,response:Response,x_demo_role:str=Header('evaluator')):
    role_check(x_demo_role,['evaluator'])
    def run(s):
        a=find(s['assessments'],aid);editable(a);r=find(a['requirements'],rid)
        if body.state=='not_applicable' and r['mandatory']:raise HTTPException(409,'Mandatory checks cannot be marked not applicable in this prototype.')
        for eid in body.evidence_ids:
            e=find(s['evidence'],eid)
            if rid not in e['requirements']:raise HTTPException(422,'Evidence does not support this requirement.')
            if e['type']=='Supplier claim' and body.state=='pass':raise HTTPException(409,'A supplier claim alone cannot establish a passing finding.')
        f=next((f for f in a['findings'] if f['requirement_id']==rid),None)
        if not f:f={'id':'F-'+rid,'requirement_id':rid};a['findings'].append(f)
        f.update({**body.model_dump(),'reviewer':PERSONAS[x_demo_role],'dependencies':r['dependencies'],'model_version':a['model_version'],'context':deepcopy(a['context']),'impact':'retained'})
        for t in a['tasks']:
            if t['requirement_id']==rid:t['status']='complete' if body.state=='pass' else 'open'
        audit(s,x_demo_role,'Finding recorded',aid,rid+': '+body.state);return view(s)
    return transact(request,response,run)
@app.post('/api/evidence')
def attach(body:EvidenceInput,request:Request,response:Response,x_demo_role:str=Header('evaluator')):
    role_check(x_demo_role,['evaluator'])
    if '://' in body.reference and not re.match(r'^https://[^\s/@]+(?:/|$)',body.reference):raise HTTPException(422,'Use a valid HTTPS source link or a plain attachment reference. Links are never fetched by the server.')
    if body.review_date<date.today().isoformat():raise HTTPException(422,'Review date must be today or later.')
    def run(s):
        a=find(s['assessments'],s['active_assessment']);editable(a)
        for rid in body.requirements:find(a['requirements'],rid)
        e={**body.model_dump(),'id':'E-'+uuid.uuid4().hex[:8],'provenance':'Evaluator supplied reference; no automatic verification','source_url':body.reference if body.reference.startswith('https://') else '', 'retrieved_at':now(),'service_context':a['usecase_id'],'model_id':a['model_id'],'context':deepcopy(a['context']),'scope_keys':['model','task','languages','dataset','deployment','sensitivity','method'],'verification':'Pending review','reviewer':None,'reuse_applicability':'Human scope review required'}
        s['evidence'].append(e);audit(s,x_demo_role,'Evidence reference attached',e['id']);return view(s)
    return transact(request,response,run)
@app.post('/api/evidence/{eid}/review')
def review(eid:str,request:Request,response:Response,x_demo_role:str=Header('evaluator')):
    role_check(x_demo_role,['evaluator'])
    def run(s):
        e=find(s['evidence'],eid)
        e['verification']='Reviewed claim; not independently verified' if e['type']=='Supplier claim' else 'Reviewed demonstration' if e['type']=='Demonstration data' else 'Verified'
        e['reviewer']=PERSONAS[x_demo_role];audit(s,x_demo_role,'Evidence reviewed',eid,'Provenance remains '+e['type']);return view(s)
    return transact(request,response,run)
@app.post('/api/evidence/{eid}/summary')
def summary(eid:str,request:Request,response:Response,x_demo_role:str=Header('evaluator')):
    role_check(x_demo_role,['owner','evaluator','approver','auditor'])
    return transact(request,response,lambda s:assistant.summarize(find(s['evidence'],eid)))
@app.post('/api/assessments/{aid}/submit')
def submit(aid:str,request:Request,response:Response,x_demo_role:str=Header('evaluator')):
    role_check(x_demo_role,['evaluator'])
    def run(s):
        a=find(s['assessments'],aid);editable(a);g=gate(s,a)
        if not g['eligible']:raise HTTPException(409,'Mandatory checks block submission: '+', '.join(g['blocked']))
        u=find(s['usecases'],a['usecase_id'])
        if u['version']!=a['usecase_version']:raise HTTPException(409,'Service has a newer version. Start a new assessment.')
        if any(t['status']=='open' for t in a['tasks']):raise HTTPException(409,'Complete all reopened checks before submission.')
        a['status']='submitted';a['submitted_at']=now();a['submitted_by']=PERSONAS[x_demo_role];audit(s,x_demo_role,'Assessment submitted',aid);return view(s)
    return transact(request,response,run)
@app.post('/api/assessments/{aid}/decision')
def decision(aid:str,body:DecisionInput,request:Request,response:Response,x_demo_role:str=Header('approver')):
    role_check(x_demo_role,['approver'])
    if body.review_date<=date.today().isoformat():raise HTTPException(422,'Decision review date must be in the future.')
    if body.decision=='approve_with_conditions' and (not body.conditions.strip() or not body.owner.strip() or body.deadline<=date.today().isoformat()):raise HTTPException(422,'Conditional approval needs conditions, an owner and a future deadline.')
    def run(s):
        a=find(s['assessments'],aid)
        if a['status']!='submitted':raise HTTPException(409,'Only submitted assessments can receive a decision.')
        if body.decision.startswith('approve'):
            g=gate(s,a)
            if not g['eligible']:raise HTTPException(409,'Mandatory requirements cannot be bypassed: '+', '.join(g['blocked']))
            if find(s['usecases'],a['usecase_id'])['version']!=a['usecase_version']:raise HTTPException(409,'Service context changed. Reassessment required.')
            if any(e['from_assessment']==aid for e in s['events']):raise HTTPException(409,'A material change has been recorded. Review the new assessment.')
            if any(t['status']=='open' for t in a['tasks']):raise HTTPException(409,'Reopened checks remain incomplete.')
        p={'id':'DEC-'+str(len(s['approvals'])+1).zfill(3),**body.model_dump(),'assessment_id':aid,'reviewer':PERSONAS[x_demo_role],'role':'Demonstration approver','at':now(),'snapshot':deepcopy(a),'evidence_snapshot':[deepcopy(e) for e in s['evidence'] if e['id'] in {eid for f in a['findings'] for eid in f['evidence_ids']}],'unresolved_issues':[r['id'] for r in check_findings(s,a) if r['state']!='pass'],'scope':'Demonstration service, exact model version, configuration and conditions only. No government authorization.'}
        s['approvals'].append(p);a['status']=body.decision
        if body.decision=='approve_with_conditions':s['conditions'].append({'id':'COND-'+p['id'],'decision_id':p['id'],'text':body.conditions,'owner':body.owner,'deadline':body.deadline,'status':'open','mandatory_exception':False})
        if body.decision=='request_changes':
            b=deepcopy(a);b.update({'id':'AS-'+str(len(s['assessments'])+1).zfill(3),'status':'draft','parent_id':aid,'created_at':now()});s['assessments'].append(b);s['active_assessment']=b['id']
        audit(s,x_demo_role,'Decision: '+body.decision,p['id'],body.rationale);return view(s)
    return transact(request,response,run)
@app.post('/api/assessments/{aid}/changes')
def change(aid:str,body:ChangeInput,request:Request,response:Response,x_demo_role:str=Header('owner')):
    role_check(x_demo_role,['owner','evaluator'])
    def run(s):
        a=find(s['assessments'],aid)
        if body.kind=='model' and body.new_value==a['model_version']:raise HTTPException(422,'Choose a different version.')
        if body.kind=='requirement':
            r=find(a['requirements'],body.requirement_id)
            try:value=float(body.new_value)
            except ValueError:raise HTTPException(422,'Threshold must be numeric.')
            if value<0 or value>1000000 or (r['unit']=='fraction' and value>1):raise HTTPException(422,'Invalid threshold for this unit.')
            if value==r['threshold']:raise HTTPException(422,'Choose a different threshold.')
        b,event=apply_change(s,a,body.kind,body.new_value,body.requirement_id)
        if body.kind=='requirement':
            u=find(s['usecases'],a['usecase_id']);u['version']+=1;b['usecase_version']=u['version'];u['requirements']=deepcopy(b['requirements']);u['versions'].append({'version':u['version'],'created_at':now(),'snapshot':{k:deepcopy(v) for k,v in u.items() if k!='versions'}})
        if body.kind=='incident':s['incidents'].append({'id':'INC-'+uuid.uuid4().hex[:8],'description':body.new_value,'assessment_id':b['id'],'at':now(),'status':'open'})
        audit(s,x_demo_role,'Change recorded',event['id'],body.kind+': '+body.new_value);return view(s)
    return transact(request,response,run)
@app.get('/api/export')
def export(request:Request,response:Response):
    data=transact(request,response,view)
    response.headers['Content-Disposition']='attachment; filename=modelfit-evidence-trail.json'
    return data
static=Path(__file__).parent.parent/'frontend'/'dist'
if static.exists():
    app.mount('/assets',StaticFiles(directory=static/'assets'),name='assets')
    @app.get('/{path:path}')
    def frontend(path:str):
        if path.startswith('api/'):raise HTTPException(404,'Endpoint not found')
        return FileResponse(static/'index.html')
