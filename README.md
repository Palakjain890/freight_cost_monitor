# Freight Cost Monitor

This project looks for freight costs that have gone up unusually on a route. It reads the shipment data and context notes, then writes one result row for each route and week.

You can run it locally with Python 3.9 or newer. It has no third-party dependencies, API keys, or service to configure.

## Run it

Open a terminal in the project folder, the one containing this README. The input files are already in `data/`. Run:

```sh
PYTHONPATH=src python3 -m freight_cost_monitor.cli
```

The results are written to `output/cost_anomalies.csv`. The command prints how many route-weeks it processed and how many increases were flagged.

To use different input files, or change the default 10% flag threshold, pass options like this:

```sh
PYTHONPATH=src python3 -m freight_cost_monitor.cli \
	--shipments data/shipment_records.csv \
	--notes data/context_notes.csv \
	--output output/cost_anomalies.csv \
	--threshold-percent 10
```

## Run the tests

From the same project folder, run:

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

The tests cover Monday-based weeks, weekly cost calculations, the eight-week history baseline, comparison with peer routes, and whether a note really applies to a route and date. They also run a small 12-case check of note matching.

## What the results mean

The cost per tonne-km for a week is the total freight cost divided by the total tonne-kilometres shipped that week. The history comparison uses up to eight prior calendar weeks and never includes the week being checked. The peer comparison uses the other routes of the same route type in that week; it leaves the current route out.

A row is flagged when its cost is at least 10% above either available comparison and is rising. The threshold can be changed with `--threshold-percent`. An increase is marked `No (justified)` only if one of the notes that explicitly supports a cost increase matches the route and time period. Other notes, such as those describing stable conditions or saying costs were not affected, do not count as justification. Unexplained increases have a blank `matched_note_id` and are left for human review.

The notes are few and have clear route and date fields, so this version checks them with explicit rules instead of sending them to a language model or a vector database. That keeps the result repeatable and avoids inventing explanations. The output follows the supplied eight-column CSV format. If a comparison baseline is unavailable, its value is shown as `N/A`.

## Reproducibility and cost

The same input produces the same CSV each time. To check this yourself, run the program three times and compare the files:

```sh
PYTHONPATH=src python3 -m freight_cost_monitor.cli --output /tmp/run-1.csv
PYTHONPATH=src python3 -m freight_cost_monitor.cli --output /tmp/run-2.csv
PYTHONPATH=src python3 -m freight_cost_monitor.cli --output /tmp/run-3.csv
cmp /tmp/run-1.csv /tmp/run-2.csv
cmp /tmp/run-2.csv /tmp/run-3.csv
```

If both `cmp` commands finish without output, the files are identical. The completed check is recorded in `artifacts/reproducibility.txt`. The note-matching check is summarized in `artifacts/evaluation.txt`.

This run does not call a model, so it uses zero model tokens and has no model usage cost. The full-run log is in `artifacts/token_cost_log.txt`.
