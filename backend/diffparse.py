"""Split a unified git diff into per-file chunks with NEW-file line numbers.

The reviewer only ever sees the new side of the diff, so every line we hand to
the model is prefixed with the line number it has in the patched file. Numbers
come straight from the `@@ -old +new @@` hunk headers.

This module never raises on malformed input: anything it cannot make sense of
becomes a `skip_reason` on the file, which the caller reports back to the user.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

HUNK_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")
DIFF_GIT_RE = re.compile(r"^diff --git a/(.+?) b/(.+)$")

# Cap on how many changed lines we inject into a single prompt.
MAX_INJECTED_LINES = 400

# Diff metadata lines that end the current hunk and carry no reviewable code.
META_PREFIXES = (
    "index ",
    "new file mode",
    "deleted file mode",
    "similarity index",
    "rename from",
    "rename to",
    "old mode",
    "new mode",
    "Binary files",
    "GIT binary patch",
)


@dataclass
class DiffLine:
    """One line of the new file, with its 1-based line number."""

    line: int
    text: str


@dataclass
class FileDiff:
    """The new side of one file's diff, plus why we might skip it."""

    path: str
    lines: list[DiffLine] = field(default_factory=list)
    skip_reason: str | None = None

    @property
    def max_line(self) -> int:
        return max((d.line for d in self.lines), default=0)

    def numbered_text(self, limit: int = MAX_INJECTED_LINES) -> str:
        """Render `N: <code>` lines for the prompt, truncated to `limit`."""
        shown = self.lines[:limit]
        body = "\n".join(f"{d.line}: {d.text}" for d in shown)
        if len(self.lines) > limit:
            body += f"\n... ({len(self.lines) - limit} changed lines omitted)"
        return body


def parse_diff(text: str) -> list[FileDiff]:
    """Parse a unified diff into one FileDiff per file, in diff order."""
    files: list[FileDiff] = []
    current: FileDiff | None = None
    new_line: int | None = None

    for raw in text.splitlines():
        line = raw.rstrip("\r")

        if line.startswith("diff --git "):
            match = DIFF_GIT_RE.match(line)
            path = match.group(2) if match else line[len("diff --git "):].strip()
            current = FileDiff(path=path)
            files.append(current)
            new_line = None
            continue

        if current is None:
            # Preamble such as a commit message or "From <sha>" line.
            continue

        if line.startswith("+++ "):
            header = line[4:].strip()
            if header == "/dev/null":
                current.skip_reason = "file deleted, nothing new to review"
            else:
                path = header[2:] if header.startswith("b/") else header
                current.path = path.strip('"')
            new_line = None
            continue

        if line.startswith("--- "):
            new_line = None
            continue

        if line.startswith(META_PREFIXES):
            new_line = None
            if line.startswith(("Binary files", "GIT binary patch")):
                current.skip_reason = "binary file"
            continue

        hunk = HUNK_RE.match(line)
        if hunk:
            new_line = int(hunk.group(1))
            continue

        if new_line is None:
            # Outside a hunk, or unrecognised content: ignore it.
            continue

        if line.startswith("+"):
            current.lines.append(DiffLine(new_line, line[1:]))
            new_line += 1
        elif line.startswith(" "):
            current.lines.append(DiffLine(new_line, line[1:]))
            new_line += 1
        elif line.startswith("-"):
            # Removed line: it has no line number in the new file.
            continue
        elif line.startswith("\\"):
            # "\ No newline at end of file"
            continue
        else:
            # Unexpected content ends the hunk rather than corrupting numbers.
            new_line = None

    for file_diff in files:
        if file_diff.skip_reason is None and not file_diff.lines:
            file_diff.skip_reason = "no added or changed lines to review"

    return files
