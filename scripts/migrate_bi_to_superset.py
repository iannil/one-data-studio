#!/usr/bin/env python3
"""
BI 仪表板迁移脚本
将 One Data Studio 的 BI 仪表板和图表迁移到 Superset

功能：
1. 连接到 Superset
2. 同步数据库连接
3. 迁移仪表板和图表
4. 生成迁移报告
"""

import os
import sys
import json
import argparse
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# 导入模型
from services.data_api.models import get_db, BIDashboard, BIChart

# 导入 Superset 服务
from services.data_api.services.superset_sync_service import (
    get_superset_sync_service,
    SupersetSyncService,
)


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class MigrationResult:
    """迁移结果"""
    success: bool
    dashboard_id: Optional[str] = None
    superset_dashboard_id: Optional[int] = None
    charts_migrated: int = 0
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'success': self.success,
            'dashboard_id': self.dashboard_id,
            'superset_dashboard_id': self.superset_dashboard_id,
            'charts_migrated': self.charts_migrated,
            'errors': self.errors,
        }


@dataclass
class MigrationReport:
    """迁移报告"""
    started_at: datetime
    completed_at: Optional[datetime] = None
    total_dashboards: int = 0
    successful_dashboards: int = 0
    failed_dashboards: int = 0
    total_charts: int = 0
    migrated_charts: int = 0
    results: List[MigrationResult] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'started_at': self.started_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'summary': {
                'total_dashboards': self.total_dashboards,
                'successful_dashboards': self.successful_dashboards,
                'failed_dashboards': self.failed_dashboards,
                'total_charts': self.total_charts,
                'migrated_charts': self.migrated_charts,
                'success_rate': (self.successful_dashboards / self.total_dashboards * 100) if self.total_dashboards > 0 else 0,
            },
            'results': [r.to_dict() for r in self.results],
        }


