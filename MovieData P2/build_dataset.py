"""Collect 1970–2025 theatrical films; one SQLite cache, no per-film files.

Uses only Python's standard library. Credentials are loaded from .env, never
included in cache keys, logs, provenance, or outputs. Reruns reuse the cache.
"""
import argparse
import concurrent.futures as futures
import csv
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent
COLUMNS = 'Movie,Year,LeadStudio,Genre,RunTime,RottenTomatoes,TheatersOpenWeek,OpeningWeekend,BOAvgOpenWeekend,DomesticBO,ForeignBO,WorldwideBO,Budget,Profitability,Director,Composer,ListofCastMembers'.split(',')
BOH = 'https://www.boxofficehistory.com/api/v1/'
TMDB = 'https://api.themoviedb.org/3/'
LOCAL = threading.local()
LOCK = threading.Lock()


def settings():
    result = dict(os.environ)
    path = ROOT / '.env'
    if path.exists():
        for line in path.read_text(encoding='utf-8-sig').splitlines():
            if '=' in line and not line.lstrip().startswith('#'):
                key, value = line.split('=', 1)
                result[key.strip()] = value.strip().strip('\"').strip("'")
    return result


def connection():
    if not hasattr(LOCAL, 'db'):
        LOCAL.db = sqlite3.connect(ROOT / 'movie_cache.sqlite', timeout=120)
    return LOCAL.db


def get_json(url, cache_key=None, token=None):
    key = cache_key or url
    db = connection()
    row = db.execute('SELECT payload FROM responses WHERE key=?', (key,)).fetchone()
    if row:
        return json.loads(row[0])
    headers = {'User-Agent': 'MovieDataP2 academic dataset collector', 'Accept': 'application/json'}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    for attempt in range(5):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=45) as response:
                data = json.load(response)
            if isinstance(data, dict) and data.get('Response') == 'False' and any(x in data.get('Error', '').lower() for x in ('limit', 'key')):
                return data
            with LOCK:
                db.execute('INSERT OR REPLACE INTO responses VALUES (?,?,?)',
                           (key, json.dumps(data, ensure_ascii=False), datetime.now(timezone.utc).isoformat()))
                db.commit()
            return data
        except urllib.error.HTTPError as error:
            if error.code in (401, 403) and urllib.parse.urlparse(url).netloc == 'www.omdbapi.com':
                try:
                    body = json.loads(error.read())
                    if isinstance(body, dict) and body.get('Response') == 'False':
                        return body
                except (ValueError, OSError):
                    pass
            if error.code in (401, 403):
                raise RuntimeError(f'HTTP {error.code} from {urllib.parse.urlparse(url).netloc}') from None
            if error.code == 404:
                return None
            if error.code not in (429, 500, 502, 503, 504) or attempt == 4:
                raise RuntimeError(f'HTTP {error.code} from {urllib.parse.urlparse(url).netloc}') from None
            time.sleep(min(float(error.headers.get('Retry-After', 2 ** attempt)), 60))
        except (urllib.error.URLError, TimeoutError, OSError):
            if attempt == 4:
                raise RuntimeError('Network request failed after five attempts') from None
            time.sleep(2 ** attempt)


def positive(value):
    return value if isinstance(value, (int, float)) and value > 0 else None


def normalize(title):
    return re.sub(r'[^a-z0-9]', '', (title or '').lower())


def people(records):
    return '; '.join(dict.fromkeys(x['name'] for x in records if x.get('name')))


