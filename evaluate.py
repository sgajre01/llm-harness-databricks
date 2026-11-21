"""Run frozen examples with checkpointed, paired comparisons."""
import argparse
import hashlib
import json
import random
import time
from decimal import Decimal, InvalidOperation
from pathlib import Path
from baseline import run_baseline
from harness import run_harness
from llm_client import LLMClient, MODEL
from scenario import public_example

MODES = ('baseline', 'full_harness', 'focused_harness')


def normalize(answer):
    if not isinstance(answer, dict) or set(answer) != {'ship_units', 'invoice_usd'}:
        raise ValueError('Answer must contain exactly ship_units and invoice_usd')
    qty = Decimal(str(answer['ship_units']))
    total = Decimal(str(answer['invoice_usd']).strip())
    if not qty.is_finite() or not total.is_finite() or qty != int(qty) or qty < 0 or total < 0:
        raise ValueError('Invalid quantity or money')
    if total != total.quantize(Decimal('.01')):
        raise ValueError('Money has more than two decimal places')
    return {'ship_units': int(qty), 'invoice_usd': format(total, '.2f')}


def score(answer, truth):
    try:
        return normalize(answer) == normalize(truth)
    except (ValueError, InvalidOperation, TypeError, OverflowError):
        return False


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(dataset, output_dir, *, model=MODEL, limit=None, workers=1):
    if workers != 1:
        raise ValueError('Serial execution is intentional for fair latency measurement')
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    root = Path(__file__).parent
    config = {'model': model, 'temperature': 0, 'dataset_sha256': digest(dataset),
        'code_sha256': {name: digest(root/name) for name in
                        ('llm_client.py', 'baseline.py', 'harness.py', 'scenario.py', 'evaluate.py')},
        'limit': limit, 'mode_order_seed': 721, 'max_transport_attempts': 3,
        'normalization': 'exact two-field object; numeric quantity; USD exact cents; formatting only'}
    config_path = output/'config.json'
    if config_path.exists() and json.loads(config_path.read_text()) != config:
        raise ValueError('Resume configuration mismatch; use a new output directory')
    config_path.write_text(json.dumps(config, indent=2))
    checkpoint = output/'predictions.jsonl'
    existing = [json.loads(line) for line in checkpoint.read_text().splitlines()] if checkpoint.exists() else []
    done = {(r['id'], r['mode']) for r in existing}
    examples = json.loads(Path(dataset).read_text())[:limit]
    client = LLMClient(output/'calls.jsonl', model)
    rng = random.Random(721)
    for example in examples:
        modes = list(MODES)
        rng.shuffle(modes)
        for mode in modes:
            if (example['id'], mode) in done:
                continue
            clean = public_example(example)
            # Ground truth exists only in evaluator, never in model-facing objects.
            assert 'ground_truth' not in clean
            started, offset = time.time(), len(client.records)
            answer, intermediate, status, error = None, None, 'completed', None
            try:
                if mode == 'baseline':
                    answer = run_baseline(clean, client)
                else:
                    answer, intermediate = run_harness(clean, client, focused=(mode == 'focused_harness'))
                normalize(answer)
            except (json.JSONDecodeError, ValueError, KeyError, TypeError, InvalidOperation) as exc:
                status, error = 'invalid_answer', str(exc)
            # Other errors (quota, permission, network) stop the run; resume skips saved rows.
            calls = client.records[offset:]
            usage = [r.get('response', {}).get('usage', {}) for r in calls]
            row = {'id': example['id'], 'split': example['split'], 'category': example['category'],
                'mode': mode, 'status': status, 'error': error, 'answer': answer,
                'ground_truth': example['ground_truth'], 'correct': score(answer, example['ground_truth']),
                'intermediate': intermediate, 'elapsed_seconds': time.time()-started,
                'call_attempts': len(calls), 'successful_calls': sum('response' in r for r in calls),
                'prompt_tokens': sum(u.get('prompt_tokens', 0) for u in usage),
                'completion_tokens': sum(u.get('completion_tokens', 0) for u in usage),
                'usage_available': all('prompt_tokens' in u for u in usage)}
            with checkpoint.open('a') as handle:
                handle.write(json.dumps(row)+'\n')
            existing.append(row)
            print(f"{example['id']} {mode}: {status}, correct={row['correct']}", flush=True)
    return existing


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--dataset', default='data/examples.json')
    parser.add_argument('--output', default='results/main')
    parser.add_argument('--model', default=MODEL)
    parser.add_argument('--limit', type=int)
    args = parser.parse_args()
    run(args.dataset, args.output, model=args.model, limit=args.limit)
