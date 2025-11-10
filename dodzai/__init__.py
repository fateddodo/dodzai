"""DodzAI package initialization.

This module exposes a small convenience API so the package can be used
programmatically without importing deep modules.  The :class:`DodzAIEngine`
class provides the primary entry point for managing providers and
conversations outside of the Tkinter desktop application.
"""
from .engine import DodzAIEngine

__all__ = ["DodzAIEngine"]
