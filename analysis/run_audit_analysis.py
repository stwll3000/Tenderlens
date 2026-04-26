"""
TenderLens — Comprehensive Audit-Based Analysis
=================================================
Runs all analyses from the audit document against project data.
Produces visualizations and summary statistics.
"""

import pandas as pd
import numpy as np
import json
import re
import sys
import os
import math
from datetime import datetime, timedelta
from pathlib import Path
from collections import Counter

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns

# Add project root to path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

# ============================================================
# THEME
# ============================================================
BG = "#141414"
GRID = "#2E2E2E"
TICK_TEXT = "#C7D2FE"
TITLE_COLOR = "#F3F4F6"
LEGEND_TEXT = "#D1D5DB"
SECONDARY_TEXT = "#9CA3AF"

PRIMARY = "#7A84FF"
SECONDARY = "#F29A45"
TERTIARY = "#A78CFF"
POSITIVE = "#35C89A"
NEGATIVE = "#F53B3A"
LINK_BLUE = "#3EB8ED"
NEUTRAL = "#6F8DA6"

EXTRA_COLORS = ["#DA9165", "#867EAA", "#6FB98C", PRIMARY, SECONDARY, TERTIARY, POSITIVE, NEGATIVE]

def apply_theme(fig, ax):
    fig.patch.set_facecolor(BG)
    if isinstance(ax, np.ndarray):
        for a in ax.flat:
            _style_ax(a)
    else:
        _style_ax(ax)

def _style_ax(ax):
    ax.set_facecolor(BG)
    ax.tick_params(colors=TICK_TEXT, labelsize=10)
    ax.xaxis.label.set_color(TICK_TEXT)
    ax.yaxis.label.set_color(TICK_TEXT)
    ax.title.set_color(TITLE_COLOR)
    ax.spines["bottom"].set_color(GRID)
    ax.spines["left"].set_color(GRID)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", color=GRID, linewidth=0.5, alpha=0.6)

OUT_DIR = ROOT / "analysis" / "output"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================
# LOAD DATA
# ============================================================
data_path = ROOT / "data" / "lots_synthetic_150_audit.json"
with open(data_path, "r", encoding="utf-8") as f:
    raw = json.load(f)

df = pd.DataFrame(raw)
df["initial_price"] = pd.to_numeric(df["initial_price"], errors="coerce")
df["final_price"] = pd.to_numeric(df["final_price"], errors="coerce")
df["price_reduction_pct"] = pd.to_numeric(df["price_reduction_pct"], errors="coerce")
df["participants_count"] = pd.to_numeric(df["participants_count"], errors="coerce")
df["pub_dt"] = pd.to_datetime(df["published_date"], format="%d.%m.%Y", errors="coerce")
df["deadline_dt"] = pd.to_datetime(df["deadline_date"], format="%d.%m.%Y", errors="coerce")
df["deadline_days"] = (df["deadline_dt"] - df["pub_dt"]).dt.days

print(f"Loaded {len(df)} lots")
print(f"Columns: {list(df.columns)}")

# ============================================================
# 1. DATA QUALITY GAP ANALYSIS
# ============================================================
print("\n" + "="*60)
print("1. DATA QUALITY GAP ANALYSIS")
print("="*60)

fields_audit = {
    "initial_price": "НМЦ (начальная максимальная цена)",
    "final_price": "Итоговая цена (из протокола)",
    "price_reduction_pct": "Снижение цены α, %",
    "participants_count": "Число участников",
    "okpd2_codes": "ОКПД2 коды",
    "published_date": "Дата публикации",
    "deadline_date": "Дата дедлайна",
}

quality_stats = []
for col, label in fields_audit.items():
    total = len(df)
    non_null = df[col].notna().sum()
    if col == "okpd2_codes":
        # JSON string — check non-empty
        non_null = df[col].apply(lambda x: x is not None and x != "" and x != "null").sum()
    pct = non_null / total * 100
    quality_stats.append({
        "field": col,
        "label": label,
        "filled": int(non_null),
        "total": total,
        "pct_filled": round(pct, 1),
        "pct_missing": round(100 - pct, 1),
    })
    print(f"  {label}: {non_null}/{total} ({pct:.1f}% filled)")

quality_df = pd.DataFrame(quality_stats)

# -- Chart 1: Data Quality Gaps --
fig, ax = plt.subplots(figsize=(12, 6))
apply_theme(fig, ax)

bars_filled = ax.barh(quality_df["label"], quality_df["pct_filled"], color=PRIMARY, label="Заполнено")
bars_missing = ax.barh(quality_df["label"], quality_df["pct_missing"], left=quality_df["pct_filled"], color=NEGATIVE, alpha=0.6, label="Пусто / NULL")

for bar, pct in zip(bars_filled, quality_df["pct_filled"]):
    if pct > 10:
        ax.text(bar.get_width() - 3, bar.get_y() + bar.get_height()/2, f"{pct:.0f}%",
                ha="right", va="center", color="white", fontweight="bold", fontsize=10)

