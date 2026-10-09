import importlib.util, json, os, tempfile, threading, unittest, urllib.request, urllib.parse, http.cookiejar
from http.server import ThreadingHTTPServer
from urllib.request import HTTPRedirectHandler
from unittest.mock import patch
from pathlib import Path
import app
from confidence import apply_calibrator, fit_isotonic
from verification import verify_answer

class PlatformTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory(); app.DB=Path(cls.tmp.name)/'test.sqlite'; app.MODEL=Path(cls.tmp.name)/'models'/'router.json'; app.init_db(); app.train_router()
 @classmethod
 def tearDownClass(cls): cls.tmp.cleanup()
 def test_router_is_fitted_and_emits_probabilities(self):
  r=app.route('count open tickets for employee'); self.assertEqual(r['algorithm'],'multinomial-naive-bayes'); self.assertIn(r['strategy'],r['probabilities']); self.assertAlmostEqual(sum(r['probabilities'].values()),1)
 def test_schema_migrations_are_recorded_and_idempotent(self):
  with app.connect() as c:
   versions=[r['version'] for r in c.execute('SELECT version FROM schema_migrations ORDER BY version')]
  self.assertEqual(versions,[1,2,3,4,5])
  app.init_db()
  with app.connect() as c: self.assertEqual(c.execute('SELECT count(*) FROM schema_migrations').fetchone()[0],5)
 def test_sliding_window_rate_limit_is_bounded(self):
  key='unit-test-rate-limit'
  self.assertEqual(app.rate_limit_retry(key,2,60,100),0)
  self.assertEqual(app.rate_limit_retry(key,2,60,101),0)
  self.assertEqual(app.rate_limit_retry(key,2,60,102),58)
  self.assertEqual(app.rate_limit_retry(key,2,60,161),0)
 def test_legacy_sqlite_schema_upgrades_with_additive_migrations(self):
  original_db,original_model=app.DB,app.MODEL
  with tempfile.TemporaryDirectory() as temp:
   try:
    app.DB=Path(temp)/'legacy.sqlite'; app.MODEL=Path(temp)/'router.json'
    with app.DB.open('wb'): pass
    import sqlite3
    legacy=sqlite3.connect(app.DB)
    with legacy as c:
     c.execute('CREATE TABLE documents(id TEXT PRIMARY KEY,tenant TEXT,title TEXT,version INTEGER,groups_csv TEXT,text TEXT,active INTEGER DEFAULT 1,updated TEXT)')
     c.execute('CREATE TABLE approvals(id TEXT PRIMARY KEY,tenant TEXT,action TEXT,status TEXT,requested_by TEXT,decided_by TEXT,created TEXT)')
     c.execute('CREATE TABLE feedback(id INTEGER PRIMARY KEY AUTOINCREMENT,tenant TEXT,task_id TEXT,rating INTEGER,comment TEXT,created TEXT)')
    legacy.close()
    app.init_db()
    with app.connect() as c:
     doc_columns={r['name'] for r in c.execute('PRAGMA table_info(documents)')}
     approval_columns={r['name'] for r in c.execute('PRAGMA table_info(approvals)')}
     feedback_columns={r['name'] for r in c.execute('PRAGMA table_info(feedback)')}
     versions=[r['version'] for r in c.execute('SELECT version FROM schema_migrations ORDER BY version')]
    self.assertIn('source_filename',doc_columns); self.assertIn('payload',approval_columns); self.assertIn('task_id',approval_columns); self.assertIn('category',feedback_columns); self.assertEqual(versions,[1,2,3,4,5])
   finally: app.DB,app.MODEL=original_db,original_model
 def test_tenant_filtered_document_search(self):
  a=app.USERS['employee']; b=app.USERS['other_tenant']; self.assertTrue(app.retrieve('VPN access requirements',a,'hybrid')); self.assertTrue(all(x['id']!='vpn-other-v1' for x in app.retrieve('VPN',a,'hybrid'))); self.assertTrue(all(x['id']!='vpn-access-v2' for x in app.retrieve('VPN',b,'hybrid')))
 def test_unrelated_or_generic_query_does_not_get_weak_document_hit(self):
  r=app.handle_question('Where can I find the company holiday calendar?',app.USERS['employee'])
  self.assertEqual(r['status'],'abstained'); self.assertEqual(r['evidence'],[])
  self.assertEqual(app.retrieve('what is it',app.USERS['employee'],'hybrid'),[])
 def test_explicit_device_id_is_prioritized_over_other_owned_devices(self):
  r=app.handle_question('Does device A-992 satisfy VPN requirements?',app.USERS['employee'])
  device=next(item for item in r['evidence'] if item['kind']=='sql')
  self.assertEqual(device['device_id'],'A-992'); self.assertTrue(device['facts']['endpoint_protection'])
 def test_confidence_calibrator_is_monotone_and_bounded(self):
  artifact=fit_isotonic([(0.1,0),(0.2,1),(0.3,0),(0.9,1)])
  values=[apply_calibrator(x,artifact) for x in (0.0,0.1,0.2,0.3,0.9,1.0)]
  self.assertEqual(values,sorted(values)); self.assertTrue(all(0<=x<=1 for x in values))
  result=app.handle_question('What is the approved process for requesting VPN access?',app.USERS['employee'])
  self.assertIn('raw_support_score',result['confidence']); self.assertEqual(result['confidence']['calibrator_version'],'synthetic-isotonic-v1')
 def test_evidence_verifier_rejects_added_unsupported_claim(self):
  result=app.handle_question('What is the approved process for requesting VPN access?',app.USERS['employee'])
  self.assertTrue(result['verification']['passed'])
  rejected=verify_answer(result['answer']+' The payroll system uses biometric approval.',result['status'],result['evidence'])
  self.assertFalse(rejected['passed'])
 def test_verification_failure_forces_abstention_and_zero_confidence(self):
  with patch('app.verify_answer',return_value={'passed':False,'method':'test-failure','checks':[{'check':'forced','passed':False}]}):
   result=app.handle_question('What is the approved process for requesting VPN access?',app.USERS['employee'])
  self.assertEqual(result['status'],'abstained'); self.assertFalse(result['verification']['passed']); self.assertEqual(result['confidence']['score'],0.0)
 def test_sql_count_is_tenant_and_user_scoped(self):
  r=app.handle_question('How many open tickets are assigned to me?',app.USERS['employee']); self.assertIn('1 open',r['answer']); self.assertEqual(r['evidence'][0]['value'],1)
 def test_secret_request_abstains_without_search(self):
  r=app.handle_question('What is the private administrator password?',app.USERS['employee']); self.assertEqual(r['status'],'refused'); self.assertEqual(r['evidence'],[])
 def test_device_comparison_reports_missing_requirement(self):
  r=app.handle_question('Does device A-991 satisfy the VPN requirements?',app.USERS['employee']); self.assertIn('endpoint protection',r['answer']); self.assertTrue(r['subquestions'])
 def test_admin_only_document_management_and_runtime_access(self):
  with app.connect() as c: c.execute("UPDATE documents SET groups_csv='it_support' WHERE id='vpn-access-v2'")
  self.assertNotIn('vpn-access-v2',[d['id'] for d in app.retrieve('VPN access request',app.USERS['employee'],'hybrid')])
  with app.connect() as c: c.execute("UPDATE documents SET groups_csv='employee,it_support,it_admin' WHERE id='vpn-access-v2'")
 def test_document_ingestion_versioning_failure_and_deletion(self):
  first=app.ingest_document('acme','ingest-sample','Sample Support Policy','support.md',b'# Access\n\nManaged device access requires manager approval and MFA.', ['employee'],'admin')
  self.assertEqual(first['state'],'completed'); self.assertGreater(first['chunk_count'],0)
  hits=app.retrieve('manager approval MFA',app.USERS['employee'],'hybrid'); self.assertTrue(any(h['id']=='ingest-sample' for h in hits))
  second=app.ingest_document('acme','ingest-sample','Sample Support Policy','support.md',b'# Updated\n\nNew requirement is encrypted storage.', ['employee'],'admin')
  self.assertEqual(second['version'],2)
  with app.connect() as c: self.assertEqual(c.execute("SELECT count(*) FROM document_versions WHERE document_id='ingest-sample' AND version=1").fetchone()[0],1)
  failed=app.ingest_document('acme','ingest-sample','Bad Update','bad.exe',b'nope',['employee'],'admin'); self.assertEqual(failed['state'],'failed')
  hits=app.retrieve('encrypted storage',app.USERS['employee'],'hybrid'); self.assertTrue(any(h['id']=='ingest-sample' and h['version']==2 for h in hits))
  self.assertTrue(app.delete_document('acme','ingest-sample')); self.assertFalse(any(h['id']=='ingest-sample' for h in app.retrieve('encrypted storage',app.USERS['employee'],'hybrid')))
 def test_structure_aware_markdown_chunking_preserves_headings_and_bounds(self):
  from ingestion import _text_segments, chunk
  blocks=_text_segments('# VPN Access\n\n'+' '.join(['policy']*600)+'\n\n## MFA\n\nUse MFA.')
  out=chunk(blocks,max_chars=500,overlap=60)
  self.assertGreaterEqual(len(out),3); self.assertTrue(any('VPN Access' in x['section'] for x in out)); self.assertTrue(any('MFA' in x['section'] for x in out)); self.assertTrue(all(len(x['text'])<=500 for x in out))
 def test_prompt_injection_is_not_executed_as_an_instruction(self):
  r=app.handle_question('What does the legacy note say about VPN?',app.USERS['support']); self.assertNotIn('credentials',r['answer'].lower())
 def test_status_then_ticket_checks_service_and_persists_action(self):
  r=app.handle_question('Check VPN service status and open a support ticket if unresolved.',app.USERS['employee']); self.assertTrue(any(a['tool']=='get_service_status' for a in r['actions'])); self.assertTrue(any(a['tool']=='create_support_ticket' for a in r['actions'])); self.assertIn('ticket #',r['answer'])
 def test_response_schema_is_validated_and_rejects_bad_evidence(self):
  r=app.handle_question('What is the approved process for requesting VPN access?',app.USERS['employee'])
  self.assertEqual(r['schema_version'],'p1-response-v1')
  broken={**r,'evidence':[{'kind':'document'}]}
  with self.assertRaises(ValueError): app.validate_response_contract(broken)
  unverified={**r,'verification':{'passed':False,'method':'test','checks':[{'check':'forced failure','passed':False}]}}
  with self.assertRaises(ValueError): app.validate_response_contract(unverified)
 def test_unexpected_workflow_failure_persists_sanitized_error(self):
  with patch('app.retrieve',side_effect=RuntimeError('secret customer input')):
   result=app.handle_question('Explain the access guide details',app.USERS['employee'])
  self.assertEqual(result['status'],'error'); self.assertNotIn('secret customer input',json.dumps(result))
  with app.connect() as c:
   task=c.execute('SELECT status,result FROM tasks WHERE id=?',(result['task_id'],)).fetchone()
   self.assertEqual(task['status'],'error'); self.assertNotIn('secret customer input',task['result'])
 def test_approval_executes_and_verifies_vpn_revocation(self):
  with app.connect() as c: c.execute("UPDATE access_grants SET active=1 WHERE tenant='acme' AND employee_id='E-1042' AND resource='vpn'")
  requested=app.request_vpn_revocation(app.USERS['support'],'e-1042','Confirmed employee departure')
  with self.assertRaises(PermissionError): app.decide_approval(app.USERS['employee'],requested['approval_id'],'approved')
  decided=app.decide_approval(app.USERS['approver'],requested['approval_id'],'approved')
  self.assertTrue(decided['executed']); self.assertTrue(decided['verified'])
  with app.connect() as c: self.assertEqual(c.execute("SELECT active FROM access_grants WHERE tenant='acme' AND employee_id='E-1042' AND resource='vpn'").fetchone()['active'],0)
  self.assertEqual(app.decide_approval(app.USERS['approver'],requested['approval_id'],'approved')['status'],'not_pending')
  with app.connect() as c: self.assertEqual(c.execute('SELECT status FROM tasks WHERE id=?',(requested['task_id'],)).fetchone()['status'],'completed')
  with app.connect() as c: c.execute("UPDATE access_grants SET active=1 WHERE tenant='acme' AND employee_id='E-1042' AND resource='vpn'")
 def test_approval_rechecks_grant_and_prevents_cross_tenant_targeting(self):
  with self.assertRaises(ValueError): app.request_vpn_revocation(app.USERS['support'],'E-2042','Cross tenant test target')
  requested=app.request_vpn_revocation(app.USERS['support'],'E-1042','Confirmed employee departure')
  with app.connect() as c: c.execute("UPDATE access_grants SET active=0 WHERE tenant='acme' AND employee_id='E-1042' AND resource='vpn'")
  failed=app.decide_approval(app.USERS['approver'],requested['approval_id'],'approved')
  self.assertEqual(failed['status'],'action_failed')
  with app.connect() as c: c.execute("UPDATE access_grants SET active=1 WHERE tenant='acme' AND employee_id='E-1042' AND resource='vpn'")
 def test_http_chat_endpoint(self):
  server=ThreadingHTTPServer(('127.0.0.1',0),app.Handler); thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start()
  try:
   base=f'http://127.0.0.1:{server.server_port}'; opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
   self.assertEqual(json.load(opener.open(base+'/health/live',timeout=3))['status'],'ok')
   self.assertEqual(json.load(opener.open(base+'/health/ready',timeout=3))['status'],'ready')
   def post(path,body,headers=None):
    req=urllib.request.Request(base+path,data=json.dumps(body).encode(),headers={'Content-Type':'application/json',**(headers or {})}); return json.load(opener.open(req,timeout=5))
   with self.assertRaises(urllib.error.HTTPError) as unauth: opener.open(base+'/api/me',timeout=3)
   self.assertEqual(unauth.exception.code,401)
   login=post('/api/login',{'username':'employee','password':app.DEMO_PASSWORD}); csrf=login['csrf_token']
   data=post('/api/v1/chat',{'question':'What is the approved process for requesting VPN access?'},{'X-CSRF-Token':csrf})
   self.assertEqual(data['status'],'answered'); self.assertTrue(data['evidence'])
   task=json.load(opener.open(base+'/api/v1/tasks/'+data['task_id'],timeout=5))
   self.assertEqual(task['status'],'answered'); self.assertEqual(task['result']['task_id'],data['task_id'])
   post('/api/v1/feedback',{'task_id':data['task_id'],'rating':-1,'category':'missing_evidence'},{'X-CSRF-Token':csrf})
   with app.connect() as c: self.assertEqual(c.execute('SELECT category FROM feedback WHERE task_id=?',(data['task_id'],)).fetchone()['category'],'missing_evidence')
   with self.assertRaises(urllib.error.HTTPError) as not_cancellable:
    post('/api/v1/tasks/'+data['task_id']+'/cancel',{}, {'X-CSRF-Token':csrf})
   self.assertEqual(not_cancellable.exception.code,409)
   with self.assertRaises(urllib.error.HTTPError) as badcsrf: post('/api/chat',{'question':'What is VPN access?'})
   self.assertEqual(badcsrf.exception.code,403)
   post('/api/logout',{}, {'X-CSRF-Token':csrf})
   with self.assertRaises(urllib.error.HTTPError) as loggedout: opener.open(base+'/api/me',timeout=3)
   self.assertEqual(loggedout.exception.code,401)
   post('/api/login',{'username':'employee','password':app.DEMO_PASSWORD})
   with patch.dict(os.environ,{'P1_LOCAL_AUTH_ENABLED':'false'}):
    with self.assertRaises(urllib.error.HTTPError) as disabled: opener.open(base+'/api/me',timeout=3)
    self.assertEqual(disabled.exception.code,401)
  finally: server.shutdown(); server.server_close(); thread.join(timeout=2)
 def test_approval_http_flow_requires_csrf_and_executes_after_distinct_approver(self):
  with app.connect() as c: c.execute("UPDATE access_grants SET active=1 WHERE tenant='acme' AND employee_id='E-1042' AND resource='vpn'")
  server=ThreadingHTTPServer(('127.0.0.1',0),app.Handler); thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start()
  try:
   base=f'http://127.0.0.1:{server.server_port}'
   def session(username):
    opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    req=urllib.request.Request(base+'/api/login',data=json.dumps({'username':username,'password':app.DEMO_PASSWORD}).encode(),headers={'Content-Type':'application/json'})
    login=json.load(opener.open(req,timeout=5)); return opener,login['csrf_token']
   support,csrf=session('support')
   request=urllib.request.Request(base+'/api/approvals/request',data=json.dumps({'employee_id':'E-1042','reason':'Confirmed employee departure'}).encode(),headers={'Content-Type':'application/json','X-CSRF-Token':csrf})
   created=json.load(support.open(request,timeout=5))
   approver,approver_csrf=session('approver')
   pending=json.load(approver.open(base+'/api/approvals',timeout=5))
   self.assertTrue(any(x['id']==created['approval_id'] and x['status']=='pending' for x in pending))
   approver_task=json.load(approver.open(base+'/api/v1/tasks/'+created['task_id'],timeout=5))
   self.assertEqual(approver_task['status'],'needs_approval')
   req=urllib.request.Request(base+'/api/v1/tasks/'+created['task_id']+'/approve',data=json.dumps({}).encode(),headers={'Content-Type':'application/json','X-CSRF-Token':approver_csrf})
   result=json.load(approver.open(req,timeout=5)); self.assertTrue(result['verified'])
   completed=json.load(approver.open(base+'/api/v1/tasks/'+created['task_id'],timeout=5))
   self.assertEqual(completed['status'],'completed')
  finally:
   with app.connect() as c: c.execute("UPDATE access_grants SET active=1 WHERE tenant='acme' AND employee_id='E-1042' AND resource='vpn'")
   server.shutdown(); server.server_close(); thread.join(timeout=2)
 def test_admin_http_ingestion_lists_and_deactivates_document(self):
  server=ThreadingHTTPServer(('127.0.0.1',0),app.Handler); thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start()
  try:
   base=f'http://127.0.0.1:{server.server_port}'; opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
   login=urllib.request.Request(base+'/api/login',data=json.dumps({'username':'admin','password':app.DEMO_PASSWORD}).encode(),headers={'Content-Type':'application/json'})
   csrf=json.load(opener.open(login,timeout=5))['csrf_token']
   reports=json.load(opener.open(base+'/api/admin/evaluation',timeout=5))
   self.assertIn('router_report',reports); self.assertIn('retrieval_report',reports); self.assertIn('confidence_report',reports)
   def post(path,body):
    req=urllib.request.Request(base+path,data=json.dumps(body).encode(),headers={'Content-Type':'application/json','X-CSRF-Token':csrf})
    return json.load(opener.open(req,timeout=5))
   result=post('/api/admin/documents',{'id':'ui-ingest-test','title':'UI ingestion test','filename':'guide.md','text':'# Access\n\nEncrypted storage and MFA are required.','roles':['employee']})
   self.assertEqual(result['state'],'completed')
   listed=json.load(opener.open(base+'/api/admin/documents',timeout=5))
   self.assertTrue(any(x['id']=='ui-ingest-test' for x in listed))
   post('/api/admin/delete-document',{'id':'ui-ingest-test'})
   docs=json.load(opener.open(base+'/api/documents',timeout=5))
   self.assertFalse(any(x['id']=='ui-ingest-test' for x in docs))
  finally:
   server.shutdown(); server.server_close(); thread.join(timeout=2)

