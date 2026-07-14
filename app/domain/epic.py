"""The epic's own contract."""

import re
from typing import Self

from pydantic import BaseModel, ConfigDict

from app.domain.type import IssueLabel, IssueNumber, LedeLine, OutcomeDescription

_STORY_REF_RE = re.compile(r"#(\d+)")


def _note_callout(text: str) -> str:
    quoted = "\n".join(f"> {ln}" if ln else ">" for ln in text.splitlines())
    return "> [!NOTE]\n" + quoted


def _dequote_note(section: str) -> str:
    """The body inside a `[!NOTE]` callout; tolerant of an Outcome not yet wrapped."""
    out: list[str] = []
    for ln in section.splitlines():
        s = ln[2:] if ln.startswith("> ") else (ln[1:] if ln.startswith(">") else ln)
        if s.strip().startswith("[!"):
            continue
        out.append(s)
    return "\n".join(out).strip()


def _epic_sections(body: str) -> dict[str, str]:
    parts = ("\n" + body).split("\n## ")
    return {p.splitlines()[0].strip(): "\n".join(p.splitlines()[1:]).strip() for p in parts[1:]}


class EpicBody(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    label: IssueLabel
    lede: LedeLine | None = None
    outcome_description: OutcomeDescription
    stories: tuple[IssueNumber, ...] = ()

    @property
    def markdown(self) -> str:
        preamble = [self.lede.root, ""] if self.lede is not None else []
        stories = (
            ["## Stories", "", *[f"- #{s.root}" for s in self.stories], ""] if self.stories else []
        )
        return (
            "\n".join(
                [
                    *preamble,
                    "## Outcome Description",
                    "",
                    _note_callout(self.outcome_description.root),
                    "",
                    *stories,
                ]
            ).rstrip("\n")
            + "\n"
        )

    @classmethod
    def from_markdown(cls, label: IssueLabel, body: str) -> Self:
        preamble = ("\n" + body).split("\n## ")[0].strip()
        lede = LedeLine(preamble) if preamble else None
        sections = _epic_sections(body)
        if "Outcome Description" not in sections:
            raise ValueError("epic body missing '## Outcome Description'")
        outcome = _dequote_note(sections["Outcome Description"])
        if not outcome:
            raise ValueError("epic body missing '## Outcome Description'")
        stories = tuple(
            IssueNumber(int(m.group(1)))
            for ln in sections.get("Stories", "").splitlines()
            if ln.strip().startswith("- ") and (m := _STORY_REF_RE.search(ln))
        )
        return cls(
            label=label,
            lede=lede,
            outcome_description=OutcomeDescription(outcome),
            stories=stories,
        )
