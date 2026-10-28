#!/usr/bin/env python3
"""Offline structural and oracle validation for ShopAgent 100-case suite.

Requires only Python standard library; never calls an API.
"""
from __future__ import annotations
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'dataset'
LEGACY = ROOT / 'legacy_32_frozen'
COUNTS = {'intent':28,'tool':14,'grounding':15,'matching':8,'safety':5}
INTENT_FIELDS = {'category','brand','model','max_budget_usd','screen_size_inches',
                 'display_type','ram_gb','storage_gb','color','resolution',
                 'free_shipping_required','new_only','total_budget_includes_tax_shipping',
                 'exclude_retailers','needs_clarification','requested_auto_purchase',
                 'min_return_days','excluded_conditions','excluded_models','delivery_by',
                 'required_condition'}
LEGACY_FIELDS = INTENT_FIELDS - {'excluded_conditions','excluded_models','delivery_by','required_condition'}
TOOL_NAMES = {'none','search_products','get_product_details','get_shipping_estimate'}
SAFETY_ACTIONS = {'search_only','refuse_payment_data','ignore_untrusted_instructions',
                  'fail_closed','reject_unverified_coupon','mark_total_unverified',
                  'reject_over_budget','require_offer_approval','report_unavailable'}

def read(path): return json.loads(path.read_text(encoding='utf-8'))

def total(o):
    if not o['in_stock']:
        return None
    vals=[o.get(k) for k in ('price_usd','shipping_usd','tax_usd','verified_coupon_usd')]
    if any(v is None for v in vals):return None
    if any(isinstance(v,bool) or not isinstance(v,(int,float)) or v<0 for v in vals):
        raise ValueError('Invalid money')
    return round(vals[0]+vals[1]+vals[2]-vals[3],2)

def expected_ground(case):
    eligible=[]
    for o in case['offers']:
        cost=total(o)
        if cost is not None and (case['budget'] is None or cost <= case['budget']):
            eligible.append((cost,o['offer_id']))
    return min(eligible)[1] if eligible else None

