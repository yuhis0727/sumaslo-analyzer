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

latest = df["date"].max()
latest_df = df[df["date"] == latest]

# 最新データ(6/18)で機種を確認してから5の日分析をする関数
def best_machines_for_model(keyword, top_n=5, min_days=5):
    # 最新データでその機種がいる台番を取得
    current_nums = set(latest_df[latest_df["model_name"].str.contains(keyword, na=False)]["machine_number"])
    if not current_nums:
        print(f"  {keyword}: 6/18データで台番見つからず")
        return

    # その台番に限定して5の日成績を集計
    df5 = df[(df["date"].dt.day.isin([5,15,25])) & (df["machine_number"].isin(current_nums))]
    stats = (df5.groupby("machine_number")
        .agg(
            model=("model_name", lambda x: x.mode()[0][:22]),
            n=("total_diff","count"),
            win_rate=("total_diff", lambda x: (x>0).mean()),
            avg_diff=("total_diff","mean"),
            avg_rate=("diff_rate","mean"),
        )
        .query(f"n >= {min_days}")
        .sort_values(["win_rate","avg_diff"], ascending=False)
        .reset_index()
    )
    print(f"  台番   勝率   平均差枚    差枚率")
    for _, r in stats.head(top_n).iterrows():
        print(f"  {int(r['machine_number'])}番  {r['win_rate']*100:.0f}%  {r['avg_diff']:>+7,.0f}枚  {r['avg_rate']:>+.3f}枚/G  ({int(r['n'])}日)")

print("=== 6/25(木) 5の日 現在台番ベースのおすすめ ===")
print()

print("【マギアレコード】現在台番での5の日成績")
best_machines_for_model("マギア")

print()
print("【カバネリ海門】現在台番での5の日成績")
best_machines_for_model("カバネリ 海門")

print()
print("【モンキーターンV】現在台番での5の日成績")
best_machines_for_model("モンキーターン")

print()
print("【2026番】6/18の機種と5の日全履歴")
m2026 = df[(df["machine_number"]==2026) & (df["date"].dt.day.isin([5,15,25]))]
for _, r in m2026.sort_values("date").iterrows():
    print(f"  {r['date'].strftime('%m/%d')}  {r['model_name'][:20]}  {int(r['total_diff']):+,}枚")
if len(m2026):
    print(f"  → 勝率 {(m2026['total_diff']>0).mean()*100:.0f}%  平均 {m2026['total_diff'].mean():+,.0f}枚")

print()
print("【戦国乙女5（新台・2064番）】直近データ")
sko5 = latest_df[latest_df["model_name"].str.contains("戦国乙女5", na=False)].sort_values("machine_number")
for _, r in sko5.head(10).iterrows():
    print(f"  {int(r['machine_number'])}番  6/18差枚: {int(r['total_diff']):+,}枚")
