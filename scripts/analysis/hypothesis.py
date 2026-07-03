"""
営業分析の仮説検証 (7の日データ限定)
差枚率 = total_diff / game_count で設定の強さを比較
"""
import sys, warnings
sys.stdout.reconfigure(encoding="utf-8")
warnings.filterwarnings("ignore")

import pandas as pd
import numpy as np

CSV_PATH = "minrepo_maruhan_kamata7_browser.csv"

df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")
df["date"]           = pd.to_datetime(df["date"])
df["total_diff"]     = pd.to_numeric(df["total_diff"], errors="coerce")
df["game_count"]     = pd.to_numeric(df["game_count"], errors="coerce")
df["machine_number"] = pd.to_numeric(df["machine_number"], errors="coerce")
df = df.dropna(subset=["total_diff", "game_count", "machine_number"])
df["machine_number"] = df["machine_number"].astype(int)
df["diff_rate"]      = df["total_diff"] / df["game_count"]  # 差枚率

# 7の日フィルタ
df7 = df[df["date"].dt.day.isin([7, 17, 27])].copy()
print(f"7の日データ: {len(df7):,}行 / {df7['date'].nunique()}日分")
print()

# ────────────────────────────────────────────────
# ヘルパー: 機種名を短縮して検索しやすく
# ────────────────────────────────────────────────
def find_model(keyword):
    """キーワードに部分一致する機種名を返す"""
    matches = df7["model_name"].unique()
    return [m for m in matches if keyword in m]

def model_stats(keyword, label=None):
    """キーワードに一致する機種の7の日統計"""
    models = find_model(keyword)
    if not models:
        return None
    sub = df7[df7["model_name"].isin(models)]
    n_days   = sub.groupby("date").ngroups
    avg_rate = sub["diff_rate"].mean()
    win_rate = (sub["total_diff"] > 0).mean()
    avg_diff = sub["total_diff"].mean()
    n_rows   = len(sub)
    return {
        "label":    label or keyword,
        "models":   models,
        "n_rows":   n_rows,
        "n_days":   n_days,
        "avg_rate": avg_rate,
        "win_rate": win_rate,
        "avg_diff": avg_diff,
    }

def print_stats(s, indent="  "):
    if s is None:
        print(f"{indent}→ データなし")
        return
    print(f"{indent}機種: {', '.join(s['models'])[:60]}")
    print(f"{indent}サンプル: {s['n_rows']}行 / {s['n_days']}日")
    print(f"{indent}平均差枚率: {s['avg_rate']:+.2f} 枚/G  |  平均差枚: {s['avg_diff']:+.0f}  |  勝率: {s['win_rate']*100:.1f}%")

sep = "=" * 65

# ════════════════════════════════════════════════
print(sep)
print("【仮説1】機種別扱い: 良 vs 悪")
print(sep)

good_models = {
    "マギアレコード": "マギア",
    "モンキーターンV": "モンキーターン",
    "化物語": "化物語",
    "戦国乙女4": "戦国乙女4",
    "ヴァルヴレイヴ2": "ヴァルヴレイヴ2",
}
bad_models = {
    "東京グール": "東京喰種",
    "カバネリ海門": "カバネリ",
    "ミリオンゴッド": "ミリオンゴッド",
}

print("\n◆ 扱いが良いとされる機種:")
good_stats = {}
for label, kw in good_models.items():
    s = model_stats(kw, label)
    print(f"\n  [{label}]")
    print_stats(s)
    if s: good_stats[label] = s

print("\n◆ 扱いが悪いとされる機種:")
bad_stats = {}
for label, kw in bad_models.items():
    s = model_stats(kw, label)
    print(f"\n  [{label}]")
    print_stats(s)
    if s: bad_stats[label] = s

print("\n◆ 比較サマリー (平均差枚率):")
all_s = list(good_stats.values()) + list(bad_stats.values())
all_s.sort(key=lambda x: x["avg_rate"], reverse=True)
for i, s in enumerate(all_s, 1):
    tag = "✅良" if s["label"] in good_stats else "❌悪"
    print(f"  {i:2d}. {s['label']:<18} {s['avg_rate']:+.3f}枚/G  勝率{s['win_rate']*100:.0f}%  {tag}")

