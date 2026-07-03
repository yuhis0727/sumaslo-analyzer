"""特徴量エンジニアリング (CLAUDE.md Phase1 仕様)

基本特徴量:
  diff_rate            差枚率 (差枚数 / ゲーム数)
  reg_prob             REG確率 (ゲーム数 / REG回数)
  big_prob             BIG確率 (ゲーム数 / BIG回数)
  bonus_total_prob     総ボーナス確率 (ゲーム数 / 総ボーナス回数)
  at_rate              AT突入率

理論値乖離特徴量:
  deviation_reg        実REG確率 / 設定6理論REG確率
  deviation_diff       実差枚率 / 設定6理論差枚率

コンテキスト特徴量:
  day_of_week          曜日 (0=月〜6=日)
  machine_position     台番号位置 (角台 / 中間台)
  relative_rank_in_store  同店舗内差枚順位
  relative_rank_in_model  同機種内差枚順位

時系列特徴量 (データが揃い次第):
  prev_day_diff_rate   前日差枚率
  prev2_day_diff_rate  前々日差枚率
  consecutive_high_days 連続高出玉日数
  rolling_avg_7d       7日間移動平均差枚率
"""

from datetime import date

import numpy as np
import pandas as pd


# アクセス間隔設定 (スクレイピング規約遵守)
SCRAPE_INTERVAL_SECONDS = 2.5
MAX_RETRIES = 3
TIMEOUT_SECONDS = 30
UPDATE_HOUR = 12  # 毎日12時に更新


def compute_basic_features(df: pd.DataFrame) -> pd.DataFrame:
    """基本特徴量を計算する

    Args:
        df: machines テーブルのデータ。必須カラム:
            games_played, diff_medals, bonus_count, reg_count,
            big_count, at_count

    Returns:
        特徴量カラムが追加された DataFrame

    """
    df = df.copy()

    # 差枚率 (枚/G)
    df["diff_rate"] = np.where(
        df["games_played"] > 0,
        df["diff_medals"] / df["games_played"],
        np.nan,
    )

    # REG確率 (1/N 形式の分母)
    df["reg_prob"] = np.where(
        df["reg_count"] > 0,
        df["games_played"] / df["reg_count"],
        np.nan,
    )

    # BIG確率
    df["big_prob"] = np.where(
        df["big_count"] > 0,
        df["games_played"] / df["big_count"],
        np.nan,
    )

    # 総ボーナス確率
    df["bonus_total_prob"] = np.where(
        df["bonus_count"] > 0,
        df["games_played"] / df["bonus_count"],
        np.nan,
    )

    # AT突入率 (AT回数 / BIG回数 — 機種によって異なるが汎用近似)
    df["at_rate"] = np.where(
        df["big_count"] > 0,
        df["at_count"].fillna(0) / df["big_count"],
        np.nan,
    )

    return df


def compute_deviation_features(
    df: pd.DataFrame,
    theoretical: dict,
) -> pd.DataFrame:
    """理論値との乖離特徴量を計算する

    Args:
        df: compute_basic_features 済みの DataFrame
        theoretical: 機種別設定6理論値の辞書
            {model_name: {"reg_prob": float, "diff_rate_per_game": float}}

    Returns:
        乖離特徴量が追加された DataFrame

    """
    df = df.copy()

    def _deviation_reg(row):
        th = theoretical.get(row["model_name"], {})
        th_reg = th.get("reg_prob")
        if th_reg and th_reg > 0 and not np.isnan(row.get("reg_prob", np.nan)):
            return row["reg_prob"] / th_reg
        return np.nan

    def _deviation_diff(row):
        th = theoretical.get(row["model_name"], {})
        th_diff = th.get("diff_rate_per_game")
        if th_diff and th_diff != 0 and not np.isnan(row.get("diff_rate", np.nan)):
            return row["diff_rate"] / th_diff
        return np.nan

    df["deviation_reg"] = df.apply(_deviation_reg, axis=1)
    df["deviation_diff"] = df.apply(_deviation_diff, axis=1)

    return df


def compute_context_features(
    df: pd.DataFrame,
    target_date: date,
    event_dates: set[date] | None = None,
) -> pd.DataFrame:
    """コンテキスト特徴量を計算する

    Args:
        df: 特徴量計算済みの DataFrame
        target_date: データの営業日付
        event_dates: イベント日の集合 (未指定は空)

    Returns:
        コンテキスト特徴量が追加された DataFrame

    """
    df = df.copy()
    if event_dates is None:
        event_dates = set()

    df["day_of_week"] = target_date.weekday()  # 0=月〜6=日
    df["is_event_day"] = int(target_date in event_dates)

    # 角台判定: 同店舗内の最小・最大台番号
    mn = df["machine_number"]
    df["machine_position"] = 0  # 0=中間
    df.loc[mn == mn.min(), "machine_position"] = 1  # 角台
    df.loc[mn == mn.max(), "machine_position"] = 1

    # 同店舗内差枚順位 (降順: 1 が最高)
    df["relative_rank_in_store"] = df["diff_medals"].rank(
        ascending=False, method="min"
    )

    # 同機種内差枚順位
    df["relative_rank_in_model"] = df.groupby("model_name")["diff_medals"].rank(
        ascending=False, method="min"
    )

    return df


