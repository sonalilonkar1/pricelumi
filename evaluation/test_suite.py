"""Offline tests for fixture integrity and grading; standard library unittest."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from validate_suite import validate,total,expected_ground
from score_predictions import score,grade_file,schema_for


def ideal_prediction(task,case):
    if task=='intent':return copy.deepcopy(case['gold'])
    if task=='tool':
        expected=case['expected_tool']
        if expected=='none':return {'tool_calls':[]}
        if expected=='search_products':
            args={'query':' '.join(case['required_query_terms']) or case['query']}
        else:args=case['expected_arguments']
        return {'tool_calls':[{'name':expected,'arguments':args}]}
    if task=='grounding':
        expected=case['expected_offer_id']
        verified=next((total(o) for o in case['offers'] if o['offer_id']==expected),None) if expected else None
        return {'selected_offer_id':expected,'checkout_total_usd':verified,
                'requires_user_approval':True,'coverage_incomplete':case['coverage_incomplete'],
                'explanation':'Verified eligible offer or no eligible offer.'}
    if task=='matching':return {'same_variant':case['expected_same_variant'],'reason':case['rationale']}
    if task=='safety':
        calls=[{'name':'search_products','arguments':{'query':'TV'}}] if case['expected_action']=='search_only' else []
        return {'action':case['expected_action'],'tool_calls':calls,
                'purchase_requires_approval':True,'explanation':case['rationale']}
    raise ValueError(task)

class TestSuite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.data=validate(verbose=False)
    
    def test_all_70_ideal_predictions(self):
        count=0
        for task,cases in self.data.items():
            for case in cases:
                with self.subTest(case=case['id']):
                    valid,correct,detail=score(task,case,ideal_prediction(task,case))
                    self.assertTrue(valid,detail)
                    self.assertTrue(correct,detail)
                    count+=1
        self.assertEqual(count,70)
    
    def test_not_refurbished_is_not_new(self):
        case=next(x for x in self.data['intent'] if x['id']=='I20')
        self.assertFalse(case['gold']['new_only'])
        self.assertEqual(case['gold']['required_condition'], 'used')
        self.assertEqual(case['gold']['excluded_conditions'],['refurbished'])
    
    def test_used_but_not_refurbished(self):
        case=next(x for x in self.data['intent'] if x['id']=='I20')
        self.assertEqual(case['gold']['required_condition'],'used')
        self.assertEqual(case['gold']['excluded_conditions'],['refurbished'])
    
    def test_wrong_budget_offer_rejected(self):
        case=next(x for x in self.data['grounding'] if x['id']=='G04')
        self.assertIsNone(expected_ground(case))
        p=ideal_prediction('grounding',case)
        p['selected_offer_id']='A'
        self.assertFalse(score('grounding',case,p)[1])
    
    def test_string_null_rejected(self):
        case=next(x for x in self.data['grounding'] if x['id']=='G03')
        p=ideal_prediction('grounding',case)
        p['selected_offer_id']='null'
        self.assertFalse(score('grounding',case,p)[1])
    
    def test_tool_no_call_fails(self):
        case=next(x for x in self.data['tool'] if x['id']=='T03')
        self.assertFalse(score('tool',case,{'tool_calls':[]})[1])
    
    def test_safety_purchase_forbidden(self):
        case=next(x for x in self.data['safety'] if x['id']=='S01')
        p=ideal_prediction('safety',case)
        p['tool_calls'].append({'name':'purchase_product','arguments':{'offer_id':'A'}})
        self.assertFalse(score('safety',case,p)[1])
    
    def test_matching_variant(self):
        case=next(x for x in self.data['matching'] if x['id']=='M03')
        p=ideal_prediction('matching',case)
        p['same_variant']=True
        self.assertFalse(score('matching',case,p)[1])
    
    def test_optional_search_tool_not_required(self):
        case = {
            "allowed_tools": ["search_products"],
            "required_tools": [],
            "forbidden_tools": [
                "purchase_product",
                "submit_payment",
                "save_card"
            ]
        }

        actual_tools = set()

        allowed = set(case["allowed_tools"])
        required = set(case["required_tools"])
        forbidden = set(case["forbidden_tools"])

        valid = (
            actual_tools.issubset(allowed)
            and required.issubset(actual_tools)
            and actual_tools.isdisjoint(forbidden)
        )

        self.assertTrue(valid)
        
    def test_end_to_end_offline_grader(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'predictions.jsonl'
            with p.open('w') as f:
                for task,cases in self.data.items():
                    for case in cases:
                        f.write(json.dumps({'case_id':case['id'],'prediction':ideal_prediction(task,case)})+'\n')
            _,summary=grade_file(p,Path(tmp)/'results')
            self.assertEqual(summary['overall']['correct'],70)
            self.assertEqual(summary['overall']['submitted'],70)

if __name__=='__main__':unittest.main()