# ════════════════════════════════════════════════
print(f"\n{sep}")
print("【仮説2】化物語 ── 確率ベースでメイン機種中トップ?")
print(sep)
mono = model_stats("化物語", "化物語")
print_stats(mono)
# 全機種の中での差枚率順位
all_model_rates = (df7.groupby("model_name")
                   .agg(avg_rate=("diff_rate","mean"), win_rate=("total_diff", lambda x: (x>0).mean()), n=("total_diff","count"))
                   .query("n >= 30")  # 30行以上のデータがある機種のみ
                   .sort_values("avg_rate", ascending=False)
                   .reset_index())
rank = all_model_rates[all_model_rates["model_name"].str.contains("化物語")].index
if len(rank):
    print(f"\n  全機種中の差枚率ランキング: {rank[0]+1}位 / {len(all_model_rates)}機種")
print("\n  上位10機種 (7の日 / 30行以上):")
for _, r in all_model_rates.head(10).iterrows():
    print(f"  {r.name+1:3d}. {r['model_name'][:28]:<30} {r['avg_rate']:+.3f}枚/G  勝率{r['win_rate']*100:.0f}%")

# ════════════════════════════════════════════════
print(f"\n{sep}")
print("【仮説3】キングハナハナ ── 年明けから急上昇?")
print(sep)
hana = df7[df7["model_name"].str.contains("ハナハナ", na=False)].copy()
if len(hana):
    hana["month"] = hana["date"].dt.month
    monthly = hana.groupby("month").agg(
        avg_rate=("diff_rate","mean"),
        win_rate=("total_diff", lambda x: (x>0).mean()),
        n=("total_diff","count")
    )
    print(f"  機種: {hana['model_name'].unique()}")
    print(f"\n  月別推移:")
    for m, r in monthly.iterrows():
        print(f"    {m}月: 差枚率{r['avg_rate']:+.3f}枚/G  勝率{r['win_rate']*100:.0f}%  ({r['n']:.0f}行)")
    early = monthly[monthly.index <= 2]["avg_rate"].mean() if any(monthly.index <= 2) else None
    late  = monthly[monthly.index >= 4]["avg_rate"].mean() if any(monthly.index >= 4) else None
    if early and late:
        print(f"\n  前半(1-2月)平均: {early:+.3f}枚/G  vs  後半(4-6月)平均: {late:+.3f}枚/G")
        print(f"  → {'上昇傾向 ✅' if late > early else '下降傾向 ❌'}")
else:
    print("  データなし")

# ════════════════════════════════════════════════
print(f"\n{sep}")
print("【仮説4】ジャグラー系 優先順位")
print(sep)
juggler_keywords = {
    "キングハナハナ":   "ハナハナ",
    "マイジャグラー":   "マイジャグラー",
    "ファンキージャグラー2": "ファンキージャグラー",
    "ゴーゴージャグラー": "ゴーゴージャグラー",
    "ハッピージャグラー": "ハッピージャグラー",
    "ジャグラーガールズ": "ジャグラーガールズ",
    "ミスタージャグラー": "ミスタージャグラー",
    "ネオアイム":       "ネオアイム",
}
juggler_stats = []
for label, kw in juggler_keywords.items():
    s = model_stats(kw, label)
    if s:
        juggler_stats.append(s)

juggler_stats.sort(key=lambda x: x["avg_rate"], reverse=True)
print("  差枚率ランキング (高い順):")
for i, s in enumerate(juggler_stats, 1):
    print(f"  {i}. {s['label']:<20} {s['avg_rate']:+.3f}枚/G  勝率{s['win_rate']*100:.0f}%  ({s['n_rows']}行)")