ax.set_xlabel("Процент заполненности (%)", fontsize=12)
ax.set_title("Заполненность ключевых полей (Аудит: гэп данных)", fontsize=14, fontweight="bold", color=TITLE_COLOR)
ax.legend(loc="lower right", facecolor=BG, edgecolor=GRID, labelcolor=LEGEND_TEXT)
ax.set_xlim(0, 100)
fig.tight_layout()
fig.savefig(OUT_DIR / "01_data_quality_gaps.png", dpi=150, facecolor=BG)
plt.close(fig)
print(f"  -> Chart saved: 01_data_quality_gaps.png")


# ============================================================
# 2. PRICE DISTRIBUTION ANALYSIS
# ============================================================
print("\n" + "="*60)
print("2. PRICE DISTRIBUTION ANALYSIS")
print("="*60)

prices = df["initial_price"].dropna()
print(f"  Count: {len(prices)}")
print(f"  Mean: {prices.mean():,.0f} ₽")
print(f"  Median: {prices.median():,.0f} ₽")
print(f"  Std: {prices.std():,.0f} ₽")
print(f"  Min: {prices.min():,.0f} ₽")
print(f"  Max: {prices.max():,.0f} ₽")
print(f"  Skewness: {prices.skew():.2f}")

# IQR outlier detection
q1, q3 = prices.quantile(0.25), prices.quantile(0.75)
iqr = q3 - q1
lower = q1 - 1.5 * iqr
upper = q3 + 1.5 * iqr
outliers = prices[(prices < lower) | (prices > upper)]
print(f"  IQR outliers: {len(outliers)} ({len(outliers)/len(prices)*100:.1f}%)")

# -- Chart 2: Price distribution (log scale) --
fig, axes = plt.subplots(1, 2, figsize=(14, 6))
apply_theme(fig, axes)

# Histogram
log_prices = np.log10(prices.clip(lower=1))
axes[0].hist(log_prices, bins=30, color=PRIMARY, edgecolor=BG, alpha=0.9)
axes[0].axvline(np.log10(prices.median()), color=POSITIVE, linestyle="--", linewidth=2, label=f"Медиана: {prices.median():,.0f} ₽")
axes[0].axvline(np.log10(prices.mean()), color=SECONDARY, linestyle="--", linewidth=2, label=f"Среднее: {prices.mean():,.0f} ₽")
axes[0].set_xlabel("log₁₀(НМЦ, ₽)", fontsize=12)
axes[0].set_ylabel("Количество лотов", fontsize=12)
axes[0].set_title("Распределение НМЦ (логарифмическая шкала)", fontsize=13, fontweight="bold")
axes[0].legend(facecolor=BG, edgecolor=GRID, labelcolor=LEGEND_TEXT, fontsize=9)

# Box by region
region_data = [df[df["region_name"] == r]["initial_price"].dropna() for r in df["region_name"].unique()]
region_labels = df["region_name"].unique()
bp = axes[1].boxplot(region_data, labels=[r[:15] for r in region_labels], patch_artist=True, vert=True)
colors_bp = [PRIMARY, SECONDARY, TERTIARY]
for patch, color in zip(bp["boxes"], colors_bp):
    patch.set_facecolor(color)
    patch.set_alpha(0.7)
for median in bp["medians"]:
    median.set_color(POSITIVE)
    median.set_linewidth(2)
for whisker in bp["whiskers"]:
    whisker.set_color(TICK_TEXT)
for cap in bp["caps"]:
    cap.set_color(TICK_TEXT)
for flier in bp["fliers"]:
    flier.set_markeredgecolor(NEGATIVE)
    
axes[1].set_ylabel("НМЦ, ₽", fontsize=12)
axes[1].set_title("Распределение НМЦ по регионам", fontsize=13, fontweight="bold")
axes[1].yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, p: f"{x/1e6:.1f}M" if x >= 1e6 else f"{x/1e3:.0f}K"))

fig.suptitle("Анализ ценообразования — текущее состояние", fontsize=15, fontweight="bold", color=TITLE_COLOR, y=1.02)
fig.tight_layout()
fig.savefig(OUT_DIR / "02_price_distribution.png", dpi=150, facecolor=BG, bbox_inches="tight")
plt.close(fig)
print(f"  -> Chart saved: 02_price_distribution.png")


# ============================================================
# 3. HHI ANALYSIS (AUDIT VALIDATION)
# ============================================================
print("\n" + "="*60)
print("3. HHI ANALYSIS — AUDIT VALIDATION")
print("="*60)

# Current implementation: HHI by CUSTOMERS (audit says this is wrong direction)
customer_volumes = df.groupby("customer_name")["initial_price"].sum()
total_vol = customer_volumes.sum()
customer_shares = (customer_volumes / total_vol * 100)
hhi_customers = (customer_shares ** 2).sum()
n_eff_customers = 1 / ((customer_shares / 100) ** 2).sum() if customer_shares.sum() > 0 else 0

