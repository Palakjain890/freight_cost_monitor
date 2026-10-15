import unittest
from datetime import date, timedelta
from decimal import Decimal

from freight_cost_monitor.analysis import aggregate_weekly_costs, analyze_costs, week_start
from freight_cost_monitor.models import ContextNote, Shipment, WeeklyCost
from freight_cost_monitor.notes import find_supporting_note


def shipment(origin, destination, route_type, quantity, distance, cost, shipped):
    return Shipment(
        origin,
        destination,
        route_type,
        Decimal(quantity),
        Decimal(distance),
        Decimal(cost),
        date.fromisoformat(shipped),
    )


class AnalysisTests(unittest.TestCase):
    def test_week_starts_on_monday(self):
        self.assertEqual(week_start(date(2025, 2, 26)), date(2025, 2, 24))

    def test_weekly_cost_is_weighted_by_tonne_kilometres(self):
        records = [
            shipment("A", "B", "Short", "1", "10", "100", "2025-01-06"),
            shipment("A", "B", "Short", "2", "10", "100", "2025-01-12"),
        ]
        result = aggregate_weekly_costs(records)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].cost_per_tonne_km, Decimal("200") / Decimal("30"))

    def test_history_excludes_current_week_and_peer_average_excludes_route(self):
        points = [
            WeeklyCost("A-B", "Short", date(2025, 1, 6), Decimal("10")),
            WeeklyCost("A-B", "Short", date(2025, 1, 13), Decimal("12")),
            WeeklyCost("C-D", "Short", date(2025, 1, 13), Decimal("8")),
        ]
        result = analyze_costs(points, [], Decimal("10"))[-2]
        self.assertEqual(result.own_history_change_pct, Decimal("20"))
        self.assertEqual(result.similar_routes_change_pct, Decimal("50"))
        self.assertEqual(result.flagged, "Yes")

    def test_peer_comparison_can_flag_first_observed_week(self):
        points = [
            WeeklyCost("A-B", "Short", date(2025, 1, 6), Decimal("15")),
            WeeklyCost("C-D", "Short", date(2025, 1, 6), Decimal("10")),
        ]
        result = analyze_costs(points, [], Decimal("10"))[0]
        self.assertIsNone(result.own_history_change_pct)
        self.assertEqual(result.similar_routes_change_pct, Decimal("50"))
        self.assertEqual(result.flagged, "Yes")

    def test_history_uses_at_most_eight_prior_observations(self):
        points = [
            WeeklyCost("A-B", "Short", date(2025, 1, 6) + timedelta(weeks=index), Decimal(index + 1))
            for index in range(10)
        ]
        result = analyze_costs(points, [], Decimal("1000"))[-1]
        self.assertEqual(
            result.own_history_change_pct,
            (Decimal("10") / Decimal("5.5") - Decimal("1")) * Decimal("100"),
        )

    def test_only_exact_route_and_effective_window_note_can_support(self):
        note = ContextNote("N001", date(2025, 2, 24), "Chennai-Bangalore", "flooding raised costs")
        self.assertIsNotNone(find_supporting_note([note], "Chennai-Bangalore", date(2025, 3, 3), Decimal("15")))
        self.assertIsNone(find_supporting_note([note], "Mumbai-Pune", date(2025, 3, 3), Decimal("15")))
        self.assertIsNone(find_supporting_note([note], "Chennai-Bangalore", date(2025, 3, 10), Decimal("15")))

    def test_unaffected_notes_cannot_justify_costs(self):
        note = ContextNote("N005", date(2024, 7, 29), "Mumbai-Delhi", "costs were not significantly affected")
        self.assertIsNone(find_supporting_note([note], "Mumbai-Delhi", date(2024, 7, 29), Decimal("15")))

    def test_labeled_note_retrieval_evaluation(self):
        notes = [
            ContextNote("N001", date(2025, 2, 24), "Chennai-Bangalore", "flooding increased costs"),
            ContextNote("N002", date(2025, 1, 20), "Ahmedabad-Mumbai", "festival surcharge"),
            ContextNote("N003", date(2025, 5, 5), "All Routes", "diesel increased costs 5-7%"),
            ContextNote("N004", date(2024, 3, 11), "All Routes", "affected routes are not in dataset"),
            ContextNote("N005", date(2024, 7, 29), "Mumbai-Delhi", "costs were not significantly affected"),
            ContextNote("N006", date(2025, 9, 22), "All Routes", "stable demand"),
            ContextNote("N007", date(2024, 5, 20), "Delhi-Jaipur", "road conditions improved"),
            ContextNote("N008", date(2025, 6, 9), "Kolkata-Bhubaneswar", "no significant disruption"),
            ContextNote("N009", date(2025, 3, 17), "Chennai-Bangalore", "route returned to normal"),
            ContextNote("N010", date(2025, 10, 27), "All Routes", "no rate change"),
        ]
        labeled_cases = [
            ("Chennai-Bangalore", date(2025, 3, 3), Decimal("15"), "N001"),
            ("Chennai-Bangalore", date(2025, 3, 10), Decimal("15"), None),
            ("Mumbai-Pune", date(2025, 3, 3), Decimal("15"), None),
            ("Ahmedabad-Mumbai", date(2025, 1, 20), Decimal("29"), "N002"),
            ("Mumbai-Pune", date(2025, 1, 20), Decimal("29"), None),
            ("Mumbai-Pune", date(2025, 5, 5), Decimal("6"), "N003"),
            ("Mumbai-Pune", date(2025, 5, 5), Decimal("9"), None),
            ("Mumbai-Pune", date(2024, 3, 11), Decimal("30"), None),
            ("Mumbai-Delhi", date(2024, 7, 29), Decimal("30"), None),
            ("Delhi-Jaipur", date(2024, 5, 20), Decimal("30"), None),
            ("Kolkata-Bhubaneswar", date(2025, 6, 9), Decimal("30"), None),
            ("Mumbai-Pune", date(2025, 10, 27), Decimal("30"), None),
        ]

        correct = sum(
            (note.note_id if note else None) == expected_note_id
            for route, week, change, expected_note_id in labeled_cases
            for note in [find_supporting_note(notes, route, week, change)]
        )
        self.assertEqual(correct, len(labeled_cases))


if __name__ == "__main__":
    unittest.main()
