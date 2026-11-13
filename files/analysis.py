"""
Coca-Cola (KO) revenue analysis, 2016 - Q3 2026
Pipeline: load -> clean/validate (pandas) -> SQL (SQLite) -> statistics -> charts -> conclusions
Run:  python analysis.py
"""
import re
import sqlite3
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).parent
DATA, CHARTS = ROOT / "data", ROOT / "charts"
CHARTS.mkdir(exist_ok=True)
RED = "#E4002B"


# ---------------------------------------------------------------- 1. LOAD
quarterly = pd.read_csv(DATA / "ko_quarterly_revenue.csv")
annual = pd.read_csv(DATA / "ko_annual_revenue.csv")
gross_profit = pd.read_csv(DATA / "ko_gross_profit_2021_2025.csv")
ytd = pd.read_csv(DATA / "ko_ytd_nine_months.csv")

# ---------------------------------------------------------------- 2. CLEAN + VALIDATE
print("=== 2. CLEANING & VALIDATION ===")
for name, df in [("quarterly", quarterly), ("annual", annual),
                 ("gross_profit", gross_profit), ("ytd", ytd)]:
    print(f"{name:13s} rows={len(df):3d}  nulls(excluding note)="
          f"{df.drop(columns='note', errors='ignore').isna().sum().sum()}  "
          f"duplicates={df.duplicated().sum()}")

quarterly["period"] = quarterly["year"].astype(str) + "Q" + quarterly["quarter"].astype(str)
quarterly["note"] = quarterly["note"].fillna("")
quarterly = quarterly.sort_values(["year", "quarter"]).reset_index(drop=True)

# Integrity check: the 4 quarters of each full year must add up to the reported annual revenue
check = (quarterly[quarterly["year"] <= 2025].groupby("year")["revenue_musd"].sum()
         .rename("sum_quarters").to_frame().join(annual.set_index("year")))
check["diff"] = check["sum_quarters"] - check["revenue_musd"]
assert (check["diff"] == 0).all(), check
print("OK: quarterly figures add up to annual revenue for all 10 years (2016-2025)")

# Integrity check: Q1+Q2+Q3 2025 must equal the 9-month 2025 figure
nine_2025 = quarterly.query("year == 2025 and quarter <= 3")["revenue_musd"].sum()
assert nine_2025 == ytd.loc[ytd.year == 2025, "revenue_musd"].iloc[0]
print("OK: Q1-Q3 2025 equals the 9-month 2025 figure used for the 2026 comparison\n")

# ---------------------------------------------------------------- 3. SQL (SQLite)
con = sqlite3.connect(":memory:")
quarterly.to_sql("quarterly", con, index=False)
annual.to_sql("annual", con, index=False)
gross_profit.to_sql("gross_profit", con, index=False)
ytd.to_sql("ytd", con, index=False)

sql_text = (ROOT / "queries.sql").read_text()
queries = dict(re.findall(r"-- name: (\w+)\n(.*?)(?=\n-- name:|\Z)", sql_text, flags=re.S))
res = {name: pd.read_sql_query(q, con) for name, q in queries.items()}

print("=== 3. SQL RESULTS ===")
for name, df in res.items():
    print(f"\n-- {name}")
    print(df.to_string(index=False))

# ---------------------------------------------------------------- 4. DESCRIPTIVE STATISTICS
print("\n=== 4. DESCRIPTIVE STATISTICS (annual revenue, USD millions) ===")
rev = annual["revenue_musd"]
growth = res["annual_growth"]["yoy_pct"].dropna()
print(rev.describe().round(0).to_string())
print(f"Coefficient of variation: {rev.std() / rev.mean():.1%}")
print(f"YoY growth: mean={growth.mean():.2f}%  median={growth.median():.2f}%  std={growth.std():.2f}%")

cagr_2016_2025 = (rev.iloc[-1] / rev.iloc[0]) ** (1 / 9) - 1
cagr_2020_2025 = (rev.iloc[-1] / rev.iloc[4]) ** (1 / 5) - 1
slope = np.polyfit(annual["year"].iloc[4:], rev.iloc[4:], 1)[0]
print(f"CAGR 2016-2025: {cagr_2016_2025:.2%}   CAGR 2020-2025: {cagr_2020_2025:.2%}")
print(f"Linear trend 2020-2025: +{slope:,.0f} USD M per year")