print(f"  HHI по ЗАКАЗЧИКАМ (текущая реализация):")
print(f"    HHI = {hhi_customers:.1f}")
print(f"    N_eff = {n_eff_customers:.1f}")
print(f"    Интерпретация: {'Конкурентный' if hhi_customers < 1000 else 'Умеренная концентрация' if hhi_customers < 1800 else 'Олигополия'}")
print()
print(f"  ⚠️  ПРОБЛЕМА (из аудита):")
print(f"    HHI считается по заказчикам, а не по поставщикам.")
print(f"    Для МСБ-поставщика нужен HHI по ПОСТАВЩИКАМ в нише.")
print(f"    Невозможно рассчитать: таблица suppliers ОТСУТСТВУЕТ.")
print()

# What we CAN show: customer concentration
top5_customers = customer_shares.nlargest(5)
print(f"  Топ-5 заказчиков (% от объёма):")
for name, share in top5_customers.items():
    print(f"    {name[:50]}: {share:.1f}%")

# -- Chart 3: HHI comparison --
fig, axes = plt.subplots(1, 2, figsize=(14, 6))
apply_theme(fig, axes)

# Customer concentration pie
top10 = customer_shares.nlargest(10)
others = pd.Series({"Остальные": 100 - top10.sum()})
pie_data = pd.concat([top10, others])
colors_pie = EXTRA_COLORS[:len(pie_data)]

wedges, texts, autotexts = axes[0].pie(
    pie_data.values, 
    labels=None,
    autopct=lambda p: f"{p:.1f}%" if p > 3 else "",
    colors=colors_pie,
    startangle=90,
    textprops={"color": TITLE_COLOR, "fontsize": 9}
)
axes[0].set_title("HHI по заказчикам\n(текущая реализация — НЕПРАВИЛЬНО)", 
                   fontsize=12, fontweight="bold", color=NEGATIVE)
legend_labels = [f"{n[:25]}..." if len(n) > 25 else n for n in pie_data.index]
axes[0].legend(wedges, legend_labels, loc="center left", bbox_to_anchor=(-0.3, 0.5), 
               fontsize=7, facecolor=BG, edgecolor=GRID, labelcolor=LEGEND_TEXT)

# What's needed: supplier concentration (empty)
axes[1].text(0.5, 0.5, "НЕТ ДАННЫХ\n\nТаблица suppliers\nотсутствует\n\n→ Нужен парсер\nпротоколов итогов",
             ha="center", va="center", fontsize=14, color=NEGATIVE, 
             fontweight="bold", transform=axes[1].transAxes,
             bbox=dict(boxstyle="round,pad=1", facecolor=BG, edgecolor=NEGATIVE, linewidth=2))
axes[1].set_title("HHI по поставщикам в нише\n(НУЖНО для Profit Score)", 
                   fontsize=12, fontweight="bold", color=POSITIVE)
axes[1].set_xticks([])
axes[1].set_yticks([])

fig.suptitle("Аудит: HHI считается не в ту сторону", fontsize=15, fontweight="bold", color=TITLE_COLOR, y=1.02)
fig.tight_layout()
fig.savefig(OUT_DIR / "03_hhi_comparison.png", dpi=150, facecolor=BG, bbox_inches="tight")
plt.close(fig)
print(f"  -> Chart saved: 03_hhi_comparison.png")


# ============================================================
# 4. TIMING / DEADLINE ANALYSIS
# ============================================================
print("\n" + "="*60)
print("4. TIMING & DEADLINE ANALYSIS")
print("="*60)

dd = df["deadline_days"].dropna()
print(f"  Средний срок подачи: {dd.mean():.1f} дней")
print(f"  Медианный срок: {dd.median():.0f} дней")

# Deadline ranges
ranges = [(0, 3, "Срочные (0-3)"), (4, 7, "Короткие (4-7)"), 
          (8, 14, "Стандартные (8-14)"), (15, 30, "Длинные (15-30)"), (31, 999, ">30 дней")]
for lo, hi, label in ranges:
    cnt = ((dd >= lo) & (dd <= hi)).sum()
    print(f"    {label}: {cnt} ({cnt/len(dd)*100:.1f}%)")

# Timing signal (from audit's profit.py spec)
def timing_signal(days):
    if days is None or np.isnan(days): return 0.5
    if days < 3: return 0.20
    if days < 7: return 0.85
    if days <= 14: return 0.95
    if days <= 30: return 0.65
    return 0.40

df["timing_signal"] = df["deadline_days"].apply(timing_signal)

# -- Chart 4: Deadline distribution + timing signal --
fig, axes = plt.subplots(1, 2, figsize=(14, 6))
apply_theme(fig, axes)

