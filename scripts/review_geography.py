"""Assess saved findings through the existing tool-free Codex provider."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from pathlib import Path
import time

from atlas.codex import CodexExtractor
from atlas.config import assets
from atlas.geography import Reviews, validate_review, review_fingerprint
from atlas.util import digest, read_json, write_json, utcnow


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--snapshot', type=Path, required=True)
    p.add_argument('--annotations', type=Path, required=True)
    p.add_argument('--source-dir', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--limit', type=int, default=1000)
    args = p.parse_args()
    if not 1 <= args.limit <= 1000:
        p.error('limit must be between 1 and 1000')
    data = read_json(args.snapshot); ann = read_json(args.annotations)
    if ann['records_sha256'] != digest(data['records']):
        raise ValueError('Annotations differ from snapshot')
    retained = {l['record_id'] for l in ann['locations']}
    prompt = assets('geography.md')
    args.out.mkdir(parents=True, exist_ok=True)
    prompt_path=args.out/'prompt.md'
    if prompt_path.exists() and prompt_path.read_text()!=prompt:
        raise ValueError('Review directory belongs to another prompt; use a separate directory')
    prompt_path.write_text(prompt)
    pending = []; results = []; characters = 0
    for record in data['records']:
        if record['id'] in retained:
            continue
        source = (args.source_dir / (record['document_id'] + '.txt')).read_text()
        key = review_fingerprint(record, source)
        path = args.out / (key + '.json')
        if path.exists():
            row = read_json(path)
            validate_review(row['review'], record, source)
            results.append(row); continue
        payload = dict(record_id=record['id'], title=record['title'], publication=record['publication'], claims=record['claims'])
        size = len(json.dumps(payload)); characters += size
        if size > 100000 or characters > 12000000:
            raise ValueError('Geographic review input exceeds configured bounds')
        pending.append((record, source, key, payload))
    pending = pending[:args.limit]
    batches = []; batch = []; size = 0
    for job in pending:
        n = len(json.dumps(job[3]))
        if batch and (len(batch) >= 12 or size + n > 30000):
            batches.append(batch); batch = []; size = 0
        batch.append(job); size += n
    if batch: batches.append(batch)
    def run(batch):
        key = digest([j[2] for j in batch])
        result, receipt = CodexExtractor('', 200000, 600).extract(
            json.dumps([j[3] for j in batch]),
            dict(title='ATLAS geographic evidence assessment', published_at=utcnow(), url=''),
            args.out / 'attempts' / (key + '-' + str(time.time_ns())), contract=Reviews, prompt=prompt)
        by_id = {r.record_id:r for r in result.records}
        if len(by_id) != len(result.records) or set(by_id) != {j[0]['id'] for j in batch}:
            raise ValueError('Model omitted or duplicated geographic assessments')
        rows = []
        for record, source, fingerprint, _ in batch:
            review = validate_review(by_id[record['id']], record, source)
            row = dict(input_sha256=fingerprint, reviewed_at=utcnow(), batch_id=key,
                       receipt=receipt, review=review.model_dump(mode='json'))
            rows.append((fingerprint, row))
        for fingerprint, row in rows: write_json(args.out / (fingerprint + '.json'), row)
        return [row for _,row in rows]
    errors = []
    print('Retained',len(retained),'cached',len(results),'pending',len(pending),'batches',len(batches),flush=True)
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(run,b):b for b in batches}
        for future in as_completed(futures):
            try:
                rows = future.result(); results.extend(rows)
                print('Completed', len(results), 'assessments',flush=True)
            except Exception as exc:
                errors.append(dict(record_ids=[j[0]['id'] for j in futures[future]],error=str(exc)))
                print('Failed batch:',str(exc),flush=True)
            write_json(args.out/'results.json', results)
            write_json(args.out/'status.json',dict(checked_at=utcnow(),retained=len(retained),completed=len(results),errors=errors))
    write_json(args.out/'results.json',results)
    write_json(args.out/'status.json',dict(checked_at=utcnow(),retained=len(retained),completed=len(results),errors=errors))
    if errors: raise SystemExit('Some assessments need review; see status.json')


if __name__ == '__main__': main()
