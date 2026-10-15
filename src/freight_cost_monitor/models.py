from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class Shipment:
    origin: str
    destination: str
    route_type: str
    quantity_tonnes: Decimal
    distance_km: Decimal
    freight_cost_inr: Decimal
    shipment_date: date

    @property
    def route(self) -> str:
        return f"{self.origin}-{self.destination}"


@dataclass(frozen=True)
class WeeklyCost:
    route: str
    route_type: str
    week_of: date
    cost_per_tonne_km: Decimal


@dataclass(frozen=True)
class ContextNote:
    note_id: str
    date: date
    applies_to: str
    text: str


@dataclass(frozen=True)
class AnalysisRow:
    route: str
    week_of: date
    cost_per_tonne_km: Decimal
    own_history_change_pct: Decimal | None
    similar_routes_change_pct: Decimal | None
    flagged: str
    matched_note_id: str
    reason: str
