"""Prompt templates (docs/PIPELINE.md), one markdown file each with `## System` and `## User`."""

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parent


@dataclass(frozen=True)
class Prompt:
    system: str
    user_template: str

    def user(self, **values: str) -> str:
        """Fill `{name}` slots. Plain replacement: resume text may itself contain braces."""
        missing = set(re.findall(r"\{(\w+)\}", self.user_template)) - set(values)
        if missing:
            raise KeyError(f"prompt is missing values for: {sorted(missing)}")
        out = self.user_template
        for name, value in values.items():
            out = out.replace("{" + name + "}", value)
        return out


@lru_cache
def load_prompt(name: str) -> Prompt:
    text = (PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8")
    match = re.search(r"^## System\s*\n(.*?)^## User\s*\n(.*)\Z", text, flags=re.DOTALL | re.MULTILINE)
    if match is None:
        raise ValueError(f"prompts/{name}.md needs a '## System' and a '## User' section")
    return Prompt(system=match.group(1).strip(), user_template=match.group(2).strip())
