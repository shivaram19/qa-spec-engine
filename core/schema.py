from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from jsonschema import Draft7Validator
from pydantic import BaseModel, Field


class HttpRequest(BaseModel):
    path: str
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"]
    headers: Dict[str, str] = Field(default_factory=dict)
    body: Optional[Dict[str, Any]] = None


class HttpExpect(BaseModel):
    status: int
    jsonBody: Optional[Dict[str, Any]] = None


class HttpSpec(BaseModel):
    baseUrl: str = "http://localhost:8080"
    request: HttpRequest
    expect: HttpExpect


class KafkaProduceMessage(BaseModel):
    topic: str
    key: Optional[str] = None
    value: Dict[str, Any]


class KafkaConsumeExpectation(BaseModel):
    topic: str
    valueMatchers: Dict[str, Any]
    timeoutSeconds: int = Field(default=10, ge=1, le=60)


class KafkaSpec(BaseModel):
    produce: List[KafkaProduceMessage] = Field(default_factory=list)
    consume: List[KafkaConsumeExpectation] = Field(default_factory=list)


class ContainersSpec(BaseModel):
    requiresKafka: bool = False
    requiresPostgres: bool = False
    properties: Dict[str, str] = Field(default_factory=dict)


class Metadata(BaseModel):
    specHash: Optional[str] = None
    createdAt: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class TestSpec(BaseModel):
    """
    Canonical JSON test specification (schemaVersion 1).

    This is the hard boundary between Software 2.0 (LLM output)
    and Software 1.0 (deterministic template binder).
    """

    schemaVersion: Literal[1] = 1
    id: str
    name: str
    labels: List[str] = Field(default_factory=list)
    testClassName: str
    testMethodName: str
    kind: Literal["http", "kafka", "hybrid"]
    http: Optional[HttpSpec] = None
    kafka: Optional[KafkaSpec] = None
    containers: ContainersSpec
    meta: Metadata = Field(default_factory=Metadata)


# JSON Schema equivalent (for direct jsonschema validation of raw LLM output)
TEST_SPEC_JSON_SCHEMA: Dict[str, Any] = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": [
        "schemaVersion",
        "id",
        "name",
        "testClassName",
        "testMethodName",
        "kind",
        "containers",
    ],
    "properties": {
        "schemaVersion": {"type": "integer", "enum": [1]},
        "id": {"type": "string", "minLength": 1},
        "name": {"type": "string", "minLength": 1},
        "labels": {"type": "array", "items": {"type": "string"}, "default": []},
        "testClassName": {
            "type": "string",
            "pattern": "^[A-Z][A-Za-z0-9]*Test$",
        },
        "testMethodName": {
            "type": "string",
            "pattern": "^test[A-Z][A-Za-z0-9]*$",
        },
        "kind": {
            "type": "string",
            "enum": ["http", "kafka", "hybrid"],
        },
        "http": {
            "type": ["object", "null"],
            "properties": {
                "baseUrl": {"type": "string"},
                "request": {
                    "type": "object",
                    "required": ["path", "method"],
                    "properties": {
                        "path": {"type": "string", "pattern": "^/.*"},
                        "method": {
                            "type": "string",
                            "enum": ["GET", "POST", "PUT", "PATCH", "DELETE"],
                        },
                        "headers": {
                            "type": "object",
                            "additionalProperties": {"type": "string"},
                        },
                        "body": {"type": ["object", "null"]},
                    },
                    "additionalProperties": False,
                },
                "expect": {
                    "type": "object",
                    "required": ["status"],
                    "properties": {
                        "status": {
                            "type": "integer",
                            "minimum": 100,
                            "maximum": 599,
                        },
                        "jsonBody": {"type": ["object", "null"]},
                    },
                    "additionalProperties": False,
                },
            },
            "additionalProperties": False,
        },
        "kafka": {
            "type": ["object", "null"],
            "properties": {
                "produce": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["topic", "value"],
                        "properties": {
                            "topic": {"type": "string"},
                            "key": {"type": ["string", "null"]},
                            "value": {"type": "object"},
                        },
                        "additionalProperties": False,
                    },
                    "default": [],
                },
                "consume": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["topic", "valueMatchers", "timeoutSeconds"],
                        "properties": {
                            "topic": {"type": "string"},
                            "valueMatchers": {"type": "object"},
                            "timeoutSeconds": {
                                "type": "integer",
                                "minimum": 1,
                                "maximum": 60,
                            },
                        },
                        "additionalProperties": False,
                    },
                    "default": [],
                },
            },
            "additionalProperties": False,
        },
        "containers": {
            "type": "object",
            "required": ["requiresKafka", "requiresPostgres"],
            "properties": {
                "requiresKafka": {"type": "boolean"},
                "requiresPostgres": {"type": "boolean"},
                "properties": {
                    "type": "object",
                    "additionalProperties": {"type": "string"},
                    "default": {},
                },
            },
            "additionalProperties": False,
        },
        "metadata": {
            "type": "object",
            "properties": {
                "specHash": {"type": ["string", "null"]},
                "createdAt": {"type": "string"},
            },
            "additionalProperties": True,
        },
    },
    "additionalProperties": False,
}

TEST_SPEC_VALIDATOR = Draft7Validator(TEST_SPEC_JSON_SCHEMA)


def validate_raw_spec(raw: Dict[str, Any]) -> List[str]:
    """
    Validate a raw JSON dict against the TestSpec schema.

    Returns a list of human-readable error strings (empty if valid).
    """
    errors: List[str] = []
    for error in TEST_SPEC_VALIDATOR.iter_errors(raw):
        path = ".".join(str(p) for p in error.path)
        errors.append(f"{path or '<root>'}: {error.message}")
    return errors
