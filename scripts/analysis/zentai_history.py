import sys; sys.stdout.reconfigure(encoding="utf-8")
import pandas as pd

df = pd.read_csv("minrepo_maruhan_kamata7_browser.csv", encoding="utf-8-sig")
df["date"] = pd.to_datetime(df["date"])
df["total_diff"] = pd.to_numeric(df["total_diff"], errors="coerce")
df["game_count"] = pd.to_numeric(df["game_count"], errors="coerce")
df["machine_number"] = pd.to_numeric(df["machine_number"], errors="coerce")
df = df.dropna(subset=["total_diff","game_count","machine_number"])
df["machine_number"] = df["machine_number"].astype(int)

latest_df = df[df["date"] == df["date"].max()]
current_nums = set(latest_df["machine_number"])

df7 = df[(df["date"].dt.day.isin([7,17,27])) & (df["machine_number"].isin(current_nums))]
nana_dates = sorted(df7["date"].unique())

DOW_JP = ["月","火","水","木","金","土","日"]

def analyze(keyword, label, zentai_thresh=0.65):
    """
    zentai_thresh: その日に何%以上の台が勝ちなら「全台系」と見なすか
    """
    sub = df7[df7["model_name"].str.contains(keyword, na=False)]
    if sub.empty:
        print(f"【{label}】データなし\n")
        return

    print(f"【{label}】 7の日 日別全台率")
    print(f"  日付        台数  勝ち台  全台率  機種平均差枚")
    print(f"  " + "-"*48)

    zentai_dates = []
    for d in nana_dates:
        day_data = sub[sub["date"] == d]
        if len(day_data) < 3:
            continue
        total = len(day_data)
        wins  = (day_data["total_diff"] > 0).sum()
        rate  = wins / total
        avg   = day_data["total_diff"].mean()
        dow   = DOW_JP[pd.Timestamp(d).dayofweek]
        mark  = " ★全台系" if rate >= zentai_thresh else ""
        print(f"  {pd.Timestamp(d).strftime('%m/%d')}({dow})  {total:>3}台  {wins:>2}勝  {rate*100:>4.0f}%  {avg:>+7,.0f}枚{mark}")
        if rate >= zentai_thresh:
            zentai_dates.append(d)

    print(f"\n  全台系回数: {len(zentai_dates)}/{len([d for d in nana_dates if len(sub[sub['date']==d])>=3])}回")
    if zentai_dates:
        last = pd.Timestamp(zentai_dates[-1])
        print(f"  最後の全台系: {last.strftime('%m/%d')} ({DOW_JP[last.dayofweek]}曜)")
    else:
        print(f"  全台系: 未確認")
    print()

# ユーザー予想機種を検証
analyze("マギア",                   "マギアレコード")
analyze("化物語",                   "化物語")
analyze("からくりサーカス",           "からくりサーカス")
analyze("スーパーブラックジャック",     "SBJ")
analyze("ヴァルヴレイヴ2",            "ヴァルヴレイヴ2")
analyze("シャーマンキング",           "シャーマンキング")
