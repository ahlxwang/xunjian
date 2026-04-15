"""seed default inspection rules

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-15
"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime

revision = '0002'
down_revision = '0001'


def upgrade() -> None:
    now = datetime.utcnow()
    op.bulk_insert(
        sa.table('rules',
            sa.column('rule_code', sa.String),
            sa.column('rule_name', sa.String),
            sa.column('resource_type', sa.String),
            sa.column('metric_name', sa.String),
            sa.column('operator', sa.String),
            sa.column('threshold_value', sa.Float),
            sa.column('risk_level', sa.String),
            sa.column('enabled', sa.Boolean),
            sa.column('description', sa.Text),
            sa.column('created_at', sa.DateTime),
            sa.column('updated_at', sa.DateTime),
        ),
        [
            # 主机规则
            dict(rule_code='host_cpu_critical', rule_name='CPU使用率严重', resource_type='host',
                 metric_name='cpu_usage_percent', operator='>', threshold_value=90.0,
                 risk_level='critical', enabled=True, description='CPU使用率超过90%', created_at=now, updated_at=now),
            dict(rule_code='host_cpu_high', rule_name='CPU使用率高危', resource_type='host',
                 metric_name='cpu_usage_percent', operator='>', threshold_value=80.0,
                 risk_level='high', enabled=True, description='CPU使用率超过80%', created_at=now, updated_at=now),
            dict(rule_code='host_memory_critical', rule_name='内存使用率严重', resource_type='host',
                 metric_name='memory_usage_percent', operator='>', threshold_value=95.0,
                 risk_level='critical', enabled=True, description='内存使用率超过95%', created_at=now, updated_at=now),
            dict(rule_code='host_memory_high', rule_name='内存使用率高危', resource_type='host',
                 metric_name='memory_usage_percent', operator='>', threshold_value=85.0,
                 risk_level='high', enabled=True, description='内存使用率超过85%', created_at=now, updated_at=now),
            dict(rule_code='host_disk_critical', rule_name='磁盘使用率严重', resource_type='host',
                 metric_name='disk_usage_percent', operator='>', threshold_value=92.0,
                 risk_level='critical', enabled=True, description='磁盘使用率超过92%', created_at=now, updated_at=now),
            dict(rule_code='host_disk_high', rule_name='磁盘使用率高危', resource_type='host',
                 metric_name='disk_usage_percent', operator='>', threshold_value=85.0,
                 risk_level='high', enabled=True, description='磁盘使用率超过85%', created_at=now, updated_at=now),
            dict(rule_code='host_load_high', rule_name='系统负载高危', resource_type='host',
                 metric_name='load_average_1m', operator='>', threshold_value=0.0,
                 risk_level='high', enabled=True, description='系统负载超过CPU核心数*2，threshold_value=0表示动态阈值', created_at=now, updated_at=now),
        ]
    )


def downgrade() -> None:
    op.execute("DELETE FROM rules WHERE rule_code IN ('host_cpu_critical','host_cpu_high','host_memory_critical','host_memory_high','host_disk_critical','host_disk_high','host_load_high')")
