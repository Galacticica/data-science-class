"""Check the delivered dataset's schema, cohort, joins and derived metrics."""
import csv
import json
import math
from pathlib import Path
from build_dataset import COLUMNS, ROOT


def read(name):
    with (ROOT / name).open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        return reader.fieldnames, list(reader)


def main():
    fields, rows = read('movies_1970_2025.csv')
    assert fields == COLUMNS, 'Output must contain exactly the 17 requested columns'
    assert rows, 'Dataset is empty'
    _, sources = read('movie_sources.csv')
    assert len(rows) == len(sources)
    seen_imdb, seen_tmdb = set(), set()
    for row, source in zip(rows, sources):
        assert (row['Movie'], row['Year']) == (source['Movie'], source['Year']), 'Provenance row mismatch'
        assert 1970 <= int(row['Year']) <= 2025
        assert float(row['DomesticBO']) >= 100000
        for col in ['IMDbID','TMDBID']:
            value = source[col]
            seen = seen_imdb if col == 'IMDbID' else seen_tmdb
            if value:
                assert value not in seen, f'Duplicate {col}: {value}'
                seen.add(value)
        if row['RottenTomatoes']:
            assert 0 <= float(row['RottenTomatoes']) <= 100
        if row['BOAvgOpenWeekend']:
            assert row['OpeningWeekend'] and row['TheatersOpenWeek']
            assert math.isclose(float(row['BOAvgOpenWeekend']), float(row['OpeningWeekend'])/float(row['TheatersOpenWeek']), abs_tol=1e-5)
        if row['Profitability']:
            assert row['WorldwideBO'] and float(row['Budget']) > 0
            assert math.isclose(float(row['Profitability']), 100*float(row['WorldwideBO'])/float(row['Budget']), abs_tol=1e-5)
        expected_missing = '; '.join(c for c in COLUMNS if row[c] == '')
        assert expected_missing == source['MissingFields'], 'Missing-field report is out of date'
        field_sources = json.loads(source['FieldSources'])
        assert all(c in field_sources for c in COLUMNS if row[c] != ''), 'Populated field has no source'
    _, coverage = read('field_coverage.csv')
    for entry in coverage:
        present = sum(r[entry['Field']] != '' for r in rows)
        assert present == int(entry['Present'])
        assert len(rows) - present == int(entry['Missing'])
    print(f'PASS: {len(rows):,} rows, 17 columns, cohort threshold, unique IDs, source alignment, coverage counts, derived metrics.')


if __name__ == '__main__':
    main()
