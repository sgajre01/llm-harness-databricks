"""Deterministic synthetic worlds, context routing, and a Decimal answer oracle."""
import copy
import json
import random
from decimal import Decimal, ROUND_HALF_UP

POLICY = '''All amounts are USD; no tax. Dates are integer calendar-day offsets from today (0).
For this order use only records matching its customer, SKU, warehouse and destination region.
Use active contracts and prices (valid_from <= 0 <= valid_to); expired or future records never apply.
For each SKU, use a matching active contract price if present, otherwise the active catalog price.
The active customer contract specifies discount_pct and excluded_skus. Discount applies to each
non-excluded SKU. Round the discounted unit price to cents BEFORE multiplying by shipped units.
Delivery deadline is inclusive. Latest dispatch day = deliver_by_day - transit_days for the region.
Usable stock = max(0, on_hand - reserved) plus incoming_qty ONLY if incoming_day <= latest dispatch day.
If latest dispatch day < 0, ship zero units. Ship min(ordered_qty, usable stock) for each SKU; partial
fulfillment is allowed. Invoice only units deliverable by the deadline; backorders are not invoiced.
Merchandise subtotal is the sum of shipped quantity times discounted unit price. If zero units ship,
freight and surcharge are both zero. Otherwise freight is zero if merchandise subtotal >= the region's
free_freight_threshold, else base_freight. A matching ACTIVE customer freight override replaces only
base_freight, not the threshold. Add the region's handling_per_unit times total shipped units.
For each shipped SKU marked hazardous in the product record add hazardous_per_unit * its shipped units.
Invoice total = merchandise subtotal + freight + handling + hazardous surcharge. Round final total to cents.
Ignore unrelated records. Never combine inventory across warehouses.'''


def money(value):
    return Decimal(str(value)).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)


def generate_example(index, split='primary', seed=20261121):
    rng = random.Random(seed + index * 7919)
    customer, warehouse, region = f'C{index:03}', f'W{index % 3}', f'R{index % 4}'
    skus = [f'P{index:03}-{j}' for j in range(2 + index % 2)]
    order = {'id': f'O{index:03}', 'customer': customer, 'warehouse': warehouse,
             'region': region, 'deliver_by_day': rng.choice([2, 3, 4, 6]),
             'lines': [{'sku': s, 'ordered_qty': rng.randint(8, 35)} for s in skus]}
    contract = {'customer': customer, 'valid_from': -20, 'valid_to': 30,
                'discount_pct': rng.choice([5, 8, 12, 15]),
                'excluded_skus': [skus[-1]] if index % 3 == 0 else []}
    tables = {k: [] for k in ('orders', 'contracts', 'prices', 'inventory', 'products', 'lanes', 'freight_overrides')}
    tables['orders'].append(order)
    tables['contracts'] += [contract, dict(contract, valid_from=-100, valid_to=-1, discount_pct=35)]
    for j, sku in enumerate(skus):
        tables['prices'].append({'sku': sku, 'customer': '*', 'unit_usd': str(money(rng.randint(1100, 9000)/100)), 'valid_from': -5, 'valid_to': 30})
        if (index+j) % 2 == 0:
            tables['prices'].append({'sku': sku, 'customer': customer, 'unit_usd': str(money(rng.randint(800, 7000)/100)), 'valid_from': -5, 'valid_to': 30})
        tables['prices'].append({'sku': sku, 'customer': customer, 'unit_usd': '3.99', 'valid_from': -100, 'valid_to': -1})
        tables['inventory'].append({'sku': sku, 'warehouse': warehouse, 'on_hand': rng.randint(4, 30),
                                    'reserved': rng.randint(0, 6), 'incoming_qty': rng.randint(3, 20), 'incoming_day': rng.choice([0, 1, 3, 7])})
        tables['inventory'].append({'sku': sku, 'warehouse': 'W-OTHER', 'on_hand': 999, 'reserved': 0, 'incoming_qty': 0, 'incoming_day': 0})
        tables['products'].append({'sku': sku, 'hazardous': (index+j) % 4 == 0})
    tables['lanes'].append({'region': region, 'transit_days': rng.choice([1, 2, 3]),
        'free_freight_threshold': rng.choice([500, 1000, 1500]), 'base_freight': rng.choice([25, 40, 65]),
        'handling_per_unit': rng.choice(['0.35', '0.60', '1.25']), 'hazardous_per_unit': '2.75'})
    tables['freight_overrides'].append({'customer': customer, 'region': region, 'active': index % 4 != 0, 'base_freight': rng.choice([10, 15, 20])})
    # Fixed distractor design, independent of model outcomes. Every table remains inspectable.
    distractors = 8 if index % 2 == 0 else 20
    for n in range(distractors):
        other_c, other_s, other_r = f'OTHER-C{n}', f'OTHER-P{n}', f'OTHER-R{n}'
        tables['orders'].append({'id': f'OTHER-O{n}', 'customer': other_c, 'warehouse': 'W-OTHER', 'region': other_r, 'deliver_by_day': 2,
                                 'lines': [{'sku': other_s, 'ordered_qty': 100}]})
        tables['contracts'].append({'customer': other_c, 'valid_from': -10, 'valid_to': 50, 'discount_pct': 40, 'excluded_skus': []})
        tables['prices'].append({'sku': other_s, 'customer': other_c, 'unit_usd': '1.00', 'valid_from': -10, 'valid_to': 50})
        tables['inventory'].append({'sku': other_s, 'warehouse': 'W-OTHER', 'on_hand': 100, 'reserved': 0, 'incoming_qty': 50, 'incoming_day': 0})
        tables['products'].append({'sku': other_s, 'hazardous': True})
        tables['lanes'].append({'region': other_r, 'transit_days': 1, 'free_freight_threshold': 100, 'base_freight': 0, 'handling_per_unit': '0.00', 'hazardous_per_unit': '0.00'})
        tables['freight_overrides'].append({'customer': other_c, 'region': other_r, 'active': True, 'base_freight': 0})
    for rows in tables.values():
        rng.shuffle(rows)
    public = {'id': f'{split}-{index:03}', 'split': split, 'order_id': order['id'],
        'category': 'higher_distraction' if distractors == 20 else 'lower_distraction',
        'question': f'For order {order["id"]}, how many units can be delivered by day {order["deliver_by_day"]}, and what is the invoice total for those units? Apply all supplied policies.',
        'policy': POLICY, 'tables': tables}
    return {**public, 'ground_truth': oracle(public)}