# ---------------------------------------------------------------- 5. SMALL FORECAST MODEL
# Seasonal-naive with growth: Q4 2026 = Q4 2025 * (1 + 9-month 2026 growth).
# It's a transparent baseline, not a trained model - see README for limits.
ytd_growth = res["ytd_comparison"]["revenue_growth_pct"].iloc[-1] / 100
q4_2025 = quarterly.query("year == 2025 and quarter == 4")["revenue_musd"].iloc[0]
q4_2026_est = q4_2025 * (1 + ytd_growth)
fy2026_est = ytd.loc[ytd.year == 2026, "revenue_musd"].iloc[0] + q4_2026_est
print("\n=== 5. BASELINE FORECAST ===")
print(f"Q4 2026 estimate: {q4_2026_est:,.0f}  |  FY2026 estimate: {fy2026_est:,.0f} (USD M)")

# Backtest of the same method on 2025: predict Q4 2025 from 9M-2025 growth over 9M-2024
nine_2024 = quarterly.query("year == 2024 and quarter <= 3")["revenue_musd"].sum()
g25 = nine_2025 / nine_2024 - 1
q4_2025_pred = quarterly.query("year == 2024 and quarter == 4")["revenue_musd"].iloc[0] * (1 + g25)
err = (q4_2025_pred - q4_2025) / q4_2025
print(f"Backtest Q4 2025: predicted {q4_2025_pred:,.0f} vs actual {q4_2025:,.0f} (error {err:+.1%})")

# ---------------------------------------------------------------- 6. CHARTS
plt.rcParams.update({"axes.spines.top": False, "axes.spines.right": False, "font.size": 10})

# 6.1 Annual revenue
fig, ax = plt.subplots(figsize=(9, 4.8))
ax.bar(annual["year"], rev / 1000, color=RED)
for x, v in zip(annual["year"], rev / 1000):
    ax.text(x, v + 0.6, f"{v:.1f}", ha="center", fontsize=8)
ax.set(title="Coca-Cola annual net operating revenue", ylabel="USD billions", xticks=annual["year"])
fig.tight_layout(); fig.savefig(CHARTS / "01_annual_revenue.png", dpi=150); plt.close(fig)

# 6.2 YoY growth
g = res["annual_growth"].dropna()
fig, ax = plt.subplots(figsize=(9, 4.5))
ax.bar(g["year"], g["yoy_pct"], color=np.where(g["yoy_pct"] >= 0, "#2E7D32", RED))
ax.axhline(0, color="black", lw=0.8)
ax.set(title="Year-over-year revenue growth (%)", xticks=g["year"], ylabel="%")
fig.tight_layout(); fig.savefig(CHARTS / "02_yoy_growth.png", dpi=150); plt.close(fig)

# 6.3 Quarterly series + rolling 12 months (through 2025) + Q3 2026
q = quarterly.copy()
q["x"] = q["year"] + (q["quarter"] - 1) / 4
t = res["rolling_ttm"].copy(); t["x"] = t["year"] + (t["quarter"] - 1) / 4
fig, ax = plt.subplots(figsize=(10, 4.8))
ax.plot(q["x"][q.year <= 2025], q["revenue_musd"][q.year <= 2025] / 1000, marker="o", ms=3,
        color=RED, label="Quarterly revenue")
ax.scatter(q["x"][q.year == 2026], q["revenue_musd"][q.year == 2026] / 1000, color="black",
           zorder=3, label="Q3 2026")
ax.set(title="Quarterly revenue (USD billions)", ylabel="USD billions")
ax2 = ax.twinx(); ax2.spines["right"].set_visible(True)
ax2.plot(t["x"], t["ttm_musd"] / 1000, color="grey", ls="--", label="Rolling 12 months (right axis)")
ax2.set_ylabel("Rolling 12 months, USD billions")
h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
ax.legend(h1 + h2, l1 + l2, loc="lower left", frameon=False)
fig.tight_layout(); fig.savefig(CHARTS / "03_quarterly_and_rolling.png", dpi=150); plt.close(fig)

# 6.4 Seasonality
s = res["seasonality"]
fig, ax = plt.subplots(figsize=(6, 4.2))
ax.bar(["Q" + str(i) for i in s["quarter"]], s["avg_share_of_year_pct"], color=RED)
ax.axhline(25, color="black", ls=":", lw=1)
for i, v in enumerate(s["avg_share_of_year_pct"]):
    ax.text(i, v + 0.2, f"{v:.1f}%", ha="center")
