"""Transcript connector.

Normalises a plain-text meeting transcript into pipeline-ready text.

Supported input formats
-----------------------
- Lines with speaker labels:    ``Alice: some text``
- Lines with timestamps:        ``[00:00] Alice: some text``
- Header lines:                 ``Meeting: <title>``, ``Date: <date>``,
                                ``Attendees: <names>``
- Free-form lines

The connector strips timestamps and leading whitespace, then reconstructs
a coherent text block that the input router will classify as a meeting
transcript (routing to ``meeting-notes-to-eos-rocks``).
"""

from __future__ import annotations

import re
from pathlib import Path

from .base_connector import ConnectorOutput


# Matches optional timestamps like "[00:00]", "[1:23:45]", etc.
_TIMESTAMP_RE = re.compile(r"^\[[\d:]+\]\s*")

# Matches "Speaker: " style labels at the start of a line.
_SPEAKER_RE = re.compile(r"^([A-Za-z][A-Za-z ]{0,30}):\s+(.+)$")

# Header keys we extract into metadata.
_HEADER_KEYS = {"meeting", "date", "attendees"}


class TranscriptConnector:
    """Normalises plain-text meeting transcripts for the pptgen pipeline."""

    def normalize(self, path: Path) -> ConnectorOutput:
        """Read the transcript at *path* and return normalised output.

        Args:
            path: Path to the plain-text transcript file.

        Returns:
            :class:`~pptgen.connectors.base_connector.ConnectorOutput` whose
            ``text`` is suitable for
            :func:`~pptgen.pipeline.generate_presentation`.

        Raises:
            FileNotFoundError: If *path* does not exist.
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Transcript file not found: {path}")

        raw = path.read_text(encoding="utf-8")
        return _process(raw)


def _process(raw: str) -> ConnectorOutput:
    """Convert raw transcript text into a ConnectorOutput."""
    metadata: dict[str, str] = {}
    content_lines: list[str] = []
    speakers: list[str] = []

    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue

        # Strip timestamp prefix if present.
        line = _TIMESTAMP_RE.sub("", line).strip()

        # Check for header key: value lines.
        lower = line.lower()
        for key in _HEADER_KEYS:
            if lower.startswith(f"{key}:"):
                value = line[len(key) + 1:].strip()
                metadata[key] = value
                if key == "attendees":
                    # Record individual speakers from the header.
                    speakers.extend(
                        s.strip() for s in value.split(",") if s.strip()
                    )
                # Header lines are captured in metadata; do not add to
                # content_lines to avoid duplication in the output.
                break
        else:
            # Try to extract speaker labels.
            m = _SPEAKER_RE.match(line)
            if m:
                speaker, utterance = m.group(1).strip(), m.group(2).strip()
                if speaker not in speakers:
                    speakers.append(speaker)
                content_lines.append(utterance)
            else:
                content_lines.append(line)

    text = _build_text(metadata, speakers, content_lines)
    if speakers:
        metadata["speakers"] = ", ".join(speakers)

    return ConnectorOutput(text=text, metadata=metadata)


def _build_text(
    metadata: dict[str, str],
    speakers: list[str],
    content_lines: list[str],
) -> str:
    """Assemble the normalised text block from extracted parts."""
    parts: list[str] = []

    if "meeting" in metadata:
        parts.append(f"Meeting: {metadata['meeting']}")
    if "date" in metadata:
        parts.append(f"Date: {metadata['date']}")
    if speakers:
        parts.append(f"Attendees: {', '.join(dict.fromkeys(speakers))}")

    # Deduplicate content lines while preserving order.
    seen: set[str] = set()
    for line in content_lines:
        if line not in seen:
            seen.add(line)
            parts.append(line)

    return "\n".join(parts)
