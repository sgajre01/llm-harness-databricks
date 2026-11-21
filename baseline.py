from scenario import packet
from llm_client import parse_json

ANSWER_FORMAT = 'Return exactly {"ship_units": INTEGER, "invoice_usd": "DECIMAL_WITH_TWO_PLACES"}.'


def run_baseline(example, client):
    prompt = f'''{example['policy']}
QUESTION: {example['question']}
SOURCE RECORDS: {packet(example)}
Work carefully through pricing, deliverable quantities, and charges. Check your arithmetic.
You may reason internally before answering. {ANSWER_FORMAT}'''
    return parse_json(client.call_llm(prompt, tag=f"{example['id']}/baseline", max_tokens=1400))
