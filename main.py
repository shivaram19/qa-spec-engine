#!/usr/bin/env python3
"""QA Spec Engine CLI"""
import sys
from pathlib import Path
import argparse
from rich.console import Console

# Fix imports
sys.path.insert(0, str(Path(__file__).parent))
from core.schema import TestSpec
from engine.spec_generator import ContextSummary, GenerationResult, generate_spec_with_llm
from engine.template_binder import render_test_java

console = Console()
RUNS_LOG = Path("artifacts") / "runs.jsonl"


def hash_context(context: ContextSummary) -> str:
    import hashlib, json
    payload = json.dumps(context.model_dump(), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def log_run(result: GenerationResult, java_path: Path, context_hash: str) -> None:
    import json
    record = {
        "contextHash": context_hash,
        "specHash": result.spec_hash,
        "testClassName": result.spec.testClassName,
        "javaPath": str(java_path),
        "attempts": result.attempts,
        "validationErrors": result.validation_errors,
    }
    RUNS_LOG.parent.mkdir(exist_ok=True)
    with RUNS_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


def main():
    parser = argparse.ArgumentParser(description="Generate Quarkus E2E tests")
    parser.add_argument("--service-name", "-s", required=True, help="Service name")
    parser.add_argument("--scenario", "-c", required=True, help="Test scenario description")
    parser.add_argument("--model", default="gpt-4o-mini", help="OpenAI model")
    
    args = parser.parse_args()
    
    console.print(f"[bold cyan]Service:[/bold cyan] {args.service_name}")
    console.print(f"[bold cyan]Scenario:[/bold cyan] {args.scenario}")
    
    context = ContextSummary(
        service_name=args.service_name,
        http_endpoints=[
            {"method": "POST", "path": "/api/orders", "summary": "Create order"},
            {"method": "GET", "path": "/api/orders/{id}", "summary": "Get order"},
        ],
        kafka_topics=[f"{args.service_name}.events.created", f"{args.service_name}.events.updated"],
    )
    
    try:
        result = generate_spec_with_llm(context, args.scenario, args.model)
        java_path = render_test_java(result.spec)
        context_hash = hash_context(context)
        log_run(result, java_path, context_hash)
        console.print(f"[green]✅ Test generated:[/green] {java_path}")
    except Exception as e:
        console.print(f"[red]❌ Error:[/red] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
