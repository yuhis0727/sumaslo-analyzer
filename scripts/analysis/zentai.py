import sys; sys.stdout.reconfigure(encoding="utf-8")
import pandas as pd

df = pd.read_csv("minrepo_maruhan_kamata7_browser.csv", encoding="utf-8-sig")
df["date"] = pd.to_datetime(df["date"])
df["total_diff"] = pd.to_numeric(df["total_diff"], errors="coerce")
df["game_count"] = pd.to_numeric(df["game_count"], errors="coerce")
df["machine_number"] = pd.to_numeric(df["machine_number"], errors="coerce")
df = df.dropna(subset=["total_diff","game_count","machine_number"])
df["machine_number"] = df["machine_number"].astype(int)
df["diff_rate"] = df["total_diff"] / df["game_count"]

latest_df = df[df["date"] == df["date"].max()]
current_nums = set(latest_df["machine_number"])

# 7の日のみ × 現在稼働台
df7 = df[(df["date"].dt.day.isin([7,17,27])) & (df["machine_number"].isin(current_nums))]

# 機種別に「台ごとの7の日勝率」を集計し、最小値（最も弱い台）で全台系か判断
def analyze_kishu(df7):
    results = []
    for model, group in df7.groupby("model_name"):
        machines = group.groupby("machine_number").agg(
            n=("total_diff","count"),
            win=("total_diff", lambda x: (x>0).mean()),
            avg=("total_diff","mean"),
        ).query("n >= 8")  # 8日以上データある台のみ

        if len(machines) < 3:  # 台数3台以上の機種のみ
            continue

        results.append({
            "model": model[:28],
            "台数": len(machines),
            "全台平均勝率": machines["win"].mean(),
            "最低勝率台": machines["win"].min(),   # これが高い = 全台系
            "最高勝率台": machines["win"].max(),
            "平均差枚(機種平均)": machines["avg"].mean(),
            "勝率50%以上台数": (machines["win"] >= 0.5).sum(),
        })

    return pd.DataFrame(results).sort_values("最低勝率台", ascending=False)

res = analyze_kishu(df7)

print("7の日 機種別「全台系指標」ランキング")
print("（最低勝率台 = 一番弱い台の勝率。高いほど全台に設定が入っている）")
print()
print(f"{'機種':<30} {'台数':>4} {'全台平均':>6} {'最低台':>6} {'最高台':>6} {'50%以上':>6} {'機種平均差枚':>10}")
print("-" * 82)
for _, r in res.iterrows():
    mark = " ★全台" if r["最低勝率台"] >= 0.6 else (" △準全台" if r["最低勝率台"] >= 0.5 else "")
    print(f"{r['model']:<30} {r['台数']:>4}台 "
          f"{r['全台平均勝率']*100:>5.0f}%  "
          f"{r['最低勝率台']*100:>5.0f}%  "
          f"{r['最高勝率台']*100:>5.0f}%  "
          f"{r['勝率50%以上台数']:>3}/{r['台数']:<3}  "
          f"{r['平均差枚(機種平均)']:>+8,.0f}枚{mark}")
