from __future__ import annotations

import csv
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from .models import AnalysisRow, ContextNote, Shipment

SHIPMENT_COLUMNS = {
    "origin",
    "destination",
    "route_type",
    "quantity_tonnes",
    "distance_km",
    "freight_cost_inr",
    "shipment_date",
}
NOTE_COLUMNS = {"note_id", "date", "applies_to", "note"}
OUTPUT_COLUMNS = [
    "route",
    "week_of",
    "cost_per_tonne_km",
    "vs_own_history",
    "vs_similar_routes",
    "flagged",
    "matched_note_id",
    "reason",
]


def _read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        if reader.fieldnames is None:
            raise ValueError(f"CSV has no header: {path}")
        return reader.fieldnames, list(reader)


def read_shipments(path: Path) -> list[Shipment]:
    columns, rows = _read_csv(path)
    missing = SHIPMENT_COLUMNS - set(columns)
    if missing:
        raise ValueError(f"Shipment CSV is missing columns: {', '.join(sorted(missing))}")

    shipments = []
    for line_number, row in enumerate(rows, start=2):
        try:
            shipment = Shipment(
                origin=row["origin"].strip(),
                destination=row["destination"].strip(),
                route_type=row["route_type"].strip(),
                quantity_tonnes=Decimal(row["quantity_tonnes"]),
                distance_km=Decimal(row["distance_km"]),
                freight_cost_inr=Decimal(row["freight_cost_inr"]),
                shipment_date=date.fromisoformat(row["shipment_date"]),
            )
        except (InvalidOperation, TypeError, ValueError) as error:
            raise ValueError(f"Invalid shipment data on CSV line {line_number}: {error}") from error
        if not shipment.origin or not shipment.destination or not shipment.route_type:
            raise ValueError(f"Route fields cannot be blank on CSV line {line_number}")
        if shipment.quantity_tonnes <= 0 or shipment.distance_km <= 0 or shipment.freight_cost_inr < 0:
            raise ValueError(f"Invalid quantity, distance, or cost on CSV line {line_number}")
        shipments.append(shipment)
    return shipments


def read_notes(path: Path) -> list[ContextNote]:
    columns, rows = _read_csv(path)
    missing = NOTE_COLUMNS - set(columns)
    if missing:
        raise ValueError(f"Context notes CSV is missing columns: {', '.join(sorted(missing))}")
    return [
        ContextNote(
            note_id=row["note_id"].strip(),
            date=date.fromisoformat(row["date"]),
            applies_to=row["applies_to"].strip(),
            text=row["note"].strip(),
        )
        for row in rows
    ]


def write_results(path: Path, results: list[AnalysisRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        for result in results:
            writer.writerow(
                {
                    "route": result.route,
                    "week_of": result.week_of.isoformat(),
                    "cost_per_tonne_km": f"{result.cost_per_tonne_km:.2f}",
                    "vs_own_history": format_change(result.own_history_change_pct, "own"),
                    "vs_similar_routes": format_change(result.similar_routes_change_pct, "peers"),
                    "flagged": result.flagged,
                    "matched_note_id": result.matched_note_id,
                    "reason": result.reason,
                }
            )


def format_change(change: Decimal | None, baseline: str) -> str:
    if change is None:
        if baseline == "own":
            return "N/A (no prior weeks)"
        return "N/A (no peer routes this week)"
    if baseline == "own":
        return f"{change:+.1f}% vs this route's past average"
    return f"{change:+.1f}% vs similar-length routes this week"
