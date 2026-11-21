"""Independent integer-cent implementation audits every generated label."""
import unittest
from scenario import generate_example


def reference(e):
    t=e['tables']; o=[r for r in t['orders'] if r['id']==e['order_id']][0]
    contract=[r for r in t['contracts'] if r['customer']==o['customer'] and r['valid_from']<=0<=r['valid_to']][0]
    lane=[r for r in t['lanes'] if r['region']==o['region']][0]
    cents=lambda x: int(round(float(x)*100))
    unit_count, merchandise, hazard_count=0,0,0
    for line in o['lines']:
        sku=line['sku']
        prices={r['customer']:cents(r['unit_usd']) for r in t['prices'] if r['sku']==sku and r['customer'] in ('*',o['customer']) and r['valid_from']<=0<=r['valid_to']}
        price=prices.get(o['customer'],prices['*'])
        pct=0 if sku in contract['excluded_skus'] else contract['discount_pct']
        discounted=(price*(100-pct)+50)//100
        stocks=[r for r in t['inventory'] if r['sku']==sku and r['warehouse']==o['warehouse']]
        stock=stocks[0]
        deadline=o['deliver_by_day']-lane['transit_days']
        supply=max(stock['on_hand']-stock['reserved'],0)
        if stock['incoming_day']<=deadline: supply+=stock['incoming_qty']
        q=0 if deadline<0 else min(supply,line['ordered_qty'])
        unit_count+=q;merchandise+=q*discounted
        if [r for r in t['products'] if r['sku']==sku][0]['hazardous']:hazard_count+=q
    freight=cents(lane['base_freight'])
    for r in t['freight_overrides']:
        if r['customer']==o['customer'] and r['region']==o['region'] and r['active']: freight=cents(r['base_freight'])
    if not unit_count or merchandise>=cents(lane['free_freight_threshold']): freight=0
    invoice=merchandise+freight+unit_count*cents(lane['handling_per_unit'])+hazard_count*cents(lane['hazardous_per_unit'])
    return {'ship_units':unit_count,'invoice_usd':f'{invoice//100}.{invoice%100:02d}'}


class ReferenceTests(unittest.TestCase):
    def test_fifty_labels_against_integer_cent_reference(self):
        for i in range(50):
            e=generate_example(i,'primary' if i<25 else 'confirmation')
            self.assertEqual(reference(e),e['ground_truth'],e['id'])

if __name__=='__main__': unittest.main()
