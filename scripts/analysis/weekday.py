"""曜日別仕掛けパターン検証"""
import sys; sys.stdout.reconfigure(encoding="utf-8")
import pandas as pd
import numpy as np

df = pd.read_csv("minrepo_maruhan_kamata7_browser.csv", encoding="utf-8-sig")
df["date"]           = pd.to_datetime(df["date"])
df["total_diff"]     = pd.to_numeric(df["total_diff"], errors="coerce")
df["game_count"]     = pd.to_numeric(df["game_count"], errors="coerce")
df["machine_number"] = pd.to_numeric(df["machine_number"], errors="coerce")
df = df.dropna(subset=["total_diff","game_count","machine_number"])
df["machine_number"] = df["machine_number"].astype(int)
df["diff_rate"]      = df["total_diff"] / df["game_count"]
df["is_win"]         = df["total_diff"] > 0
df["dow"]            = df["date"].dt.dayofweek   # 0=月 1=火 ... 6=日
df["dow_name"]       = df["date"].dt.day_name()
df["last_digit"]     = df["machine_number"] % 10
DOW_JP = {0:"月",1:"火",2:"水",3:"木",4:"金",5:"土",6:"日"}

sep = "=" * 65

# ── 全曜日の基本勝率 ────────────────────────────────
print(sep)
print("【基準】全台 曜日別平均勝率・差枚率")
print(sep)
base = df.groupby("dow").agg(
    n=("is_win","count"),
    win_rate=("is_win","mean"),
    avg_rate=("diff_rate","mean")
).reset_index()
for _, r in base.iterrows():
    print(f"  {DOW_JP[r['dow']]}曜日: 勝率{r['win_rate']*100:.1f}%  差枚率{r['avg_rate']:+.3f}枚/G  ({int(r['n'])}行)")

# ── 各モデルの機種内「角台」を定義 ─────────────────
# 各機種の最小・最大台番を角台とみなす
model_ranges = df.groupby("model_name")["machine_number"].agg(["min","max"])
corner_nums = set()
for _, r in model_ranges.iterrows():
    corner_nums.add(r["min"])
    corner_nums.add(r["max"])
df["is_corner"] = df["machine_number"].isin(corner_nums)

# ── 火曜日 🎯角系 ────────────────────────────────
print(f"\n{sep}")
print("【火曜日】角系（機種内 最小・最大台番）")
print(sep)
tue = df[df["dow"] == 1]
corner_tue = tue.groupby("is_corner").agg(win_rate=("is_win","mean"), avg_rate=("diff_rate","mean"), n=("is_win","count"))
for corner, r in corner_tue.iterrows():
    tag = "角台" if corner else "中間台"
    print(f"  {tag}: 勝率{r['win_rate']*100:.1f}%  差枚率{r['avg_rate']:+.3f}枚/G  ({int(r['n'])}行)")

# 全曜日での比較
print("\n  角台 vs 中間台 の全曜日比較:")
comp = df.groupby(["dow","is_corner"])["is_win"].mean().unstack()
for dow in range(7):
    if dow in comp.index:
        kado  = comp.loc[dow, True]  if True  in comp.columns else None
        naka  = comp.loc[dow, False] if False in comp.columns else None
        diff  = (kado - naka) if kado and naka else 0
        mark  = "← 火曜日 ✅差あり" if dow == 1 and diff > 0.02 else ""
        print(f"  {DOW_JP[dow]}曜日: 角{kado*100:.1f}% vs 中間{naka*100:.1f}%  差{diff*100:+.1f}pt  {mark}")

# ── 水曜日 🎯末尾 ───────────────────────────────
print(f"\n{sep}")
print("【水曜日】末尾（台番号の下1桁）")
print(sep)
wed = df[df["dow"] == 2]
by_digit_wed = wed.groupby("last_digit").agg(win_rate=("is_win","mean"), avg_rate=("diff_rate","mean"), n=("is_win","count")).reset_index()
by_digit_all = df.groupby("last_digit")["is_win"].mean().rename("all_win")
by_digit_wed = by_digit_wed.merge(by_digit_all, on="last_digit")
by_digit_wed["lift"] = by_digit_wed["win_rate"] - by_digit_wed["all_win"]
by_digit_wed = by_digit_wed.sort_values("win_rate", ascending=False)

print(f"  末尾  水曜勝率  全日比  差枚率  件数")
for _, r in by_digit_wed.iterrows():
    mark = " ◀ 有望" if r["lift"] > 0.03 else ""
    print(f"  {int(r['last_digit'])}番台:  {r['win_rate']*100:5.1f}%  {r['lift']*100:+4.1f}pt  {r['avg_rate']:+.3f}枚/G  ({int(r['n'])}){mark}")

