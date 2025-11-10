import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[2]))

try:
    from backend.power_workflow import (
        POWER_DEVELOPER_PERSONAS,
        resolve_power_developer_persona,
    )
except ModuleNotFoundError as exc:  # pragma: no cover - environment dependent
    pytest.skip(f"main.py dependencies missing: {exc}", allow_module_level=True)


def test_resolve_persona_defaults_to_greenfield_when_missing():
    persona, requested, status = resolve_power_developer_persona(None)
    assert persona == "greenfield"
    assert requested == ""
    assert status == "defaulted"


def test_resolve_persona_honors_stranded_case_insensitive():
    persona, requested, status = resolve_power_developer_persona("Stranded")
    assert persona == "stranded"
    assert requested == "Stranded"
    assert status == "valid"


def test_resolve_persona_rejects_invalid_value():
    persona, requested, status = resolve_power_developer_persona("unknown")
    assert persona == "greenfield"
    assert requested == "unknown"
    assert status == "invalid"


def test_defined_personas_match_weights():
    for persona_name in ("greenfield", "repower", "stranded"):
        persona, _, status = resolve_power_developer_persona(persona_name)
        assert status == "valid"
        assert persona in POWER_DEVELOPER_PERSONAS