class BIMigrator:
    """BI 仪表板迁移器"""

    def __init__(
        self,
        superset_url: str = None,
        superset_username: str = None,
        superset_password: str = None,
        db_host: str = None,
        db_port: int = 3306,
        db_username: str = None,
        db_password: str = None,
        db_database: str = None,
    ):
        """
        初始化迁移器

        Args:
            superset_url: Superset URL
            superset_username: Superset 用户名
            superset_password: Superset 密码
            db_host: 数据库主机
            db_port: 数据库端口
            db_username: 数据库用户名
            db_password: 数据库密码
            db_database: 数据库名
        """
        self.superset_service = SupersetSyncService(
            superset_url=superset_url,
            username=superset_username,
            password=superset_password,
        )

        self.db_config = {
            'host': db_host or os.getenv('MYSQL_HOST', 'localhost'),
            'port': db_port or int(os.getenv('MYSQL_PORT', '3306')),
            'username': db_username or os.getenv('MYSQL_USER', 'onedata'),
            'password': db_password or os.getenv('MYSQL_PASSWORD', ''),
            'database': db_database or os.getenv('MYSQL_DATABASE', 'onedata'),
        }

        self.report = MigrationReport(started_at=datetime.now())
        self._db_id: Optional[int] = None

    def connect_superset(self) -> bool:
        """连接到 Superset"""
        try:
            if not self.superset_service.client.login():
                logger.error("连接 Superset 失败")
                return False

            logger.info(f"已连接到 Superset: {self.superset_service.client.base_url}")
            return True

        except Exception as e:
            logger.error(f"连接 Superset 异常: {e}")
            return False

    def sync_database(self) -> bool:
        """同步数据库到 Superset"""
        try:
            logger.info("开始同步数据库...")

            self._db_id = self.superset_service.sync_database(
                name=self.db_config['database'],
                host=self.db_config['host'],
                port=self.db_config['port'],
                username=self.db_config['username'],
                password=self.db_config['password'],
                database=self.db_config['database'],
            )

            if self._db_id:
                logger.info(f"数据库同步成功: ID = {self._db_id}")
                return True
            else:
                logger.error("数据库同步失败")
                return False

        except Exception as e:
            logger.error(f"同步数据库异常: {e}")
            return False

    def migrate_dashboard(
        self,
        bi_dashboard: BIDashboard,
        session,
    ) -> MigrationResult:
        """
        迁移单个仪表板

        Args:
            bi_dashboard: BI 仪表板对象
            session: 数据库会话

        Returns:
            迁移结果
        """
        result = MigrationResult(success=False, dashboard_id=bi_dashboard.dashboard_id)

        try:
            logger.info(f"迁移仪表板: {bi_dashboard.name} ({bi_dashboard.dashboard_id})")

            # 获取仪表板下的图表
            charts = session.query(BIChart).filter(
                BIChart.dashboard_id == bi_dashboard.dashboard_id
            ).all()

            self.report.total_charts += len(charts)
            result.charts_migrated = len(charts)

            # 迁移图表并构建映射
            chart_map = {}

            for chart in charts:
                try:
                    # 创建数据集
                    dataset_id = self.superset_service.sync_dataset(
                        db_id=self._db_id,
                        schema=self.db_config['database'],
                        table_name=f"chart_{chart.chart_id}",
                        dataset_name=f"ds_{chart.chart_id}",
                    )

                    if not dataset_id:
                        result.errors.append(f"图表 {chart.name} 数据集同步失败")
                        continue

                    # 创建图表
                    superset_chart_id = self.superset_service.create_chart_from_bi_chart(
                        bi_chart=chart,
                        dataset_id=dataset_id,
                    )

                    if superset_chart_id:
                        chart_map[chart.name] = superset_chart_id
                        self.report.migrated_charts += 1
                        logger.info(f"  - 图表迁移成功: {chart.name} (ID: {superset_chart_id})")
                    else:
                        result.errors.append(f"图表 {chart.name} 创建失败")

                except Exception as e:
                    result.errors.append(f"图表 {chart.name} 迁移异常: {str(e)}")
                    logger.error(f"  - 图表迁移失败: {chart.name} - {e}")

            # 创建仪表板
            if chart_map:
                superset_dashboard_id = self.superset_service.create_dashboard_from_bi_dashboard(
                    bi_dashboard=bi_dashboard,
                    chart_map=chart_map,
                )

                if superset_dashboard_id:
                    result.success = True
                    result.superset_dashboard_id = superset_dashboard_id
                    self.report.successful_dashboards += 1
                    logger.info(f"仪表板迁移成功: {bi_dashboard.name} -> ID: {superset_dashboard_id}")
                else:
                    result.errors.append("仪表板创建失败")
                    self.report.failed_dashboards += 1
            else:
                result.errors.append("没有成功迁移的图表")
                self.report.failed_dashboards += 1

        except Exception as e:
            result.errors.append(f"仪表板迁移异常: {str(e)}")
            logger.error(f"仪表板迁移异常: {e}")
            self.report.failed_dashboards += 1

        return result

    def migrate_all(
        self,
        dashboard_ids: List[str] = None,
    ) -> MigrationReport:
        """
        迁移所有仪表板

        Args:
            dashboard_ids: 指定要迁移的仪表板 ID（可选）

        Returns:
            迁移报告
        """
        logger.info("=" * 60)
        logger.info("开始 BI 仪表板迁移")
        logger.info("=" * 60)

        # 连接 Superset
        if not self.connect_superset():
            self.report.completed_at = datetime.now()
            return self.report

        # 同步数据库
        if not self.sync_database():
            self.report.completed_at = datetime.now()
            return self.report

        # 获取要迁移的仪表板
        session = get_db()
        query = session.query(BIDashboard)

        if dashboard_ids:
            query = query.filter(BIDashboard.dashboard_id.in_(dashboard_ids))

        dashboards = query.all()
        self.report.total_dashboards = len(dashboards)

        logger.info(f"找到 {len(dashboards)} 个仪表板需要迁移")

        # 迁移每个仪表板
        for dashboard in dashboards:
            result = self.migrate_dashboard(dashboard, session)
            self.report.results.append(result)

        self.report.completed_at = datetime.now()

        # 打印摘要
        self._print_summary()

        return self.report

    def _print_summary(self):
        """打印迁移摘要"""
        logger.info("=" * 60)
        logger.info("迁移完成")
        logger.info("=" * 60)
        logger.info(f"总仪表板数: {self.report.total_dashboards}")
        logger.info(f"成功迁移: {self.report.successful_dashboards}")
        logger.info(f"迁移失败: {self.report.failed_dashboards}")
        logger.info(f"总图表数: {self.report.total_charts}")
        logger.info(f"迁移图表: {self.report.migrated_charts}")
        logger.info(f"成功率: {self.report.to_dict()['summary']['success_rate']:.1f}%")
        logger.info("=" * 60)

    def save_report(self, filepath: str = None):
        """保存迁移报告到文件"""
        if not filepath:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filepath = f"migration_report_{timestamp}.json"

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.report.to_dict(), f, ensure_ascii=False, indent=2)

        logger.info(f"迁移报告已保存到: {filepath}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='BI 仪表板迁移工具')
    parser.add_argument(
        '--superset-url',
        default=os.getenv('SUPERSET_URL', 'http://localhost:8088'),
        help='Superset URL'
    )
    parser.add_argument(
        '--superset-username',
        default=os.getenv('SUPERSET_USERNAME', 'admin'),
        help='Superset 用户名'
    )
    parser.add_argument(
        '--superset-password',
        default=os.getenv('SUPERSET_PASSWORD', 'admin'),
        help='Superset 密码'
    )
    parser.add_argument(
        '--db-host',
        default=os.getenv('MYSQL_HOST', 'localhost'),
        help='数据库主机'
    )
    parser.add_argument(
        '--db-port',
        type=int,
        default=int(os.getenv('MYSQL_PORT', '3306')),
        help='数据库端口'
    )
    parser.add_argument(
        '--db-username',
        default=os.getenv('MYSQL_USER', 'onedata'),
        help='数据库用户名'
    )
    parser.add_argument(
        '--db-password',
        default=os.getenv('MYSQL_PASSWORD', ''),
        help='数据库密码'
    )
    parser.add_argument(
        '--db-database',
        default=os.getenv('MYSQL_DATABASE', 'onedata'),
        help='数据库名'
    )
    parser.add_argument(
        '--dashboard-ids',
        nargs='+',
        help='指定要迁移的仪表板 ID'
    )
    parser.add_argument(
        '--report-file',
        help='迁移报告输出文件'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='仅显示将要迁移的仪表板，不执行实际迁移'
    )

    args = parser.parse_args()

    if args.dry_run:
        logger.info("干跑模式：仅显示将要迁移的仪表板")
        session = get_db()
        query = session.query(BIDashboard)

        if args.dashboard_ids:
            query = query.filter(BIDashboard.dashboard_id.in_(args.dashboard_ids))

        dashboards = query.all()
        logger.info(f"将迁移 {len(dashboards)} 个仪表板:")
        for d in dashboards:
            charts = session.query(BIChart).filter(
                BIChart.dashboard_id == d.dashboard_id
            ).count()
            logger.info(f"  - {d.name} ({d.dashboard_id}): {charts} 个图表")
        return

    # 创建迁移器
    migrator = BIMigrator(
        superset_url=args.superset_url,
        superset_username=args.superset_username,
        superset_password=args.superset_password,
        db_host=args.db_host,
        db_port=args.db_port,
        db_username=args.db_username,
        db_password=args.db_password,
        db_database=args.db_database,
    )

    # 执行迁移
    migrator.migrate_all(dashboard_ids=args.dashboard_ids)

    # 保存报告
    if args.report_file:
        migrator.save_report(args.report_file)
    else:
        migrator.save_report()


if __name__ == '__main__':
    main()
