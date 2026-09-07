"""Regression tests. No external account, secret or network service is required."""
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import urlparse

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
_tmp=tempfile.TemporaryDirectory()
os.environ['PRATES_DATA_DIR']=_tmp.name
os.environ.pop('DATABASE_URL',None)
os.environ.pop('VERCEL',None)
import server
from database import postgres_sql
spec=importlib.util.spec_from_file_location('vercel_entry',ROOT/'api'/'index.py')
entry=importlib.util.module_from_spec(spec);spec.loader.exec_module(entry)


class Request(entry.handler):
    def __init__(self,path,body=None,headers=None):
        self.path=path
        raw=json.dumps(body or {}).encode()
        self.headers={'Host':'example.test','Content-Length':str(len(raw)),**(headers or {})}
        self.client_address=('127.0.0.1',0)
        self.rfile=io.BytesIO(raw)
        self.wfile=io.BytesIO()
        self.status=None;self.response_headers={}
    def send_response(self,status): self.status=status
    def send_header(self,key,value): self.response_headers[key]=value
    def end_headers(self):pass
    def result(self):return json.loads(self.wfile.getvalue())


class Routes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        server.ensure_ready()

    def request(self,path,method='GET',body=None,headers=None):
        r=Request(path,body,headers);r.handle_request(method);return r

    def test_rewritten_session(self):
        r=self.request('/api?_prates_route=session')
        self.assertEqual(r.status,200)
        self.assertIn('setup',r.result())
        self.assertTrue(r.response_headers['Content-Type'].startswith('application/json'))

    def test_original_route(self):
        r=self.request('/api/session')
        self.assertEqual(r.status,200)

    def test_unknown_route_is_json(self):
        r=self.request('/api?_prates_route=unknown')
        self.assertEqual(r.status,401)
        self.assertIn('error',r.result())

    def test_api_root_without_route_is_json_404(self):
        r=self.request('/api')
        self.assertEqual(r.status,404)

    def test_source_is_not_served(self):
        self.assertEqual(self.request('/server.py').status,404)

    def test_cloud_cannot_fall_back_to_sqlite(self):
        with patch.object(server,'CLOUD',True),patch.object(server,'DATABASE_URL',''),patch.object(server,'_ready',False):
            r=self.request('/api/session')
            self.assertEqual(r.status,503)
            self.assertEqual(r.result()['code'],'CONFIGURATION_REQUIRED')
            self.assertIn('DATABASE_URL',r.result()['error'])

    def test_setup_key_required(self):
        with patch.dict(os.environ,{'PRATES_SETUP_KEY':'test-only-installation-key-1234'}):
            r=self.request('/api/setup','POST',{'name':'Test','email':'test@example.test','password':'password-test-123'})
            self.assertEqual(r.status,403)

    def test_payload_rejected_before_parse(self):
        r=self.request('/api/login','POST',headers={'Content-Length':'4200000'})
        self.assertEqual(r.status,400)

    def test_secure_cookie_in_cloud(self):
        with server.conn() as c,patch.object(server,'CLOUD',True):
            # Cookie behavior independently of remote DB availability.
            uid=server.secrets.token_hex(12)
            c.execute('INSERT INTO users VALUES(?,?,?,?,?,1,?)',(uid,'Cookie','cookie@example.test','hash','admin','recovery'))
            request=Request('/api/session')
            _,headers=request.auth_cookie(c,uid)
            self.assertIn('; Secure',headers['Set-Cookie'])
            self.assertIn('HttpOnly',headers['Set-Cookie'])
            c.execute('DELETE FROM sessions WHERE user_id=?',(uid,))
            c.execute('DELETE FROM users WHERE id=?',(uid,))

    def test_sql_parameters_remain_bound(self):
        self.assertEqual(postgres_sql("SELECT '?' as label WHERE email=?"),"SELECT '?' as label WHERE email=%s")
        self.assertIn('ON CONFLICT (key)',postgres_sql('INSERT OR REPLACE INTO attempts VALUES(?,?,?)'))
        self.assertIn('pg_advisory_xact_lock',postgres_sql('BEGIN IMMEDIATE'))

    def test_read_only_cloud_import(self):
        path=Path(_tmp.name)/'must-not-be-created'
        env={**os.environ,'VERCEL':'1','PRATES_DATA_DIR':str(path),'DATABASE_URL':''}
        r=subprocess.run([sys.executable,'-c','import server'],cwd=ROOT,env=env,capture_output=True)
        self.assertEqual(r.returncode,0,r.stderr.decode())
        self.assertFalse(path.exists())


if __name__=='__main__':unittest.main()
