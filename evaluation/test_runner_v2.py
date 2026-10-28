import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from run_openai_v2 import (load_inputs, request_payload, normalize_response, estimated_cost,
                           main)
from score_predictions import score
from validate_suite import validate


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.cases = load_inputs()
        self.gold = validate(verbose=False)
        self.args = SimpleNamespace(model="gpt-5-nano", max_output_tokens=1200,
                                    reasoning="minimal",input_rate=0.05,cached_rate=0.005,output_rate=0.40)

    def test_exactly_70_cases(self):
        self.assertEqual(len(self.cases), 70)
        self.assertEqual(len({c['case_id'] for c in self.cases}), 70)

    def test_strict_intent(self):
        case=next(c for c in self.cases if c['case_id']=='I01')
        payload,mode=request_payload(case,self.args)
        self.assertEqual(mode,'strict_json_schema')
        self.assertEqual(payload['text']['format']['schema']['type'],'object')

    def test_native_tools(self):
        case=next(c for c in self.cases if c['case_id']=='T13')
        payload,mode=request_payload(case,self.args)
        self.assertEqual(mode,'native_tool_call')
        self.assertEqual(len(payload['tools']),3)

    def test_safety_json_mode(self):
        case=next(c for c in self.cases if c['case_id']=='S01')
        payload,mode=request_payload(case,self.args)
        self.assertEqual(mode,'json_object_local_validation')

    def test_native_call_normalization(self):
        response=SimpleNamespace(output=[SimpleNamespace(type='function_call',name='get_product_details',arguments='{"product_id":"P-104"}')])
        self.assertEqual(normalize_response(response,'tool')['tool_calls'][0]['arguments']['product_id'],'P-104')

    def test_invalid_json_fails(self):
        response=SimpleNamespace(output_text='not json',output=[])
        self.assertIsNone(normalize_response(response,'intent'))

    def test_usage_cost(self):
        usage=SimpleNamespace(input_tokens=100,output_tokens=50,input_tokens_details=SimpleNamespace(cached_tokens=20))
        expected=(80*0.05+20*0.005+50*0.40)/1_000_000
        self.assertAlmostEqual(estimated_cost(usage,self.args),expected)

    def test_default_is_offline(self):
        self.assertEqual(main(['--task','intent','--limit','1']),0)

    def test_holdout_locked(self):
        with self.assertRaises(SystemExit) as ctx:
            main(['--split','holdout'])
        self.assertEqual(ctx.exception.code,2)

    def test_all_requires_explicit_call_limit(self):
        with self.assertRaises(SystemExit) as ctx:
            main(['--all-cases'])
        self.assertEqual(ctx.exception.code,2)


if __name__=='__main__': unittest.main()