# Histogram of deadline days
axes[0].hist(dd, bins=20, color=PRIMARY, edgecolor=BG, alpha=0.9)
axes[0].axvline(7, color=POSITIVE, linestyle="--", linewidth=2, label="Оптимум 7-14 дней")
axes[0].axvline(14, color=POSITIVE, linestyle="--", linewidth=2)
axes[0].axvspan(7, 14, alpha=0.1, color=POSITIVE)
axes[0].set_xlabel("Дней на подачу заявки", fontsize=12)
axes[0].set_ylabel("Количество лотов", fontsize=12)
axes[0].set_title("Распределение сроков подачи", fontsize=13, fontweight="bold")
axes[0].legend(facecolor=BG, edgecolor=GRID, labelcolor=LEGEND_TEXT)

# Timing signal distribution
signal_vals = df["timing_signal"].dropna()
axes[1].hist(signal_vals, bins=15, color=TERTIARY, edgecolor=BG, alpha=0.9)
axes[1].axvline(signal_vals.mean(), color=SECONDARY, linestyle="--", linewidth=2, 
                label=f"Среднее: {signal_vals.mean():.2f}")
axes[1].set_xlabel("Timing Signal (0-1)", fontsize=12)
axes[1].set_ylabel("Количество лотов", fontsize=12)
axes[1].set_title("Распределение Timing Signal (компонент D)", fontsize=13, fontweight="bold")
axes[1].legend(facecolor=BG, edgecolor=GRID, labelcolor=LEGEND_TEXT)

fig.suptitle("Временной анализ — готовность к Profit Score", fontsize=15, fontweight="bold", color=TITLE_COLOR, y=1.02)
fig.tight_layout()
fig.savefig(OUT_DIR / "04_timing_analysis.png", dpi=150, facecolor=BG, bbox_inches="tight")
plt.close(fig)
print(f"  -> Chart saved: 04_timing_analysis.png")

# ============================================================
# 5. OKPD2 NORMALIZATION ANALYSIS
# ============================================================
print("\n" + "="*60)
print("5. OKPD2 NORMALIZATION ANALYSIS")
print("="*60)

def parse_okpd2(codes_str):
    try:
        codes = json.loads(codes_str) if codes_str else []
        return codes if isinstance(codes, list) else []
    except:
        return []

df["okpd2_parsed"] = df["okpd2_codes"].apply(parse_okpd2)
df["okpd2_count"] = df["okpd2_parsed"].apply(len)
df["okpd2_prefix2"] = df["okpd2_parsed"].apply(lambda x: x[0][:2] if x else None)

print(f"  Лоты с ОКПД2: {(df['okpd2_count'] > 0).sum()} ({(df['okpd2_count'] > 0).mean()*100:.1f}%)")
print(f"  Уникальных ОКПД2 кодов: {len(set(c for codes in df['okpd2_parsed'] for c in codes))}")
print(f"  Уникальных 2-digit prefix: {df['okpd2_prefix2'].nunique()}")
print(f"\n  ⚠️  ПРОБЛЕМА (из аудита):")
print(f"    ОКПД2 хранится как JSON-строка, нет нормализации.")
print(f"    Нет маппинга ОКПД2 → niche_slug.")
print(f"    Невозможно построить price benchmark по нише.")

# Niche mapping simulation (from audit)
NICHE_MAP = {
    "med-rashodniki": ["32.50", "21.20"],
    "it-oborudovanie": ["26.20", "27.20"],
    "siz": ["14.12", "32.99"],
    "kanc": ["17.23"],
    "klining-uslugi": ["81.21", "81.22"],
    "remont": ["41.20", "43.31", "43.91"],
    "pitanie": ["10.11", "10.51"],
    "ohrana": ["80.10"],
    "transport": ["49.41"],
    "mebel": ["31.01", "31.09"],
    "it-uslugi": ["62.09", "95.11"],
    "hoztovary": ["20.41"],
    "blagoustroistvo": ["81.30"],
    "specodezhda": ["15.20"],
    "lift": ["33.12"],
}

def classify_niche(codes):
    for niche, prefixes in NICHE_MAP.items():
        for code in codes:
            for prefix in prefixes:
                if code.startswith(prefix):
                    return niche
    return "other"

df["niche_slug"] = df["okpd2_parsed"].apply(classify_niche)
niche_dist = df["niche_slug"].value_counts()
print(f"\n  Распределение по нишам (после маппинга):")
for niche, cnt in niche_dist.items():
    print(f"    {niche}: {cnt} ({cnt/len(df)*100:.1f}%)")

# -- Chart 5: OKPD2 / Niche distribution --
fig, axes = plt.subplots(1, 2, figsize=(14, 6))
apply_theme(fig, axes)

# OKPD2 prefix distribution
prefix_counts = df["okpd2_prefix2"].value_counts().head(12)
bars = axes[0].barh(prefix_counts.index[::-1], prefix_counts.values[::-1], color=PRIMARY)
axes[0].set_xlabel("Количество лотов", fontsize=12)
axes[0].set_title("Топ ОКПД2 (2-digit prefix)", fontsize=13, fontweight="bold")

