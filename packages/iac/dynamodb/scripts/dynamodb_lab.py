#!/usr/bin/env python3
"""Small AWS CLI driver for the academic DynamoDB event activity lab."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import subprocess
import sys
import tempfile
import time
import uuid
from typing import Any


EVENT_TYPES = ("login", "lesson_started", "quiz_answer", "mentor_message", "xp_granted")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("load", "simulate", "query", "metrics", "validate-fixtures"))
    parser.add_argument("--table", default="")
    parser.add_argument("--profile", default="shifu-lab")
    parser.add_argument("--region", default="us-east-2")
    parser.add_argument("--fixtures", type=pathlib.Path, required=True)
    parser.add_argument("--evidence-dir", type=pathlib.Path, default=pathlib.Path("evidence-local"))
    parser.add_argument("--responsible", default="Gabriel da Silva")
    parser.add_argument("--learner", default="learner-001")
    parser.add_argument("--event-type", choices=EVENT_TYPES, default="login")
    parser.add_argument("--event-date", default="2026-11-17")
    parser.add_argument("--start-time", default="")
    parser.add_argument("--end-time", default="")
    parser.add_argument("--expected-table-units", type=float, default=None)
    parser.add_argument("--expected-gsi-units", type=float, default=None)
    return parser.parse_args()


def dynamodb_value(value: Any) -> dict[str, Any]:
    if value is None:
        return {"NULL": True}
    if isinstance(value, bool):
        return {"BOOL": value}
    if isinstance(value, str):
        return {"S": value}
    if isinstance(value, (int, float)):
        return {"N": str(value)}
    if isinstance(value, list):
        return {"L": [dynamodb_value(entry) for entry in value]}
    if isinstance(value, dict):
        return {"M": {key: dynamodb_value(entry) for key, entry in value.items()}}
    raise TypeError(f"Unsupported fixture value type: {type(value).__name__}")


def make_item(event: dict[str, Any]) -> dict[str, Any]:
    occurred_at = event["occurred_at"]
    event_date = occurred_at[:10]
    item = {
        "PK": f"LEARNER#{event['learner_id']}",
        "SK": f"{occurred_at}#{event['event_id']}",
        "GSI1PK": f"EVENT#{event['event_type']}#{event_date}",
        "GSI1SK": f"{occurred_at}#{event['learner_id']}#{event['event_id']}",
        "eventType": event["event_type"],
        "eventId": event["event_id"],
        "learnerId": event["learner_id"],
        "occurredAt": occurred_at,
        "eventDate": event_date,
        "attributes": event["attributes"],
    }
    return {key: dynamodb_value(value) for key, value in item.items()}


def load_events(path: pathlib.Path) -> list[dict[str, Any]]:
    events = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(events, list):
        raise ValueError("Fixture root must be a JSON array")
    return events


def write_evidence(args: argparse.Namespace, name: str, data: dict[str, Any]) -> pathlib.Path:
    args.evidence_dir.mkdir(parents=True, exist_ok=True)
    path = args.evidence_dir / name
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def aws(args: argparse.Namespace, operation: list[str], payload: dict[str, Any] | None = None) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="shifu-dynamodb-") as directory:
        command = ["aws", *operation]
        if payload is not None:
            request_path = pathlib.Path(directory) / "request.json"
            request_path.write_text(json.dumps(payload), encoding="utf-8")
            command.extend(["--cli-input-json", f"file://{request_path}"])
        command.extend(["--profile", args.profile, "--region", args.region, "--output", "json", "--no-cli-pager"])
        result = subprocess.run(command, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"AWS CLI exited with {result.returncode}")
    return json.loads(result.stdout) if result.stdout.strip() else {}


def require_table(args: argparse.Namespace) -> None:
    if not args.table:
        raise ValueError("Set --table or apply the Terraform lab so its output is available")


def validate_fixtures(events: list[dict[str, Any]]) -> dict[str, Any]:
    if len(events) < 15:
        raise ValueError(f"Expected at least 15 items, found {len(events)}")
    if set(event["event_type"] for event in events) != set(EVENT_TYPES):
        raise ValueError("Fixture must include all five requested event types")
    keys = [(event["learner_id"], event["occurred_at"], event["event_id"]) for event in events]
    if len(keys) != len(set(keys)):
        raise ValueError("Fixture contains duplicate composite keys")
    return {
        "items": len(events),
        "event_types": {event_type: sum(event["event_type"] == event_type for event in events) for event_type in EVENT_TYPES},
        "learners": len({event["learner_id"] for event in events}),
        "unique_composite_keys": len(keys),
    }


def write_events(args: argparse.Namespace, events: list[dict[str, Any]], pacing_seconds: float) -> dict[str, Any]:
    require_table(args)
    started = dt.datetime.now(dt.timezone.utc)
    consumed_table = 0.0
    consumed_indexes = 0.0
    failures: list[dict[str, str]] = []
    successes = 0
    for index, event in enumerate(events):
        try:
            response = aws(args, ["dynamodb", "put-item"], {
                "TableName": args.table,
                "Item": make_item(event),
                "ReturnConsumedCapacity": "INDEXES",
            })
            capacity = response.get("ConsumedCapacity", {})
            consumed_table += float(capacity.get("Table", {}).get("CapacityUnits", 0))
            consumed_indexes += sum(float(value.get("CapacityUnits", 0)) for value in capacity.get("GlobalSecondaryIndexes", {}).values())
            successes += 1
        except RuntimeError as error:
            failures.append({"event_id": event["event_id"], "error": str(error)})
        if pacing_seconds and index + 1 < len(events):
            time.sleep(pacing_seconds)
    finished = dt.datetime.now(dt.timezone.utc)
    return {
        "table": args.table,
        "start_time_utc": started.isoformat(),
        "end_time_utc": finished.isoformat(),
        "writes_succeeded": successes,
        "writes_failed": len(failures),
        "failure_details": failures,
        "duration_seconds": round((finished - started).total_seconds(), 3),
        "pacing_seconds": pacing_seconds,
        "capacity_units_from_put_item_responses": {
            "table": consumed_table,
            "global_secondary_indexes": consumed_indexes,
        },
        "interpretation": "Symbolic low-rate activity simulation; it is not an AWS service-limit test.",
    }


def simulate_events() -> list[dict[str, Any]]:
    run_id = uuid.uuid4().hex[:12]
    now = dt.datetime.now(dt.timezone.utc)
    events = []
    for index in range(60):
        occurred_at = (now + dt.timedelta(seconds=index)).isoformat(timespec="microseconds").replace("+00:00", "Z")
        events.append({
            "learner_id": f"simulation-{run_id}",
            "event_id": f"sim-{run_id}-{index + 1:03d}",
            "event_type": EVENT_TYPES[index % len(EVENT_TYPES)],
            "occurred_at": occurred_at,
            "attributes": {"simulation_run": run_id, "sequence": index + 1, "fictitious": True},
        })
    return events


def query_examples(args: argparse.Namespace) -> dict[str, Any]:
    require_table(args)
    sample_events = load_events(args.fixtures)
    event = next(event for event in sample_events if event["learner_id"] == args.learner)
    item_response = aws(args, ["dynamodb", "get-item"], {
        "TableName": args.table,
        "Key": {"PK": {"S": f"LEARNER#{args.learner}"}, "SK": {"S": f"{event['occurred_at']}#{event['event_id']}"}},
        "ConsistentRead": True,
    })
    learner_response = aws(args, ["dynamodb", "query"], {
        "TableName": args.table,
        "KeyConditionExpression": "PK = :pk",
        "ExpressionAttributeValues": {":pk": {"S": f"LEARNER#{args.learner}"}},
        "ScanIndexForward": True,
    })
    index_response = aws(args, ["dynamodb", "query"], {
        "TableName": args.table,
        "IndexName": "EventTypeDayIndex",
        "KeyConditionExpression": "GSI1PK = :gsi1pk",
        "ExpressionAttributeValues": {":gsi1pk": {"S": f"EVENT#{args.event_type}#{args.event_date}"}},
        "ScanIndexForward": True,
    })
    return {
        "table": args.table,
        "profile": args.profile,
        "region": args.region,
        "responsible": args.responsible,
        "get_item_found": "Item" in item_response,
        "learner_query_count": learner_response.get("Count", 0),
        "gsi_query": {"event_type": args.event_type, "event_date": args.event_date, "count": index_response.get("Count", 0)},
        "results": {"get_item": item_response, "learner_query": learner_response, "gsi_query": index_response},
    }


def metric_statistics(args: argparse.Namespace, dimensions: list[dict[str, str]], start: str, end: str) -> dict[str, Any]:
    command = [
        "aws", "cloudwatch", "get-metric-statistics",
        "--namespace", "AWS/DynamoDB",
        "--metric-name", "ConsumedWriteCapacityUnits",
        "--dimensions", *[f"Name={item['Name']},Value={item['Value']}" for item in dimensions],
        "--start-time", start,
        "--end-time", end,
        "--period", "60",
        "--statistics", "Sum",
        "--profile", args.profile,
        "--region", args.region,
        "--output", "json",
        "--no-cli-pager",
    ]
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"AWS CLI exited with {result.returncode}")
    return json.loads(result.stdout)


def collect_metrics(args: argparse.Namespace) -> dict[str, Any]:
    require_table(args)
    if not args.start_time or not args.end_time:
        raise ValueError("metrics requires --start-time and --end-time from the simulation output")
    started = dt.datetime.fromisoformat(args.start_time.replace("Z", "+00:00"))
    ended = dt.datetime.fromisoformat(args.end_time.replace("Z", "+00:00"))
    query_start = (started.replace(second=0, microsecond=0) - dt.timedelta(minutes=1)).isoformat().replace("+00:00", "Z")
    query_end = (ended.replace(second=0, microsecond=0) + dt.timedelta(minutes=2)).isoformat().replace("+00:00", "Z")
    table_dimensions = [{"Name": "TableName", "Value": args.table}]
    index_dimensions = [
        {"Name": "TableName", "Value": args.table},
        {"Name": "GlobalSecondaryIndexName", "Value": "EventTypeDayIndex"},
    ]
    table_metric = metric_statistics(args, table_dimensions, query_start, query_end)
    index_metric = metric_statistics(args, index_dimensions, query_start, query_end)
    wait_elapsed = 0
    first_bucket = started.replace(second=0, microsecond=0)
    last_bucket = ended.replace(second=0, microsecond=0)
    settled_after = last_bucket + dt.timedelta(minutes=2)

    def window_total(metric: dict[str, Any]) -> float:
        return sum(
            float(point.get("Sum", 0))
            for point in metric.get("Datapoints", [])
            if first_bucket <= dt.datetime.fromisoformat(point["Timestamp"].replace("Z", "+00:00")) <= last_bucket
        )

    def is_reconciled() -> bool:
        if dt.datetime.now(dt.timezone.utc) < settled_after:
            return False
        if not table_metric.get("Datapoints") or not index_metric.get("Datapoints"):
            return False
        return (
            args.expected_table_units is not None
            and args.expected_gsi_units is not None
            and abs(window_total(table_metric) - args.expected_table_units) < 0.001
            and abs(window_total(index_metric) - args.expected_gsi_units) < 0.001
        )

    confirmed = is_reconciled()
    while not confirmed and wait_elapsed < 900:
        time.sleep(30)
        wait_elapsed += 30
        table_metric = metric_statistics(args, table_dimensions, query_start, query_end)
        index_metric = metric_statistics(args, index_dimensions, query_start, query_end)
        confirmed = is_reconciled()
    return {
        "table": args.table,
        "metric": "AWS/DynamoDB ConsumedWriteCapacityUnits",
        "statistic": "Sum",
        "period_seconds": 60,
        "query_start_utc": query_start,
        "query_end_utc": query_end,
        "simulation_start_utc": started.isoformat(),
        "simulation_end_utc": ended.isoformat(),
        "cloudwatch_wait_seconds": wait_elapsed,
        "table_simulation_window_sum": window_total(table_metric),
        "gsi_simulation_window_sum": window_total(index_metric),
        "expected_table_units": args.expected_table_units,
        "expected_gsi_units": args.expected_gsi_units,
        "metrics_reconciled_with_put_item": confirmed,
        "table_datapoints": sorted(table_metric.get("Datapoints", []), key=lambda point: point["Timestamp"]),
        "gsi_datapoints": sorted(index_metric.get("Datapoints", []), key=lambda point: point["Timestamp"]),
        "interpretation": "Metrics are confirmed only after the final minute bucket settles and both sums match PutItem consumed capacity; missing or mismatched data remains pending.",
    }


def main() -> int:
    args = parse_args()
    try:
        events = load_events(args.fixtures)
        if args.mode == "validate-fixtures":
            result = validate_fixtures(events)
            result["validation"] = "passed"
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        if args.mode == "load":
            result = write_events(args, events, 0)
            filename = "seed-results.json"
        elif args.mode == "simulate":
            result = write_events(args, simulate_events(), 1)
            filename = "simulation-results.json"
        elif args.mode == "query":
            result = query_examples(args)
            filename = "query-results.json"
        else:
            result = collect_metrics(args)
            filename = "cloudwatch-metrics.json"
        result["responsible"] = args.responsible
        result["profile"] = args.profile
        result["region"] = args.region
        result["collected_at_utc"] = dt.datetime.now(dt.timezone.utc).isoformat()
        result["status"] = (
            "completed_with_errors" if result.get("writes_failed", 0)
            else "pending_metric_confirmation" if args.mode == "metrics" and not result.get("metrics_reconciled_with_put_item")
            else "completed"
        )
        result["evidence_file"] = str(write_evidence(args, filename, result))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if result.get("writes_failed", 0) or result.get("status") == "pending_metric_confirmation" else 0
    except (OSError, ValueError, KeyError, RuntimeError, StopIteration, json.JSONDecodeError) as error:
        print(f"lab error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
