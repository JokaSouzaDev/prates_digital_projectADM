"""Prates Digital: local administrative application, Python standard library only."""
import base64, csv, hashlib, hmac, io, json, os, re, secrets, sqlite3, sys, time
from datetime import date, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

ROOT = Path(__file__).resolve().parent
DATA = Path(os.environ.get('PRATES_DATA_DIR', str(ROOT / 'data')))
DATA.mkdir(parents=True, exist_ok=True)
(DATA / 'uploads').mkdir(exist_ok=True)
DB = DATA / 'prates.sqlite3'
ENTITIES = ['clients','leads','services','proposals','contracts','sales','onboarding','projects','content','campaigns','subscriptions','receivables','expenses','partners','goals','tasks']
ROLES = {'admin': ENTITIES, 'finance': ['clients','services','contracts','sales','subscriptions','receivables','expenses','partners','goals','tasks'], 'sales': ['clients','leads','services','proposals','contracts','sales','goals','tasks'], 'production': ['clients','services','onboarding','projects','content','campaigns','tasks']}

def conn():
    c = sqlite3.connect(DB, timeout=20)
    c.row_factory = sqlite3.Row
    c.execute('PRAGMA foreign_keys=ON')
    return c

def initialize():
    with conn() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY,name TEXT NOT NULL,email TEXT UNIQUE NOT NULL,password TEXT NOT NULL,role TEXT NOT NULL,active INTEGER NOT NULL DEFAULT 1,recovery TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY,user_id TEXT REFERENCES users(id),csrf TEXT,expires REAL);
        CREATE TABLE IF NOT EXISTS records(id TEXT PRIMARY KEY,entity TEXT NOT NULL,data TEXT NOT NULL,created TEXT NOT NULL,updated TEXT NOT NULL,version INTEGER NOT NULL DEFAULT 1);
        CREATE INDEX IF NOT EXISTS entity_idx ON records(entity);
        CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY AUTOINCREMENT,at TEXT,user_id TEXT,action TEXT,entity TEXT,record_id TEXT,detail TEXT);
        CREATE TABLE IF NOT EXISTS settings(id INTEGER PRIMARY KEY CHECK(id=1),data TEXT);
        CREATE TABLE IF NOT EXISTS attachments(id TEXT PRIMARY KEY,record_id TEXT REFERENCES records(id),name TEXT,size INTEGER,created TEXT);
        CREATE TABLE IF NOT EXISTS attempts(key TEXT PRIMARY KEY,count INTEGER,until REAL);
        ''')
        c.execute('INSERT OR IGNORE INTO settings VALUES(1,?)', (json.dumps({'name':'Prates Digital','email':'','phone':'','document':'','address':'','logo':'','proposalFooter':'Obrigado por escolher a Prates Digital.'}),))
        if not c.execute("SELECT 1 FROM records WHERE entity='services'").fetchone():
            for name,category,recurring in [('Sites e landing pages','Desenvolvimento',False),('Bots para WhatsApp e Instagram','Automação',False),('Integração com IA e automações','Automação',False),('Identidade visual','Design',False),('Criação de artes','Design',False),('Edição de vídeos','Conteúdo',False),('Gestão e otimização de redes sociais','Conteúdo',True),('Perfil da empresa no Google','Presença digital',False),('Tráfego pago e rastreamento','Marketing',True),('Estratégia comercial e resultados','Consultoria',True)]:
                add_record(c,'services',{'name':name,'category':category,'price':0,'cost':0,'deadline':0,'billing':'Mensal' if recurring else 'Avulso','status':'Ativo','description':'Defina preço, escopo e prazo antes de vender.'})

def now(): return datetime.now().isoformat(timespec='seconds')
def audit(c,u,action,entity='',rid='',detail=None):
    c.execute('INSERT INTO audit(at,user_id,action,entity,record_id,detail) VALUES(?,?,?,?,?,?)',(now(),u,action,entity,rid,json.dumps(detail or {},ensure_ascii=False)))
def add_record(c,entity,data):
    rid=secrets.token_hex(12)
    c.execute('INSERT INTO records VALUES(?,?,?,?,?,1)',(rid,entity,json.dumps(data,ensure_ascii=False),now(),now()))
    return rid
def unpack(r): return {'id':r['id'],'entity':r['entity'],'created':r['created'],'updated':r['updated'],'version':r['version'],**json.loads(r['data'])}
def records(c,entity): return [unpack(r) for r in c.execute('SELECT * FROM records WHERE entity=? ORDER BY created DESC',(entity,))]
def password_hash(p):
    salt=secrets.token_hex(16)
    return salt+':'+hashlib.pbkdf2_hmac('sha256',p.encode(),bytes.fromhex(salt),300000).hex()
def verify(p,stored):
    salt,digest=stored.split(':')
    return hmac.compare_digest(hashlib.pbkdf2_hmac('sha256',p.encode(),bytes.fromhex(salt),300000).hex(),digest)
def recovery_code(): return secrets.token_hex(16)
def digest(s): return hashlib.sha256(s.encode()).hexdigest()
def user_public(u): return {k:u[k] for k in ('id','name','email','role','active')}
def month_add(s,n):
    d=date.fromisoformat(s); m=d.month-1+n; y=d.year+m//12; m=m%12+1
    import calendar
    return date(y,m,min(d.day,calendar.monthrange(y,m)[1])).isoformat()

class App(BaseHTTPRequestHandler):
    server_version='PratesDigital'
    def log_message(self,*args): pass
    def send(self,status,obj,ctype='application/json; charset=utf-8',headers=None):
        raw=json.dumps(obj,ensure_ascii=False).encode() if 'json' in ctype else obj if isinstance(obj,bytes) else obj.encode()
        self.send_response(status)
        self.send_header('Content-Type',ctype);self.send_header('Content-Length',str(len(raw)))
        self.send_header('X-Content-Type-Options','nosniff');self.send_header('X-Frame-Options','DENY')
        self.send_header('Referrer-Policy','no-referrer');self.send_header('Cache-Control','no-store')
        self.send_header('Content-Security-Policy',"default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; script-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
        for k,v in (headers or {}).items(): self.send_header(k,v)
        self.end_headers();self.wfile.write(raw)
    def body(self):
        size=int(self.headers.get('Content-Length','0'))
        if size>8_000_000: raise ValueError('Arquivo ou conteúdo muito grande. Limite: 5 MB por anexo.')
        return json.loads(self.rfile.read(size) or '{}')
    def session(self,c):
        cookies=dict(re.findall(r'(\w+)=([^;]+)',self.headers.get('Cookie','')))
        row=c.execute('SELECT u.*,s.csrf FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token=? AND s.expires>? AND u.active=1',(digest(cookies.get('prates','')),time.time())).fetchone()
        return row
    def auth_cookie(self,c,uid):
        token=secrets.token_urlsafe(32);csrf=secrets.token_urlsafe(24)
        c.execute('DELETE FROM sessions WHERE expires<?',(time.time(),))
        c.execute('INSERT INTO sessions VALUES(?,?,?,?)',(digest(token),uid,csrf,time.time()+43200))
        secure='; Secure' if os.environ.get('PRATES_SECURE_COOKIE')=='1' else ''
        return csrf,{'Set-Cookie':f'prates={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age=43200{secure}'}
    def do_GET(self): self.handle_request('GET')
    def do_POST(self): self.handle_request('POST')
    def do_PUT(self): self.handle_request('PUT')
    def do_DELETE(self): self.handle_request('DELETE')
    def handle_request(self,method):
        try:
            parsed=urlparse(self.path);path=parsed.path
            if not path.startswith('/api/'):
                if method!='GET': return self.send(405,{'error':'Método inválido.'})
                files={'/':('index.html','text/html; charset=utf-8'),'/app.js':('app.js','text/javascript; charset=utf-8'),'/style.css':('style.css','text/css; charset=utf-8')}
                if path not in files: return self.send(404,{'error':'Não encontrado.'})
                f,ct=files[path];return self.send(200,(ROOT/f).read_bytes(),ct)
            if method!='GET':
                origin=self.headers.get('Origin')
                if origin and urlparse(origin).netloc!=self.headers.get('Host'):return self.send(403,{'error':'Origem não permitida.'})
            with conn() as c:
                if path=='/api/session':
                    u=self.session(c)
                    return self.send(200,{'setup':not bool(c.execute('SELECT 1 FROM users').fetchone()),'user':user_public(u) if u else None,'csrf':u['csrf'] if u else None})
                if path in ['/api/setup','/api/login','/api/recover'] and method=='POST':
                    b=self.body();email=str(b.get('email','')).strip().lower();pw=str(b.get('password',''))
                    key=self.client_address[0]+':'+email
                    attempt=c.execute('SELECT * FROM attempts WHERE key=?',(key,)).fetchone()
                    if attempt and attempt['count']>=8 and attempt['until']>time.time():return self.send(429,{'error':'Muitas tentativas. Aguarde 15 minutos.'})
                    if path=='/api/setup':
                        c.execute('BEGIN IMMEDIATE')
                        if c.execute('SELECT 1 FROM users').fetchone():return self.send(409,{'error':'A configuração inicial já foi concluída.'})
                        if len(pw)<10 or '@' not in email or not b.get('name','').strip():raise ValueError('Informe nome, e-mail e uma senha com pelo menos 10 caracteres.')
                        uid=secrets.token_hex(12);code=recovery_code()
                        c.execute('INSERT INTO users VALUES(?,?,?,?,?,1,?)',(uid,b['name'].strip(),email,password_hash(pw),'admin',digest(code)))
                        audit(c,uid,'Conta inicial criada');csrf,headers=self.auth_cookie(c,uid)
                        c.commit();return self.send(201,{'recovery':code,'csrf':csrf},headers=headers)
                    u=c.execute('SELECT * FROM users WHERE email=? AND active=1',(email,)).fetchone()
                    valid=u and (verify(pw,u['password']) if path=='/api/login' else hmac.compare_digest(digest(str(b.get('code',''))),u['recovery']))
                    if not valid:
                        count=attempt['count']+1 if attempt and attempt['until']>time.time() else 1
                        c.execute('INSERT OR REPLACE INTO attempts VALUES(?,?,?)',(key,count,time.time()+900));c.commit()
                        return self.send(401,{'error':'Credenciais inválidas.'})
                    code=None
                    if path=='/api/recover':
                        if len(pw)<10:raise ValueError('A nova senha deve ter pelo menos 10 caracteres.')
                        code=recovery_code();c.execute('UPDATE users SET password=?,recovery=? WHERE id=?',(password_hash(pw),digest(code),u['id']));c.execute('DELETE FROM sessions WHERE user_id=?',(u['id'],))
                    c.execute('DELETE FROM attempts WHERE key=?',(key,));csrf,headers=self.auth_cookie(c,u['id']);audit(c,u['id'],'Recuperação de acesso' if code else 'Login');c.commit()
                    return self.send(200,{'csrf':csrf,'recovery':code},headers=headers)
                u=self.session(c)
                if not u:return self.send(401,{'error':'Entre na sua conta para continuar.'})
                if method!='GET' and not hmac.compare_digest(self.headers.get('X-CSRF-Token',''),u['csrf']):return self.send(403,{'error':'Sessão inválida. Atualize a página.'})
                if path=='/api/logout' and method=='POST':
                    c.execute('DELETE FROM sessions WHERE user_id=? AND csrf=?',(u['id'],u['csrf']));c.commit()
                    return self.send(200,{},headers={'Set-Cookie':'prates=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0'})
                allowed=ROLES[u['role']]
                if path=='/api/state' and method=='GET':
                    result={e:records(c,e) for e in allowed}
                    users=[user_public(x) for x in c.execute('SELECT * FROM users')]
                    if u['role']!='admin':users=[{k:x[k] for k in ('id','name','active')} for x in users]
                    return self.send(200,{'data':result,'users':users,'settings':json.loads(c.execute('SELECT data FROM settings WHERE id=1').fetchone()[0]),'allowed':allowed})
                if path=='/api/settings' and method=='PUT':
                    if u['role']!='admin':return self.send(403,{'error':'Apenas administradores.'})
                    b=self.body();clean={k:str(b.get(k,''))[:2000] for k in ['name','email','phone','document','address','proposalFooter']};clean['logo']=str(b.get('logo',''))
                    if clean['logo'] and not re.match(r'^data:image/(png|jpeg|webp);base64,',clean['logo']):raise ValueError('Use uma imagem PNG, JPG ou WebP.')
                    c.execute('UPDATE settings SET data=? WHERE id=1',(json.dumps(clean),));audit(c,u['id'],'Configurações atualizadas');c.commit();return self.send(200,{'ok':True})
                if path=='/api/users' and method=='POST':
                    if u['role']!='admin':return self.send(403,{'error':'Apenas administradores.'})
                    b=self.body();email=str(b.get('email','')).strip().lower();pw=str(b.get('password',''));role=b.get('role','production')
                    if role not in ROLES or len(pw)<10 or '@' not in email or not b.get('name'):raise ValueError('Confira nome, e-mail, perfil e senha (mínimo 10 caracteres).')
                    uid=secrets.token_hex(12);code=recovery_code();c.execute('INSERT INTO users VALUES(?,?,?,?,?,1,?)',(uid,b['name'],email,password_hash(pw),role,digest(code)));audit(c,u['id'],'Usuário criado','users',uid);c.commit();return self.send(201,{'recovery':code})
                if path.startswith('/api/users/') and method=='PUT':
                    if u['role']!='admin':return self.send(403,{'error':'Apenas administradores.'})
                    uid=path.rsplit('/',1)[1];b=self.body();role=b.get('role');active=1 if b.get('active') else 0
                    if role not in ROLES:raise ValueError('Perfil inválido.')
                    if uid==u['id'] and (not active or role!='admin'):raise ValueError('Você não pode remover seu próprio acesso de administrador.')
                    c.execute('UPDATE users SET active=?,role=? WHERE id=?',(active,role,uid))
                    if uid!=u['id']:c.execute('DELETE FROM sessions WHERE user_id=?',(uid,))
                    audit(c,u['id'],'Permissões atualizadas','users',uid);c.commit();return self.send(200,{'ok':True})
                if path=='/api/audit' and method=='GET':
                    if u['role']!='admin':return self.send(403,{'error':'Apenas administradores.'})
                    return self.send(200,[dict(x) for x in c.execute('SELECT a.*,u.name as actor FROM audit a LEFT JOIN users u ON u.id=a.user_id ORDER BY a.id DESC LIMIT 500')])
                if path=='/api/backup' and method=='GET':
                    if u['role']!='admin':return self.send(403,{'error':'Apenas administradores.'})
                    import zipfile
                    dest=io.BytesIO()
                    mem=sqlite3.connect(':memory:');c.backup(mem)
                    with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED) as z:
                        z.writestr('prates.sqlite3',mem.serialize())
                        for f in (DATA/'uploads').iterdir():
                            if f.is_file():z.write(f,'uploads/'+f.name)
                    mem.close()
                    return self.send(200,dest.getvalue(),'application/zip',{'Content-Disposition':'attachment; filename="prates-backup.zip"'})
                if path.startswith('/api/attachments'):
                    if method=='POST' and path=='/api/attachments':
                        b=self.body();r=c.execute('SELECT * FROM records WHERE id=?',(b.get('record_id'),)).fetchone()
                        if not r or r['entity'] not in allowed:return self.send(403,{'error':'Registro indisponível.'})
                        raw=base64.b64decode(b.get('content',''),validate=True)
                        if len(raw)>5_000_000:raise ValueError('O limite por arquivo é 5 MB.')
                        aid=secrets.token_hex(16);name=Path(str(b.get('name','arquivo')).replace('\\','/')).name[:160]
                        (DATA/'uploads'/aid).write_bytes(raw);c.execute('INSERT INTO attachments VALUES(?,?,?,?,?)',(aid,r['id'],name,len(raw),now()));audit(c,u['id'],'Anexo adicionado',r['entity'],r['id'],{'name':name});c.commit();return self.send(201,{'id':aid})
                    if method=='GET' and path=='/api/attachments':
                        rid=parse_qs(parsed.query).get('record_id',[''])[0];r=c.execute('SELECT entity FROM records WHERE id=?',(rid,)).fetchone()
                        if not r or r['entity'] not in allowed:return self.send(403,{'error':'Registro indisponível.'})
                        return self.send(200,[dict(x) for x in c.execute('SELECT * FROM attachments WHERE record_id=?',(rid,))])
                    if method=='GET':
                        aid=path.rsplit('/',1)[1];a=c.execute('SELECT a.*,r.entity FROM attachments a JOIN records r ON r.id=a.record_id WHERE a.id=?',(aid,)).fetchone()
                        if not a or a['entity'] not in allowed:return self.send(404,{'error':'Arquivo indisponível.'})
                        from urllib.parse import quote
                        return self.send(200,(DATA/'uploads'/aid).read_bytes(),'application/octet-stream',{'Content-Disposition':"attachment; filename*=UTF-8''"+quote(a['name'])})
                match=re.fullmatch('/api/records/([a-z]+)(?:/([a-f0-9]+))?(?:/(settle|convert|generate))?',path)
                if match:
                    entity,rid,action=match.groups()
                    if entity not in allowed:return self.send(403,{'error':'Seu perfil não possui acesso a esta área.'})
                    if method not in ['POST','PUT','DELETE']:return self.send(405,{'error':'Método inválido.'})
                    b=self.body();c.execute('BEGIN IMMEDIATE')
                    row=c.execute('SELECT * FROM records WHERE id=? AND entity=?',(rid,entity)).fetchone() if rid else None
                    if rid and not row:return self.send(404,{'error':'Registro não encontrado.'})
                    old=json.loads(row['data']) if row else {}
                    if action:
                        if method!='POST':raise ValueError('Ação inválida.')
                        if b.get('version')!=row['version']:return self.send(409,{'error':'O registro mudou. Atualize a página antes de repetir a operação.'})
                        result=self.action(c,u,entity,rid,action,old,b)
                        c.commit();return self.send(200,result)
                    if method=='DELETE':
                        if entity in ['sales','receivables','expenses','partners','subscriptions']:raise ValueError('Para preservar o histórico financeiro, cancele o registro em vez de excluir.')
                        for other in c.execute('SELECT data FROM records WHERE id!=?',(rid,)):
                            data=json.loads(other[0])
                            if rid in [v for v in data.values() if isinstance(v,str)] or any(isinstance(v,list) and any(isinstance(i,dict) and i.get('service')==rid for i in v) for v in data.values()):raise ValueError('Este registro está vinculado a outros. Atualize os vínculos antes de excluir.')
                        if c.execute('SELECT 1 FROM attachments WHERE record_id=?',(rid,)).fetchone():raise ValueError('Registros com anexos devem ser mantidos para preservar o histórico.')
                        c.execute('DELETE FROM records WHERE id=?',(rid,));audit(c,u['id'],'Exclusão',entity,rid,old)
                    else:
                        if row and b.get('version')!=row['version']:return self.send(409,{'error':'Este registro foi alterado por outra pessoa. Feche, atualize e tente novamente.'})
                        data={k:v for k,v in b.items() if k not in ['id','entity','created','updated','version']}
                        self.validate(c,entity,data)
                        if entity=='sales' and not row and data.get('status')!='Confirmada':raise ValueError('Uma nova venda deve ser confirmada. Cancele depois, se necessário.')
                        if entity in ['receivables','expenses']:
                            if not row:data['paid']=0;data['payments']=[]
                            else:
                                data['paid']=old.get('paid',0);data['payments']=old.get('payments',[])
                                if data.get('amount',0)<data['paid']:raise ValueError('O valor não pode ser menor que o valor já pago.')
                                if data.get('status')=='Cancelado' and data['paid']:raise ValueError('Um lançamento com pagamento não pode ser cancelado. Registre o estorno como um lançamento separado.')
                        if entity=='sales' and row:
                            for k in ['items','amount','discount','installments','due','client','downPayment','entryDue']:
                                default=0 if k=='downPayment' else '' if k=='entryDue' else None
                                if data.get(k,default)!=old.get(k,default):raise ValueError('Valores e cliente de uma venda lançada não podem mudar. Cancele e registre uma nova venda.')
                            if data.get('status')=='Cancelado' and old.get('status')!='Cancelado':
                                for rec in records(c,'receivables'):
                                    if rec.get('sale')==rid:
                                        if rec.get('paid',0)>0:raise ValueError('Esta venda já tem recebimentos. Registre os estornos antes de tratar o cancelamento.')
                                        self.update(c,rec['id'],{k:v for k,v in rec.items() if k not in ['id','entity','created','updated','version']}|{'status':'Cancelado'})
                        if row:self.update(c,rid,data)
                        else:
                            rid=add_record(c,entity,data)
                            if entity=='sales':self.sale_flow(c,rid,data)
                        audit(c,u['id'],'Atualização' if row else 'Criação',entity,rid,{'before':old,'after':data})
                    c.commit();return self.send(200,{'id':rid})
                return self.send(404,{'error':'Operação não encontrada.'})
        except ValueError as e:self.send(400,{'error':str(e)})
        except sqlite3.IntegrityError:self.send(409,{'error':'Já existe um cadastro com esses dados ou um vínculo impede a operação.'})
        except Exception as e:
            print(type(e).__name__,str(e),file=sys.stderr)
            self.send(500,{'error':'Não foi possível concluir a operação. Os dados da transação não foram salvos.'})
    def update(self,c,rid,data):c.execute('UPDATE records SET data=?,updated=?,version=version+1 WHERE id=?',(json.dumps(data,ensure_ascii=False),now(),rid))
    def validate(self,c,entity,d):
        if len(json.dumps(d))>150000:raise ValueError('Conteúdo muito extenso.')
        if not str(d.get('name','')).strip():raise ValueError('Informe o nome ou título.')
        for key in ['amount','price','cost','discount','downPayment','budget','spend','revenue','target','current','deadline','leads','clicks','impressions','conversions']:
            if key in d:
                try:d[key]=round(float(d[key] or 0),2)
                except (ValueError,TypeError):raise ValueError('Valor numérico inválido: '+key)
                if not 0<=d[key]<=1e12:raise ValueError('Valores devem ser positivos e finitos.')
        for key in ['date','due','entryDue','start','end','validUntil','nextDue']:
            if d.get(key):date.fromisoformat(d[key])
        for key,target in [('client','clients'),('service','services'),('project','projects'),('owner','users')]:
            if d.get(key):
                row=c.execute('SELECT 1 FROM users WHERE id=?',(d[key],)).fetchone() if target=='users' else c.execute('SELECT 1 FROM records WHERE id=? AND entity=?',(d[key],target)).fetchone()
                if not row:raise ValueError('Vínculo inválido: '+key)
        if entity in ['sales','proposals']:
            if not d.get('client'):raise ValueError('Selecione o cliente.')
            items=d.get('items',[])
            if not items:raise ValueError('Adicione pelo menos um serviço.')
            total=0
            for i in items:
                if not c.execute("SELECT 1 FROM records WHERE id=? AND entity='services'",(i.get('service'),)).fetchone():raise ValueError('Serviço inválido.')
                q=float(i.get('quantity',0));p=float(i.get('price',0))
                if not 0<q<=10000 or not 0<=p<=1e9:raise ValueError('Confira quantidades e preços.')
                total+=round(q*p,2)
            discount=d.get('discount',0)
            if discount>total:raise ValueError('O desconto não pode superar o total.')
            d['amount']=round(total-discount,2)
            if d.get('downPayment',0)>d['amount']:raise ValueError('A entrada não pode superar o total.')
            if d.get('downPayment',0)>0 and not d.get('entryDue'):raise ValueError('Informe a data de vencimento da entrada.')
            d['installments']=int(d.get('installments',1))
            if not 1<=d['installments']<=60:raise ValueError('Use entre 1 e 60 parcelas.')
            if entity=='sales' and (not d.get('due') or d['amount']<=0):raise ValueError('Informe vencimento e valor de venda maior que zero.')
        if entity in ['receivables','expenses','subscriptions'] and (not d.get('due' if entity!='subscriptions' else 'nextDue') or d.get('amount',0)<=0):raise ValueError('Informe um valor maior que zero e um vencimento.')
    def sale_flow(self,c,rid,d):
        entry=d.get('downPayment',0)
        if entry>0:add_record(c,'receivables',{'name':d['name']+' · Entrada','client':d['client'],'sale':rid,'amount':entry,'paid':0,'payments':[],'due':d['entryDue'],'date':d.get('date',date.today().isoformat()),'category':'Serviços','status':'Pendente','owner':d.get('owner','')})
        n=d['installments'];cents=round((d['amount']-entry)*100);each=cents//n
        if cents:
            if cents<n:raise ValueError('Há parcelas demais para o valor restante.')
            for i in range(n):add_record(c,'receivables',{'name':d['name']+f' · {i+1}/{n}','client':d['client'],'sale':rid,'amount':(each+(cents%n if i==n-1 else 0))/100,'paid':0,'payments':[],'due':month_add(d['due'],i),'date':d.get('date',date.today().isoformat()),'category':'Serviços','status':'Pendente','owner':d.get('owner','')})
        add_record(c,'projects',{'name':d['name'],'client':d['client'],'sale':rid,'owner':d.get('owner',''),'status':'Onboarding','due':d.get('end',''),'notes':'Projeto criado pela venda. Confirme contrato, pagamento combinado e briefing antes de iniciar.','checklist':'[ ] Confirmar proposta e contrato\n[ ] Confirmar pagamento combinado\n[ ] Receber briefing\n[ ] Planejar entregas'})
        add_record(c,'onboarding',{'name':'Briefing · '+d['name'],'client':d['client'],'sale':rid,'owner':d.get('owner',''),'status':'Pendente','checklist':'[ ] Dados da empresa\n[ ] Objetivos e público\n[ ] Materiais e identidade visual\n[ ] Permissões de acesso','notes':'Registre apenas referências ao gerenciador de senhas, nunca senhas de clientes.'})
    def action(self,c,u,e,rid,action,d,b):
        if action=='settle' and e in ['receivables','expenses']:
            if d.get('status')=='Cancelado':raise ValueError('Lançamento cancelado.')
            amount=round(float(b.get('amount',0)),2);remaining=round(d['amount']-d.get('paid',0),2)
            if not 0<amount<=remaining:raise ValueError('O pagamento deve ser positivo e não superar o saldo restante.')
            day=b.get('date',date.today().isoformat());date.fromisoformat(day)
            if day>date.today().isoformat():raise ValueError('Um pagamento confirmado não pode ter data futura.')
            d['paid']=round(d.get('paid',0)+amount,2);d.setdefault('payments',[]).append({'amount':amount,'date':day,'method':b.get('method','Pix'),'by':u['id']});d['status']='Pago' if d['paid']==d['amount'] else 'Parcial';self.update(c,rid,d)
        elif action=='convert' and e=='proposals':
            if 'sales' not in ROLES[u['role']]:raise ValueError('Sem permissão para vendas.')
            if d.get('sale'):raise ValueError('Esta proposta já foi convertida.')
            if d.get('status')!='Aprovada':raise ValueError('A proposta precisa estar aprovada.')
            sale={**d,'name':d['name'],'date':date.today().isoformat(),'due':b.get('due',date.today().isoformat()),'status':'Confirmada','proposal':rid};self.validate(c,'sales',sale)
            sid=add_record(c,'sales',sale);self.sale_flow(c,sid,sale);d['sale']=sid;self.update(c,rid,d)
        elif action=='generate' and e=='subscriptions':
            if d.get('status')!='Ativo':raise ValueError('A mensalidade não está ativa.')
            due=d['nextDue']
            if d.get('end') and due>d['end']:raise ValueError('O vencimento está depois do fim do contrato.')
            add_record(c,'receivables',{'name':d['name']+' · '+due[:7],'client':d.get('client',''),'subscription':rid,'amount':d['amount'],'paid':0,'payments':[],'due':due,'date':date.today().isoformat(),'category':'Mensalidades','status':'Pendente'});d['nextDue']=month_add(due,1);self.update(c,rid,d)
        elif action=='generate' and e=='expenses':
            if d.get('recurring')!='Mensal' or d.get('status')=='Cancelado':raise ValueError('Somente despesas mensais ativas podem gerar o próximo mês.')
            if d.get('nextExpense'):raise ValueError('O próximo mês já foi gerado para esta despesa.')
            new={**d,'due':month_add(d['due'],1),'date':date.today().isoformat(),'paid':0,'payments':[],'status':'Pendente'}
            new.pop('nextExpense',None)
            d['nextExpense']=add_record(c,'expenses',new);self.update(c,rid,d)
        else:raise ValueError('Ação indisponível.')
        audit(c,u['id'],action,e,rid,{'after':d});return {'ok':True}

if __name__=='__main__':
    initialize();host=os.environ.get('PRATES_HOST','127.0.0.1');port=int(os.environ.get('PRATES_PORT','8765'))
    print(f'Prates Digital disponível em http://{host}:{port}',flush=True)
    ThreadingHTTPServer((host,port),App).serve_forever()
