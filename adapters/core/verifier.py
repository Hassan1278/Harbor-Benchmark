"""
Verifier configuration.

Knobs the builder consumes when writing task.toml. Benchmark-specific
judge logic lives in the template/tests/ scripts, not here.
"""

from dataclasses import dataclass, field


@dataclass
class VerifierConfig:
    """Describes how to verify task results."""
    timeout_sec: float = 300.0
    env: dict[str, str] = field(default_factory=dict)