def collect(item, token):
    film = get_json(BOH + 'movies/' + urllib.parse.quote(item['id']) + '.json')
    if not film:
        return {'item': item, 'error': 'Box-office detail record missing'}
    tmdb_id = (film.get('ids') or {}).get('tmdb')
    imdb_id = (film.get('ids') or {}).get('imdb')
    detail = None
    match = 'unresolved'
    if tmdb_id:
        detail = get_json(TMDB + f'movie/{tmdb_id}?append_to_response=credits,external_ids', token=token)
        match = 'source TMDB ID'
    elif imdb_id:
        found = get_json(TMDB + f'find/{imdb_id}?external_source=imdb_id', token=token)
        results = (found or {}).get('movie_results', [])
        if len(results) == 1:
            tmdb_id = results[0]['id']
            detail = get_json(TMDB + f'movie/{tmdb_id}?append_to_response=credits,external_ids', token=token)
            match = 'IMDb ID lookup'
    # Deliberately avoid fuzzy title joins: a missing credit is better than the wrong film.
    return {'item': item, 'film': film, 'tmdb': detail, 'match': match, 'tmdb_id': tmdb_id}


def row_from(result, legacy):
    film, item, tmdb = result['film'], result['item'], result.get('tmdb') or {}
    warnings = []
    row = dict.fromkeys(COLUMNS)
    sources = {}
    def put(column, value, source):
        if value is not None and value != '':
            row[column] = value
            sources[column] = source
    put('Movie', tmdb.get('title') or film.get('title') or item['t'], 'TMDB' if tmdb.get('title') else 'Box Office History')
    # Cohort year is the domestic release year from the financial index, not a
    # potentially different worldwide premiere year from TMDB.
    put('Year', item['y'], 'Box Office History domestic index year')
    put('LeadStudio', film.get('distributor') or item.get('d'), 'Box Office History domestic distributor')
    put('Genre', (tmdb.get('genres') or [{}])[0].get('name') or film.get('genre'), 'TMDB' if tmdb.get('genres') else 'Box Office History')
    put('RunTime', positive(tmdb.get('runtime')) or positive(film.get('runtimeMin')), 'TMDB' if positive(tmdb.get('runtime')) else 'Box Office History')
    credits = tmdb.get('credits') or {}
    crew = credits.get('crew') or []
    players = film.get('players') or {}
    for col, job, fallback in [('Director', 'Director', 'Director'), ('Composer', 'Original Music Composer', 'Composer')]:
        names = people([p for p in crew if p.get('job') == job])
        put(col, names or people(players.get(fallback) or []), 'TMDB credits' if names else 'Box Office History credits')
    cast = sorted(credits.get('cast') or [], key=lambda x: x.get('order', 999999))
    put('ListofCastMembers', people(cast) or people(players.get('Actor') or []), 'TMDB full returned cast, billing order' if cast else 'Box Office History available cast')
    if not tmdb:
        warnings.append('TMDB metadata unavailable; financial-source metadata used where available')
    source_imdb = (film.get('ids') or {}).get('imdb')
    if source_imdb and tmdb.get('imdb_id') and source_imdb != tmdb['imdb_id']:
        warnings.append('Financial-source IMDb ID differs from TMDB; TMDB IMDb ID retained')
    release = tmdb.get('release_date') or ''
    if release and int(release[:4]) != item['y']:
        warnings.append('TMDB premiere year differs from domestic cohort year')
    current = film.get('current') or {}
    # Never combine a current component with an old component if it would
    # silently create a false total. Select one consistent snapshot first.
    snapshot = current if positive(current.get('domestic')) else film
    domestic = positive(snapshot.get('domestic')) or positive(item.get('g'))
    foreign = positive(snapshot.get('international') if snapshot is current else snapshot.get('foreign'))
    worldwide = positive(snapshot.get('worldwide'))
    financial_source = 'Box Office History current snapshot' if snapshot is current else 'Box Office History archived summary'
    put('DomesticBO', domestic, financial_source)
    put('ForeignBO', foreign, financial_source)
    put('WorldwideBO', worldwide, financial_source)
    if worldwide and domestic and foreign and abs(worldwide - domestic - foreign) > max(1000, worldwide * 0.005):
        warnings.append('Reported worldwide differs from domestic plus foreign by >0.5% or $1000')
    if not worldwide and domestic and foreign:
        put('WorldwideBO', domestic + foreign, 'calculated: DomesticBO + ForeignBO, same snapshot')
    budget = positive(tmdb.get('budget')) or positive(film.get('budget'))
    put('Budget', budget, 'TMDB' if positive(tmdb.get('budget')) else 'Box Office History')
    if budget and row['WorldwideBO']:
        put('Profitability', round(100 * row['WorldwideBO'] / budget, 6), 'calculated: 100 * WorldwideBO / Budget')
    opening = film.get('opening') or {}
    weekend_rows = [w for w in film.get('weekends', []) if w.get('days') == 3 and w.get('week') == 1 and positive(w.get('gross'))]
    weekend_rows.sort(key=lambda w: w.get('start') or '9999')
    first = weekend_rows[0] if weekend_rows else None
    gross = positive(opening.get('gross'))
    theaters = positive(opening.get('theaters'))
    if first and (gross is None or abs(first['gross'] - gross) <= 1):
        gross = first['gross']
        theaters = positive(first.get('theaters')) or theaters
    elif first and gross:
        warnings.append('Opening summary differs from week-one 3-day weekend; opening theater count left blank')
        theaters = None
    put('OpeningWeekend', gross, 'Box Office History opening summary / verified week-one 3-day record')
    put('TheatersOpenWeek', theaters, 'Box Office History opening theater count, same opening gross')
    if gross and theaters:
        put('BOAvgOpenWeekend', round(gross / theaters, 6), 'calculated: OpeningWeekend / TheatersOpenWeek')
    if gross and not first:
        warnings.append('Opening summary provided; 3-day duration not independently verified')
    legacy_row = legacy.get((normalize(row['Movie']), item['y'])) or legacy.get((normalize(item['t']), item['y']))
    if legacy_row and legacy_row.get('RottenTomatoes'):
        score = float(legacy_row['RottenTomatoes'])
        if 0 <= score <= 100:
            put('RottenTomatoes', int(score), 'existing MovieData/HollywoodMovies.csv; historical score, collection date unknown')
    provenance = {'Movie': row['Movie'], 'Year': row['Year'], 'BoxOfficeID': item['id'],
        'IMDbID': tmdb.get('imdb_id') or source_imdb, 'SourceIMDbID': source_imdb, 'TMDBID': result.get('tmdb_id'),
        'TMDBMatch': result.get('match'), 'TMDBPremiereDate': release,
        'FinancialSnapshotDate': current.get('captured') if snapshot is current else '',
        'BoxOfficeURL': BOH + 'movies/' + urllib.parse.quote(item['id']) + '.json',
        'TMDBURL': f'https://www.themoviedb.org/movie/{result["tmdb_id"]}' if result.get('tmdb_id') else '',
        'MissingFields': '; '.join(k for k,v in row.items() if v is None),
        'Warnings': '; '.join(warnings), 'FieldSources': json.dumps(sources, ensure_ascii=False),
        'ArchivedSources': json.dumps(film.get('sources') or [], ensure_ascii=False)}
    return row, provenance


