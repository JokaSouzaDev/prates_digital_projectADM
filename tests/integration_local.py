import json, urllib.request, urllib.error, http.cookiejar, os, sys, subprocess, time, tempfile, zipfile, io
from pathlib import Path
root=Path(__file__).resolve().parents[1]
testdata=Path(tempfile.mkdtemp(prefix='prates-regression-')).resolve()
env=dict(os.environ,PRATES_DATA_DIR=str(testdata),PRATES_PORT='8876',DATABASE_URL='',VERCEL='',PRATES_SETUP_KEY='')
server=subprocess.Popen([sys.executable,str(root/'server.py')],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
base='http://127.0.0.1:8876'
csrf=None
client=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
def api(path,method='GET',body=None,expected=200,agent=None,token=True):
    headers={'Content-Type':'application/json'}
    if token and csrf:headers['X-CSRF-Token']=csrf
    req=urllib.request.Request(base+'/api'+path,data=json.dumps(body).encode() if body is not None else None,method=method,headers=headers)
    try:r=(agent or client).open(req);code=r.status;raw=r.read()
    except urllib.error.HTTPError as e:code=e.code;raw=e.read()
    assert code==expected,(path,code,raw.decode(errors='replace'))
    return json.loads(raw)
try:
    for i in range(50):
        try:api('/session');break
        except OSError:time.sleep(.1)
    assert api('/session')['setup']
    code=api('/setup','POST',{'name':'Joaquim','email':'admin@example.test','password':'test-password-123'},201)['recovery']
    csrf=api('/session')['csrf']
    api('/records/clients','POST',{'name':'CSRF'},403,token=False)
    cid=api('/records/clients','POST',{'name':'Cliente de teste','email':'client@example.test','status':'Ativo'})['id']
    state=api('/state');service=state['data']['services'][0]['id']
    sale={'name':'Projeto de teste','client':cid,'items':[{'service':service,'quantity':1,'price':1000.01}],'discount':0,'installments':3,'due':'2026-09-10','date':'2026-09-01','status':'Confirmada'}
    sid=api('/records/sales','POST',sale)['id']
    st=api('/state')['data'];rs=[r for r in st['receivables'] if r.get('sale')==sid]
    assert round(sum(r['amount'] for r in rs),2)==1000.01
    assert len(rs)==3 and len(st['projects'])==1 and len(st['onboarding'])==1
    entrysale=api('/records/sales','POST',{**sale,'name':'Venda com entrada','downPayment':200,'entryDue':'2026-09-01'})['id']
    entries=[r for r in api('/state')['data']['receivables'] if r.get('sale')==entrysale]
    assert len(entries)==4 and round(sum(r['amount'] for r in entries),2)==1000.01
    assert next(r for r in entries if 'Entrada' in r['name'])['amount']==200
    rec=rs[0]
    api('/records/receivables/'+rec['id']+'/settle','POST',{'amount':100,'date':'2026-09-01','version':rec['version']})
    api('/records/receivables/'+rec['id']+'/settle','POST',{'amount':100,'date':'2026-09-01','version':rec['version']},409)
    st=api('/state')['data'];rec=next(r for r in st['receivables'] if r['id']==rec['id'])
    assert rec['paid']==100 and rec['status']=='Parcial'
    api('/records/receivables/'+rec['id']+'/settle','POST',{'amount':9999,'version':rec['version']},400)
    original=next(r for r in st['sales'] if r['id']==sid)
    api('/records/sales/'+sid,'PUT',{**original,'status':'Cancelado'},400)
    sub=api('/records/subscriptions','POST',{'name':'Mensalidade','client':cid,'amount':450,'nextDue':'2026-10-01','status':'Ativo'})['id']
    api('/records/subscriptions/'+sub+'/generate','POST',{'version':1})
    api('/records/subscriptions/'+sub+'/generate','POST',{'version':1},409)
    proposal=api('/records/proposals','POST',{**sale,'name':'Proposta teste','status':'Aprovada'})['id']
    api('/records/proposals/'+proposal+'/convert','POST',{'version':1,'due':'2026-10-01'})
    api('/records/proposals/'+proposal+'/convert','POST',{'version':1},409)
    exp=api('/records/expenses','POST',{'name':'Ferramenta','amount':30,'due':'2026-09-10','recurring':'Mensal','status':'Pendente'})['id']
    api('/records/expenses/'+exp+'/generate','POST',{'version':1})
    api('/records/expenses/'+exp+'/generate','POST',{'version':1},409)
    user=api('/users','POST',{'name':'Kauã','email':'production@example.test','password':'test-password-456','role':'production'},201)
    prod=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    api('/login','POST',{'email':'production@example.test','password':'test-password-456'},agent=prod)
    ps=api('/state',agent=prod);assert 'receivables' not in ps['data'] and 'sales' not in ps['data']
    api('/backup',expected=403,agent=prod)
    api('/audit',expected=403,agent=prod)
    import base64
    aid=api('/attachments','POST',{'record_id':cid,'name':'briefing.txt','content':base64.b64encode(b'attachment test').decode()},201)['id']
    assert len(api('/attachments?record_id='+cid))==1
    raw=client.open(base+'/api/backup').read()
    with zipfile.ZipFile(io.BytesIO(raw)) as z:assert 'prates.sqlite3' in z.namelist() and 'uploads/'+aid in z.namelist()
    api('/logout','POST',{})
    api('/state',expected=401)
    api('/recover','POST',{'email':'admin@example.test','password':'new-test-password-123','code':code})
    assert api('/session')['user']['name']=='Joaquim'
    assert len(api('/state')['data']['sales'])==3
    print('PASS: setup, CSRF, sale rounding and linked records, partial payment, stale action protection, overpayment rejection, cancellation rollback, monthly billing, proposal conversion, recurring expense, roles, attachments, backup, recovery and persistence.')
finally:
    server.terminate();server.wait(timeout=10)
