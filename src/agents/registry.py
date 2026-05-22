"""Specialist registry — name → instance lookup.

The Orchestrator uses this to dispatch Planner decisions to specialists.
Specialists are constructed once at app startup and reused per turn.
"""

from __future__ import annotations

from typing import Any, Protocol

from src.agents.appointment_agent import AppointmentAgent
from src.agents.base import SpecialistInput, SpecialistName, SpecialistOutput
from src.agents.casual_agent import CasualAgent
from src.agents.constitution_agent import ConstitutionAgent
from src.agents.faq_agent import FAQAgent
from src.agents.greeting_agent import GreetingAgent
from src.agents.sales_agent import SalesAgent
from src.llm import LLMClient
from src.tools.kb_search import KBSearch


class SpecialistProtocol(Protocol):
    async def run(
        self, inp: SpecialistInput
    ) -> tuple[SpecialistOutput, dict[str, Any]]: ...


def build_specialist_registry(
    client: LLMClient,
    *,
    kb_search: KBSearch | None = None,
) -> dict[SpecialistName, SpecialistProtocol]:
    return {
        SpecialistName.GREETING: GreetingAgent(client),
        SpecialistName.CASUAL: CasualAgent(client),
        SpecialistName.FAQ: FAQAgent(client=client, kb_search=kb_search),
        SpecialistName.SALES: SalesAgent(client=client),
        SpecialistName.CONSTITUTION: ConstitutionAgent(
            client=client, kb_search=kb_search
        ),
        SpecialistName.APPOINTMENT: AppointmentAgent(),
    }
