from datetime import date

import pytest

from birthdays.services import next_birthday


@pytest.mark.parametrize(
    ("birth_date", "from_date", "expected"),
    [
        (date(2000, 2, 29), date(2025, 2, 1), date(2025, 2, 28)),
        (date(2000, 2, 29), date(2024, 2, 1), date(2024, 2, 29)),
        (date(1990, 6, 15), date(2026, 6, 15), date(2026, 6, 15)),
        (date(1990, 6, 15), date(2026, 6, 16), date(2027, 6, 15)),
    ],
)
def test_next_birthday(birth_date, from_date, expected):
    assert next_birthday(birth_date, from_date) == expected