# ════════════════════════════════════════════════
print(f"\n{sep}")
print("【仮説5】2026番 設定6継続疑惑 (モンキーターン → カバネリ海門)")
print(sep)
m2026 = df7[df7["machine_number"] == 2026].sort_values("date")
if len(m2026):
    print(f"  2026番の機種推移:")
    model_changes = m2026.groupby("model_name").agg(
        最初=("date","min"), 最後=("date","max"),
        avg_rate=("diff_rate","mean"),
        win_rate=("total_diff", lambda x:(x>0).mean()),
        n=("total_diff","count")
    ).reset_index()
    for _, r in model_changes.iterrows():
        print(f"    {r['model_name'][:30]}")
        print(f"      期間: {r['最初'].strftime('%m/%d')}〜{r['最後'].strftime('%m/%d')}  差枚率:{r['avg_rate']:+.3f}枚/G  勝率:{r['win_rate']*100:.0f}%  ({r['n']:.0f}日)")

    print(f"\n  2026番 日別データ:")
    for _, row in m2026.iterrows():
        diff_str = f"{int(row['total_diff']):+,}"
        rate_str = f"{row['diff_rate']:+.3f}枚/G"
        print(f"    {row['date'].strftime('%m/%d')} {row['model_name'][:20]:<22} 差枚:{diff_str:>8}  {rate_str}")
else:
    print("  データなし")

# ════════════════════════════════════════════════
print(f"\n{sep}")
print("【仮説6】カバネリ海門 ── 6月から改善?")
print(sep)
kaba = df7[df7["model_name"].str.contains("カバネリ", na=False)].copy()
if len(kaba):
    kaba["month"] = kaba["date"].dt.month
    monthly_k = kaba.groupby("month").agg(
        avg_rate=("diff_rate","mean"),
        win_rate=("total_diff", lambda x:(x>0).mean()),
        n=("total_diff","count")
    )
    print("  月別推移:")
    for m, r in monthly_k.iterrows():
        print(f"    {m}月: {r['avg_rate']:+.3f}枚/G  勝率{r['win_rate']*100:.0f}%  ({r['n']:.0f}行)")

    before = monthly_k[monthly_k.index < 6]["avg_rate"].mean() if any(monthly_k.index < 6) else None
    after  = monthly_k[monthly_k.index >= 6]["avg_rate"].mean() if any(monthly_k.index >= 6) else None
    if before is not None and after is not None:
        print(f"\n  〜5月平均: {before:+.3f}枚/G  6月〜: {after:+.3f}枚/G")
        print(f"  → {'改善傾向 ✅' if after > before else '改善なし ❌'}")
else:
    print("  データなし")

# ════════════════════════════════════════════════
print(f"\n{sep}")
print("【仮説7】BT機 ── 12/7から上昇 (1月以降での傾向確認)")
print(sep)
bt_keywords = ["ヴァルヴレイヴ", "北斗", "マギア", "カバネリ", "モンキーターン", "SAO", "ソードアート"]
bt_all = df7[df7["model_name"].str.contains("|".join(bt_keywords), na=False)].copy()
bt_all["month"] = bt_all["date"].dt.month
monthly_bt = bt_all.groupby("month").agg(
    avg_rate=("diff_rate","mean"),
    win_rate=("total_diff", lambda x:(x>0).mean()),
    n=("total_diff","count")
)
print("  BT/AT系合計 月別推移 (1月スタート時点の基準として):")
for m, r in monthly_bt.iterrows():
    bar = "█" * int(max(0, r["avg_rate"] * 30 + 15))
    print(f"    {m}月: {r['avg_rate']:+.3f}枚/G  勝率{r['win_rate']*100:.0f}%  {bar}")

# ════════════════════════════════════════════════
print(f"\n{sep}")
print("【追加】サブ機種 扱い確認")
print(sep)
sub_keywords = {
    "SAO":      "ソードアート",
    "七つの魔剣": "七つの魔剣",
    "超電磁砲2":  "超電磁砲",
    "エウレカ":   "エウレカ",
    "ガルパン":   "ガールズ",
    "ゴッドイーター": "ゴッドイーター",
}
sub_stats = []
for label, kw in sub_keywords.items():
    s = model_stats(kw, label)
    if s: sub_stats.append(s)
sub_stats.sort(key=lambda x: x["avg_rate"], reverse=True)
print("  差枚率ランキング:")
for i, s in enumerate(sub_stats, 1):
    print(f"  {i}. {s['label']:<15} {s['avg_rate']:+.3f}枚/G  勝率{s['win_rate']*100:.0f}%")
