# Movie dataset, 1970–2025

The completed collection contains **13,467 films**, with **3,519 Rotten
Tomatoes critic scores**. The other 9,948 critic scores remain blank after the
available OMDb request allowance was exhausted. Financial collection completed
with zero failed records. The schema, unique IDs, inclusion threshold,
provenance alignment, coverage counts, and calculated fields passed validation.
See `field_coverage.csv` for missing values in every column and
`year_coverage.csv` for the uneven historical coverage (only 15 films in 1970).

`movies_1970_2025.csv` has the 17 requested columns, excluding AudienceScore.
The inclusion rule is **domestic theatrical box office of at least US$100,000**,
with a domestic release/index year from 1970 through 2025 inclusive. Domestic
means the source's U.S./Canada market. International productions with a domestic
release can qualify. This is an observational dataset of available records,
not a guaranteed census of every qualifying film. Historical coverage is much
thinner in the 1970s. Do not interpret missing records as zero-gross films.

## Sources and field definitions

- **TMDB** supplies the preferred title, first listed genre, positive runtime,
  production budget, director, original music composer, and all returned cast
  names in billing order. TMDB's first genre is a deterministic choice rather
  than an assertion that TMDB designates an official primary genre. Full cast
  means all names returned by its credits endpoint, not every person in the
  film's end credits. Multiple directors/composers are separated by semicolons.
- **Box Office History** supplies the qualifying inventory, domestic release
  year, domestic distributor (`LeadStudio`), domestic/international/worldwide
  grosses, and opening weekend figures. It aggregates archived Box Office Mojo
  records and other sources; its per-film source links are retained. Financial
  totals use its `current` snapshot where a positive domestic figure exists,
  otherwise its archived summary. Components from different snapshots are not
  silently mixed. Reported contradictions are flagged in the source CSV.
- When TMDB has no positive budget/runtime or no matching credits, the financial
  source can supply a fallback, explicitly labeled in `movie_sources.csv`.
- **RottenTomatoes** is a 0–100 critic percentage. Initially available scores
  come from the existing class dataset, matched by normalized title and year.
  They are historical, with an unknown collection date. Missing scores remain
  empty; no TMDB or IMDb user rating is substituted.
  `enrich_ratings.py` fills additional gaps through OMDb's `Ratings` entries
  labeled `Rotten Tomatoes`. These responses and their retrieval timestamps
  share the single SQLite cache. Historical class scores are preserved rather
  than overwritten. Free OMDb keys allow 1,000 daily requests; quota exhaustion
  leaves the remaining scores blank, and rerunning later resumes from cache.
- **All monetary fields are nominal USD in whole-dollar units**, unlike the
  old class CSV's million-dollar units. They are not adjusted for inflation.
  Grosses are lifetime/source-snapshot figures and may include rereleases after
  2025; 2025 is the release-cohort cutoff, not a cutoff on earnings.
- **Profitability** = `100 * WorldwideBO / Budget`, a percentage consistent
  with the old class dataset. A value of 400 means gross was four times the
  production budget. It is not an estimate of actual net profit.
- **BOAvgOpenWeekend** = `OpeningWeekend / TheatersOpenWeek`, in USD/theater.
  The opening is the source's initial opening, including limited releases;
  it is not changed to a later wide opening. Theater counts are paired with
  that same gross, never substituted from widest release. A week-one 3-day
  record verifies the summary where available; otherwise the source notes
  explicitly say the 3-day duration was not independently verified.
- Zero or unavailable budgets, runtimes and financials are treated as unknown.
  Missing values are empty CSV cells, never fabricated or imputed.

## Files

- `movies_1970_2025.csv`: analysis dataset, one row per resolved film.
- `movie_sources.csv`: IDs, field sources, financial snapshot date, missing
  fields, warnings, and archived source URLs. Some cells contain structured
  JSON text to preserve multiple sources **inside this single CSV**.
- `field_coverage.csv` / `year_coverage.csv`: nonmissing counts and cohort counts.
- `collection_errors.csv`: failed requests; header only means none failed.
- `merged_aliases.csv`: source records merged using shared IMDb/TMDB IDs.
- `collection_report.json`: one small dataset-wide report.
- `movie_cache.sqlite`: **one cache database for the entire collection**.
  No per-movie JSON files are written. The cache contains raw API responses
  and their fetch timestamps, enabling inspection and resumable reruns.

## Rebuild

Requires Python 3.10+ and no third-party Python packages. Put this locally in
`.env` (ignored by Git; never commit or share it):

```dotenv
TMDB_READ_ACCESS_TOKEN=your_read_access_token
OMDB_API_KEY=your_omdb_key
```

Run from the repository root:

```powershell
.\.venv\Scripts\python.exe 'MovieData P2\build_dataset.py'
.\.venv\Scripts\python.exe 'MovieData P2\enrich_ratings.py'
.\.venv\Scripts\python.exe 'MovieData P2\validate_dataset.py'
```

The collector reuses cached responses. It joins on source-supplied TMDB IDs,
then IMDb ID lookups, rather than fuzzy movie-title searches. Shared IMDb IDs
or TMDB IDs merge duplicate source aliases; explicitly marked rerelease aliases
are excluded from the initial cohort. Unresolved records can use documented
financial-source metadata. Inspect source notes before statistical analysis,
especially when comparing budgets or historical opening weekends.

## Attribution

This product uses the TMDB API but is not endorsed or certified by TMDB.

- TMDB: https://www.themoviedb.org/
- TMDB API: https://developer.themoviedb.org/
- Box Office History API: https://www.boxofficehistory.com/api
- Box Office History source methods: https://www.boxofficehistory.com/about
- Historical critic scores: `../MovieData/HollywoodMovies.csv`
- OMDb: https://www.omdbapi.com/ (CC BY-NC 4.0)

The raw source data retain their respective source terms; this project does
not assert a new redistribution license over them.
