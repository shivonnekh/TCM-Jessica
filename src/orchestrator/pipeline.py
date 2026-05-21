"""JessicaPipeline — runs Planner → Specialists → Writer for one turn.

The pipeline is responsible for:
  - Loading CRM snapshot
  - Calling Planner
  - Dispatching specialists (parallel or sequential per decision)
  - Calling Writer
  - Persisting CRM updates
  - Writing the trace bundle

NOT responsible for:
  - WhatsApp send (that's the caller's job, so tests can call the
    pipeline without actually sending)
  - Buffer / merge logic (that's the gateway's job — see CLAUDE.md §3.2)
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Any

from anthropic import AsyncAnthropic
from pydantic import BaseModel, ConfigDict

from src.agents.base import (
    PlannerDecision,
    SpecialistInput,
    SpecialistName,
    SpecialistOutput,
    WriterOutput,
)
from src.agents.planner import PlannerAgent
from src.agents.registry import SpecialistProtocol
from src.agents.writer import WriterAgent
from src.crm.models import ConversationMessage, User
from src.crm.repo import CRMRepo
from src.trace.models import (
    SpecialistTrace,
    StepTrace,
    TraceBundle,
)
from src.trace.writer import TraceWriter

logger = logging.getLogger("orchestrator.pipeline")


class PipelineResult(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    turn_id: str
    user: User
    writer_output: WriterOutput
    trace: TraceBundle


class JessicaPipeline:
    def __init__(
        self,
        *,
        crm: CRMRepo,
        trace_writer: TraceWriter,
        client: AsyncAnthropic,
        specialists: dict[SpecialistName, SpecialistProtocol],
        planner: PlannerAgent | None = None,
        writer: WriterAgent | None = None,
    ) -> None:
        self._crm = crm
        self._trace_writer = trace_writer
        self._planner = planner or PlannerAgent(client)
        self._writer_agent = writer or WriterAgent(client)
        self._specialists = specialists

    async def run_turn(
        self,
        *,
        phone: str,
        user_message: str,
        media_urls: list[str] | None = None,
        merged_from_fragments: list[str] | None = None,
        wa_message_id: str | None = None,
    ) -> PipelineResult:
        turn_id = _new_turn_id()
        media_urls = media_urls or []
        merged_from_fragments = merged_from_fragments or []
        turn_start = datetime.utcnow()

        # 1. Load CRM — pre-turn snapshot. We deliberately do NOT
        # pre-append the current user message; agents need to see the
        # PRIOR conversation history so first-touch detection works.
        # (User message is appended after the pipeline succeeds, below.)
        user_for_planner = await self._crm.get_or_create_user(phone)

        bundle = TraceBundle(
            turn_id=turn_id,
            phone=phone,
            received_at=turn_start,
            user_message=user_message,
            merged_from_fragments=merged_from_fragments,
            media_urls=media_urls,
            crm_snapshot=user_for_planner.model_dump(mode="json"),
        )

        try:
            # 2. Planner
            planner_step = StepTrace(input={"user_message": user_message})
            t0 = _now_ms()
            decision, planner_usage = await self._planner.decide(
                user_for_planner, user_message, media_urls=media_urls
            )
            planner_step.latency_ms = _now_ms() - t0
            planner_step.output = decision.model_dump(mode="json")
            planner_step.model = planner_usage.get("model")
            planner_step.input_tokens = planner_usage.get("input_tokens", 0)
            planner_step.output_tokens = planner_usage.get("output_tokens", 0)
            planner_step.ended_at = datetime.utcnow()
            bundle.planner = planner_step

            # 3. Dispatch specialists
            outputs = await self._dispatch_specialists(
                decision=decision,
                user=user_for_planner,
                user_message=user_message,
                media_urls=media_urls,
                bundle=bundle,
            )

            # 4. Writer
            writer_step = StepTrace(
                input={
                    "specialists_used": [o.specialist.value for o in outputs],
                }
            )
            t0 = _now_ms()
            writer_output, writer_usage = await self._writer_agent.compose(
                user=user_for_planner,
                user_message=user_message,
                planner_decision=decision,
                specialist_outputs=outputs,
            )
            writer_step.latency_ms = _now_ms() - t0
            writer_step.output = writer_output.model_dump(mode="json")
            writer_step.model = writer_usage.get("model")
            writer_step.input_tokens = writer_usage.get("input_tokens", 0)
            writer_step.output_tokens = writer_usage.get("output_tokens", 0)
            writer_step.ended_at = datetime.utcnow()
            bundle.writer = writer_step

            # 5. Apply suggested CRM diffs from specialists
            user_after = _apply_specialist_diffs(user_for_planner, outputs)

            # Append the inbound user message NOW (post-pipeline) so
            # next turn's agents see it as prior history, but THIS turn's
            # is_first_touch logic saw a clean pre-turn snapshot.
            await self._crm.append_message(
                phone,
                ConversationMessage(
                    role="user",
                    content=user_message,
                    media_urls=media_urls,
                    wa_message_id=wa_message_id,
                    turn_id=turn_id,
                    at=turn_start,
                ),
            )

            # Append Jessica's reply to history (joined bubbles for storage)
            jessica_text = "\n\n".join(writer_output.bubbles)
            await self._crm.append_message(
                phone,
                ConversationMessage(
                    role="jessica",
                    content=jessica_text,
                    turn_id=turn_id,
                    at=datetime.utcnow(),
                ),
            )

            await self._crm.save_user(user_after)

            # New appointments live in a separate table — save_user
            # doesn't touch it. Detect appointments that appeared via
            # the _append diff and persist them now.
            new_appointments = [
                a for a in user_after.appointments
                if a not in user_for_planner.appointments
            ]
            for appt in new_appointments:
                await self._crm.add_appointment(phone, appt)

            bundle.crm_diff = _diff_user(user_for_planner, user_after)

        except Exception as exc:  # noqa: BLE001
            logger.exception("pipeline error on turn=%s phone=%s", turn_id, phone)
            bundle.fatal_error = f"{type(exc).__name__}: {exc}"
            # Fall back to a generic apology bubble so trace can still
            # capture the writer_output slot.
            writer_output = WriterOutput(
                bubbles=["唔好意思啊，我而家有啲技術問題，請你等一陣再試 🙏"]
            )
            user_after = user_for_planner

        bundle.completed_at = datetime.utcnow()
        bundle.total_latency_ms = _now_ms() - _epoch_ms(turn_start)
        self._trace_writer.write(bundle)

        return PipelineResult(
            turn_id=turn_id,
            user=user_after,
            writer_output=writer_output,
            trace=bundle,
        )

    # ---------------------------------------------------------------
    # Internals
    # ---------------------------------------------------------------

    async def _dispatch_specialists(
        self,
        *,
        decision: PlannerDecision,
        user: User,
        user_message: str,
        media_urls: list[str],
        bundle: TraceBundle,
    ) -> list[SpecialistOutput]:
        async def _run_one(
            name: SpecialistName, co: SpecialistName | None
        ) -> SpecialistOutput:
            spec = self._specialists.get(name)
            if spec is None:
                logger.warning("unknown specialist: %s", name)
                trace = SpecialistTrace(name=name.value, error="unknown_specialist")
                bundle.add_specialist(trace)
                return SpecialistOutput(specialist=name, payload={}, error="unknown")

            trace = SpecialistTrace(name=name.value)
            t0 = _now_ms()
            try:
                output, usage = await spec.run(
                    SpecialistInput(
                        user=user,
                        user_message=user_message,
                        media_urls=media_urls,
                        planner_notes=decision.notes_for_writer,
                        co_specialist=co,
                    )
                )
            except Exception as exc:  # noqa: BLE001
                logger.exception("specialist %s failed", name)
                trace.error = f"{type(exc).__name__}: {exc}"
                trace.latency_ms = _now_ms() - t0
                trace.ended_at = datetime.utcnow()
                bundle.add_specialist(trace)
                return SpecialistOutput(
                    specialist=name, payload={}, error=trace.error
                )

            trace.latency_ms = _now_ms() - t0
            trace.input = {
                "user_message": user_message,
                "media_urls": media_urls,
                "co_specialist": co.value if co else None,
            }
            trace.output = output.model_dump(mode="json")
            trace.tools_called = output.tools_called
            trace.cards_read = output.cards_used
            trace.model = usage.get("model")
            trace.input_tokens = usage.get("input_tokens", 0)
            trace.output_tokens = usage.get("output_tokens", 0)
            trace.ended_at = datetime.utcnow()
            bundle.add_specialist(trace)
            return output

        names = list(decision.specialists)

        # Parallel — only meaningful with 2 specialists.
        if decision.mode == "parallel" and len(names) == 2:
            return list(
                await asyncio.gather(
                    _run_one(names[0], names[1]),
                    _run_one(names[1], names[0]),
                )
            )

        # Solo or sequential — run in order, primary first.
        results: list[SpecialistOutput] = []
        for i, n in enumerate(names):
            other = names[1 - i] if len(names) == 2 else None
            results.append(await _run_one(n, other))
        return results


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------


def _new_turn_id() -> str:
    return uuid.uuid4().hex[:16]


def _now_ms() -> int:
    return int(datetime.utcnow().timestamp() * 1000)


def _epoch_ms(dt: datetime) -> int:
    return int(dt.timestamp() * 1000)


_APPEND_SUFFIX = "_append"


def _apply_specialist_diffs(user: User, outputs: list[SpecialistOutput]) -> User:
    """Merge ``suggested_user_state_diff`` from each specialist into User.

    Two diff conventions are supported:

    * ``"<field>": value`` — REPLACE the field with ``value``. Standard.
    * ``"<field>_append": [items]`` — APPEND items to the existing list
      field, deduplicating (order-preserving). Use this when a specialist
      contributes incremental items without authority over the full list.
      Example: Sales emits ``products_pitched_append: ["soup_xxx"]``
      because it doesn't want to clobber pitches by other turns.

    Unknown / malformed keys are logged + dropped (never raises — a buggy
    specialist must not break the turn).
    """
    allowed = set(User.model_fields.keys())
    changes: dict[str, Any] = {}

    for o in outputs:
        for k, v in o.suggested_user_state_diff.items():
            # --- "_append" convention -------------------------------
            if k.endswith(_APPEND_SUFFIX):
                base = k[: -len(_APPEND_SUFFIX)]
                if base not in allowed:
                    logger.warning(
                        "specialist %s wrote append for unknown field %r — dropped",
                        o.specialist,
                        k,
                    )
                    continue
                existing = changes.get(base, getattr(user, base))
                if not isinstance(existing, list):
                    logger.warning(
                        "specialist %s tried _append on non-list field %r — dropped",
                        o.specialist,
                        base,
                    )
                    continue
                new_items = v if isinstance(v, list) else [v]
                merged = list(existing)
                for item in new_items:
                    if item not in merged:
                        merged.append(item)
                changes[base] = merged
                continue

            # --- replace --------------------------------------------
            if k not in allowed:
                logger.warning(
                    "specialist %s wrote unknown user field %r — dropped",
                    o.specialist,
                    k,
                )
                continue
            changes[k] = v

    return user.with_updates(**changes) if changes else user


def _diff_user(before: User, after: User) -> dict[str, Any]:
    """Return only the User fields that changed (for trace.crm_diff)."""
    b = before.model_dump(mode="json")
    a = after.model_dump(mode="json")
    return {k: {"before": b[k], "after": a[k]} for k in a if a[k] != b.get(k)}
