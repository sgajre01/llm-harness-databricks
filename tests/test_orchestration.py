import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import evaluate
from baseline import run_baseline
from harness import run_harness
from llm_client import parse_json
from scenario import generate_example, public_example
from report import paired


class FakeClient:
    def __init__(self, *args, **kwargs):
        self.prompts=[]
        self.records=[]
    def call_llm(self, prompt, *, tag, max_tokens):
        self.prompts.append(prompt)
        self.records.append({'response':{'usage':{'prompt_tokens':10,'completion_tokens':5}}})
        if tag.endswith('/plan'):
            return json.dumps({'steps':[{'domain':s,'instruction':s} for s in ('pricing','fulfillment','charges')]})
        if tag.endswith('/pricing'): return '{"lines":[]}'
        if tag.endswith('/fulfillment'): return '{"lines":[],"ship_units":0}'
        if tag.endswith('/charges'): return '{"invoice_usd":"0.00","ship_units":0}'
        return '{"ship_units":0,"invoice_usd":"0.00"}'


class OrchestrationTests(unittest.TestCase):
    def test_call_counts_and_source_scope(self):
        e=public_example(generate_example(1))
        full,focused=FakeClient(),FakeClient()
        run_harness(e,full,False)
        run_harness(e,focused,True)
        self.assertEqual(len(full.prompts),5)
        self.assertEqual(len(focused.prompts),5)
        self.assertIn('OTHER-C',full.prompts[1])
        self.assertNotIn('OTHER-C',focused.prompts[1])
        self.assertNotIn('ground_truth',''.join(full.prompts+focused.prompts))
        base=FakeClient()
        run_baseline(e,base)
        self.assertEqual(len(base.prompts),1)

    def test_checkpoint_resume_and_config_guard(self):
        with tempfile.TemporaryDirectory() as d:
            data=Path(d)/'data.json';out=Path(d)/'out'
            data.write_text(json.dumps([generate_example(1)]))
            with patch.object(evaluate,'LLMClient',FakeClient):
                first=evaluate.run(data,out)
                second=evaluate.run(data,out)
                self.assertEqual(len(first),3)
                self.assertEqual(first,second)
                data.write_text(json.dumps([generate_example(2)]))
                with self.assertRaises(ValueError): evaluate.run(data,out)

    def test_duplicate_json_rejected(self):
        with self.assertRaises(ValueError): parse_json('{"x":1,"x":2}')

    def test_paired_stats_known_case(self):
        rows=[]
        for i in range(5):
            rows += [{'id':str(i),'split':'primary','mode':'baseline','correct':False},
                     {'id':str(i),'split':'primary','mode':'focused_harness','correct':True}]
        result=paired(rows,'focused_harness')
        self.assertEqual(result['difference_pp'],100)
        self.assertEqual(result['paired_bootstrap_95_ci_pp'],[100,100])
        self.assertEqual(result['mcnemar_exact_p'],.0625)

if __name__=='__main__': unittest.main()