# ── 土曜日 🎯3台並び ──────────────────────────────
print(f"\n{sep}")
print("【土曜日】3台並び（連続する3台が全部プラスになる確率）")
print(sep)

def count_consecutive_wins(day_df, day_label):
    """その日の稼働台の中で、3台連続して全部プラスになるグループ数を計算"""
    results = []
    for date, grp in day_df.groupby("date"):
        nums = grp.set_index("machine_number")["is_win"].to_dict()
        sorted_nums = sorted(nums.keys())
        triples_all_win = 0
        triples_total   = 0
        for i in range(len(sorted_nums) - 2):
            a, b, c = sorted_nums[i], sorted_nums[i+1], sorted_nums[i+2]
            if b == a+1 and c == b+1:   # 連番3台
                triples_total += 1
                if nums[a] and nums[b] and nums[c]:
                    triples_all_win += 1
        if triples_total > 0:
            results.append(triples_all_win / triples_total)
    return np.mean(results) if results else 0

sat = df[df["dow"] == 5]
other = df[df["dow"] != 5]

sat_rate   = count_consecutive_wins(sat, "土曜")
other_rate = count_consecutive_wins(other, "他曜日")
print(f"  土曜日: 3台連続全勝率 = {sat_rate*100:.1f}%")
print(f"  他曜日: 3台連続全勝率 = {other_rate*100:.1f}%")
print(f"  差: {(sat_rate-other_rate)*100:+.1f}pt  {'← ✅差あり' if sat_rate > other_rate + 0.01 else ''}")

# ── 月曜日 🎯列全 ───────────────────────────────
print(f"\n{sep}")
print("【月曜日】列全（同機種の全台一斉高設定 = 機種内全勝率）")
print(sep)

def model_all_win_rate(day_df):
    """各日×各機種で全台プラスになる割合"""
    rates = []
    for (date, model), grp in day_df.groupby(["date","model_name"]):
        if len(grp) >= 3:  # 3台以上の機種のみ
            rates.append((grp["is_win"] == True).all())
    return np.mean(rates) if rates else 0

mon = df[df["dow"] == 0]
oth = df[df["dow"] != 0]
mon_rate = model_all_win_rate(mon)
oth_rate = model_all_win_rate(oth)
print(f"  月曜日: 機種内全台プラス率 = {mon_rate*100:.1f}%")
print(f"  他曜日: 機種内全台プラス率 = {oth_rate*100:.1f}%")
print(f"  差: {(mon_rate-oth_rate)*100:+.1f}pt  {'← ✅差あり' if mon_rate > oth_rate + 0.01 else ''}")

# ── 日曜日 🎯機種1以上3台以上 ────────────────────
print(f"\n{sep}")
print("【日曜日】機種1台以上（3台以上の機種で最低1台プラス）")
print(sep)

def at_least_one_win_rate(day_df):
    rates = []
    for (date, model), grp in day_df.groupby(["date","model_name"]):
        if len(grp) >= 3:
            rates.append(grp["is_win"].any())
    return np.mean(rates) if rates else 0

sun = df[df["dow"] == 6]
oth = df[df["dow"] != 6]
sun_rate = at_least_one_win_rate(sun)
oth_rate = at_least_one_win_rate(oth)
print(f"  日曜日: 機種内1台以上プラス率 = {sun_rate*100:.1f}%")
print(f"  他曜日: 機種内1台以上プラス率 = {oth_rate*100:.1f}%")
print(f"  差: {(sun_rate-oth_rate)*100:+.1f}pt  {'← ✅差あり' if sun_rate > oth_rate + 0.01 else ''}")

# ── 末尾別 全曜日比較（水曜日の末尾を特定）───────
print(f"\n{sep}")
print("【末尾別】曜日×末尾 勝率マトリックス")
print(sep)
pivot = df.pivot_table(index="last_digit", columns="dow", values="is_win", aggfunc="mean") * 100
pivot.columns = [DOW_JP[c] for c in pivot.columns]
print(f"  末尾  " + "  ".join(f"{c}曜" for c in pivot.columns))
print("  " + "-"*50)
for idx, row in pivot.iterrows():
    vals = "  ".join(f"{v:5.1f}%" for v in row.values)
    best_dow = pivot.columns[row.values.argmax()]
    print(f"  {int(idx)}番台  {vals}  ← {best_dow}曜日が最高")
