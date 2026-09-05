"""A2A client used by the Lab Agent to invoke the Experiment Agent."""

import os
from typing import Optional

from a2a.utils.message import get_message_text
from beeai_framework.adapters.a2a.agents import A2AAgent
from beeai_framework.context import RunContext
from beeai_framework.emitter import Emitter
from beeai_framework.memory import UnconstrainedMemory
from beeai_framework.tools import Tool
from beeai_framework.tools.types import StringToolOutput, ToolRunOptions
from pydantic import BaseModel, Field


class ExperimentClientInput(BaseModel):
    request: str = Field(description="Hybrid quantum experiment or research request.")


def extract_experiment_response(response: object) -> str:
    """Return the final agent message, not the preceding Canvas artifact.

    BeeAI's A2A adapter currently exposes an artifact as ``last_message`` when
    an agent emits both Canvas content and a final text message. The complete
    A2A task still contains the final message in its history.
    """
    events = getattr(response, "event", ())
    if not isinstance(events, (tuple, list)):
        events = (events,)
    for event in reversed(events):
        history = getattr(event, "history", None) or ()
        for message in reversed(history):
            try:
                text = get_message_text(message).strip()
            except Exception:
                continue
            if text:
                return text

    last_message = getattr(response, "last_message", None)
    text = getattr(last_message, "text", "")
    return text.strip() if isinstance(text, str) else str(response)


class QuantumExperimentClient(Tool[ExperimentClientInput]):
    @property
    def name(self) -> str:
        return "quantum_experiment_client"

    @property
    def description(self) -> str:
        return (
            "Invokes the Quantum Experiment Agent (port 8004) for QAOA, VQE, Max-Cut, "
            "hybrid optimization, simulator/QPU comparisons, and error-mitigation plans."
        )

    @property
    def input_schema(self) -> type[ExperimentClientInput]:
        return ExperimentClientInput

    def _create_emitter(self) -> Emitter:
        return Emitter()

    async def _run(
        self,
        input: ExperimentClientInput,
        options: Optional[ToolRunOptions] = None,
        context: Optional[RunContext] = None,
    ) -> StringToolOutput:
        host = os.getenv("EXPERIMENT_HOST", "127.0.0.1")
        port = int(os.getenv("EXPERIMENT_PORT", "8004"))
        try:
            agent = A2AAgent(url=f"http://{host}:{port}", memory=UnconstrainedMemory())
            response = await agent.run(input.request)
            text = extract_experiment_response(response)
            return StringToolOutput(result=text or "⚠️ The Experiment Agent returned an empty response.")
        except Exception as error:
            return StringToolOutput(
                result=(
                    f"❌ Could not connect to the Quantum Experiment Agent at {host}:{port}. "
                    f"Start it with ./start_experiment.sh. Error: {error}"
                )
            )
