"""Bounded planner and three sequential domain calls, followed by synthesis."""
import json
from baseline import ANSWER_FORMAT
from llm_client import parse_json
from scenario import packet

STAGES = ('pricing', 'fulfillment', 'charges')
INSTRUCTIONS = {
 'pricing': 'Identify the target order and active customer contract. Resolve price precedence, exclusions and discount. Return {"lines":[{"sku":"...","discounted_unit_usd":"0.00"}]}. Include every target SKU exactly once. Do not calculate freight.',
 'fulfillment': 'Resolve target region transit and latest dispatch day. For each ordered SKU calculate units deliverable by deadline from the correct warehouse after reservations and eligible arrivals. Return {"lines":[{"sku":"...","ship_qty":0}],"ship_units":0}. Include every target SKU exactly once. Do not calculate prices or invoice amounts.',
 'charges': 'Using prior pricing and fulfillment results, calculate merchandise subtotal, freight after threshold and active override, per-unit handling and hazardous surcharge. Invoice only shipped units. Return merchandise_usd, freight_usd, handling_usd, hazardous_usd, invoice_usd and ship_units.'}


def decompose(example, client, focused):
    # Planner sees the same question; domain routing supplies source records to solvers.
    prompt = f'''Plan this order analysis in exactly three ordered steps with domains
pricing, fulfillment, charges (in that order). Include a short instruction for each.
QUESTION: {example['question']}
POLICY: {example['policy']}
Return {{"steps":[{{"domain":"pricing","instruction":"..."}},{{"domain":"fulfillment","instruction":"..."}},{{"domain":"charges","instruction":"..."}}]}}.'''
    mode = 'focused' if focused else 'full'
    plan = parse_json(client.call_llm(prompt, tag=f"{example['id']}/{mode}/plan", max_tokens=600))
    if [s['domain'] for s in plan['steps']] != list(STAGES):
        raise ValueError('Planner did not produce the required domain sequence')
    return plan['steps']


def solve_step(example, client, step, previous, focused):
    stage = step['domain']
    prompt = f'''POLICY: {example['policy']}
QUESTION: {example['question']}
STEP: {stage}. {INSTRUCTIONS[stage]}
PLANNER INSTRUCTION: {step['instruction']}
PRIOR RESULTS: {json.dumps(previous)}
SOURCE RECORDS: {packet(example, stage, focused)}
Return exactly one JSON object in the requested step schema. Do not answer other steps. Include enough numeric detail for the next step to use.'''
    mode = 'focused' if focused else 'full'
    return parse_json(client.call_llm(prompt, tag=f"{example['id']}/{mode}/{stage}", max_tokens=1400))


def synthesize(example, client, steps, focused):
    prompt = f'''QUESTION: {example['question']}
POLICY: {example['policy']}
COMPLETED STEP RESULTS: {json.dumps(steps)}
Check that the final total is merchandise plus freight, handling and hazardous charges.
Use these results to give the final answer. {ANSWER_FORMAT}'''
    mode = 'focused' if focused else 'full'
    return parse_json(client.call_llm(prompt, tag=f"{example['id']}/{mode}/synthesis", max_tokens=1400))


def run_harness(example, client, focused=True):
    plan = decompose(example, client, focused)
    results = {}
    for step in plan:
        results[step['domain']] = solve_step(example, client, step, results, focused)
    return synthesize(example, client, results, focused), {'plan': plan, 'steps': results}
