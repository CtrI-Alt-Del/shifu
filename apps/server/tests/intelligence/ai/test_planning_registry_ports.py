# pyright: reportPrivateUsage=false
"""Planner ports owned by the Intelligence workflows registry."""

from __future__ import annotations

import pytest

from shifu.intelligence.ai.intelligence_workflows_registry import (
    _UnavailablePlanningSkillRetrievalProvider,
)
from shifu.intelligence.core.domain.errors import PlanningIndexUnavailableError
from shifu.intelligence.core.domain.structures import PlanningQuery


def test_registry_fails_closed_when_no_curriculum_catalog_is_available() -> None:
    provider = _UnavailablePlanningSkillRetrievalProvider()

    with pytest.raises(PlanningIndexUnavailableError):
        provider.retrieve(PlanningQuery(intent='Quero aprender React'))
