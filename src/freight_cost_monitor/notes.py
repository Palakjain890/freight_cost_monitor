from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from .models import ContextNote


SUPPORT_RULES = {
    "N001": ("Chennai-Bangalore", date(2025, 2, 24), date(2025, 3, 8), "disruption"),
    "N002": ("Ahmedabad-Mumbai", date(2025, 1, 20), date(2025, 1, 26), "surcharge"),
    "N003": ("All Routes", date(2025, 5, 5), None, "fuel"),
}


def find_supporting_note(
    notes: list[ContextNote], route: str, week_of: date, own_change_pct: Decimal | None
) -> ContextNote | None:
    """Return the first explicitly applicable note that supports this week's rise."""
    week_end = week_of + timedelta(days=6)
    for note in notes:
        rule = SUPPORT_RULES.get(note.note_id)
        if rule is None:
            continue

        scope, effective_from, effective_to, reason_type = rule
        if note.applies_to != scope or note.date != effective_from:
            continue
        if scope != "All Routes" and scope != route:
            continue
        if week_end < effective_from or (effective_to is not None and week_of > effective_to):
            continue

        if reason_type in {"disruption", "surcharge"}:
            return note
        if reason_type == "fuel" and own_change_pct is not None:
            if Decimal("5") <= own_change_pct <= Decimal("7"):
                return note
    return None
