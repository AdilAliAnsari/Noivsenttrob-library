"""
Domain logic that doesn't belong to the HTTP layer: the fine strategy
pattern (kept from the original script, now driven by real dates) and
loan-period rules per member type.
"""
from datetime import date, datetime, timedelta

try:
    from .config import LOAN_RULES
except ImportError:
    from config import LOAN_RULES


class Fine:
    """Base fine strategy: flat rate per day late."""
    RATE_PER_DAY = 1.0

    def calculate(self, days_late: int) -> float:
        if days_late <= 0:
            return 0.0
        return round(days_late * self.RATE_PER_DAY, 2)


class StudentFine(Fine):
    RATE_PER_DAY = 0.5


class FacultyFine(Fine):
    def calculate(self, days_late: int) -> float:
        return 0.0


def get_fine_calculator(member_type: str) -> Fine:
    return {
        "Student": StudentFine(),
        "Faculty": FacultyFine(),
    }.get(member_type, Fine())


def loan_rules_for(member_type: str) -> dict:
    return LOAN_RULES.get(member_type, LOAN_RULES["Member"])


def compute_due_date(member_type: str, issued_on: date | None = None) -> date:
    issued_on = issued_on or date.today()
    days = loan_rules_for(member_type)["loan_days"]
    return issued_on + timedelta(days=days)


def days_late(due_date: date, returned_on: date | None = None) -> int:
    returned_on = returned_on or date.today()
    return max(0, (returned_on - due_date).days)


def parse_date(value: str) -> date:
    return datetime.fromisoformat(value).date()