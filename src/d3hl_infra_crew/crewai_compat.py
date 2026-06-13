"""Compatibility shims for the pinned CrewAI version.

CrewAI 1.14.6 routes every agent through the experimental, Flow-based
``AgentExecutor`` (``crewai.experimental.agent_executor``). Its human-input
handling passes that executor to the human-input provider as the
``ExecutorContext`` and the provider then reads and writes
``context.ask_for_human_input`` as a flat attribute
(``crewai/core/providers/human_input.py``). The experimental executor is a
pydantic model that only stores the flag at ``self.state.ask_for_human_input``,
so it does not satisfy the ``ExecutorContext`` protocol: every task with
``human_input: true`` crashes with::

    'AgentExecutor' object has no attribute 'ask_for_human_input'

``apply_changes`` is exactly such a task — it is the human-review checkpoint and
the only task that writes files — so the live crew run dies before writing
anything into the target repo.

This module adds an ``ask_for_human_input`` property to the experimental
executor that proxies get/set to ``state.ask_for_human_input``, restoring the
checkpoint. It is applied at import time; importing it before ``crew.kickoff()``
(the crew module does this) is sufficient.
"""

from __future__ import annotations


def apply_crewai_human_input_patch() -> bool:
    """Bridge experimental ``AgentExecutor.ask_for_human_input`` to its state.

    Idempotent and defensive: returns ``True`` if the property is in place
    (newly applied or already present), ``False`` if the target class could not
    be located (e.g. a future CrewAI that fixes this upstream and renames it).
    """
    try:
        from crewai.experimental.agent_executor import AgentExecutor
    except Exception:
        return False

    existing = getattr(AgentExecutor, "ask_for_human_input", None)
    if isinstance(existing, property):
        return True

    def _get(self: AgentExecutor) -> bool:
        return self.state.ask_for_human_input

    def _set(self: AgentExecutor, value: object) -> None:
        self.state.ask_for_human_input = bool(value)

    AgentExecutor.ask_for_human_input = property(_get, _set)
    return True


PATCH_APPLIED = apply_crewai_human_input_patch()
