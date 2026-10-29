"""Deterministic prototype rules. No model or assistant can override these gates."""
from datetime import date
from copy import deepcopy
from .seed import now

def evidence_valid(e):
    return e.get('verification') in ('Reviewed demonstration','Verified','Source retrieved; workbook inspected') and bool(e.get('reviewer')) and e.get('review_date','') >= date.today().isoformat()

def check_findings(s,a):
    ev={e['id']:e for e in s['evidence']};out=[]
    for r in a['requirements']:
        f=next((f for f in a['findings'] if f['requirement_id']==r['id']),None)
        state=f['state'] if f else 'missing';reason=f.get('rationale','') if f else 'No finding recorded'
        if state=='not_applicable' and (r['mandatory'] or not reason.strip()):state='needs_review'
        if state=='pass':
            records=[ev.get(i) for i in f['evidence_ids']]
            if not records or any(not e or not evidence_valid(e) for e in records):state='missing';reason='Valid, reviewed, unexpired evidence is required.'
            elif any(e.get('model_id') and e['model_id']!=a['model_id'] for e in records):state='needs_review';reason='Model identifier differs from evidence scope.'
            elif any('model' in e.get('scope_keys',[]) and e['model_version']!=a['model_version'] for e in records):state='needs_review';reason='Exact model version differs from evidence scope.'
            elif any(any(e['context'].get(k)!=a['context'].get(k) for k in e.get('scope_keys',[]) if k!='model') for e in records):state='needs_review';reason='Evidence dependencies differ from current assessment context.'
            elif not (f['value']>=r['threshold'] if r['operator']=='>=' else f['value']<=r['threshold']):state='fail';reason='Result does not meet the configured threshold.'
        out.append({**r,'state':state,'reason':reason,'finding':f})
    return out

def gate(s,a):
    checks=check_findings(s,a);blocked=[r for r in checks if r['mandatory'] and r['state']!='pass']
    return {'eligible':not blocked,'blocked':[r['id'] for r in blocked],'checks':checks,'passed':sum(r['state']=='pass' for r in checks),'mandatory_passed':sum(r['mandatory'] and r['state']=='pass' for r in checks),'mandatory_total':sum(r['mandatory'] for r in checks),'coverage':round(100*sum(r['mandatory'] and r['state']=='pass' for r in checks)/max(1,sum(r['mandatory'] for r in checks)))}

def reuse_compatibility(e,a):
    checks=[]
    for key in e['scope_keys']:
        old=e['model_version'] if key=='model' else e['context'].get(key)
        new=a['model_version'] if key=='model' else a['context'].get(key)
        checks.append({'dependency':key,'previous':old,'current':new,'matches':old==new})
    checks.append({'dependency':'validity period','previous':e['review_date'],'current':date.today().isoformat(),'matches':evidence_valid(e)})
    if e.get('model_id'): checks.append({'dependency':'model identifier','previous':e['model_id'],'current':a['model_id'],'matches':e['model_id']==a['model_id']})
    return checks

def apply_change(s,a,kind,new_value,requirement_id=None):
    """Fork, never mutate earlier findings or decision snapshots."""
    b=deepcopy(a);b['id']='AS-'+str(len(s['assessments'])+1).zfill(3);b['status']='draft';b['created_at']=now();b['started_at']=now();b['parent_id']=a['id'];b['tasks']=[]
    mapping={'model':'model','requirement':'threshold','deployment':'deployment','data':'sensitivity','expiry':'validity','incident':'model'}
    dep=mapping[kind];old=a['model_version'] if kind=='model' else a['context'].get(dep,'No recorded change')
    if kind=='model':b['model_version']=new_value
    elif kind in ('deployment','data'):b['context'][dep]=new_value
    elif kind=='requirement':
        r=next((r for r in b['requirements'] if r['id']==requirement_id),None)
        if r is None:raise ValueError('Unknown requirement')
        old=r['threshold'];r['threshold']=float(new_value);b['usecase_version']+=1
    impacts=[]
    for f in b['findings']:
        r=next(r for r in b['requirements'] if r['id']==f['requirement_id'])
        affected=(dep in f['dependencies']) if kind not in ('requirement','expiry') else (f['requirement_id']==requirement_id if kind=='requirement' else bool(f['evidence_ids']))
        classification='retained';reason='Recorded dependencies are unchanged; evidence still needs to remain valid.'
        if affected:
            classification='invalidated' if kind in ('model','expiry','data') else 'needs_review'
            reason=f"{dep} changed: {old} → {new_value}. Finding {f['id']} depends on {', '.join(f['dependencies'])}."
            f['state']='needs_review';f['rationale']=reason
            b['tasks'].append({'id':'T-'+b['id']+'-'+r['id'],'requirement_id':r['id'],'title':'Reassess '+r['title'],'status':'open','owner':'Evaluator','reason':reason})
        f['impact']=classification
        impacts.append({'requirement_id':r['id'],'finding_id':f['id'],'evidence_ids':f['evidence_ids'],'classification':classification,'reason':reason})
    event={'id':'CHG-'+str(len(s['events'])+1).zfill(3),'kind':kind,'previous':old,'new':new_value,'from_assessment':a['id'],'to_assessment':b['id'],'impacts':impacts,'tasks_created':len(b['tasks']),'approval_impact':'Previous decision preserved for its exact snapshot. Changed configuration requires reassessment.','at':now()}
    s['assessments'].append(b);s['events'].append(event);s['active_assessment']=b['id']
    return b,event
