import copy
import unittest
from decimal import Decimal
from evaluate import normalize, score
from scenario import generate_example, oracle, public_example, route, packet, money


class ExperimentTests(unittest.TestCase):
    def test_round_half_up(self):
        self.assertEqual(money('1.005'), Decimal('1.01'))

    def test_score_strict(self):
        truth = {'ship_units': 3, 'invoice_usd': '12.50'}
        self.assertTrue(score({'ship_units':'3', 'invoice_usd':'12.5'}, truth))
        for bad in ({'ship_units':3, 'invoice_usd':'12.51'}, {'ship_units':3.2, 'invoice_usd':'12.50'},
                    {'ship_units':3, 'invoice_usd':'12.50', 'note':'x'}, None):
            self.assertFalse(score(bad, truth))

    def test_hand_calculated_oracle(self):
        e = {'order_id':'O', 'tables': {
            'orders':[{'id':'O','customer':'C','warehouse':'W','region':'R','deliver_by_day':3,
                       'lines':[{'sku':'P','ordered_qty':10}]}],
            'contracts':[{'customer':'C','valid_from':-1,'valid_to':1,'discount_pct':10,'excluded_skus':[]}],
            'prices':[{'sku':'P','customer':'*','unit_usd':'20.00','valid_from':-1,'valid_to':1},
                      {'sku':'P','customer':'C','unit_usd':'10.05','valid_from':-1,'valid_to':1}],
            'inventory':[{'sku':'P','warehouse':'W','on_hand':8,'reserved':2,'incoming_qty':2,'incoming_day':2}],
            'products':[{'sku':'P','hazardous':True}],
            'lanes':[{'region':'R','transit_days':1,'free_freight_threshold':100,'base_freight':20,'handling_per_unit':'0.50','hazardous_per_unit':'2.75'}],
            'freight_overrides':[{'customer':'C','region':'R','active':True,'base_freight':5}]}}
        # 10.05 * .9 = 9.045 -> 9.05; 8 units * 9.05 + 5 + 4 + 22 = 103.40
        self.assertEqual(oracle(e), {'ship_units':8,'invoice_usd':'103.40'})
        e['tables']['inventory'][0]['incoming_day'] = 3
        self.assertEqual(oracle(e), {'ship_units':6,'invoice_usd':'78.80'})
        e['tables']['orders'][0]['deliver_by_day'] = 0
        self.assertEqual(oracle(e), {'ship_units':0,'invoice_usd':'0.00'})

    def test_all_worlds_and_router_label_independence(self):
        for i in range(50):
            e = generate_example(i)
            self.assertEqual(oracle(e), e['ground_truth'])
            clean = public_example(e)
            self.assertNotIn('ground_truth', clean)
            changed = copy.deepcopy(e)
            changed['ground_truth'] = {'ship_units':-999,'invoice_usd':'99999'}
            self.assertEqual(route(e), route(changed))
            selected = dict(clean, tables=route(clean))
            self.assertEqual(oracle(selected), e['ground_truth'])
            self.assertLess(len(packet(clean, 'pricing', True)), len(packet(clean)))
            self.assertNotIn('ground_truth', packet(clean))

    def test_invariants(self):
        for i in range(50):
            e = generate_example(i)
            order = next(r for r in e['tables']['orders'] if r['id']==e['order_id'])
            self.assertLessEqual(e['ground_truth']['ship_units'], sum(r['ordered_qty'] for r in order['lines']))
            self.assertGreaterEqual(Decimal(e['ground_truth']['invoice_usd']), 0)

if __name__ == '__main__':
    unittest.main()
