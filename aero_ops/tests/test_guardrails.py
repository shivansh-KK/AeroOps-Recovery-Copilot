"""Hard aviation safety constraint tests."""
from datetime import datetime, timedelta, timezone
import pytest

from aero_ops.guardrails.aviation_safety_guard import AviationSafetyGuard
from aero_ops.guardrails.exceptions import AviationSafetyViolation


def test_crew_duty_limit_is_enforced():
    start = datetime(2026, 11, 19, 4, tzinfo=timezone.utc)
    with pytest.raises(AviationSafetyViolation, match="exceeding"):
        AviationSafetyGuard().validate_crew_duty(start, start + timedelta(hours=14, minutes=1), 14)


def test_subminimum_widebody_turn_is_rejected():
    with pytest.raises(AviationSafetyViolation, match="minimum is 90"):
        AviationSafetyGuard().validate_turnaround(60, 90, "A6-EKB")
