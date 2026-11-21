"""Standard-library report generator: paired statistics, CSV and Markdown."""
import argparse
import csv
import json
import math
import random
import statistics
from pathlib import Path
from evaluate import MODES, normalize


def paired(rows, treatment, split=None, reference="baseline"):
    subset = [r for r in rows if split is None or r['split'] == split]
    groups = {}
    for row in subset:
        groups.setdefault(row['id'], {})[row['mode']] = row
    pairs = [(g[reference]['correct'], g[treatment]['correct']) for g in groups.values()
             if reference in g and treatment in g]
    n = len(pairs)
    if not n:
        return {'n': 0}
    wins = sum(t and not b for b,t in pairs)
    losses = sum(b and not t for b,t in pairs)
    discordant = wins + losses
    pvalue = min(1, 2 * sum(math.comb(discordant,k) for k in range(min(wins,losses)+1))/2**discordant) if discordant else 1.0
    differences = [int(t)-int(b) for b,t in pairs]
    rng = random.Random(20261121)
    draws = sorted(sum(rng.choices(differences,k=n))/n*100 for _ in range(10000))
    return {'n':n, 'wins':wins, 'losses':losses, 'ties':n-wins-losses,
            'difference_pp':sum(differences)/n*100,
            'paired_bootstrap_95_ci_pp':[draws[249],draws[9749]], 'mcnemar_exact_p':pvalue}


def build(result_dir, target=None):
    source = Path(result_dir)
    target = Path(target or source)
    target.mkdir(parents=True, exist_ok=True)
    rows = [json.loads(x) for x in (source/'predictions.jsonl').read_text().splitlines()]
    keys = [(r['id'],r['mode']) for r in rows]
    if len(set(keys)) != len(keys):
        raise ValueError('Duplicate scored observations')
    summary = {'completed_rows':len(rows), 'arms':{}, 'paired':{}}
    for split in ('primary','confirmation','all'):
        selected = [r for r in rows if split == 'all' or r['split']==split]
        summary['arms'][split] = {}
        for mode in MODES:
            arm = [r for r in selected if r['mode']==mode]
            if not arm:
                continue
            summary['arms'][split][mode] = {'n':len(arm),'correct':sum(r['correct'] for r in arm),
                'accuracy':sum(r['correct'] for r in arm)/len(arm),
                'median_seconds':statistics.median(r['elapsed_seconds'] for r in arm),
                'successful_calls':sum(r['successful_calls'] for r in arm),
                'call_attempts':sum(r['call_attempts'] for r in arm),
                'prompt_tokens':sum(r['prompt_tokens'] for r in arm),
                'completion_tokens':sum(r['completion_tokens'] for r in arm),
                'invalid_answers':sum(r['status']=='invalid_answer' for r in arm)}
        summary['paired'][split] = {mode:paired(rows,mode,None if split=='all' else split) for mode in MODES[1:]}
    summary['by_distraction'] = {category:{mode:{'n':len(arm), 'correct':sum(r['correct'] for r in arm)}
        for mode in MODES if (arm := [r for r in rows if r['category']==category and r['mode']==mode])}
        for category in sorted({r['category'] for r in rows})}
    summary['focused_vs_full'] = paired(rows, 'focused_harness', reference='full_harness')
    summary['field_accuracy'] = {}
    for mode in MODES:
        arm = [r for r in rows if r['mode']==mode]
        scores = {'ship_units':0,'invoice_usd':0}
        for r in arm:
            try:
                answer = normalize(r['answer'])
            except Exception:
                continue
            for key in scores:
                scores[key] += answer[key] == r['ground_truth'][key]
        summary['field_accuracy'][mode] = {'n':len(arm),**scores}
    calls_path = source/'calls.jsonl'
    if calls_path.exists():
        calls = [json.loads(line) for line in calls_path.read_text().splitlines()]
        stages = {}
        for call in calls:
            tag = call['tag'].split('/')
            stage = '/'.join(tag[1:])
            usage = call.get('response', {}).get('usage', {})
            if 'prompt_tokens' in usage:
                stages.setdefault(stage, []).append(usage['prompt_tokens'])
        summary['mean_prompt_tokens_by_call_stage'] = {k:statistics.mean(v) for k,v in stages.items()}
        summary['logged_application_attempts'] = len(calls)
    (target/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    columns = ['id','split','category','mode','status','correct','answer','ground_truth','elapsed_seconds','successful_calls','prompt_tokens','completion_tokens']
    with (target/'comparison.csv').open('w',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({k:json.dumps(row[k],sort_keys=True) if isinstance(row[k],dict) else row[k] for k in columns})
    text = ['# Experiment results','',f'Completed scored observations: {len(rows)}. Expected: 150 (50 questions × 3 arms).','',
            '| Set | Approach | Correct / total | Accuracy | Median seconds | Prompt tokens | Output tokens |',
            '|---|---|---:|---:|---:|---:|---:|']
    for split, arms in summary['arms'].items():
        for mode,a in arms.items():
            text.append(f"| {split} | {mode} | {a['correct']}/{a['n']} | {a['accuracy']:.1%} | {a['median_seconds']:.2f} | {a['prompt_tokens']:,} | {a['completion_tokens']:,} |")
    text += ['','## Paired comparisons against baseline','',
             '| Set | Approach | Gain (pp) | Wins / losses / ties | Bootstrap 95% interval (pp) | Exact p |',
             '|---|---|---:|---:|---:|---:|']
    for split, modes in summary['paired'].items():
        for mode,p in modes.items():
            if not p['n']: continue
            lo,hi=p['paired_bootstrap_95_ci_pp']
            text.append(f"| {split} | {mode} | {p['difference_pp']:+.1f} | {p['wins']}/{p['losses']}/{p['ties']} | [{lo:+.1f}, {hi:+.1f}] | {p['mcnemar_exact_p']:.4f} |")
    focus = summary['focused_vs_full']
    if focus['n']:
        text += ['', f"Focused versus full-context harness: {focus['difference_pp']:+.1f} pp; {focus['wins']} wins, {focus['losses']} losses, {focus['ties']} ties."]
    text += ['','The bootstrap resamples paired questions (10,000 draws, fixed seed). P-values are unadjusted exploratory comparisons. One observation per arm/question; no repeated-run stability claim. See the protocol for scope and normalization.','',
             '## Per-example comparison','', '| ID | Ground truth | Baseline | Full harness | Focused harness |', '|---|---|---|---|---|']
    grouped={}
    for r in rows: grouped.setdefault(r['id'],{})[r['mode']]=r
    for key,g in grouped.items():
        truth=next(iter(g.values()))['ground_truth']
        values=[]
        for mode in MODES:
            r=g.get(mode)
            values.append(('✓ ' if r['correct'] else '✗ ')+json.dumps(r['answer'],sort_keys=True) if r else 'not completed')
        text.append('| '+ ' | '.join([key,json.dumps(truth,sort_keys=True),*values])+' |')
    (target/'report.md').write_text('\n'.join(text)+'\n')
    return summary

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('result_dir')
    args=parser.parse_args()
    print(json.dumps(build(args.result_dir),indent=2))
