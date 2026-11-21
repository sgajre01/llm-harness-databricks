# Databricks notebook source
# Run this notebook on Databricks Free Edition serverless compute.
import json
import sys
from pathlib import Path

dbutils.widgets.text('dataset', 'pilot')
dbutils.widgets.text('output_name', 'pilot_v1')
dbutils.widgets.text('model', 'databricks-qwen3-next-80b-a3b-instruct')
notebook_path = dbutils.notebook.entry_point.getDbutils().notebook().getContext().notebookPath().get()
root = Path('/Workspace' + notebook_path).parent.parent
sys.path.insert(0, str(root))
from evaluate import run
import platform
import importlib.metadata
output_dir = root/'outputs'/dbutils.widgets.get('output_name')
output_dir.mkdir(parents=True, exist_ok=True)
(output_dir/'runtime.json').write_text(json.dumps({
    'python': platform.python_version(),
    'databricks_sdk': importlib.metadata.version('databricks-sdk'),
    'execution': 'Databricks Free Edition serverless notebook',
}, indent=2))

rows = run(root/'data'/(dbutils.widgets.get('dataset')+'.json'),
           root/'outputs'/dbutils.widgets.get('output_name'), model=dbutils.widgets.get('model'))
from report import build
build(output_dir)
summary = {mode: {'n': sum(r['mode']==mode for r in rows),
                  'correct': sum(r['mode']==mode and r['correct'] for r in rows)}
           for mode in ('baseline','full_harness','focused_harness')}
print(json.dumps(summary, indent=2))
dbutils.notebook.exit(json.dumps({'output_name':dbutils.widgets.get('output_name'), 'summary':summary}))
