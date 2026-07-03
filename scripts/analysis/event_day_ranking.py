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

# 現在稼働台番（6/18）
latest_df = df[df["date"] == df["date"].max()]
current_nums = set(latest_df["machine_number"])

# 7の日のみ（全17日）× 現在稼働台
df7 = df[(df["date"].dt.day.isin([7,17,27])) & (df["machine_number"].isin(current_nums))]

stats = (df7.groupby("machine_number")
    .agg(
        model=("model_name", lambda x: x.mode()[0][:22]),
        n=("total_diff","count"),
        win_rate=("total_diff", lambda x: (x>0).mean()),
        avg_diff=("total_diff","mean"),
        avg_rate=("diff_rate","mean"),
    )
    .query("n >= 10")
    .sort_values(["win_rate","avg_diff"], ascending=False)
    .reset_index()
)

print("7の日のみ 台番別勝率ランキング TOP30（10日以上・現稼働台限定）")
print(f"{'台番':>5}  {'機種':<24}  {'勝率':>5}  {'平均差枚':>8}  {'差枚率':>8}  {'日数'}")
print("-" * 75)
for _, r in stats.head(30).iterrows():
    print(f"{int(r['machine_number']):>5}  {r['model']:<24}  {r['win_rate']*100:>4.0f}%  "
          f"{r['avg_diff']:>+8,.0f}  {r['avg_rate']:>+7.3f}枚/G  ({int(r['n'])}日)")
