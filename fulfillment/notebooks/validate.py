# Databricks notebook source
# Post-run evidence audit. This notebook makes no model calls.
import hashlib,json,sys
from pathlib import Path
path=dbutils.notebook.entry_point.getDbutils().notebook().getContext().notebookPath().get()
root=Path('/Workspace'+path).parent.parent
out=root/'outputs/main_v1'
config=json.loads((out/'config.json').read_text())
manifest=json.loads((root/'data/frozen_manifest.json').read_text())
for name,expected in manifest['files'].items():
    assert hashlib.sha256((root/name).read_bytes()).hexdigest()==expected,name
for name,expected in config['source_sha256'].items():
    assert hashlib.sha256((root/name).read_bytes()).hexdigest()==expected,name
assert config['dataset_sha256']==manifest['files']['data/examples.json']
rows=[json.loads(s) for s in (out/'predictions.jsonl').read_text().splitlines()]
calls=[json.loads(s) for s in (out/'calls.jsonl').read_text().splitlines()]
examples={r['id']:r for r in json.loads((root/'data/examples.json').read_text())}
assert len(rows)==100 and len({(r['id'],r['arm']) for r in rows})==100
assert {r['id'] for r in rows}==set(examples)
assert all(r['ground_truth']==examples[r['id']]['ground_truth'] for r in rows)
assert all('ground_truth' not in json.dumps(c['request']) for c in calls)
assert len({c['model'] for c in calls})==1
runtime=json.loads((out/'runtime.json').read_text())
audit={'questions':50,'observations':100,'unique_pairs':100,'model_endpoint':config['model'],
       'application_call_attempts':len(calls),'successful_calls':sum('response' in c for c in calls),
       'tests_passed':runtime['tests_passed'],'frozen_hashes_match':True,
       'expected_labels_match_dataset':True,'label_keys_absent_from_prompts':True,
       'provider_response_models':sorted({c['response']['model'] for c in calls if 'response' in c})}
(out/'audit.json').write_text(json.dumps(audit,indent=2))
print(json.dumps(audit,indent=2))
dbutils.notebook.exit(json.dumps(audit))