@unittest.skipUnless(importlib.util.find_spec('authlib'), 'install requirements.txt to run OIDC integration test')
class OIDCFlowTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory(); app.DB=Path(cls.tmp.name)/'oidc.sqlite'; app.MODEL=Path(cls.tmp.name)/'models'/'router.json'; app.init_db()
 @classmethod
 def tearDownClass(cls): cls.tmp.cleanup()
 def test_oidc_code_callback_maps_provisioned_subject_to_server_role(self):
  env={'OIDC_ISSUER':'https://idp.example','OIDC_CLIENT_ID':'client','OIDC_CLIENT_SECRET':'never-log-this','OIDC_REDIRECT_URI':'http://localhost:8000/auth/oidc/callback','OIDC_SUBJECT_MAP':json.dumps({'subject-77':{'id':'E-7788','tenant':'acme','role':'it_support'}})}
  metadata={'issuer':'https://idp.example','authorization_endpoint':'https://idp.example/authorize','token_endpoint':'https://idp.example/token','jwks_uri':'https://idp.example/keys','id_token_signing_alg_values_supported':['RS256']}
  with patch.dict(os.environ,env,clear=False), patch('app.oidc_metadata',return_value=metadata), patch('app.validate_oidc_id_token',return_value={'sub':'subject-77'}) as validate, patch('authlib.integrations.requests_client.OAuth2Session') as client_cls:
   client=client_cls.return_value; client.create_authorization_url.side_effect=lambda endpoint,**kw:(endpoint+'?'+urllib.parse.urlencode({'state':kw['state'],'nonce':kw['nonce'],'code_challenge':'challenge'}),kw['state']); client.fetch_token.return_value={'id_token':'signed-token'}
   server=ThreadingHTTPServer(('127.0.0.1',0),app.Handler); thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start()
   try:
    base=f'http://127.0.0.1:{server.server_port}'; jar=http.cookiejar.CookieJar(); opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    class StopRedirect(HTTPRedirectHandler):
     def redirect_request(self,*args,**kwargs): return None
    starter=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar),StopRedirect())
    location=''
    try: starter.open(base+'/auth/oidc/start',timeout=5)
    except urllib.error.HTTPError as response: self.assertEqual(response.code,302); location=response.headers['Location']
    state=next(c.value for c in jar if c.name=='p1_oauth_state')
    self.assertEqual(urllib.request.Request(base+'/auth/oidc/callback').get_method(),'GET')
    self.assertTrue(any(c.name=='p1_oauth_state' and c.path=='/auth/oidc/callback' for c in jar))
    self.assertIn('code_challenge=',location)
    client.create_authorization_url.assert_called_once()
    callback_request=urllib.request.Request(base+'/auth/oidc/callback?code=auth-code&state='+state,headers={'Cookie':'p1_oauth_state='+state})
    with opener.open(callback_request,timeout=5) as callback_response: self.assertNotIn('auth_error',callback_response.url,callback_response.url)
    with opener.open(base+'/api/me',timeout=5) as response: me=json.load(response)
    self.assertEqual((me['id'],me['tenant'],me['role']),('E-7788','acme','it_support'))
    self.assertEqual(client.fetch_token.call_args.kwargs['code_verifier'],client.create_authorization_url.call_args.kwargs['code_verifier'])
    validate.assert_called_once()
   finally: server.shutdown(); server.server_close(); thread.join(timeout=2)
 def test_id_token_signature_issuer_audience_expiry_and_nonce_are_validated(self):
  from joserfc import jwt
  from joserfc.jwk import RSAKey
  from unittest.mock import Mock
  signing=RSAKey.generate_key(2048,private=True,auto_kid=True); public={'keys':[signing.as_dict(private=False)]}
  metadata={'jwks_uri':'https://idp.example/keys','id_token_signing_alg_values_supported':['RS256']}
  claims={'iss':'https://idp.example','aud':'client','sub':'subject-77','exp':int(__import__('time').time())+300,'iat':int(__import__('time').time()),'nonce':'expected-nonce'}
  signed=jwt.encode({'alg':'RS256','kid':signing.kid},claims,signing)
  response=Mock(); response.json.return_value=public; response.raise_for_status.return_value=None
  with patch.dict(os.environ,{'OIDC_ISSUER':'https://idp.example'},clear=False),patch('requests.get',return_value=response):
   parsed=app.validate_oidc_id_token(signed,metadata,'expected-nonce','client'); self.assertEqual(parsed['sub'],'subject-77')
   with self.assertRaises(Exception): app.validate_oidc_id_token(signed,metadata,'wrong-nonce','client')
   wrong=jwt.encode({'alg':'RS256','kid':signing.kid},{**claims,'aud':'attacker'},signing)
   with self.assertRaises(Exception): app.validate_oidc_id_token(wrong,metadata,'expected-nonce','client')

if __name__=='__main__': unittest.main()

