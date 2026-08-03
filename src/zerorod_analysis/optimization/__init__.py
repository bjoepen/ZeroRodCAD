"""Internal duplicate analysis and optimization planning."""

from .duplicates import duplicate_groups
from .planner import DeduplicationAction, choose_canonical, create_plan

__all__ = ["DeduplicationAction", "choose_canonical", "create_plan", "duplicate_groups"]
