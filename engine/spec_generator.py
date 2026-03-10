from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, ValidationError
from rich.console import Console

from core.schema import TestSpec, validate_raw_spec

console = Console()
ARTIFACTS_DIR = Path("artifacts")
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
SPECS_LOG = ARTIFACTS_DIR / "specs.jsonl"
load_dotenv()  # loads .env into os.environ

@dataclass
class GenerationResult:
    raw_spec: Dict[str, Any]
    spec: TestSpec
    spec_hash: str
    validation_errors: List[str]
    attempts: int


class ContextSummary(BaseModel):
    """
    Minimal context we feed to the LLM.
    In a real system this could be derived from OpenAPI/Kafka configs,
    but we keep it deliberately small and explicit.
    """

    service_name: str
    http_endpoints: List[Dict[str, Any]]
    kafka_topics: List[str]

def _canonical_json(data: Dict[str, Any]) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"))


def _hash_spec(raw_spec: Dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(raw_spec).encode("utf-8")).hexdigest()


def log_spec(raw_spec: Dict[str, Any], spec_hash: str) -> None:
    record = {"specHash": spec_hash, "spec": raw_spec}
    with SPECS_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


def build_system_prompt() -> str:
    return (
        "You are a senior SDET generating JSON test specifications for "
        "Quarkus microservices with Kafka.\n\n"
        "Output ONLY a single JSON object that conforms to the provided schema "
        "(no prose, no markdown). You must:\n"
        "- Fill required fields: schemaVersion, id, name, testClassName, "
        "testMethodName, kind, containers.\n"
        "- For HTTP flows, populate http.request and http.expect.\n"
        "- For Kafka flows, populate kafka.produce and/or kafka.consume.\n"
        "- Use placeholders like {{ANY_UUID}}, {{ANY_TIMESTAMP}}, "
        "{{CAPTURE:field}}, {{EQUALS:value}}, {{EQUALS_REF:field}} inside "
        "jsonBody/valueMatchers where values are dynamic.\n"
    )


def build_user_prompt(context: ContextSummary, scenario_hint: str) -> str:
    return (
        "Generate a single comprehensive E2E test specification for the "
        "following scenario.\n\n"
        f"Service name: {context.service_name}\n"
        f"HTTP endpoints (examples):\n{json.dumps(context.http_endpoints, indent=2)}\n\n"
        f"Kafka topics (examples):\n{json.dumps(context.kafka_topics, indent=2)}\n\n"
        "Scenario description:\n"
        f"{scenario_hint}\n\n"
        "Choose kind = 'http', 'kafka', or 'hybrid' based on the scenario. "
        "Ensure the JSON is valid and self-contained."
    )


def _invoke_llm(
    client: OpenAI, system_prompt: str, user_prompt: str, model: str
) -> Dict[str, Any]:
    response = client.chat.completions.create(
        model=model,
        temperature=0.0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    content = response.choices[0].message.content
    assert content is not None
    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM returned non-JSON content: {e}: {content[:200]}")


def _validate_and_coerce(raw_spec: Dict[str, Any]) -> Tuple[TestSpec, List[str]]:
    schema_errors = validate_raw_spec(raw_spec)
    if schema_errors:
        # We still try to coerce via Pydantic to surface additional issues.
        try:
            spec = TestSpec.model_validate(raw_spec)
        except ValidationError:
            spec = None  # type: ignore[assignment]
        return spec, schema_errors  # type: ignore[return-value]
    spec = TestSpec.model_validate(raw_spec)
    return spec, []


def generate_spec_with_llm(
    context: ContextSummary,
    scenario_hint: str,
    model: str = "gpt-4.1-mini",
    max_attempts: int = 3,
) -> GenerationResult:
    """
    Core Software 2.0 function: call the LLM to generate a JSON spec,
    validate it against the schema, and retry with structured feedback.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY environment variable is not set")

    client = OpenAI(api_key=api_key)
    system_prompt = build_system_prompt()

    last_errors: List[str] = []
    raw: Dict[str, Any] = {}
    spec: TestSpec | None = None
    attempts = 0

    for attempt in range(1, max_attempts + 1):
        attempts = attempt
        user_prompt = build_user_prompt(context, scenario_hint)
        if last_errors:
            # Structured feedback for the retry: tell the model exactly what failed.
            user_prompt += (
                "\n\nThe previous JSON did not validate. Here are the errors:\n"
                + "\n".join(f"- {err}" for err in last_errors)
                + "\n\nProduce a corrected JSON object that fixes these issues."
            )

        console.log(f"[bold cyan]LLM call attempt {attempt}[/bold cyan]")
        console.log(user_prompt)

        raw = _invoke_llm(client, system_prompt, user_prompt, model=model)
        validation_spec, schema_errors = _validate_and_coerce(raw)

        if not schema_errors and validation_spec is not None:
            spec = validation_spec
            break

        last_errors = schema_errors
        console.print("[yellow]Validation errors from schema:[/yellow]")
        for err in schema_errors:
            console.print(f" - {err}")

    if spec is None:
        raise ValueError(
            f"Failed to generate a valid spec after {max_attempts} attempts. "
            f"Last errors: {last_errors}"
        )

    # Compute content hash & attach to metadata
    spec_hash = _hash_spec(raw)
    spec.metadata.specHash = spec_hash

    # Log raw spec for data engine
    log_spec(raw, spec_hash)

    return GenerationResult(
        raw_spec=raw,
        spec=spec,
        spec_hash=spec_hash,
        validation_errors=last_errors,
        attempts=attempts,
    )
