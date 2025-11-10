"""Lightweight Markdown parsing helpers for the Tkinter UI."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List


@dataclass
class MarkdownSegment:
    text: str
    style: str


_CODE_BLOCK = re.compile(r"```(.*?)```", re.DOTALL)
_INLINE_CODE = re.compile(r"`([^`]+)`")
_BOLD = re.compile(r"\*\*([^*]+)\*\*")
_ITALIC = re.compile(r"\*([^*]+)\*")


def parse_markdown(text: str) -> List[MarkdownSegment]:
    segments: List[MarkdownSegment] = []
    # Extract fenced code blocks first
    last_end = 0
    for match in _CODE_BLOCK.finditer(text):
        before = text[last_end : match.start()]
        if before:
            segments.extend(_parse_paragraphs(before))
        code_text = match.group(1)
        segments.append(MarkdownSegment(text=code_text.strip("\n"), style="code_block"))
        last_end = match.end()
    if last_end < len(text):
        segments.extend(_parse_paragraphs(text[last_end:]))
    return segments


def _parse_paragraphs(chunk: str) -> List[MarkdownSegment]:
    lines = chunk.splitlines()
    segments: List[MarkdownSegment] = []
    buffer: List[str] = []
    style = "paragraph"
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if buffer:
                segments.extend(_flush_paragraph(buffer, style))
                buffer = []
                style = "paragraph"
            continue
        if stripped.startswith("- ") or stripped.startswith("* "):
            if buffer and style != "list":
                segments.extend(_flush_paragraph(buffer, style))
                buffer = []
            style = "list"
            buffer.append(stripped[2:])
        elif stripped.startswith("#"):
            if buffer:
                segments.extend(_flush_paragraph(buffer, style))
                buffer = []
            level = len(stripped) - len(stripped.lstrip("#"))
            content = stripped[level:].strip()
            segments.append(MarkdownSegment(text=content, style=f"header{level}"))
            style = "paragraph"
        else:
            buffer.append(stripped)
    if buffer:
        segments.extend(_flush_paragraph(buffer, style))
    return segments


def _flush_paragraph(buffer: List[str], style: str) -> List[MarkdownSegment]:
    text = "\n".join(buffer)
    text = _apply_inline_styles(text)
    if style == "list":
        return [MarkdownSegment(text=f"• {line}", style="list_item") for line in text.split("\n")]
    return [MarkdownSegment(text=text, style=style)]


def _apply_inline_styles(text: str) -> str:
    text = _BOLD.sub(lambda m: f"<bold>{m.group(1)}</bold>", text)
    text = _ITALIC.sub(lambda m: f"<italic>{m.group(1)}</italic>", text)
    text = _INLINE_CODE.sub(lambda m: f"<code>{m.group(1)}</code>", text)
    return text


def strip_markdown(text: str) -> str:
    plain = _CODE_BLOCK.sub(lambda m: m.group(1), text)
    plain = _BOLD.sub(lambda m: m.group(1), plain)
    plain = _ITALIC.sub(lambda m: m.group(1), plain)
    plain = _INLINE_CODE.sub(lambda m: m.group(1), plain)
    plain = re.sub(r"^#+\s*", "", plain, flags=re.MULTILINE)
    plain = re.sub(r"^[*-]\s+", "", plain, flags=re.MULTILINE)
    return plain
