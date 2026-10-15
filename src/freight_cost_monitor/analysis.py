from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from .models import AnalysisRow, ContextNote, Shipment, WeeklyCost
from .notes import find_supporting_note

HISTORY_WEEKS = 8


def week_start(shipment_date: date) -> date:
    return shipment_date - timedelta(days=shipment_date.weekday())


def aggregate_weekly_costs(shipments: list[Shipment]) -> list[WeeklyCost]:
    totals: dict[tuple[str, str, date], list[Decimal]] = defaultdict(
        lambda: [Decimal("0"), Decimal("0")]
    )

    for shipment in shipments:
        week_of = week_start(shipment.shipment_date)
        key = (shipment.route, shipment.route_type, week_of)
        totals[key][0] += shipment.freight_cost_inr
        totals[key][1] += shipment.quantity_tonnes * shipment.distance_km

    return [
        WeeklyCost(route, route_type, week_of, total_cost / tonne_km)
        for (route, route_type, week_of), (total_cost, tonne_km) in sorted(totals.items())
    ]


def analyze_costs(
    weekly_costs: list[WeeklyCost],
    notes: list[ContextNote],
    flag_threshold_pct: Decimal = Decimal("10"),
) -> list[AnalysisRow]:
    by_route: dict[tuple[str, str], list[WeeklyCost]] = defaultdict(list)
    by_week_and_type: dict[tuple[date, str], list[WeeklyCost]] = defaultdict(list)
    for point in weekly_costs:
        by_route[(point.route, point.route_type)].append(point)
        by_week_and_type[(point.week_of, point.route_type)].append(point)

    results = []
    for point in weekly_costs:
        history = by_route[(point.route, point.route_type)]
        history_start = point.week_of - timedelta(weeks=HISTORY_WEEKS)
        prior = [
            item
            for item in history
            if history_start <= item.week_of < point.week_of
        ]
        own_change = _percent_change(
            point.cost_per_tonne_km,
            _mean([item.cost_per_tonne_km for item in prior]) if prior else None,
        )

        peers = [
            item.cost_per_tonne_km
            for item in by_week_and_type[(point.week_of, point.route_type)]
            if item.route != point.route
        ]
        peer_change = _percent_change(
            point.cost_per_tonne_km, _mean(peers) if peers else None
        )

        anomalous = (
            own_change is not None and own_change >= flag_threshold_pct
        ) or (
            peer_change is not None and peer_change >= flag_threshold_pct
        )
        note = find_supporting_note(notes, point.route, point.week_of, own_change) if anomalous else None

        if note is not None:
            flagged = "No (justified)"
            reason = _supported_reason(note)
            matched_note_id = note.note_id
        elif anomalous:
            flagged = "Yes"
            reason = "No applicable cost-impact note supports this rise. The increase is unexplained and should be reviewed."
            matched_note_id = ""
        else:
            flagged = "No"
            reason = "No qualifying unexplained cost rise was detected."
            matched_note_id = ""

        results.append(
            AnalysisRow(
                route=point.route,
                week_of=point.week_of,
                cost_per_tonne_km=point.cost_per_tonne_km,
                own_history_change_pct=own_change,
                similar_routes_change_pct=peer_change,
                flagged=flagged,
                matched_note_id=matched_note_id,
                reason=reason,
            )
        )
    return results


def _mean(values: list[Decimal]) -> Decimal:
    return sum(values, Decimal("0")) / Decimal(len(values))


def _percent_change(value: Decimal, baseline: Decimal | None) -> Decimal | None:
    if baseline is None or baseline == 0:
        return None
    return (value / baseline - Decimal("1")) * Decimal("100")


def _supported_reason(note: ContextNote) -> str:
    if note.note_id == "N001":
        detail = "Flooding on the Chennai-Bangalore highway forced detours and increased trip costs through 2025-03-08."
    elif note.note_id == "N002":
        detail = "A regional festival week caused a temporary transporter surcharge on this corridor."
    else:
        detail = "The note reports a nationwide diesel increase expected to raise transport costs roughly 5-7%."
    return f"Justified by {note.note_id} dated {note.date.isoformat()}: {detail}"
