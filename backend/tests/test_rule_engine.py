import pytest
from app.engine.rule_engine import RuleEngine, RuleMatch
from app.collectors.base import HostMetric
from app.models.rule import Rule


def make_rule(rule_code, metric_name, operator, threshold, risk_level, resource_type="host"):
    rule = Rule()
    rule.id = 1
    rule.rule_code = rule_code
    rule.rule_name = rule_code
    rule.resource_type = resource_type
    rule.metric_name = metric_name
    rule.operator = operator
    rule.threshold_value = threshold
    rule.risk_level = risk_level
    rule.enabled = True
    rule.description = ""
    return rule


def test_cpu_critical_rule_matches():
    rules = [make_rule("host_cpu_critical", "cpu_usage_percent", ">", 90.0, "critical")]
    engine = RuleEngine(rules)
    metric = HostMetric(
        resource_id="192.168.1.1:9100",
        resource_name="192.168.1.1",
        cloud_provider="idc",
        cpu_usage_percent=92.0,
    )
    matches = engine.evaluate_host(metric)
    assert len(matches) == 1
    assert matches[0].risk_level == "critical"
    assert matches[0].metric_value == 92.0


def test_cpu_normal_no_match():
    rules = [make_rule("host_cpu_critical", "cpu_usage_percent", ">", 90.0, "critical")]
    engine = RuleEngine(rules)
    metric = HostMetric(
        resource_id="192.168.1.1:9100",
        resource_name="192.168.1.1",
        cloud_provider="idc",
        cpu_usage_percent=50.0,
    )
    matches = engine.evaluate_host(metric)
    assert matches == []


def test_multiple_rules_multiple_matches():
    rules = [
        make_rule("host_cpu_high", "cpu_usage_percent", ">", 80.0, "high"),
        make_rule("host_disk_critical", "disk_usage_percent", ">", 90.0, "critical"),
    ]
    engine = RuleEngine(rules)
    metric = HostMetric(
        resource_id="192.168.1.1:9100",
        resource_name="192.168.1.1",
        cloud_provider="idc",
        cpu_usage_percent=85.0,
        disk_usage_percent=95.0,
    )
    matches = engine.evaluate_host(metric)
    assert len(matches) == 2


def test_disabled_rule_skipped():
    rule = make_rule("host_cpu_critical", "cpu_usage_percent", ">", 90.0, "critical")
    rule.enabled = False
    engine = RuleEngine([rule])
    metric = HostMetric(
        resource_id="192.168.1.1:9100",
        resource_name="192.168.1.1",
        cloud_provider="idc",
        cpu_usage_percent=99.0,
    )
    matches = engine.evaluate_host(metric)
    assert matches == []


def test_load_average_rule_with_core_count():
    """系统负载 > CPU核心数*2 触发告警"""
    rules = [make_rule("host_load_high", "load_average_1m", ">", 0, "high")]
    # 特殊规则：阈值由 cpu_core_count * 2 动态计算，threshold_value=0 表示动态
    engine = RuleEngine(rules)
    metric = HostMetric(
        resource_id="192.168.1.1:9100",
        resource_name="192.168.1.1",
        cloud_provider="idc",
        load_average_1m=10.0,
        cpu_core_count=4,
    )
    matches = engine.evaluate_host(metric)
    assert len(matches) == 1
    assert matches[0].threshold_value == 8.0  # 4 * 2