# Niche distribution
niche_top = niche_dist.head(10)
colors_niche = EXTRA_COLORS[:len(niche_top)]
axes[1].barh(niche_top.index[::-1], niche_top.values[::-1], color=colors_niche[::-1])
axes[1].set_xlabel("Количество лотов", fontsize=12)
axes[1].set_title("Распределение по нишам\n(после маппинга ОКПД2→niche)", fontsize=13, fontweight="bold")

fig.suptitle("ОКПД2 нормализация — текущее состояние vs. нужное", fontsize=15, fontweight="bold", color=TITLE_COLOR, y=1.02)
fig.tight_layout()
fig.savefig(OUT_DIR / "05_okpd2_niche.png", dpi=150, facecolor=BG, bbox_inches="tight")
plt.close(fig)
print(f"  -> Chart saved: 05_okpd2_niche.png")


# ============================================================
# 6. SPEC PURITY — RIGGED DETECTOR ANALYSIS
# ============================================================
print("\n" + "="*60)
print("6. SPEC PURITY — RIGGED DETECTOR")
print("="*60)

RIGGED_PATTERNS = [
    (r"опыт.*не\s*менее\s*([5-9]|1[0-9])\s*(лет|года)", "long_experience_required"),
    (r"наличи[ея]\s*св-?ва?\s*СРО", "rare_sro"),
    (r"(наличие|свидетельство)\s*(свидетельства\s*)?СРО", "rare_sro2"),
    (r"конкретн[аы][ея]?\s*модел[ьи]", "specific_model"),
    (r"производител[ья]\s*[A-ZА-Я]", "specific_manufacturer"),
    (r"эквивалент\s*не\s*допуск", "no_equivalent"),
    (r"должен\s*находиться\s*в\s*", "geo_lock"),
]

def detect_rigging(text):
    text_lower = text.lower()
    flags = []
    for pattern, flag in RIGGED_PATTERNS:
        if re.search(pattern, text_lower):
            flags.append(flag)
    return flags

df["rigging_flags"] = df["object_name"].apply(detect_rigging)
df["rigging_count"] = df["rigging_flags"].apply(len)
df["is_rigged"] = df["rigging_count"] > 0

print(f"  Лоты с признаками «заточки»: {df['is_rigged'].sum()} ({df['is_rigged'].mean()*100:.1f}%)")
all_flags = [f for flags in df["rigging_flags"] for f in flags]
flag_counts = Counter(all_flags)
for flag, cnt in flag_counts.most_common():
    print(f"    {flag}: {cnt}")

# Spec purity signal
def spec_purity_signal(n_penalties):
    if n_penalties == 0: return 0.95
    if n_penalties == 1: return 0.55
    if n_penalties == 2: return 0.25
    return 0.05

df["spec_purity_signal"] = df["rigging_count"].apply(spec_purity_signal)

# -- Chart 6: Rigging detection --
fig, axes = plt.subplots(1, 2, figsize=(14, 6))
apply_theme(fig, axes)

# Rigging flags bar
if flag_counts:
    flags_df = pd.DataFrame(list(flag_counts.items()), columns=["flag", "count"]).sort_values("count")
    axes[0].barh(flags_df["flag"], flags_df["count"], color=NEGATIVE)
    axes[0].set_xlabel("Количество лотов", fontsize=12)
    axes[0].set_title("Обнаруженные паттерны «заточки»", fontsize=13, fontweight="bold")
else:
    axes[0].text(0.5, 0.5, "Нет обнаруженных паттернов", ha="center", va="center", 
                 color=TICK_TEXT, fontsize=14, transform=axes[0].transAxes)
    axes[0].set_title("Обнаруженные паттерны «заточки»", fontsize=13, fontweight="bold")

# Spec purity distribution
vals = df["spec_purity_signal"].value_counts().sort_index()
axes[1].bar(vals.index.astype(str), vals.values, color=[POSITIVE if v > 0.5 else SECONDARY if v > 0.2 else NEGATIVE for v in vals.index])
axes[1].set_xlabel("Spec Purity Signal", fontsize=12)
axes[1].set_ylabel("Количество лотов", fontsize=12)
axes[1].set_title("Распределение Spec Purity Signal (компонент E)", fontsize=13, fontweight="bold")

fig.suptitle("Детектор «заточки» — Компонент Profit Score", fontsize=15, fontweight="bold", color=TITLE_COLOR, y=1.02)
fig.tight_layout()
fig.savefig(OUT_DIR / "06_rigged_detector.png", dpi=150, facecolor=BG, bbox_inches="tight")
plt.close(fig)
print(f"  -> Chart saved: 06_rigged_detector.png")


# ============================================================
# 7. PROFIT SCORE FEASIBILITY — WHAT CAN BE COMPUTED NOW
# ============================================================
print("\n" + "="*60)
print("7. PROFIT SCORE FEASIBILITY")
print("="*60)