def compute_timeseries_features(
    df: pd.DataFrame,
    history: pd.DataFrame,
) -> pd.DataFrame:
    """時系列特徴量を計算する

    Args:
        df: 当日の DataFrame (compute_basic_features 済み)
        history: 過去データの DataFrame。同じカラム構造 + date カラム必須

    Returns:
        時系列特徴量が追加された DataFrame

    """
    df = df.copy()

    if history.empty:
        df["prev_day_diff_rate"] = np.nan
        df["prev2_day_diff_rate"] = np.nan
        df["consecutive_high_days"] = 0
        df["rolling_avg_7d"] = np.nan
        return df

    history = history.copy()
    if "diff_rate" not in history.columns:
        history = compute_basic_features(history)

    def _get_prev_rate(machine_number: int, model_name: str, n_days: int) -> float:
        dates_sorted = sorted(history["date"].unique(), reverse=True)
        if len(dates_sorted) < n_days:
            return np.nan
        target_d = dates_sorted[n_days - 1]
        mask = (
            (history["machine_number"] == machine_number)
            & (history["model_name"] == model_name)
            & (history["date"] == target_d)
        )
        rows = history[mask]
        return float(rows["diff_rate"].iloc[0]) if not rows.empty else np.nan

    def _rolling_avg(machine_number: int, model_name: str, days: int = 7) -> float:
        mask = (history["machine_number"] == machine_number) & (
            history["model_name"] == model_name
        )
        rows = history[mask].sort_values("date", ascending=False).head(days)
        return float(rows["diff_rate"].mean()) if not rows.empty else np.nan

    def _consecutive_high(machine_number: int, model_name: str, threshold: float = 0) -> int:
        mask = (history["machine_number"] == machine_number) & (
            history["model_name"] == model_name
        )
        rows = history[mask].sort_values("date", ascending=False)
        count = 0
        for rate in rows["diff_rate"]:
            if not np.isnan(rate) and rate > threshold:
                count += 1
            else:
                break
        return count

    df["prev_day_diff_rate"] = df.apply(
        lambda r: _get_prev_rate(r["machine_number"], r["model_name"], 1), axis=1
    )
    df["prev2_day_diff_rate"] = df.apply(
        lambda r: _get_prev_rate(r["machine_number"], r["model_name"], 2), axis=1
    )
    df["consecutive_high_days"] = df.apply(
        lambda r: _consecutive_high(r["machine_number"], r["model_name"]), axis=1
    )
    df["rolling_avg_7d"] = df.apply(
        lambda r: _rolling_avg(r["machine_number"], r["model_name"]), axis=1
    )

    return df


def build_label_theoretical(
    df: pd.DataFrame,
    theoretical: dict,
    threshold_ratio: float = 0.95,
) -> pd.Series:
    """理論値ベースの擬似ラベルを生成する (アプローチ1)

    設定6理論差枚率の threshold_ratio 以上なら高設定候補 (1)。

    Args:
        df: diff_rate カラムを含む DataFrame
        theoretical: {model_name: {"diff_rate_per_game": float}}
        threshold_ratio: 0.95 = 設定6理論値の95%以上で高設定候補

    Returns:
        0/1 のラベル Series

    """

    def _label(row):
        th = theoretical.get(row["model_name"], {})
        th_diff = th.get("diff_rate_per_game")
        if th_diff is not None and not np.isnan(row.get("diff_rate", np.nan)):
            return int(row["diff_rate"] >= th_diff * threshold_ratio)
        # 理論値がない場合は差枚率 > 0 を高設定候補とする
        return int(row.get("diff_rate", 0) > 0)

    return df.apply(_label, axis=1)


FEATURE_COLUMNS = [
    "diff_rate",
    "reg_prob",
    "big_prob",
    "bonus_total_prob",
    "at_rate",
    "deviation_reg",
    "deviation_diff",
    "day_of_week",
    "is_event_day",
    "machine_position",
    "relative_rank_in_store",
    "relative_rank_in_model",
    "prev_day_diff_rate",
    "prev2_day_diff_rate",
    "consecutive_high_days",
    "rolling_avg_7d",
]
