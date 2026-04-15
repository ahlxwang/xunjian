import operator as op
from dataclasses import dataclass
from typing import Optional
from app.collectors.base import HostMetric, DBMetric, ContainerMetric
from app.models.rule import Rule

OPERATORS = {
    ">": op.gt,
    "<": op.lt,
    ">=": op.ge,
    "<=": op.le,
    "==": op.eq,
    "!=": op.ne,
}

# host metric 字段映射：rule.metric_name -> HostMetric 属性名
HOST_METRIC_MAP = {
    "cpu_usage_percent": "cpu_usage_percent",
    "memory_usage_percent": "memory_usage_percent",
    "disk_usage_percent": "disk_usage_percent",
    "load_average_1m": "load_average_1m",
}


@dataclass
class RuleMatch:
    rule: Rule
    risk_level: str
    risk_title: str
    risk_detail: str
    metric_value: float
    threshold_value: float


class RuleEngine:
    def __init__(self, rules: list[Rule]):
        self.rules = [r for r in rules if r.enabled]

    def _compare(self, value: float, operator: str, threshold: float) -> bool:
        fn = OPERATORS.get(operator)
        if fn is None:
            return False
        return fn(value, threshold)

    def evaluate_host(self, metric: HostMetric) -> list[RuleMatch]:
        matches = []
        host_rules = [r for r in self.rules if r.resource_type == "host"]

        for rule in host_rules:
            attr = HOST_METRIC_MAP.get(rule.metric_name)
            if attr is None:
                continue
            value = getattr(metric, attr, None)
            if value is None:
                continue

            # 系统负载特殊处理：阈值=0 表示动态阈值 cpu_core_count * 2
            threshold = rule.threshold_value
            if rule.metric_name == "load_average_1m" and threshold == 0:
                if metric.cpu_core_count is None:
                    continue
                threshold = metric.cpu_core_count * 2.0

            if self._compare(value, rule.operator, threshold):
                matches.append(RuleMatch(
                    rule=rule,
                    risk_level=rule.risk_level,
                    risk_title=f"{metric.resource_name} {rule.rule_name}（当前值: {value:.1f}，阈值: {threshold:.1f}）",
                    risk_detail=rule.description or "",
                    metric_value=value,
                    threshold_value=threshold,
                ))
        return matches

    def evaluate_database(self, metric: DBMetric) -> list[RuleMatch]:
        # Phase 2 实现，Phase 1 返回空
        return []

    def evaluate_container(self, metric: ContainerMetric) -> list[RuleMatch]:
        # Phase 2 实现，Phase 1 返回空
        return []
