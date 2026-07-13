import ast,json,re,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
HERE=Path(__file__).parent;sys.path.insert(0,str(HERE))
import server
from server import DEFAULT_BIND,LAN_BIND,ExclusiveHTTPServer,Handler,bind_config,current_view_model,parse_args
from view_model import ALLOWED_SOURCES,escape,normalize_dashboard,render_authority_text

def inputs(stale=False):
    recall={"activation":{"state":"ACTIVE","continuation_allowed":True},"freshness":{"fresh":not stale},"projection":{"status":"active","focus":"now","generated_at_utc":"2026-07-13T02:06:51+00:00","sources":["memory:m1"],"source_snapshots":[{"ref":"memory:m1","exists":not stale,"fresh":not stale},{"ref":"scope:head","exists":True,"fresh":True}]}}
    governance={"proposals":[{"summary":"Path A / Path B 07-10","state":"historical","sources":["peer-chat:old"]}]}
    return recall,governance,{"open_agenda":[]},{"scope":"scope:head"}

class DashboardAcceptance(unittest.TestCase):
 def test_01_stale_cards_are_history(self):
  vm=normalize_dashboard(*inputs());self.assertFalse(vm['governance'][0]['valid']);self.assertNotIn('待拍板',render_authority_text(vm))
 def test_02_only_derived_sources(self):
  self.assertEqual(ALLOWED_SOURCES,("memory-recall:projection","governance-show","prospective-show","control-heads","peer-chat:formal-channel","frame-ledger:closed-continuation"));text=' '.join(p.read_text('utf-8') for p in [HERE/'view_model.py',HERE/'server.py']);self.assertNotRegex(text,r'wake-agent-runs|run-log|AGENT_RUNS');self.assertIn('_authority_command("memory-recall")',text);self.assertIn('_authority_command("governance-show")',text);self.assertIn('_authority_command("prospective-show")',text)
 def test_03_refresh_preserves_scroll(self): self.assertIn("sessionStorage.setItem(scrollKey",(HERE/'app.js').read_text('utf-8'));self.assertIn('scrollTo(0,saved)',(HERE/'app.js').read_text('utf-8'))
 def test_04_mobile_and_desktop(self):
  h=(HERE/'index.html').read_text('utf-8');css=(HERE/'style.css').read_text('utf-8');self.assertIn('width=device-width',h);self.assertIn('@media(max-width:700px)',css)
 def test_05_no_js_authority_text(self): self.assertIn('<noscript>',(HERE/'index.html').read_text('utf-8'));self.assertIn('ACTIVE/PAUSED',(HERE/'index.html').read_text('utf-8'))
 def test_06_convergence_and_escape(self): self.assertEqual(normalize_dashboard(*inputs()),normalize_dashboard(*inputs()));self.assertEqual(escape('<x "y">'),'&lt;x &quot;y&quot;&gt;')
 def test_06b_real_schema_maps_converge(self):
  a=list(inputs());a[2]={"goals":{"goal:x":{"description":"x","source":"frame:f"}}};vm=normalize_dashboard(*a);self.assertEqual(vm['agenda'][0]['description'],'x')
 def test_06c_terminal_goals_are_not_active_agenda(self):
  a=list(inputs());a[2]={"goals":{"goal:done":{"state":"SATISFIED"},"goal:collapsed":{"state":"COLLAPSED"},"goal:a":{"state":"ACTIVE"},"goal:b":{"state":"ACTIVE"}}};vm=normalize_dashboard(*a);self.assertEqual(len(vm['agenda']),2);self.assertTrue(all(x['state']=='ACTIVE' for x in vm['agenda']))
 def test_07_authority_not_color_only(self):
  h=(HERE/'index.html').read_text('utf-8');self.assertIn('valid / 历史',h);self.assertIn('激活状态',h)
 def test_08_pwa_android_localhost(self):
  m=json.loads((HERE/'manifest.webmanifest').read_text('utf-8'));self.assertEqual(m['display'],'standalone');self.assertEqual(bind_config(parse_args([]))['host'],'127.0.0.1')
 def test_09_disconnect_falls_back_to_poll(self):
  js=(HERE/'app.js').read_text('utf-8');sw=(HERE/'sw.js').read_text('utf-8');self.assertIn('finally{setTimeout(poll,15000)}',js);self.assertIn("caches.match",sw)
 def test_10_dead_snapshot_never_current(self):
  vm=normalize_dashboard(*inputs(stale=True));self.assertFalse(vm['projection']['valid']);self.assertEqual(vm['projection']['label'],'已失效/脏')
 def test_11_network_three_rings(self):
  local=bind_config(parse_args([]));lan=bind_config(parse_args(['--lan']));self.assertEqual(local['host'],DEFAULT_BIND);self.assertEqual(lan['host'],LAN_BIND);self.assertTrue(lan['lan']);self.assertEqual(lan['banner'],'同网可访问');self.assertNotIn('wan',(HERE/'server.py').read_text('utf-8').lower())
 def test_12_as_of_or_whole_vm_unverifiable(self):
  vm=normalize_dashboard(*inputs());self.assertEqual(vm['as_of'],'2026-07-13T02:06:51+00:00');self.assertTrue(vm['verifiable'])
  missing=list(inputs());missing[0]['projection'].pop('generated_at_utc');self.assertFalse(normalize_dashboard(*missing)['verifiable'])
  html=(HERE/'index.html').read_text('utf-8');js=(HERE/'app.js').read_text('utf-8');self.assertIn('截至此次 recall 裁断',html);self.assertIn('整页无法核验',js)
 def test_13_uncovered_declared_refs_are_unverifiable(self):
  recall,governance,prospective,heads=inputs();prospective={'open_agenda':[{'goal_ref':'goal:frame','source':'frame:f'},{'goal_ref':'goal:memory','source':'memory:missing'},{'goal_ref':'goal:no-ref'}]};heads={'scope':'control-event-id'}
  vm=normalize_dashboard(recall,governance,prospective,heads);self.assertTrue(vm['agenda'][0]['valid']);self.assertTrue(vm['agenda'][1]['unverifiable']);self.assertFalse(vm['agenda'][1]['valid']);self.assertTrue(vm['agenda'][2]['valid']);self.assertTrue(vm['authority']['valid']);self.assertTrue(vm['verifiable'])
  recall['freshness']['fresh']=False;stale=normalize_dashboard(recall,governance,prospective,heads);self.assertFalse(stale['authority']['valid']);self.assertFalse(stale['verifiable'])
 def test_14_frontend_has_zero_resolver(self):
  tree=ast.parse((HERE/'view_model.py').read_text('utf-8'));imports={n.names[0].name for n in ast.walk(tree) if isinstance(n,(ast.Import,ast.ImportFrom))};calls={n.func.id for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name)}
  self.assertTrue(imports.isdisjoint({'pathlib','os','json','subprocess'}));self.assertTrue(calls.isdisjoint({'open','compile','eval','exec'}))
  js=(HERE/'app.js').read_text('utf-8');self.assertNotRegex(js,r'FileReader|localStorage|indexedDB|\.text\(\)|\.jsonl|source_snapshots');self.assertEqual(re.findall(r"fetch\('([^']+)'",js),['/api/config','/api/view-model'])
 def test_15_information_parity_fields_are_source_carried(self):
  vm=normalize_dashboard(*inputs(),chat=[{'from':'owner','text':'x','source_refs':['peer-chat#L1']}],receipts=[{'frame_id':'wf-x','source_refs':['frame:wf-x']}],governance_items=[{'state':'approved','source_refs':['peer-chat#L2','peer-chat#L3']}])
  self.assertEqual(vm['chat'][0]['from'],'owner');self.assertEqual(vm['recent_receipts'][0]['frame_id'],'wf-x');self.assertEqual(vm['discussion'][0]['state'],'approved')
  html=(HERE/'index.html').read_text('utf-8');self.assertIn('三方茶水间',html);self.assertIn('产出窗口',html);self.assertIn('任务线',html);self.assertIn('双签提案与裁断',html)
 def test_15b_governance_pairs_exact_re_timestamp(self):
  rows=[{'from':'claude','time':'2026-07-14 02:12:16','text':'【提案·修订观察窗脱离验收，不改功能目标】x'},{'from':'codex','time':'2026-07-14 02:13:00','text':'【同意·别的题目】y'},{'from':'codex','time':'2026-07-14 02:18:55','re':'2026-07-14 02:12:16','text':'【同意·修订观察窗脱离验收】z'}]
  with tempfile.TemporaryDirectory() as tmp:
   chat=Path(tmp)/'peer-chat.jsonl';chat.write_text('\n'.join(json.dumps(x,ensure_ascii=False) for x in rows)+'\n','utf-8')
   with patch.object(server,'PEER_CHAT',chat),patch.object(server,'GATE_MIGRATION_BOUNDARY',1): signed=server._structured_governance()
  self.assertEqual(len(signed),1);self.assertEqual(signed[0]['proposal_time'],'2026-07-14 02:12:16');self.assertEqual(signed[0]['decision_time'],'2026-07-14 02:18:55')
 def test_16_real_view_model_has_information_complete_sources(self):
  vm=current_view_model();self.assertTrue(vm['recent_receipts']);self.assertEqual(len(vm['agenda']),2);self.assertTrue(vm['discussion']);self.assertTrue(vm['verifiable']);self.assertTrue({x.get('from') for x in vm['chat']} >= {'owner','claude','codex'})
  self.assertTrue(any(x.get('proposal_time')=='2026-07-14 02:12:16' and x.get('decision_time')=='2026-07-14 02:18:55' for x in vm['discussion']))
  self.assertTrue(all(x.get('source_refs') for x in vm['recent_receipts']));self.assertTrue(all(x.get('source_refs') for x in vm['discussion']))
 def test_17_exclusive_bind_rejects_second_listener(self):
  first=ExclusiveHTTPServer(('127.0.0.1',0),Handler)
  try:
   with self.assertRaises(OSError): ExclusiveHTTPServer(first.server_address,Handler)
  finally:first.server_close()

if __name__=='__main__':unittest.main()
