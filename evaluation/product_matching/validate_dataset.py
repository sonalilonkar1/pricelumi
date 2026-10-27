"""Validate format and separation of synthetic labeled product pairs."""
import json
from collections import Counter, defaultdict
from pathlib import Path

from baseline import normalize_gtin

DATASET=Path(__file__).resolve().parents[1] / 'product_pairs.jsonl'
CATALOG=Path(__file__).resolve().parent / 'mock_products.json'


def main():
    catalogue=json.loads(CATALOG.read_text(encoding='utf-8'))
    known={r['id']:r for r in catalogue}
    assert len(known)==len(catalogue), 'Duplicate catalogue IDs'
    for product in catalogue:
        assert product['data_origin']=='synthetic'
        if product.get('gtin') is not None:
            assert normalize_gtin(product['gtin']), f"Invalid fixture GTIN: {product['id']}"

    split_ids=defaultdict(set)
    split_counts=Counter()
    pair_ids=set()
    for idx,line in enumerate(DATASET.read_text(encoding='utf-8').splitlines(),start=1):
        item=json.loads(line)
        assert item['pair_id'] not in pair_ids, f'Duplicate pair at {idx}'
        pair_ids.add(item['pair_id'])
        assert item['split'] in ('development','holdout')
        assert type(item['label'])==int and item['label'] in (0,1)
        assert item['data_origin']=='synthetic'
        assert item['product_a']['id']!=item['product_b']['id']
        for side in ('product_a','product_b'):
            record=item[side]
            assert record['data_origin']=='synthetic'
            assert record['retailer'].startswith('mock_')
            assert isinstance(record['variants'],dict)
            if not item.get('stress_case'):
                assert record==known[record['id']], f'Unexpected fixture mismatch {record["id"]}'
            # Stress examples have deliberately contradictory/missing fields.
            original_id=record['id'].split('_stress_')[0]
            assert original_id in known, f'Unrecognized mock product: {record["id"]}'
            family=original_id.rsplit('_',1)[0]
            split_ids[item['split']].add(family)
        split_counts[(item['split'],item['label'])]+=1
    assert not (split_ids['development'] & split_ids['holdout']), 'Family leakage between splits'
    assert set(split_ids)=={'development','holdout'}
    print('Dataset valid:',len(catalogue),'base listings,',len(pair_ids),'pairs')
    print('Label counts by split:',dict(split_counts))
    print('Distinct product families: development',len(split_ids['development']),
          ', holdout',len(split_ids['holdout']))


if __name__=='__main__':
    main()
