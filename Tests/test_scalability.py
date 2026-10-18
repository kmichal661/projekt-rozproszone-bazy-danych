from __future__ import annotations

from .test_response_time import run as run_response_time
from .test_catalog import DESCRIPTIONS
from .test_models import TestResult


def run() -> TestResult:
    result = run_response_time((100, 1000, 10000))
    result.name = DESCRIPTIONS["scalability"].name
    result.section = DESCRIPTIONS["scalability"].section
    result.purpose = DESCRIPTIONS["scalability"].purpose
    result.method = DESCRIPTIONS["scalability"].method
    result.expected = DESCRIPTIONS["scalability"].expected
    return result