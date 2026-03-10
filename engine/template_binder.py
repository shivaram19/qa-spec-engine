from __future__ import annotations

from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from core.schema import TestSpec

TEMPLATES_DIR = Path("templates")
OUTPUT_DIR = Path("generated_tests")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _create_env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
        undefined=StrictUndefined,
    )

    def tojson(value) -> str:
        import json

        return json.dumps(value, indent=2)

    env.filters["tojson"] = tojson
    return env


def render_test_java(
    spec: TestSpec,
    template_name: str = "QuarkusKafkaTest.java.j2",
    output_dir: Optional[Path] = None,
) -> Path:
    """
    Pure Software 1.0: render Java test code from a validated TestSpec.
    """
    if output_dir is None:
        output_dir = OUTPUT_DIR

    env = _create_env()
    template = env.get_template(template_name)

    rendered = template.render(
        testClassName=spec.testClassName,
        testMethodName=spec.testMethodName,
        id=spec.id,
        name=spec.name,
        labels=spec.labels,
        kind=spec.kind,
        http=spec.http.model_dump() if spec.http else None,
        kafka=spec.kafka.model_dump() if spec.kafka else None,
        containers=spec.containers.model_dump(),
        metadata=spec.metadata.model_dump(),
    )

    output_path = output_dir / f"{spec.testClassName}.java"
    output_path.write_text(rendered, encoding="utf-8")
    return output_path
