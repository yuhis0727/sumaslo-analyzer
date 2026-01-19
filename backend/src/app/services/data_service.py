"""スクレイピングデータのDB保存・集計サービス"""

from datetime import date, datetime

from sqlalchemy.orm import Session

from src.app.models.slot_data import (
    DailyModelSummary,
    DailyStoreSummary,
    MachinePositionHistory,
    ScrapingLog,
    SlotMachine,
    SlotModel,
    Store,
)


class DataService:
    """データ保存・集計サービス"""

    def __init__(self, db: Session):
        self.db = db

    # ===================
    # 店舗管理
    # ===================

    def get_or_create_store(
        self,
        name: str,
        area: str | None = None,
        anaslo_url: str | None = None,
    ) -> Store:
        """店舗を取得または作成"""
        store = self.db.query(Store).filter(Store.name == name).first()
        if not store:
            store = Store(name=name, area=area, anaslo_url=anaslo_url)
            self.db.add(store)
            self.db.commit()
            self.db.refresh(store)
        return store

    # ===================
    # 機種マスター管理
    # ===================

    def get_or_create_model(self, name: str) -> SlotModel:
        """機種マスターを取得または作成"""
        model = self.db.query(SlotModel).filter(SlotModel.name == name).first()
        if not model:
            model = SlotModel(name=name)
            self.db.add(model)
            self.db.commit()
            self.db.refresh(model)
        return model

    # ===================
    # 台データ保存
    # ===================

    def save_scraped_data(
        self,
        scraped_data: dict,
        data_date: date | None = None,
    ) -> int:
        """スクレイピングデータをDBに保存

        Args:
            scraped_data: AnasloScraper.scrape_store_data_by_date()の戻り値
            data_date: データの日付（Noneの場合は今日）

        Returns:
            保存した台数
        """
        if data_date is None:
            data_date = date.today()

        # 店舗を取得または作成
        store = self.get_or_create_store(
            name=scraped_data["store_name"],
            anaslo_url=scraped_data.get("store_url"),
        )

        saved_count = 0

        for machine_data in scraped_data.get("machines", []):
            # 機種マスターを取得または作成
            self.get_or_create_model(machine_data["model_name"])

            # 既存データがあるか確認（UPSERT）
            existing = (
                self.db.query(SlotMachine)
                .filter(
                    SlotMachine.store_id == store.id,
                    SlotMachine.machine_number == machine_data["machine_number"],
                    SlotMachine.data_date == data_date,
                )
                .first()
            )

            if existing:
                # 更新
                existing.model_name = machine_data["model_name"]
                existing.game_count = machine_data.get("game_count")
                existing.big_bonus = machine_data.get("big_bonus")
                existing.regular_bonus = machine_data.get("regular_bonus")
                existing.art_count = machine_data.get("art_count")
                existing.total_difference = machine_data.get("total_difference")
                existing.bb_probability = machine_data.get("bb_rate")
                existing.rb_probability = machine_data.get("rb_rate")
                existing.combined_probability = machine_data.get("combined_rate")
                existing.updated_at = datetime.now()
            else:
                # 新規作成
                slot_machine = SlotMachine(
                    store_id=store.id,
                    machine_number=machine_data["machine_number"],
                    model_name=machine_data["model_name"],
                    game_count=machine_data.get("game_count"),
                    big_bonus=machine_data.get("big_bonus"),
                    regular_bonus=machine_data.get("regular_bonus"),
                    art_count=machine_data.get("art_count"),
                    total_difference=machine_data.get("total_difference"),
                    bb_probability=machine_data.get("bb_rate"),
                    rb_probability=machine_data.get("rb_rate"),
                    combined_probability=machine_data.get("combined_rate"),
                    data_date=data_date,
                )
                self.db.add(slot_machine)
                saved_count += 1

        self.db.commit()
        return saved_count

    # ===================
    # スクレイピングログ
    # ===================

    def create_scraping_log(
        self,
        store_id: int | None = None,
        status: str = "running",
    ) -> ScrapingLog:
        """スクレイピングログを作成"""
        log = ScrapingLog(
            store_id=store_id,
            status=status,
            started_at=datetime.now(),
        )
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log

    def update_scraping_log(
        self,
        log: ScrapingLog,
        status: str,
        scraped_count: int = 0,
        error_message: str | None = None,
    ) -> None:
        """スクレイピングログを更新"""
        log.status = status
        log.scraped_count = scraped_count
        log.error_message = error_message
        log.completed_at = datetime.now()
        self.db.commit()

    # ===================
    # 集計処理
    # ===================

    def aggregate_daily_store_summary(
        self,
        store_id: int,
        data_date: date,
    ) -> DailyStoreSummary:
        """店舗の日次サマリーを集計"""
        machines = (
            self.db.query(SlotMachine)
            .filter(
                SlotMachine.store_id == store_id,
                SlotMachine.data_date == data_date,
            )
            .all()
        )

        if not machines:
            return None

        total_machines = len(machines)
        differences = [
            m.total_difference for m in machines if m.total_difference is not None
        ]
        game_counts = [m.game_count for m in machines if m.game_count is not None]

        positive_machines = sum(1 for d in differences if d > 0)
        negative_machines = sum(1 for d in differences if d < 0)
        total_difference = sum(differences) if differences else None
        average_difference = (
            sum(differences) / len(differences) if differences else None
        )
        average_game_count = (
            sum(game_counts) / len(game_counts) if game_counts else None
        )

        # 既存レコードがあれば更新、なければ作成
        existing = (
            self.db.query(DailyStoreSummary)
            .filter(
                DailyStoreSummary.store_id == store_id,
                DailyStoreSummary.data_date == data_date,
            )
            .first()
        )

        if existing:
            existing.total_machines = total_machines
            existing.positive_machines = positive_machines
            existing.negative_machines = negative_machines
            existing.total_difference = total_difference
            existing.average_difference = average_difference
            existing.average_game_count = average_game_count
            existing.updated_at = datetime.now()
            summary = existing
        else:
            summary = DailyStoreSummary(
                store_id=store_id,
                data_date=data_date,
                total_machines=total_machines,
                positive_machines=positive_machines,
                negative_machines=negative_machines,
                total_difference=total_difference,
                average_difference=average_difference,
                average_game_count=average_game_count,
            )
            self.db.add(summary)

        self.db.commit()
        self.db.refresh(summary)
        return summary

    def aggregate_daily_model_summary(
        self,
        store_id: int,
        data_date: date,
    ) -> list[DailyModelSummary]:
        """機種別の日次サマリーを集計"""
        machines = (
            self.db.query(SlotMachine)
            .filter(
                SlotMachine.store_id == store_id,
                SlotMachine.data_date == data_date,
            )
            .all()
        )

        if not machines:
            return []

        # 機種ごとにグループ化
        model_groups: dict[str, list[SlotMachine]] = {}
        for m in machines:
            if m.model_name not in model_groups:
                model_groups[m.model_name] = []
            model_groups[m.model_name].append(m)

        summaries = []
        for model_name, group in model_groups.items():
            # 機種マスターを取得
            model = self.get_or_create_model(model_name)

            machine_count = len(group)
            differences = [
                m.total_difference for m in group if m.total_difference is not None
            ]
            game_counts = [m.game_count for m in group if m.game_count is not None]

            total_game_count = sum(game_counts) if game_counts else None
            average_game_count = (
                sum(game_counts) / len(game_counts) if game_counts else None
            )
            total_difference = sum(differences) if differences else None
            average_difference = (
                sum(differences) / len(differences) if differences else None
            )
            positive_count = sum(1 for d in differences if d > 0)
            max_difference = max(differences) if differences else None
            min_difference = min(differences) if differences else None

            # 既存レコードがあれば更新
            existing = (
                self.db.query(DailyModelSummary)
                .filter(
                    DailyModelSummary.store_id == store_id,
                    DailyModelSummary.model_id == model.id,
                    DailyModelSummary.data_date == data_date,
                )
                .first()
            )

            if existing:
                existing.machine_count = machine_count
                existing.total_game_count = total_game_count
                existing.average_game_count = average_game_count
                existing.total_difference = total_difference
                existing.average_difference = average_difference
                existing.positive_count = positive_count
                existing.max_difference = max_difference
                existing.min_difference = min_difference
                existing.updated_at = datetime.now()
                summary = existing
            else:
                summary = DailyModelSummary(
                    store_id=store_id,
                    model_id=model.id,
                    data_date=data_date,
                    machine_count=machine_count,
                    total_game_count=total_game_count,
                    average_game_count=average_game_count,
                    total_difference=total_difference,
                    average_difference=average_difference,
                    positive_count=positive_count,
                    max_difference=max_difference,
                    min_difference=min_difference,
                )
                self.db.add(summary)

            summaries.append(summary)

        self.db.commit()
        return summaries

    def update_machine_position_history(
        self,
        store_id: int,
        period_start: date,
        period_end: date,
    ) -> list[MachinePositionHistory]:
        """台番号ごとの履歴を集計・更新"""
        # 期間内のデータを取得
        machines = (
            self.db.query(SlotMachine)
            .filter(
                SlotMachine.store_id == store_id,
                SlotMachine.data_date >= period_start,
                SlotMachine.data_date <= period_end,
            )
            .all()
        )

        if not machines:
            return []

        # 台番号ごとにグループ化
        position_groups: dict[int, list[SlotMachine]] = {}
        for m in machines:
            if m.machine_number not in position_groups:
                position_groups[m.machine_number] = []
            position_groups[m.machine_number].append(m)

        histories = []
        for machine_number, group in position_groups.items():
            data_count = len(group)
            differences = [
                m.total_difference for m in group if m.total_difference is not None
            ]

            if not differences:
                continue

            total_difference = sum(differences)
            average_difference = total_difference / len(differences)
            positive_days = sum(1 for d in differences if d > 0)
            negative_days = sum(1 for d in differences if d < 0)
            max_difference = max(differences)
            min_difference = min(differences)

            # 高設定スコアを計算（単純な例: プラス日数の割合 × 100）
            high_setting_score = (
                (positive_days / len(differences)) * 100 if differences else 0
            )

            # 既存レコードがあれば更新
            existing = (
                self.db.query(MachinePositionHistory)
                .filter(
                    MachinePositionHistory.store_id == store_id,
                    MachinePositionHistory.machine_number == machine_number,
                    MachinePositionHistory.period_start == period_start,
                    MachinePositionHistory.period_end == period_end,
                )
                .first()
            )

            if existing:
                existing.data_count = data_count
                existing.total_difference = total_difference
                existing.average_difference = average_difference
                existing.positive_days = positive_days
                existing.negative_days = negative_days
                existing.max_difference = max_difference
                existing.min_difference = min_difference
                existing.high_setting_score = high_setting_score
                existing.updated_at = datetime.now()
                history = existing
            else:
                history = MachinePositionHistory(
                    store_id=store_id,
                    machine_number=machine_number,
                    period_start=period_start,
                    period_end=period_end,
                    data_count=data_count,
                    total_difference=total_difference,
                    average_difference=average_difference,
                    positive_days=positive_days,
                    negative_days=negative_days,
                    max_difference=max_difference,
                    min_difference=min_difference,
                    high_setting_score=high_setting_score,
                )
                self.db.add(history)

            histories.append(history)

        self.db.commit()
        return histories

    def run_all_aggregations(
        self,
        store_id: int,
        data_date: date,
        history_days: int = 30,
    ) -> dict:
        """全ての集計処理を実行"""
        from datetime import timedelta

        store_summary = self.aggregate_daily_store_summary(store_id, data_date)
        model_summaries = self.aggregate_daily_model_summary(store_id, data_date)

        # 履歴は過去N日分
        period_start = data_date - timedelta(days=history_days)
        position_histories = self.update_machine_position_history(
            store_id, period_start, data_date
        )

        return {
            "store_summary": store_summary,
            "model_summaries": model_summaries,
            "position_histories": position_histories,
        }
