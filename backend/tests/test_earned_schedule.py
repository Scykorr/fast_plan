from datetime import date
from types import SimpleNamespace

from projects.cpm import compute_evm_lite


def _activity(start, end, progress):
    return SimpleNamespace(
        progress=progress,
        start_date=start,
        end_date=end,
    )


def test_earned_schedule_on_time():
    project = SimpleNamespace(budget=100)
    activities = [
        _activity(date(2026, 1, 1), date(2026, 1, 11), 50),
    ]
    as_of = date(2026, 1, 6)
    evm = compute_evm_lite(project, activities, actual_cost=0, as_of=as_of)
    assert evm["percent_complete"] == 50
    assert evm["earned_schedule_date"] == "2026-01-06"
    assert evm["schedule_variance_time"] == 0
    assert evm["spi_t"] == 1.0
    assert evm["planned_duration_days"] == 10
    assert evm["earned_duration_days"] == 5


def test_earned_schedule_behind():
    project = SimpleNamespace(budget=100)
    activities = [
        _activity(date(2026, 1, 1), date(2026, 1, 11), 20),
    ]
    as_of = date(2026, 1, 6)
    evm = compute_evm_lite(project, activities, as_of=as_of)
    assert evm["earned_schedule_date"] == "2026-01-03"
    assert evm["schedule_variance_time"] == -3
    assert evm["spi_t"] == 0.4
