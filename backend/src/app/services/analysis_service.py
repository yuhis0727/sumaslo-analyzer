"""高設定台推測・分析サービス"""

from datetime import date, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.app.models.slot_data import (
    DailyModelSummary,
    DailyStoreSummary,
    MachinePositionHistory,
    SlotMachine,
    SlotModel,
    Store,
)


class AnalysisService:
    """座るべき台を推測する分析サービス"""

    def __init__(self, db: Session):
        self.db = db

    def get_recommended_machines(
        self,
        store_id: int,
        target_date: date | None = None,
        history_days: int = 30,
        top_n: int = 10,
    ) -> dict:
        """座るべき台を推測して返す

        Args:
            store_id: 店舗ID
            target_date: 予測対象日（デフォルトは今日）
            history_days: 分析に使う過去日数
            top_n: 推奨台数

        Returns:
            推奨台情報と分析詳細
        """
        if target_date is None:
            target_date = date.today()

        store = self.db.query(Store).filter(Store.id == store_id).first()
        if not store:
            return {"error": "店舗が見つかりません"}

        period_start = target_date - timedelta(days=history_days)

        # 各分析を実行
        position_analysis = self._analyze_positions(store_id, period_start, target_date)
        model_analysis = self._analyze_models(store_id, period_start, target_date)
        pattern_analysis = self._analyze_patterns(store_id, period_start, target_date)

        # スコアを統合して推奨台を決定
        recommendations = self._calculate_recommendations(
            store_id,
            position_analysis,
            model_analysis,
            pattern_analysis,
            top_n,
        )

        return {
            "store_name": store.name,
            "store_id": store_id,
            "analysis_date": target_date.isoformat(),
            "period": {
                "start": period_start.isoformat(),
                "end": target_date.isoformat(),
                "days": history_days,
            },
            "recommendations": recommendations,
            "analysis_details": {
                "position_analysis": position_analysis,
                "model_analysis": model_analysis,
                "pattern_analysis": pattern_analysis,
            },
        }

    def _analyze_positions(
        self,
        store_id: int,
        period_start: date,
        period_end: date,
    ) -> dict:
        """台番号ごとの傾向を分析"""
        histories = (
            self.db.query(MachinePositionHistory)
            .filter(
                MachinePositionHistory.store_id == store_id,
                MachinePositionHistory.period_start >= period_start,
                MachinePositionHistory.period_end <= period_end,
            )
            .all()
        )

        # 履歴がない場合は直接SlotMachineから集計
        if not histories:
            return self._analyze_positions_from_raw(store_id, period_start, period_end)

        position_scores = []
        for h in histories:
            score = self._calculate_position_score(h)
            position_scores.append({
                "machine_number": h.machine_number,
                "score": score,
                "data_count": h.data_count,
                "average_difference": h.average_difference,
                "positive_rate": (
                    (h.positive_days / h.data_count * 100) if h.data_count else 0
                ),
                "total_difference": h.total_difference,
                "reasons": self._get_position_reasons(h),
            })

        # スコア順にソート
        position_scores.sort(key=lambda x: x["score"], reverse=True)

        return {
            "total_positions": len(position_scores),
            "top_positions": position_scores[:10],
            "hot_numbers": self._find_hot_numbers(position_scores),
        }

    def _analyze_positions_from_raw(
        self,
        store_id: int,
        period_start: date,
        period_end: date,
    ) -> dict:
        """SlotMachineから直接台番号分析"""
        machines = (
            self.db.query(SlotMachine)
            .filter(
                SlotMachine.store_id == store_id,
                SlotMachine.data_date >= period_start,
                SlotMachine.data_date <= period_end,
            )
            .all()
        )

        # 台番号ごとにグループ化
        position_data: dict[int, list] = {}
        for m in machines:
            if m.machine_number not in position_data:
                position_data[m.machine_number] = []
            position_data[m.machine_number].append(m.total_difference or 0)

        position_scores = []
        for machine_number, differences in position_data.items():
            if not differences:
                continue

            data_count = len(differences)
            total_diff = sum(differences)
            avg_diff = total_diff / data_count
            positive_days = sum(1 for d in differences if d > 0)
            positive_rate = (positive_days / data_count) * 100

            # スコア計算
            score = self._calculate_raw_position_score(
                avg_diff, positive_rate, data_count
            )

            position_scores.append({
                "machine_number": machine_number,
                "score": score,
                "data_count": data_count,
                "average_difference": avg_diff,
                "positive_rate": positive_rate,
                "total_difference": total_diff,
                "reasons": [],
            })

        position_scores.sort(key=lambda x: x["score"], reverse=True)

        return {
            "total_positions": len(position_scores),
            "top_positions": position_scores[:10],
            "hot_numbers": self._find_hot_numbers(position_scores),
        }

    def _calculate_position_score(self, history: MachinePositionHistory) -> float:
        """台番号のスコアを計算"""
        score = 0.0

        # 高設定スコアがあればそれを基準に
        if history.high_setting_score:
            score = history.high_setting_score

        # 平均差枚数ボーナス
        if history.average_difference:
            if history.average_difference > 0:
                score += min(history.average_difference / 100, 20)  # 最大+20点

        # プラス日数の安定性ボーナス
        if history.data_count and history.positive_days:
            positive_rate = history.positive_days / history.data_count
            if positive_rate >= 0.6:  # 60%以上プラス
                score += 15
            elif positive_rate >= 0.5:
                score += 10

        # データ件数の信頼性ボーナス
        if history.data_count >= 20:
            score += 10
        elif history.data_count >= 10:
            score += 5

        return min(score, 100)  # 最大100点

    def _calculate_raw_position_score(
        self,
        avg_diff: float,
        positive_rate: float,
        data_count: int,
    ) -> float:
        """生データからスコアを計算"""
        score = positive_rate  # プラス率を基準に

        # 平均差枚数ボーナス
        if avg_diff > 0:
            score += min(avg_diff / 100, 20)

        # データ件数の信頼性ボーナス
        if data_count >= 20:
            score += 10
        elif data_count >= 10:
            score += 5

        return min(score, 100)

    def _get_position_reasons(self, history: MachinePositionHistory) -> list[str]:
        """台番号の推奨理由を生成"""
        reasons = []

        if history.positive_days and history.data_count:
            rate = history.positive_days / history.data_count * 100
            if rate >= 60:
                reasons.append(f"プラス率が高い（{rate:.1f}%）")

        if history.average_difference and history.average_difference > 500:
            reasons.append(f"平均差枚が良い（+{history.average_difference:.0f}枚）")

        if history.data_count and history.data_count >= 20:
            reasons.append("データ件数が多く信頼性が高い")

        return reasons

    def _find_hot_numbers(self, position_scores: list[dict]) -> list[int]:
        """ホットナンバー（末尾番号の傾向）を検出"""
        # 末尾番号ごとに平均スコアを計算
        suffix_scores: dict[int, list[float]] = {}
        for pos in position_scores:
            suffix = pos["machine_number"] % 10
            if suffix not in suffix_scores:
                suffix_scores[suffix] = []
            suffix_scores[suffix].append(pos["score"])

        # 平均スコアが高い末尾番号
        hot_suffixes = []
        for suffix, scores in suffix_scores.items():
            avg_score = sum(scores) / len(scores) if scores else 0
            if avg_score >= 60:  # 平均60点以上
                hot_suffixes.append({"suffix": suffix, "avg_score": avg_score})

        hot_suffixes.sort(key=lambda x: x["avg_score"], reverse=True)
        return [h["suffix"] for h in hot_suffixes[:3]]

    def _analyze_models(
        self,
        store_id: int,
        period_start: date,
        period_end: date,
    ) -> dict:
        """機種ごとの傾向を分析"""
        summaries = (
            self.db.query(DailyModelSummary)
            .filter(
                DailyModelSummary.store_id == store_id,
                DailyModelSummary.data_date >= period_start,
                DailyModelSummary.data_date <= period_end,
            )
            .all()
        )

        # 機種ごとに集約
        model_data: dict[int, list] = {}
        for s in summaries:
            if s.model_id not in model_data:
                model_data[s.model_id] = []
            model_data[s.model_id].append(s)

        model_scores = []
        for model_id, data_list in model_data.items():
            model = self.db.query(SlotModel).filter(SlotModel.id == model_id).first()
            if not model:
                continue

            # 期間内の統計
            total_days = len(data_list)
            total_positive = sum(d.positive_count or 0 for d in data_list)
            total_machines = sum(d.machine_count for d in data_list)
            avg_difference = (
                sum(d.average_difference or 0 for d in data_list) / total_days
                if total_days else 0
            )

            positive_rate = (
                (total_positive / total_machines * 100) if total_machines else 0
            )

            score = self._calculate_model_score(
                avg_difference, positive_rate, total_days
            )

            model_scores.append({
                "model_id": model_id,
                "model_name": model.name,
                "score": score,
                "days_analyzed": total_days,
                "average_difference": avg_difference,
                "positive_rate": positive_rate,
                "is_favorable": score >= 60,
            })

        model_scores.sort(key=lambda x: x["score"], reverse=True)

        return {
            "total_models": len(model_scores),
            "favorable_models": [m for m in model_scores if m["is_favorable"]],
            "top_models": model_scores[:5],
        }

    def _calculate_model_score(
        self,
        avg_diff: float,
        positive_rate: float,
        data_days: int,
    ) -> float:
        """機種スコアを計算"""
        score = positive_rate  # プラス率を基準に

        if avg_diff > 0:
            score += min(avg_diff / 50, 20)

        if data_days >= 20:
            score += 10
        elif data_days >= 10:
            score += 5

        return min(score, 100)

    def _analyze_patterns(
        self,
        store_id: int,
        period_start: date,
        period_end: date,
    ) -> dict:
        """曜日・パターン分析"""
        summaries = (
            self.db.query(DailyStoreSummary)
            .filter(
                DailyStoreSummary.store_id == store_id,
                DailyStoreSummary.data_date >= period_start,
                DailyStoreSummary.data_date <= period_end,
            )
            .all()
        )

        # 曜日ごとの傾向
        weekday_data: dict[int, list] = {i: [] for i in range(7)}
        for s in summaries:
            weekday = s.data_date.weekday()
            weekday_data[weekday].append({
                "date": s.data_date,
                "average_difference": s.average_difference or 0,
                "positive_machines": s.positive_machines or 0,
                "total_machines": s.total_machines,
            })

        weekday_names = ["月", "火", "水", "木", "金", "土", "日"]
        weekday_analysis = []
        for weekday, data_list in weekday_data.items():
            if not data_list:
                continue

            avg_diff = (
                sum(d["average_difference"] for d in data_list) / len(data_list)
            )
            total_positive = sum(d["positive_machines"] for d in data_list)
            total_machines = sum(d["total_machines"] for d in data_list)
            positive_rate = (
                (total_positive / total_machines * 100) if total_machines else 0
            )

            weekday_analysis.append({
                "weekday": weekday,
                "weekday_name": weekday_names[weekday],
                "data_count": len(data_list),
                "average_difference": avg_diff,
                "positive_rate": positive_rate,
                "is_favorable": avg_diff > 0 and positive_rate >= 40,
            })

        weekday_analysis.sort(key=lambda x: x["average_difference"], reverse=True)

        return {
            "weekday_analysis": weekday_analysis,
            "best_weekdays": [
                w["weekday_name"] for w in weekday_analysis
                if w["is_favorable"]
            ][:3],
        }

    def _calculate_recommendations(
        self,
        store_id: int,
        position_analysis: dict,
        model_analysis: dict,
        pattern_analysis: dict,
        top_n: int,
    ) -> list[dict]:
        """分析結果を統合して推奨台リストを作成"""
        # 台番号スコアを取得
        position_scores = {
            p["machine_number"]: p
            for p in position_analysis.get("top_positions", [])
        }

        # 有利な機種リスト
        favorable_models = {
            m["model_name"]
            for m in model_analysis.get("favorable_models", [])
        }

        # 最新の台データを取得
        latest_date = (
            self.db.query(func.max(SlotMachine.data_date))
            .filter(SlotMachine.store_id == store_id)
            .scalar()
        )

        if not latest_date:
            return []

        latest_machines = (
            self.db.query(SlotMachine)
            .filter(
                SlotMachine.store_id == store_id,
                SlotMachine.data_date == latest_date,
            )
            .all()
        )

        recommendations = []
        for machine in latest_machines:
            pos_data = position_scores.get(machine.machine_number, {})
            position_score = pos_data.get("score", 50)  # デフォルト50点

            # 機種ボーナス
            model_bonus = 15 if machine.model_name in favorable_models else 0

            # 総合スコア
            total_score = position_score + model_bonus

            reasons = []
            if pos_data.get("reasons"):
                reasons.extend(pos_data["reasons"])
            if machine.model_name in favorable_models:
                reasons.append(f"{machine.model_name}は高設定が入りやすい機種")

            recommendations.append({
                "machine_number": machine.machine_number,
                "model_name": machine.model_name,
                "total_score": min(total_score, 100),
                "position_score": position_score,
                "model_bonus": model_bonus,
                "reasons": reasons,
                "confidence": self._get_confidence_level(total_score),
            })

        # スコア順にソート
        recommendations.sort(key=lambda x: x["total_score"], reverse=True)

        return recommendations[:top_n]

    def _get_confidence_level(self, score: float) -> str:
        """信頼度レベルを返す"""
        if score >= 80:
            return "高"
        elif score >= 60:
            return "中"
        else:
            return "低"

    def get_machine_detail(
        self,
        store_id: int,
        machine_number: int,
        history_days: int = 30,
    ) -> dict:
        """特定の台番号の詳細分析"""
        period_end = date.today()
        period_start = period_end - timedelta(days=history_days)

        machines = (
            self.db.query(SlotMachine)
            .filter(
                SlotMachine.store_id == store_id,
                SlotMachine.machine_number == machine_number,
                SlotMachine.data_date >= period_start,
                SlotMachine.data_date <= period_end,
            )
            .order_by(SlotMachine.data_date.desc())
            .all()
        )

        if not machines:
            return {"error": "データが見つかりません"}

        # 日別データ
        daily_data = []
        differences = []
        for m in machines:
            diff = m.total_difference or 0
            differences.append(diff)
            daily_data.append({
                "date": m.data_date.isoformat(),
                "model_name": m.model_name,
                "game_count": m.game_count,
                "total_difference": diff,
                "bb": m.big_bonus,
                "rb": m.regular_bonus,
                "combined_probability": m.combined_probability,
            })

        # 統計
        total_diff = sum(differences)
        avg_diff = total_diff / len(differences) if differences else 0
        positive_days = sum(1 for d in differences if d > 0)
        positive_rate = (positive_days / len(differences) * 100) if differences else 0

        return {
            "machine_number": machine_number,
            "store_id": store_id,
            "period": {
                "start": period_start.isoformat(),
                "end": period_end.isoformat(),
            },
            "statistics": {
                "data_count": len(machines),
                "total_difference": total_diff,
                "average_difference": avg_diff,
                "positive_days": positive_days,
                "negative_days": len(differences) - positive_days,
                "positive_rate": positive_rate,
                "max_difference": max(differences) if differences else 0,
                "min_difference": min(differences) if differences else 0,
            },
            "daily_data": daily_data,
            "recommendation_score": self._calculate_raw_position_score(
                avg_diff, positive_rate, len(machines)
            ),
        }
