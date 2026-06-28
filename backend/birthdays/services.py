import calendar
from datetime import date


def birthday_day_month_for_year(birth_date: date, year: int) -> tuple[int, int]:
    if birth_date.month == 2 and birth_date.day == 29:
        if calendar.isleap(year):
            return 2, 29
        return 2, 28
    return birth_date.month, birth_date.day


def next_birthday(birth_date: date, from_date: date | None = None) -> date:
    reference = from_date or date.today()
    year = reference.year
    month, day = birthday_day_month_for_year(birth_date, year)
    candidate = date(year, month, day)
    if candidate < reference:
        year += 1
        month, day = birthday_day_month_for_year(birth_date, year)
        candidate = date(year, month, day)
    return candidate


def days_until_birthday(birth_date: date, from_date: date | None = None) -> int:
    reference = from_date or date.today()
    return (next_birthday(birth_date, reference) - reference).days


def birthday_in_month(birth_date: date, year: int, month: int) -> date | None:
    month_, day = birthday_day_month_for_year(birth_date, year)
    if month_ != month:
        return None
    return date(year, month_, day)
