"""Fill missing Rotten Tomatoes critic scores through OMDb; cache in SQLite.

Never creates per-movie files. Stops at an explicit request cap or API quota.
Existing class scores are preserved to spend the free allowance on gaps.
"""
import argparse
import concurrent.futures as futures
import csv
import hashlib
import json
import urllib.parse
from datetime import datetime, timezone
from build_dataset import ROOT, COLUMNS, connection, get_json, settings, write_csv


def read_csv(name):
    with (ROOT / name).open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--max-requests', type=int, default=1000)
    args = parser.parse_args()
    key = settings().get('OMDB_API_KEY')
    if not key:
        raise SystemExit('Set OMDB_API_KEY in MovieData P2/.env first.')
    rows = read_csv('movies_1970_2025.csv')
    sources = read_csv('movie_sources.csv')
    assert len(rows) == len(sources)
    pending = [(i, s['IMDbID']) for i,s in enumerate(sources) if s['IMDbID'] and not rows[i]['RottenTomatoes']]
    # Stable shuffled order spreads a limited free-key batch across years.
    pending.sort(key=lambda x: hashlib.sha256(x[1].encode()).digest())
    db = connection()
    cached = {r[0] for r in db.execute("SELECT key FROM responses WHERE key LIKE 'omdb:%'")}
    selected, requests = [], 0
    for pair in pending:
        if 'omdb:' + pair[1] in cached:
            selected.append(pair)
        elif requests < args.max_requests:
            selected.append(pair)
            requests += 1
    print(f'Checking {len(selected)} films, at most {requests} new OMDb requests.', flush=True)
    filled = 0
    exhausted = False
    errors = []
    def fetch(pair):
        i, imdb = pair
        params = urllib.parse.urlencode({'apikey': key, 'i': imdb, 'type': 'movie'})
        return i, get_json('https://www.omdbapi.com/?' + params, cache_key='omdb:' + imdb)
    with futures.ThreadPoolExecutor(max_workers=4) as pool:
        # Small batches prevent queueing thousands of calls after quota exhaustion.
        for offset in range(0, len(selected), 4):
            batch = [pool.submit(fetch, pair) for pair in selected[offset:offset+4]]
            for job in batch:
                try:
                    i, result = job.result()
                except Exception as error:
                    errors.append(type(error).__name__ + ': ' + str(error))
                    if 'HTTP 401' in str(error) or 'HTTP 403' in str(error):
                        exhausted = True
                        print('OMDb rejected further requests; stopping this batch.', flush=True)
                    continue
                if not result or result.get('Response') == 'False':
                    message = (result or {}).get('Error', 'Empty OMDb response')
                    if 'limit' in message.lower() or 'key' in message.lower():
                        exhausted = True
                        print('OMDb quota or credential issue: ' + message, flush=True)
                    continue
                for rating in result.get('Ratings', []):
                    if rating.get('Source') == 'Rotten Tomatoes':
                        value = rating.get('Value', '')
                        if value.endswith('%') and value[:-1].isdigit() and 0 <= int(value[:-1]) <= 100:
                            rows[i]['RottenTomatoes'] = int(value[:-1])
                            field_sources = json.loads(sources[i]['FieldSources'])
                            field_sources['RottenTomatoes'] = 'OMDb Ratings: Rotten Tomatoes critic percentage'
                            sources[i]['FieldSources'] = json.dumps(field_sources, ensure_ascii=False)
                            sources[i]['MissingFields'] = '; '.join(c for c in COLUMNS if rows[i][c] is None or rows[i][c] == '')
                            filled += 1
            if offset % 100 == 0:
                print(f'Checked {min(offset+4,len(selected))}/{len(selected)}; filled {filled} scores', flush=True)
            if exhausted:
                break
    write_csv(ROOT / 'movies_1970_2025.csv', rows, COLUMNS)
    write_csv(ROOT / 'movie_sources.csv', sources, list(sources[0]))
    coverage = [{'Field': c, 'Present': sum(r[c] is not None and r[c] != '' for r in rows), 'Missing': sum(r[c] is None or r[c] == '' for r in rows), 'Total': len(rows)} for c in COLUMNS]
    write_csv(ROOT / 'field_coverage.csv', coverage, ['Field','Present','Missing','Total'])
    report_path = ROOT / 'collection_report.json'
    report = json.loads(report_path.read_text(encoding='utf-8'))
    report['fields'] = coverage
    report['omdb_last_run'] = {'utc': datetime.now(timezone.utc).isoformat(), 'scores_added': filled, 'quota_or_key_issue': exhausted, 'request_errors': errors}
    report_path.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(f'Added {filled} Rotten Tomatoes scores. Remaining missing: {sum(not r["RottenTomatoes"] and r["RottenTomatoes"] != 0 for r in rows)}. Request errors: {len(errors)}', flush=True)


if __name__ == '__main__':
    main()