def public_example(example):
    return {k: copy.deepcopy(v) for k, v in example.items() if k != 'ground_truth'}


def route(example):
    """Relational selection uses the public order ID and source fields, never labels.

    Keeps same-customer historical prices/contracts and wrong-warehouse stock in the
    focused packet: the model must still apply dates and warehouse policy itself.
    """
    tables = example['tables']
    order = next(r for r in tables['orders'] if r['id'] == example['order_id'])
    skus = {r['sku'] for r in order['lines']}
    return {'orders': [order],
        'contracts': [r for r in tables['contracts'] if r['customer'] == order['customer']],
        'prices': [r for r in tables['prices'] if r['sku'] in skus and r['customer'] in ('*', order['customer'])],
        'inventory': [r for r in tables['inventory'] if r['sku'] in skus],
        'products': [r for r in tables['products'] if r['sku'] in skus],
        'lanes': [r for r in tables['lanes'] if r['region'] == order['region']],
        'freight_overrides': [r for r in tables['freight_overrides'] if r['customer'] == order['customer'] and r['region'] == order['region']]}


STAGE_TABLES = {'pricing': ('orders', 'contracts', 'prices'),
                'fulfillment': ('orders', 'inventory', 'lanes'),
                'charges': ('orders', 'products', 'lanes', 'freight_overrides')}


def packet(example, stage=None, focused=False):
    tables = route(example) if focused else example['tables']
    if focused and stage:
        tables = {k: tables[k] for k in STAGE_TABLES[stage]}
    return json.dumps(tables, separators=(',', ':'))


def oracle(example):
    # Deliberately reads original tables directly, not the harness context router.
    t = example['tables']
    o = next(x for x in t['orders'] if x['id'] == example['order_id'])
    c = next(x for x in t['contracts'] if x['customer'] == o['customer'] and x['valid_from'] <= 0 <= x['valid_to'])
    lane = next(x for x in t['lanes'] if x['region'] == o['region'])
    dispatch = o['deliver_by_day'] - lane['transit_days']
    units, subtotal, hazardous = 0, Decimal('0'), 0
    for line in o['lines']:
        sku = line['sku']
        inv = next(x for x in t['inventory'] if x['sku'] == sku and x['warehouse'] == o['warehouse'])
        available = max(0, inv['on_hand'] - inv['reserved']) + (inv['incoming_qty'] if inv['incoming_day'] <= dispatch else 0)
        qty = min(line['ordered_qty'], available) if dispatch >= 0 else 0
        prices = [x for x in t['prices'] if x['sku'] == sku and x['customer'] in ('*', o['customer']) and x['valid_from'] <= 0 <= x['valid_to']]
        p = next((x for x in prices if x['customer'] == o['customer']), next(x for x in prices if x['customer'] == '*'))
        discount = 0 if sku in c['excluded_skus'] else c['discount_pct']
        unit = money(Decimal(p['unit_usd']) * (100 - discount) / 100)
        units += qty
        subtotal += unit * qty
        if next(x for x in t['products'] if x['sku'] == sku)['hazardous']:
            hazardous += qty
    base = Decimal(str(lane['base_freight']))
    override = next((x for x in t['freight_overrides'] if x['customer'] == o['customer'] and x['region'] == o['region'] and x['active']), None)
    if override:
        base = Decimal(str(override['base_freight']))
    freight = Decimal('0') if not units or subtotal >= Decimal(str(lane['free_freight_threshold'])) else base
    total = subtotal + freight + units * Decimal(lane['handling_per_unit']) + hazardous * Decimal(lane['hazardous_per_unit'])
    return {'ship_units': units, 'invoice_usd': str(money(total))}