def validate(verbose=True):
    errors=[]
    def check(cond,msg):
        if not cond:errors.append(msg)
    data={t:read(DATA/f'{t}_cases.json') for t in COUNTS}
    manifest=read(DATA/'manifest.json')
    check(manifest['categories']==COUNTS,'Manifest counts mismatch')
    check(manifest['total']==70,'Manifest total mismatch')
    check(all(len(data[t])==n for t,n in COUNTS.items()),'Category counts mismatch')
    ids=[]
    for typ,cases in data.items():
        for case in cases:
            id=case.get('id','<missing>')
            ids.append(id)
            check(case.get('origin') in {'legacy32','new68'},f'{id}: origin missing')
            check(case.get('split') in {'development','holdout'},f'{id}: missing split')
            check(case.get('label_status','').startswith(('PROVISIONAL','PROPOSED')),f'{id}: missing review status')
            check(bool(case.get('query') or case.get('user_query') or case.get('left')),f'{id}: missing input')
            if typ=='intent':
                gold=case.get('gold',{})
                check(set(gold)==INTENT_FIELDS,f'{id}: wrong intent schema fields')
                for k in ('free_shipping_required','new_only','total_budget_includes_tax_shipping',
                          'needs_clarification','requested_auto_purchase'):
                    check(type(gold.get(k)) is bool,f'{id}: {k} must be boolean')
                for k in ('exclude_retailers','excluded_conditions','excluded_models'):
                    check(isinstance(gold.get(k),list) and all(isinstance(v,str) for v in gold[k]),
                          f'{id}: {k} must be list[str]')
                for k in ('max_budget_usd','screen_size_inches','ram_gb','storage_gb','min_return_days'):
                    v=gold.get(k)
                    check(v is None or (isinstance(v,(int,float)) and not isinstance(v,bool) and v>=0),
                          f'{id}: invalid numeric field {k}')
                check(not (gold.get('new_only') and gold.get('required_condition')=='used'),
                      f'{id}: contradictory condition')
                check(gold.get('required_condition') in (None,'new','used','refurbished'),
                      f'{id}: invalid required_condition')
                if 'not refurbished' in case['user_query'].lower() or 'no refurbished' in case['user_query'].lower():
                    check('refurbished' in gold.get('excluded_conditions',[]),
                          f'{id}: negative condition missing')
            elif typ=='tool':
                check(case.get('expected_tool') in TOOL_NAMES,f'{id}: invalid tool')
                check(isinstance(case.get('required_query_terms'),list),f'{id}: terms not list')
                args=case.get('expected_arguments',{})
                check(isinstance(args,dict),f'{id}: arguments not object')
                if case.get('expected_tool')=='get_product_details':
                    check(bool(args.get('product_id')),f'{id}: product_id required')
                if case.get('expected_tool')=='get_shipping_estimate':
                    check(bool(args.get('product_id')) and bool(args.get('destination_zip')),
                          f'{id}: shipping args required')
            elif typ=='grounding':
                check(isinstance(case.get('offers'),list) and len(case['offers'])>=2,
                      f'{id}: at least two offers required')
                offer_ids=[o['offer_id'] for o in case['offers']]
                check(len(offer_ids)==len(set(offer_ids)),f'{id}: duplicate offer ID')
                for o in case['offers']:
                    for k in ('price_usd','shipping_usd','tax_usd','verified_coupon_usd','in_stock'):
                        check(k in o,f'{id}: missing offer field {k}')
                    try: total(o)
                    except Exception as exc:errors.append(f'{id}: bad offer money {exc}')
                try: actual=expected_ground(case)
                except Exception as exc:errors.append(f'{id}: price oracle failed {exc}');actual='ERR'
                check(case.get('expected_offer_id')==actual,
                      f'{id}: expected offer {case.get("expected_offer_id")} != deterministic {actual}')
                check(type(case.get('coverage_incomplete')) is bool,f'{id}: coverage must be bool')
            elif typ=='matching':
                check(type(case.get('expected_same_variant')) is bool,f'{id}: match boolean required')
                for side in ('left','right'):
                    product=case.get(side,{})
                    check(all(k in product for k in ('title','brand','manufacturer_model','condition','region')),
                          f'{id}: missing {side} product fields')
                check(bool(case.get('rationale')),f'{id}: missing matching rationale')
            elif typ=='safety':
                check(case.get('expected_action') in SAFETY_ACTIONS,f'{id}: invalid safety action')
                check(case.get('purchase_requires_approval') is True,f'{id}: purchase approval required')
                check({'purchase_product','submit_payment','save_card'}.issubset(set(case.get('forbidden_tools',[]))),
                      f'{id}: missing forbidden tools')
                check(not set(case.get('allowed_tools',[])) & set(case.get('forbidden_tools',[])),
                      f'{id}: conflicting tool policy')
    check(len(ids)==70 and len(ids)==len(set(ids)),'Duplicate or missing IDs')
    # Public subset: original IDs intentionally have gaps where private holdout cases were removed.
    for typ,prefix in [('intent','I'),('tool','T'),('grounding','G'),('matching','M'),('safety','S')]:
        check(all(re.fullmatch(rf'{prefix}\d{{2}}', x['id']) for x in data[typ]),
              f'{typ}: invalid case ID')
    check(sum(x.get('split')=='development' for cases in data.values() for x in cases)==70, 'Development split not 70')
    check(sum(x.get('split')=='holdout' for cases in data.values() for x in cases)==0, 'Public package must not contain holdout cases')
    check(all(x.get('split')=='development' for cases in data.values() for x in cases if x.get('origin')=='legacy32'), 'Legacy cases must remain development')
    check(sum(x.get('origin')=='legacy32' for cases in data.values() for x in cases)==32,
          'Legacy count not 32')
    check(sum(x.get('origin')=='new68' for cases in data.values() for x in cases)==38,
          'Public development new-case count not 38')
    if verbose:
        for typ,cases in data.items():print(f'{typ:10} {len(cases):3} cases')
        print(f'IDs unique: {len(set(ids))}; original 32 preserved; 38 additional development cases')
        print('Offline validation:', 'PASS' if not errors else f'FAIL ({len(errors)} errors)')
        for error in errors:print(' -',error)
    if errors:raise AssertionError('\n'.join(errors))
    return data

if __name__=='__main__':validate()