def write_csv(path, rows, fields):
    temporary = path.with_suffix('.tmp')
    with temporary.open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--start-year', type=int, default=1970)
    parser.add_argument('--end-year', type=int, default=2025)
    parser.add_argument('--min-domestic', type=int, default=100000)
    parser.add_argument('--workers', type=int, default=8)
    parser.add_argument('--limit', type=int)
    args = parser.parse_args()
    config = settings()
    token = config.get('TMDB_READ_ACCESS_TOKEN')
    if not token:
        raise SystemExit('Set TMDB_READ_ACCESS_TOKEN in MovieData P2/.env')
    db = connection()
    db.execute('PRAGMA journal_mode=WAL')
    db.execute('CREATE TABLE IF NOT EXISTS responses (key TEXT PRIMARY KEY, payload TEXT NOT NULL, fetched_at TEXT NOT NULL)')
    db.commit()
    # Fail before a large collection if the credential is invalid.
    get_json(TMDB + 'authentication', token=token)
    index = get_json(BOH + 'index/movies.json')
    cohort = [r for r in index if args.start_year <= (r.get('y') or 0) <= args.end_year and (r.get('g') or 0) >= args.min_domestic and not r.get('o')]
    cohort.sort(key=lambda r: (r['y'], r['t']))
    if args.limit:
        cohort = cohort[:args.limit]
    legacy = {}
    with (ROOT.parent / 'MovieData' / 'HollywoodMovies.csv').open(encoding='utf-8-sig', newline='') as stream:
        for row in csv.DictReader(stream):
            legacy[(normalize(row['Movie']), int(row['Year']))] = row
    print(f'Collecting {len(cohort)} candidate films with {args.workers} workers.', flush=True)
    results, errors = [], []
    with futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        jobs = {pool.submit(collect, item, token): item for item in cohort}
        for number, job in enumerate(futures.as_completed(jobs), 1):
            item = jobs[job]
            try:
                result = job.result()
                if result.get('error'):
                    errors.append({'BoxOfficeID': item['id'], 'Movie': item['t'], 'Year': item['y'], 'Error': result['error']})
                else:
                    results.append(result)
            except Exception as error:
                errors.append({'BoxOfficeID': item['id'], 'Movie': item['t'], 'Year': item['y'], 'Error': type(error).__name__ + ': ' + str(error)})
            if number % 250 == 0 or number == len(cohort):
                print(f'Collected {number}/{len(cohort)}; errors {len(errors)}', flush=True)
    # Merge multiple financial aliases of a single IMDb/TMDB movie. Prefer the
    # earliest cohort year, then the record with the strongest domestic gross.
    groups = defaultdict(list)
    for result in results:
        film, item = result['film'], result['item']
        ids = film.get('ids') or {}
        canonical_imdb = (result.get('tmdb') or {}).get('imdb_id') or ids.get('imdb')
        key = ('imdb', canonical_imdb) if canonical_imdb else (('tmdb', result['tmdb_id']) if result.get('tmdb_id') else ('title-year', normalize(item['t']), item['y']))
        groups[key].append(result)
    rows, provenance, duplicates = [], [], []
    for group in groups.values():
        group.sort(key=lambda r: (r['item']['y'], -(r['item'].get('g') or 0)))
        chosen = group[0]
        row, prov = row_from(chosen, legacy)
        if not row['DomesticBO'] or row['DomesticBO'] < args.min_domestic:
            continue
        if len(group) > 1:
            prov['Warnings'] += '; duplicate source aliases merged: ' + ', '.join(r['item']['id'] for r in group[1:])
            duplicates.extend({'KeptID': chosen['item']['id'], 'RemovedID': r['item']['id'], 'Movie': row['Movie']} for r in group[1:])
        rows.append(row)
        provenance.append(prov)
    rows.sort(key=lambda r: (r['Year'], r['Movie']))
    provenance.sort(key=lambda r: (r['Year'], r['Movie']))
    write_csv(ROOT / 'movies_1970_2025.csv', rows, COLUMNS)
    if provenance:
        write_csv(ROOT / 'movie_sources.csv', provenance, list(provenance[0]))
    write_csv(ROOT / 'collection_errors.csv', errors, ['BoxOfficeID','Movie','Year','Error'])
    write_csv(ROOT / 'merged_aliases.csv', duplicates, ['KeptID','RemovedID','Movie'])
    coverage = [{'Field': c, 'Present': sum(r[c] is not None and r[c] != '' for r in rows), 'Missing': sum(r[c] is None or r[c] == '' for r in rows), 'Total': len(rows)} for c in COLUMNS]
    write_csv(ROOT / 'field_coverage.csv', coverage, ['Field','Present','Missing','Total'])
    counts = Counter(r['Year'] for r in rows)
    write_csv(ROOT / 'year_coverage.csv', [{'Year': y, 'Movies': counts[y]} for y in range(args.start_year, args.end_year+1)], ['Year','Movies'])
    report = {'built_at_utc': datetime.now(timezone.utc).isoformat(), 'candidate_records': len(cohort), 'rows': len(rows), 'errors': len(errors), 'merged_aliases': len(duplicates), 'fields': coverage}
    (ROOT / 'collection_report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k != 'fields'}), flush=True)


if __name__ == '__main__':
    main()
