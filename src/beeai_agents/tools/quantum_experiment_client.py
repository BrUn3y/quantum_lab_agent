"""A2A client used by the Lab Agent to invoke the Experiment Agent."""

import os
from typing import Optional

from beeai_framework.adapters.a2a.agents import A2AAgent
from beeai_framework.context import RunContext
from beeai_framework.emitter import Emitter
from beeai_framework.memory import UnconstrainedMemory
from beeai_framework.tools import Tool
from beeai_framework.tools.types import StringToolOutput, ToolRunOptions
from pydantic import BaseModel, Field

from .a2a_response import extract_final_text


class ExperimentClientInput(BaseModel):
    request: str = Field(description="Hybrid quantum experiment or research request.")


extract_experiment_response = extract_final_text


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
