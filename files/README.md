# Coca-Cola Revenue Analysis (2016 – Q3 2026)

A small, end-to-end data analysis project: **real public financial data → cleaning with Pandas → SQL (SQLite) → descriptive statistics → charts → conclusions → a simple forecasting baseline.**

## Question

How has The Coca-Cola Company's revenue evolved over the last ten years (2016 → 2026), and what do seasonality, growth and margins tell us?

## Data

All figures are **real, publicly reported** numbers from The Coca-Cola Company (SEC filings / earnings releases), in **USD millions**.

| File | Content | Source |
|---|---|---|
| `data/ko_annual_revenue.csv` | Annual net operating revenue, 2016–2025 | Company filings, via Macrotrends / TickerLeague |
| `data/ko_quarterly_revenue.csv` | Quarterly revenue, 2016 Q1 – 2025 Q4, plus Q3 2026 | Same + Q3 2026 earnings release (27 Oct 2026) |
| `data/ko_gross_profit_2021_2025.csv` | Gross profit, 2021–2025 (rounded to ~$10M) | MarketScreener |
| `data/ko_ytd_nine_months.csv` | 9-month 2025 vs 9-month 2026: revenue, gross profit, consolidated net income | Q3 2026 earnings release |

**Data limitations (please read):**
- This is **company-wide revenue**, mostly concentrate sales to bottlers. Coca-Cola does **not** publish sales by individual product, store or country in a downloadable dataset, so this project cannot answer "how many Coke Zero cans were sold".
- Q2 2019 (`9,997`) is **derived** (annual total minus the other three quarters). It is flagged in the `note` column.
- Q1 and Q2 2026 are not included as individual quarters; 2026 is covered by the 9-month totals and Q3.
- Part of the 2016–2018 decline reflects the company's refranchising of bottling operations, not only lower demand.

## Project structure

```
├── analysis.py          # full pipeline (load → clean → SQL → stats → charts → conclusions)
├── queries.sql          # all SQL queries, named blocks
├── data/                # CSV datasets
├── charts/              # generated figures
├── conclusions.txt      # conclusions generated from the data
├── run_output.txt       # console output of the last run
└── requirements.txt
```

## How to run

```bash
pip install -r requirements.txt
python analysis.py
```

## Method

1. **Cleaning & validation (Pandas):** type checks, nulls, duplicates, period labels, and two integrity checks — the four quarters of every year add up exactly to the reported annual revenue, and Q1–Q3 2025 equals the 9-month 2025 figure.
2. **SQL (SQLite):** window functions for year-over-year growth (`LAG`), rolling 12-month revenue (`SUM() OVER`), seasonality (`JOIN` + `AVG`), gross margin and 2026 vs 2025 comparison.
3. **Descriptive statistics:** mean, median, standard deviation, coefficient of variation, CAGR, linear trend.
4. **Visualizations:** 5 charts in `charts/`.
5. **Forecast baseline:** seasonal-naive with growth (`Q4 2026 = Q4 2025 × (1 + 9-month growth)`). It is intentionally simple and transparent; the backtest on Q4 2025 is a single data point, so treat it as an illustration, not a prediction.

## Key results

1. Revenue went from $41.9B (2016) to $47.9B (2025): +14.5% in 9 years, a CAGR of 1.5%.
2. Two phases: decline/trough 2016–2020 (low of $33.0B in 2020) and recovery since (CAGR 7.7% for 2020–2025).
3. Worst year: 2017 (−13.5%); best year: 2021 (+17.1%), largely a rebound from the 2020 pandemic trough.
4. Growth has been decelerating: +17.1% (2021) → +11.2% → +6.4% → +2.9% → +1.9% (2025).
5. Seasonality: Q2 is the strongest quarter (26.1% of the year on average), Q1 the weakest (24.0%).
6. 2026 is accelerating: 9-month revenue is $39.2B, +8.6% vs 2025, and Q3 2026 ($13.38B) is the highest quarter in the dataset.
7. Gross margin improved from 60.3% (2021) to 61.6% (2025); the 9-month 2026 margin is 63.0% vs 62.1% a year earlier.
8. Naive baseline: FY2026 revenue of about $52.1B (Q4 2026 ≈ $12.8B).
9. Caveat: company-wide revenue, not product-level retail sales.

## Charts

| | |
|---|---|
| ![annual](charts/01_annual_revenue.png) | ![yoy](charts/02_yoy_growth.png) |
| ![quarterly](charts/03_quarterly_and_rolling.png) | ![seasonality](charts/04_seasonality.png) |

## Possible next steps

- Add Q1/Q2 2026 from the 10-Q filings.
- Add segment data (North America, Latin America, EMEA, Asia Pacific) from the 10-K.
- Compare with PepsiCo or Keurig Dr Pepper.
- Replace the baseline with a proper time-series model (e.g. SARIMA / Prophet).