components = {
    "A: Margin Signal": {
        "requires": "price_benchmarks (медианная НМЦ по нише)",
        "available": False,
        "reason": "Нет таблицы price_benchmarks, нет niche_slug"
    },
    "B: Competition Signal": {
        "requires": "suppliers + lot_participations (уникальные поставщики)",
        "available": False,
        "reason": "Нет таблицы suppliers, participants_count пуст у 89% лотов"
    },
    "C: Captive Signal": {
        "requires": "lot_participations + suppliers (история побед по заказчику)",
        "available": False,
        "reason": "Нет данных о поставщиках и победителях"
    },
    "D: Timing Signal": {
        "requires": "published_date + deadline_date",
        "available": True,
        "reason": "Даты есть, можно рассчитать прямо сейчас"
    },
    "E: Spec Purity Signal": {
        "requires": "object_name + tz_text (текст ТЗ)",
        "available": True,  # partial
        "reason": "Можно по object_name (базово); для полного — нужен tz_text"
    },
    "F: Customer Health": {
        "requires": "ИНН → ЕГРЮЛ/DaData + РНП + арбитражи",
        "available": False,
        "reason": "ИНН не парсится, нет обогащения данных"
    },
}

available_count = sum(1 for c in components.values() if c["available"])
total_components = len(components)
print(f"  Компонентов Profit Score: {total_components}")
print(f"  Доступно для расчёта: {available_count}/{total_components}")
print(f"  Недоступно: {total_components - available_count}/{total_components}")

for name, info in components.items():
    status = "✅" if info["available"] else "❌"
    print(f"    {status} {name}")
    print(f"       Требует: {info['requires']}")
    print(f"       Статус: {info['reason']}")

# Simulated partial Profit Score (only D + E)
df["partial_profit_score"] = (
    df["timing_signal"] * 0.10 / 0.20 +  # re-weight D
    df["spec_purity_signal"] * 0.10 / 0.20  # re-weight E
) * 100

# -- Chart 7: Profit Score feasibility --
fig, axes = plt.subplots(1, 2, figsize=(14, 7))
apply_theme(fig, axes)

# Component availability
comp_names = list(components.keys())
comp_avail = [1 if components[c]["available"] else 0 for c in comp_names]
weights = [0.30, 0.25, 0.15, 0.10, 0.10, 0.10]
colors_avail = [POSITIVE if a else NEGATIVE for a in comp_avail]

bars = axes[0].barh(comp_names[::-1], [w*100 for w in weights[::-1]], color=colors_avail[::-1])
axes[0].set_xlabel("Вес в Profit Score (%)", fontsize=12)
axes[0].set_title("Компоненты Profit Score:\nдоступность данных", fontsize=13, fontweight="bold")
# Add labels
for bar, avail in zip(bars, comp_avail[::-1]):
    label = "ДОСТУПЕН" if avail else "НЕТ ДАННЫХ"
    axes[0].text(bar.get_width() + 0.5, bar.get_y() + bar.get_height()/2,
                 label, va="center", fontsize=9, color=POSITIVE if avail else NEGATIVE, fontweight="bold")
axes[0].set_xlim(0, 40)

# Partial profit score distribution
axes[1].hist(df["partial_profit_score"].dropna(), bins=20, color=TERTIARY, edgecolor=BG, alpha=0.9)
axes[1].axvline(df["partial_profit_score"].mean(), color=SECONDARY, linestyle="--", linewidth=2,
                label=f"Среднее: {df['partial_profit_score'].mean():.1f}")
axes[1].set_xlabel("Partial Profit Score (D+E only)", fontsize=12)
axes[1].set_ylabel("Количество лотов", fontsize=12)
axes[1].set_title("Частичный Profit Score\n(только Timing + Spec Purity)", fontsize=13, fontweight="bold")
axes[1].legend(facecolor=BG, edgecolor=GRID, labelcolor=LEGEND_TEXT)

fig.suptitle("Profit Score — текущая готовность", fontsize=15, fontweight="bold", color=TITLE_COLOR, y=1.02)
fig.tight_layout()
fig.savefig(OUT_DIR / "07_profit_score_feasibility.png", dpi=150, facecolor=BG, bbox_inches="tight")
plt.close(fig)
print(f"  -> Chart saved: 07_profit_score_feasibility.png")


# ============================================================
# 8. FINAL_PRICE / PARTICIPANTS_COUNT COVERAGE
# ============================================================
print("\n" + "="*60)
print("8. PROTOCOL DATA COVERAGE")
print("="*60)

# By status
status_coverage = df.groupby("status").agg(
    total=("reg_number", "count"),
    has_final_price=("final_price", lambda x: x.notna().sum()),
    has_participants=("participants_count", lambda x: x.notna().sum()),
).reset_index()
status_coverage["final_price_pct"] = (status_coverage["has_final_price"] / status_coverage["total"] * 100).round(1)
status_coverage["participants_pct"] = (status_coverage["has_participants"] / status_coverage["total"] * 100).round(1)

print(status_coverage.to_string(index=False))