ax.set(title="Average share of annual revenue by quarter (2016-2025)", ylabel="%", ylim=(20, 28))
fig.tight_layout(); fig.savefig(CHARTS / "04_seasonality.png", dpi=150); plt.close(fig)

# 6.5 Gross margin
m = res["gross_margin"]
fig, ax = plt.subplots(figsize=(6.5, 4.2))
ax.plot(m["year"], m["gross_margin_pct"], marker="o", color=RED)
for x, v in zip(m["year"], m["gross_margin_pct"]):
    ax.text(x, v + 0.25, f"{v}%", ha="center", fontsize=9)
ax.set(title="Gross margin (%) 2021-2025", xticks=m["year"], ylim=(55, 65))
fig.tight_layout(); fig.savefig(CHARTS / "05_gross_margin.png", dpi=150); plt.close(fig)

# ---------------------------------------------------------------- 7. CONCLUSIONS (computed from the data)
best = res["annual_growth"].loc[res["annual_growth"]["yoy_pct"].idxmax()]
worst = res["annual_growth"].loc[res["annual_growth"]["yoy_pct"].idxmin()]
y = res["ytd_comparison"].set_index("year")
peak_q = res["best_and_worst_quarters"].iloc[0]
q2share = s.set_index("quarter").loc[2, "avg_share_of_year_pct"]
q1share = s.set_index("quarter").loc[1, "avg_share_of_year_pct"]
mm = m.set_index("year")["gross_margin_pct"]

conclusions = [
    f"Revenue went from ${rev.iloc[0]/1000:.1f}B (2016) to ${rev.iloc[-1]/1000:.1f}B (2025): "
    f"{rev.iloc[-1]/rev.iloc[0]-1:+.1%} over 9 years, a CAGR of {cagr_2016_2025:.1%}.",
    f"The decade has two distinct phases: decline/trough 2016-2020 (low: ${rev.min()/1000:.1f}B in 2020) "
    f"and recovery since (CAGR {cagr_2020_2025:.1%} for 2020-2025).",
    f"Worst year: {int(worst.year)} ({worst.yoy_pct:+.1f}%); best year: {int(best.year)} ({best.yoy_pct:+.1f}%). "
    f"2021's jump is a rebound from the 2020 pandemic trough, not 'normal' growth.",
    f"Growth has been decelerating: +{growth.iloc[-5]:.1f}% (2021), then {growth.iloc[-4]:+.1f}%, "
    f"{growth.iloc[-3]:+.1f}%, {growth.iloc[-2]:+.1f}%, {growth.iloc[-1]:+.1f}% (2025).",
    f"Seasonality is clear: Q2 is the strongest quarter ({q2share:.1f}% of the year on average) "
    f"and Q1 the weakest ({q1share:.1f}%).",
    f"2026 is accelerating: 9-month revenue is ${y.loc[2026,'revenue_musd']/1000:.1f}B, "
    f"{y.loc[2026,'revenue_growth_pct']:+.1f}% vs the same period of 2025, and Q3 2026 "
    f"(${peak_q.revenue_musd/1000:.2f}B) is the highest of all quarters in the dataset (Q1 and Q2 2026 are not included).",
    f"Profitability is improving: gross margin rose from {mm.loc[2021]}% (2021) to {mm.loc[2025]}% (2025), "
    f"and the 9-month 2026 margin is {y.loc[2026,'gross_margin_pct']}% vs {y.loc[2025,'gross_margin_pct']}% a year earlier.",
    f"A naive baseline projects FY2026 revenue of about ${fy2026_est/1000:.1f}B "
    f"(Q4 2026 ≈ ${q4_2026_est/1000:.1f}B). Backtest error on Q4 2025 was {err:+.1%}.",
    "Caveat: this is company-wide revenue (concentrate sales to bottlers), not retail sales by product or country. "
    "Part of the 2016-2018 decline reflects the company's refranchising of bottling operations, "
    "so the drop is not only a demand effect.",
]
print("\n=== 7. CONCLUSIONS ===")
for i, c in enumerate(conclusions, 1):
    print(f"{i}. {c}")
(ROOT / "conclusions.txt").write_text("\n".join(f"{i}. {c}" for i, c in enumerate(conclusions, 1)))
