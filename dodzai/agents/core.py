"""Minimal agent runtime used for local tool execution."""
from __future__ import annotations

import dataclasses
from typing import Dict, Iterable, List, Optional


@dataclasses.dataclass
class AgentPlan:
    """Represents a simple sequence of instructions for tools to execute."""

    steps: List[str]


@dataclasses.dataclass
class AgentResult:
    """Result returned by :class:`AgentRuntime`."""

    output: str
    logs: List[str] = dataclasses.field(default_factory=list)


class Tool:
    """Base class for runtime tools."""

    name: str
    description: str

    def __init__(self, name: str, description: str) -> None:
        self.name = name
        self.description = description

    def __call__(self, instructions: str, *, context: Optional[Dict] = None) -> str:
        return self.run(instructions, context=context or {})

    def run(self, instructions: str, *, context: Dict) -> str:  # pragma: no cover - to be implemented by subclasses
        raise NotImplementedError


class AgentRuntime:
    """Execute :class:`AgentPlan` instructions using registered tools."""

    def __init__(self, tools: Optional[Iterable[Tool]] = None, *, context: Optional[Dict] = None) -> None:
        self.tools: Dict[str, Tool] = {}
        if tools:
            for tool in tools:
                self.register(tool)
        self.context: Dict = context or {}

    def register(self, tool: Tool) -> None:
        self.tools[tool.name] = tool

    def available_tools(self) -> List[str]:
        return sorted(self.tools)

    def execute(self, plan: AgentPlan) -> AgentResult:
        logs: List[str] = []
        outputs: List[str] = []
        for step in plan.steps:
            tool_name, instructions = self._parse_step(step)
            if tool_name and tool_name in self.tools:
                tool = self.tools[tool_name]
                logs.append(f"Executing {tool_name}: {instructions}")
                try:
                    result = tool(instructions, context=self.context)
                except Exception as exc:  # pragma: no cover - defensive programming
                    result = f"Tool '{tool_name}' failed: {exc}"
                outputs.append(result)
            else:
                logs.append(f"No matching tool for step: {step}")
                outputs.append(step)
        return AgentResult(output="\n".join(outputs).strip(), logs=logs)

    def _parse_step(self, step: str) -> tuple[Optional[str], str]:
        if ":" in step:
            prefix, remainder = step.split(":", 1)
            name = prefix.strip().lower()
            if name in self.tools:
                return name, remainder.strip()
        parts = step.split()
        if parts:
            first = parts[0].lower()
            if first in self.tools:
                return first, " ".join(parts[1:])
        return None, step