# For completed lots specifically
completed = df[df["status"].isin(["Определение поставщика завершено", "Закупка завершена"])]
print(f"\n  Завершённые лоты: {len(completed)}")
print(f"  С final_price: {completed['final_price'].notna().sum()} ({completed['final_price'].notna().mean()*100:.1f}%)")
print(f"  С participants_count: {completed['participants_count'].notna().sum()} ({completed['participants_count'].notna().mean()*100:.1f}%)")
print(f"  ⚠️  Аудит KPI: final_price покрытие должно быть ≥80% для завершённых лотов")

# Price reduction stats (where available)
with_alpha = df[df["price_reduction_pct"].notna()]
if len(with_alpha) > 0:
    print(f"\n  Снижение цены α (где есть данные, n={len(with_alpha)}):")
    print(f"    Среднее α: {with_alpha['price_reduction_pct'].mean():.1f}%")
    print(f"    Медиана α: {with_alpha['price_reduction_pct'].median():.1f}%")
    print(f"    Мин α: {with_alpha['price_reduction_pct'].min():.1f}%")
    print(f"    Макс α: {with_alpha['price_reduction_pct'].max():.1f}%")

# -- Chart 8: Protocol coverage by status --
fig, axes = plt.subplots(1, 2, figsize=(14, 6))
apply_theme(fig, axes)

x = np.arange(len(status_coverage))
width = 0.35
axes[0].bar(x - width/2, status_coverage["final_price_pct"], width, label="final_price", color=PRIMARY)
axes[0].bar(x + width/2, status_coverage["participants_pct"], width, label="participants_count", color=SECONDARY)
axes[0].set_xticks(x)
axes[0].set_xticklabels([s[:20] for s in status_coverage["status"]], rotation=30, ha="right", fontsize=9)
axes[0].set_ylabel("% заполненности", fontsize=12)
axes[0].set_title("Покрытие данных протоколов по статусу", fontsize=13, fontweight="bold")
axes[0].legend(facecolor=BG, edgecolor=GRID, labelcolor=LEGEND_TEXT)
axes[0].axhline(80, color=POSITIVE, linestyle="--", linewidth=1.5, alpha=0.7, label="Цель аудита: 80%")
axes[0].legend(facecolor=BG, edgecolor=GRID, labelcolor=LEGEND_TEXT, fontsize=9)

# Alpha distribution
if len(with_alpha) > 0:
    axes[1].hist(with_alpha["price_reduction_pct"], bins=15, color=POSITIVE, edgecolor=BG, alpha=0.9)
    axes[1].axvline(with_alpha["price_reduction_pct"].median(), color=SECONDARY, linestyle="--", linewidth=2,
                    label=f"Медиана: {with_alpha['price_reduction_pct'].median():.1f}%")
    axes[1].set_xlabel("Снижение цены α, %", fontsize=12)
    axes[1].set_ylabel("Количество лотов", fontsize=12)
    axes[1].set_title(f"Распределение α (n={len(with_alpha)} из {len(df)})", fontsize=13, fontweight="bold")
    axes[1].legend(facecolor=BG, edgecolor=GRID, labelcolor=LEGEND_TEXT)
else:
    axes[1].text(0.5, 0.5, "НЕТ ДАННЫХ", ha="center", va="center", fontsize=18, color=NEGATIVE, transform=axes[1].transAxes)

fig.suptitle("Данные протоколов — главный гэп для Profit Score", fontsize=15, fontweight="bold", color=TITLE_COLOR, y=1.02)
fig.tight_layout()
fig.savefig(OUT_DIR / "08_protocol_coverage.png", dpi=150, facecolor=BG, bbox_inches="tight")
plt.close(fig)
print(f"  -> Chart saved: 08_protocol_coverage.png")


# ============================================================
# 9. CUSTOMER REPEAT PATTERNS
# ============================================================
print("\n" + "="*60)
print("9. CUSTOMER REPEAT PATTERNS")
print("="*60)

customer_lots = df.groupby("customer_name").agg(
    lot_count=("reg_number", "count"),
    avg_price=("initial_price", "mean"),
    total_volume=("initial_price", "sum"),
    regions=("region_name", "nunique"),
).reset_index().sort_values("lot_count", ascending=False)

repeat_customers = customer_lots[customer_lots["lot_count"] >= 3]
print(f"  Заказчиков с ≥3 лотов: {len(repeat_customers)} ({len(repeat_customers)/len(customer_lots)*100:.1f}%)")
print(f"  Их лоты: {repeat_customers['lot_count'].sum()} ({repeat_customers['lot_count'].sum()/len(df)*100:.1f}% от всех)")
print(f"\n  ⚠️  Аудит: «повторяемость» заказчика — потенциальное «золото» для МСБ")
print(f"    Но без niche_slug и supplier history нельзя определить «похожие» лоты")


# ============================================================
# 10. OVERALL SUMMARY — AUDIT SCORECARD
# ============================================================
print("\n" + "="*60)
print("10. AUDIT SCORECARD")
print("="*60)

