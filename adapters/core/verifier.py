"""
Verifier configuration.

Different benchmarks verify results differently:
  - Terminal-Bench: deterministic test scripts (pytest, bash assertions)
  - GDPVal: LLM-as-judge with rubric (Gemini 3.1 Pro)
  - SWE-Bench: run existing repo test suite

This module provides a configuration object that tells the builder
what kind of verification to set up.
"""

from dataclasses import dataclass, field
from enum import Enum


class VerifierType(Enum):
    """How the benchmark checks if the agent succeeded."""
    TEST_SCRIPT = "test_script"      # Run bash/pytest tests (Terminal-Bench)
    LLM_JUDGE = "llm_judge"          # Send output to LLM for scoring (GDPVal)
    FILE_MATCH = "file_match"        # Compare output files to expected files


@dataclass
class VerifierConfig:
    """
    Describes how to verify task results.

    The builder uses this to generate the appropriate test.sh.
    Benchmark plugins provide their own config.
    """
    verifier_type: VerifierType = VerifierType.TEST_SCRIPT
    judge_model: str = ""
    judge_api_env_var: str = ""
    timeout_sec: float = 300.0
    extra: dict = field(default_factory=dict)
