import argparse
from decimal import Decimal, InvalidOperation
from pathlib import Path

from .analysis import aggregate_weekly_costs, analyze_costs
from .csv_io import read_notes, read_shipments, write_results


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Find unusual weekly freight cost increases.")
    parser.add_argument("--shipments", type=Path, default=Path("data/shipment_records.csv"))
    parser.add_argument("--notes", type=Path, default=Path("data/context_notes.csv"))
    parser.add_argument("--output", type=Path, default=Path("output/cost_anomalies.csv"))
    parser.add_argument("--threshold-percent", default="10", help="Positive rise needed to flag (default: 10).")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        threshold = Decimal(args.threshold_percent)
        if not threshold.is_finite() or threshold < 0:
            raise InvalidOperation
        shipments = read_shipments(args.shipments)
        notes = read_notes(args.notes)
        weekly_costs = aggregate_weekly_costs(shipments)
        results = analyze_costs(weekly_costs, notes, threshold)
        write_results(args.output, results)
    except (OSError, ValueError, InvalidOperation) as error:
        parser.error(str(error))

    flagged_count = sum(row.flagged == "Yes" for row in results)
    justified_count = sum(row.flagged == "No (justified)" for row in results)
    print(f"Wrote {len(results)} route-weeks to {args.output}")
    print(f"Unexplained flags: {flagged_count}; justified increases: {justified_count}")
    print("LLM calls: 0; token usage: 0; model cost: 0 (deterministic local rules)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
