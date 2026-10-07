"""A fake LLM provider that answers by schema name, for tests that exercise stages calling the gateway."""

import json
from collections.abc import Callable
from typing import Any

from app.services.llm import ProviderUnavailable


class SchemaProvider:
    """`replies` maps a schema name (e.g. "ProjectJudgement") to a dict, a JSON string, an exception,
    or a function of the user prompt returning any of those. Every call is recorded."""

    name = "fake"

    def __init__(self, replies: dict[str, Any]):
        self.replies = replies
        self.calls: list[dict] = []

    def model_for(self, tier: str) -> str:
        return f"fake-{tier}"

    def complete(self, **kwargs) -> str:
        self.calls.append(kwargs)
        reply = self.replies.get(kwargs["schema"].__name__)
        if reply is None:
            raise ProviderUnavailable(f"no scripted reply for {kwargs['schema'].__name__}")
        if isinstance(reply, Callable):
            reply = reply(kwargs["user"])
        if isinstance(reply, Exception):
            raise reply
        return reply if isinstance(reply, str) else json.dumps(reply)

    def calls_for(self, schema_name: str) -> list[dict]:
        return [c for c in self.calls if c["schema"].__name__ == schema_name]

    @property
    def prompts(self) -> str:
        """Everything that was sent to the model, system and user text together."""
        return "\n".join(f"{c['system']}\n{c['user']}" for c in self.calls)


def project_judgement(**overrides) -> dict:
    base = {
        "what_it_does": "A REST API for campus event registration.",
        "has_metric": True,
        "has_architecture_detail": True,
        "specificity": 3,
        "buzzwords": [],
        "unsupported_claims": [],
        "issues": [
            {"issue": "No deployment instructions.", "fix": "Add a short Deploy section to the README."}
        ],
        "honest_rewrite": "Built a FastAPI service for campus event registration backed by PostgreSQL.",
    }
    return {**base, **overrides}


def design_judgement(**overrides) -> dict:
    base = {
        "readable": True,
        "problem_statement": 20,
        "process_evidence": 22,
        "outcome_or_metrics": 10,
        "tool_evidence": 12,
        "presentation": 8,
        "tools_seen": ["Figma"],
        "issues": [
            {"issue": "No usability test results.", "fix": "Add what changed after testing with five users."}
        ],
    }
    return {**base, **overrides}