scorecard = [
    {"issue": "final_price покрытие (завершённые лоты)", "current": f"{completed['final_price'].notna().mean()*100:.0f}%", "target": "≥80%", "gap": "critical"},
    {"issue": "participants_count (уникальные ИНН)", "current": "0%", "target": "≥80%", "gap": "critical"},
    {"issue": "Таблица suppliers", "current": "Отсутствует", "target": "Создана и наполнена", "gap": "critical"},
    {"issue": "Таблица lot_participations", "current": "Отсутствует", "target": "Создана и наполнена", "gap": "critical"},
    {"issue": "niche_slug на лотах", "current": "0%", "target": "≥95%", "gap": "high"},
    {"issue": "Price benchmark по нише", "current": "Отсутствует", "target": "Ежедневный расчёт", "gap": "high"},
    {"issue": "Profit Score", "current": "0% (2/6 компонентов)", "target": "100% активных лотов", "gap": "critical"},
    {"issue": "HHI по поставщикам", "current": "HHI по заказчикам (неверно)", "target": "HHI по поставщикам + N_eff", "gap": "high"},
    {"issue": "Spec purity (детектор заточки)", "current": "Частично (object_name)", "target": "object_name + ТЗ текст", "gap": "medium"},
    {"issue": "Customer health (ИНН)", "current": "ИНН не парсится", "target": "ЕГРЮЛ + РНП + арбитражи", "gap": "high"},
    {"issue": "Telegram-дайджест", "current": "Отсутствует", "target": "Ежедневно 08:00 МСК", "gap": "medium"},
    {"issue": "Объём данных", "current": "150 лотов / 3 регионa", "target": "50-100k лотов / 12+ регионов", "gap": "critical"},
]

for item in scorecard:
    icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}[item["gap"]]
    print(f"  {icon} {item['issue']}: {item['current']} → {item['target']}")

# -- Chart 9: Audit Scorecard --
fig, ax = plt.subplots(figsize=(14, 8))
apply_theme(fig, ax)

sc_df = pd.DataFrame(scorecard)
gap_colors = {"critical": NEGATIVE, "high": SECONDARY, "medium": "#FBBF24", "low": POSITIVE}
bar_colors = [gap_colors[g] for g in sc_df["gap"]]

y_pos = np.arange(len(sc_df))
ax.barh(y_pos, [1]*len(sc_df), color=bar_colors, alpha=0.8, height=0.7)

for i, row in sc_df.iterrows():
    ax.text(0.02, i, f"{row['issue']}", va="center", fontsize=10, color="white", fontweight="bold")
    ax.text(0.98, i, f"{row['current']} → {row['target']}", va="center", ha="right",
            fontsize=8, color=TICK_TEXT)

ax.set_yticks([])
ax.set_xticks([])
ax.set_title("Аудит TenderLens — Карта разрывов (Gap Analysis)", fontsize=15, fontweight="bold", color=TITLE_COLOR)

# Legend
from matplotlib.patches import Patch
legend_elements = [
    Patch(facecolor=NEGATIVE, label="Критический"),
    Patch(facecolor=SECONDARY, label="Высокий"),
    Patch(facecolor="#FBBF24", label="Средний"),
    Patch(facecolor=POSITIVE, label="Низкий"),
]
ax.legend(handles=legend_elements, loc="upper right", facecolor=BG, edgecolor=GRID, 
          labelcolor=LEGEND_TEXT, title="Уровень разрыва", title_fontsize=10)

fig.tight_layout()
fig.savefig(OUT_DIR / "09_audit_scorecard.png", dpi=150, facecolor=BG)
plt.close(fig)
print(f"\n  -> Chart saved: 09_audit_scorecard.png")

# ============================================================
# SAVE ANALYSIS SUMMARY
# ============================================================
summary_path = OUT_DIR / "audit_analysis_summary.json"
summary = {
    "generated_at": datetime.now().isoformat(),
    "total_lots": len(df),
    "data_quality": quality_stats,
    "price_stats": {
        "mean": float(prices.mean()),
        "median": float(prices.median()),
        "min": float(prices.min()),
        "max": float(prices.max()),
        "outliers_count": int(len(outliers)),
    },
    "hhi_customers": float(hhi_customers),
    "n_eff_customers": float(n_eff_customers),
    "timing": {
        "mean_deadline_days": float(dd.mean()),
        "median_deadline_days": float(dd.median()),
        "avg_timing_signal": float(df["timing_signal"].mean()),
    },
    "rigging": {
        "flagged_lots": int(df["is_rigged"].sum()),
        "flagged_pct": float(df["is_rigged"].mean() * 100),
        "flag_counts": dict(flag_counts),
    },
    "profit_score_components_available": available_count,
    "profit_score_components_total": total_components,
    "scorecard": scorecard,
}
with open(summary_path, "w", encoding="utf-8") as f:
    json.dump(summary, f, ensure_ascii=False, indent=2)
print(f"\nFull summary saved -> {summary_path}")
print("\n✅ ANALYSIS COMPLETE")
