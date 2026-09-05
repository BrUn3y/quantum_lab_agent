"""Quantum Experiment Agent for hybrid and iterative quantum workflows."""

import os
import re
from datetime import datetime
from typing import Annotated

from a2a.types import AgentSkill, Message, TextPart
from a2a.utils.message import get_message_text
from agentstack_sdk.a2a.extensions import AgentDetail, AgentDetailTool
from agentstack_sdk.a2a.extensions.ui.canvas import CanvasExtensionServer, CanvasExtensionSpec
from agentstack_sdk.a2a.extensions import TrajectoryExtensionServer, TrajectoryExtensionSpec
from agentstack_sdk.a2a.types import AgentArtifact, AgentMessage
from agentstack_sdk.platform.file import File
from agentstack_sdk.server import Server
from agentstack_sdk.server.context import RunContext
from agentstack_sdk.server.store.platform_context_store import PlatformContextStore
from beeai_framework.adapters.a2a.agents import A2AAgent
from beeai_framework.agents.react import ReActAgent
from beeai_framework.memory import UnconstrainedMemory

from .experiment_engine import QAOAExperimentResult, run_maxcut_qaoa
from .model_config import create_chat_model, explain_error, model_name, run_agent_with_retries
from .tools.a2a_response import extract_final_text


EXPERIMENT_INSTRUCTIONS = """You are the Quantum Experiment Agent, powered by IBM Granite 4.2.

You design hybrid quantum experiments. Produce technically conservative plans covering:
- the mathematical objective or Hamiltonian;
- algorithm selection (QAOA, VQE, amplitude estimation, or related methods);
- circuit/resource estimates;
- simulator baselines and exact classical validation;
- QPU evaluation, noise considerations, and error mitigation;
- measurable success criteria.

This agent is in active development. Clearly distinguish implemented capabilities from proposed experiment steps.
The implemented execution capability is p=1 QAOA Max-Cut for graphs with 2–8 nodes.
"""

EXPERIMENT_DETAIL = AgentDetail(
    user_greeting=(
        "🧪 Hello! I'm the Quantum Experiment Agent, powered by IBM Granite 4.2. "
        "I design hybrid experiments and currently execute validated p=1 QAOA Max-Cut studies. "
        "This agent is in active development."
    ),
    version="0.1.0",
    framework="Agent Stack + BeeAI + A2A + IBM Granite 4.2",
    author={"name": "Edgar Bruney"},
    tools=[
        AgentDetailTool(
            name="QAOA Max-Cut Experiment",
            description="Optimizes p=1 QAOA locally and validates it against the exact Max-Cut solution.",
        ),
        AgentDetailTool(
            name="Quantum Computing Client (A2A)",
            description="Submits the optimized final circuit to the Computing Agent when QPU execution is requested.",
        ),
    ],
)

EXPERIMENT_SKILLS = [
    AgentSkill(
        id="hybrid-quantum-experiments",
        name="Hybrid Quantum Experiments",
        description="Designs, optimizes, validates, and visualizes hybrid quantum experiments.",
        tags=["QAOA", "VQE", "Max-Cut", "Optimization", "IBM Granite", "Development"],
        examples=[
            "Use QAOA to solve Max-Cut on a 5-node graph using the local simulator",
            "Run QAOA for edges (0,1), (1,2), (2,3), (3,0) and validate the result",
            "Compare a 5-node QAOA Max-Cut baseline with real IBM Quantum hardware",
            "Design a VQE experiment for a small molecular Hamiltonian",
        ],
    )
]

server = Server()

_QAOA_MAXCUT_PATTERN = re.compile(r"\b(qaoa|max[- ]?cut|maxcut)\b", re.IGNORECASE)
_SIMULATOR_PATTERN = re.compile(
    r"\b(local\s+simulator|simulat(?:e|ed|ion|or)|simulador|simulaci[oó]n|simular)\b",
    re.IGNORECASE,
)
_HARDWARE_PATTERN = re.compile(
    r"\b(real hardware|hardware real|qpu|ibm quantum|backend real|hardware cu[aá]ntico)\b",
    re.IGNORECASE,
)


def is_qaoa_maxcut_request(request: str) -> bool:
    return bool(_QAOA_MAXCUT_PATTERN.search(request))


def should_submit_hardware(request: str) -> bool:
    """Submit only when hardware is explicit or execution is not explicitly simulated."""
    if _SIMULATOR_PATTERN.search(request) and not _HARDWARE_PATTERN.search(request):
        return False
    execution_requested = re.search(
        r"\b(run|execut\w*|submit\w*|ejec(?:u|ú)t\w*|corre\w*|compara\w*|compare)\b",
        request,
        re.IGNORECASE,
    )
    return bool(_HARDWARE_PATTERN.search(request) or execution_requested)


def format_experiment_summary(result: QAOAExperimentResult) -> str:
    top_outcomes = list(result.counts.items())[:8]
    rows = "\n".join(f"| `{state}` | {count:,} |" for state, count in top_outcomes)
    edges = ", ".join(f"({left},{right})" for left, right in result.edges)
    return (
        "## 🧪 QAOA Max-Cut experiment\n\n"
        f"- **Graph:** {result.node_count} nodes; edges {edges}\n"
        "- **Ansatz:** QAOA depth `p=1`\n"
        f"- **Optimized parameters:** γ={result.gamma:.4f}, β={result.beta:.4f}\n"
        f"- **Expected cut:** {result.expected_cut:.4f}\n"
        f"- **Exact optimum:** {result.exact_cut}\n"
        f"- **Approximation ratio:** {result.approximation_ratio:.2%}\n"
        f"- **Best sampled partition:** `{result.best_bitstring}` (cut {result.best_cut})\n\n"
        "### Top sampled solutions\n\n"
        "| Bitstring | Shots |\n|---|---:|\n"
        f"{rows}\n\n"
        "### Optimized circuit\n\n"
        f"```qasm\n{result.qasm.strip()}\n```"
    )


async def _submit_to_computing(request: str, qasm: str) -> str:
    host = os.getenv("COMPUTING_HOST", "127.0.0.1")
    port = int(os.getenv("COMPUTING_PORT", "8003"))
    agent = A2AAgent(url=f"http://{host}:{port}", memory=UnconstrainedMemory())
    execution_request = (
        "Execute this optimized QAOA Max-Cut circuit exactly once on the least busy operational "
        "real IBM Quantum backend with 1024 shots. Always create a new job and return its Job ID.\n\n"
        f"Original experiment request: {request}\n\n```qasm\n{qasm}\n```"
    )
    response = await agent.run(execution_request)
    return extract_final_text(response)


async def _upload_dashboard(result: QAOAExperimentResult) -> tuple[AgentArtifact | None, str]:
    try:
        uploaded = await File.create(
            filename=result.dashboard_path.name,
            content=result.dashboard_path.read_bytes(),
            content_type="image/png",
        )
        image_markdown = f"![QAOA experiment dashboard](agentstack://{uploaded.id})"
        queried_at = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
        artifact = AgentArtifact(
            name="QAOA Max-Cut experiment",
            description="Optimization convergence, graph partition, and sampled solutions.",
            metadata={"algorithm": "QAOA", "problem": "Max-Cut", "development_status": "active"},
            parts=[TextPart(text=f"{image_markdown}\n\nGenerated locally: {queried_at}")],
        )
        return artifact, image_markdown
    except Exception as error:
        return None, f"⚠️ Canvas upload failed: {explain_error(error)}"
    finally:
        result.dashboard_path.unlink(missing_ok=True)


def create_experiment_planner() -> ReActAgent:
    return ReActAgent(
        llm=create_chat_model("EXPERIMENT"),
        tools=[],
        memory=UnconstrainedMemory(),
    )


@server.agent(
    name="Quantum Experiment Agent (Development)",
    detail=EXPERIMENT_DETAIL,
    skills=EXPERIMENT_SKILLS,
    default_output_modes=["text/plain", "image/png"],
)
async def quantum_experiment_agent(
    input: Message,
    context: RunContext,
    trajectory: Annotated[TrajectoryExtensionServer, TrajectoryExtensionSpec()],
    _canvas: Annotated[CanvasExtensionServer, CanvasExtensionSpec()],
):
    user_query = get_message_text(input)
    yield trajectory.trajectory_metadata(
        title="🧪 Designing hybrid experiment",
        content=f"Model: {model_name('EXPERIMENT')}\n\nRequest: {user_query[:240]}",
    )

    if is_qaoa_maxcut_request(user_query):
        try:
            result = run_maxcut_qaoa(user_query)
            yield trajectory.trajectory_metadata(
                title="📈 QAOA optimization complete",
                content=(
                    f"- Grid evaluations: {len(result.optimization_trace)}\n"
                    f"- Exact optimum: {result.exact_cut}\n"
                    f"- Approximation ratio: {result.approximation_ratio:.2%}"
                ),
            )
            artifact, canvas_markdown = await _upload_dashboard(result)
            if artifact:
                yield artifact
                try:
                    await context.store(artifact)
                except Exception:
                    pass

            response = format_experiment_summary(result)
            response += f"\n\n### Experiment Canvas\n\n{canvas_markdown}"
            if should_submit_hardware(user_query):
                yield trajectory.trajectory_metadata(
                    title="⚛️ Submitting QPU evaluation",
                    content="Sending the optimized final circuit once to the Quantum Computing Agent...",
                )
                hardware_response = await _submit_to_computing(user_query, result.qasm)
                response += f"\n\n## ⚛️ IBM Quantum evaluation\n\n{hardware_response}"
            else:
                response += (
                    "\n\n> Simulator baseline completed. Request real IBM Quantum hardware "
                    "to submit the optimized circuit as a new QPU job."
                )

            message = AgentMessage(text=response)
            yield message
            try:
                await context.store(message)
            except Exception:
                pass
            return
        except Exception as error:
            yield AgentMessage(text=f"❌ Experiment failed: {explain_error(error)}")
            return

    try:
        planner = create_experiment_planner()
        run_context = await run_agent_with_retries(
            planner,
            f"{EXPERIMENT_INSTRUCTIONS}\n\nUSER REQUEST:\n{user_query}",
        )
        output = getattr(run_context, "output", run_context)
        if isinstance(output, list) and output:
            output = getattr(output[-1], "text", output[-1])
        yield AgentMessage(text=str(output))
    except Exception as error:
        yield AgentMessage(text=f"❌ Could not design the experiment: {explain_error(error)}")


def run() -> None:
    host = os.getenv("EXPERIMENT_HOST", "127.0.0.1")
    port = int(os.getenv("EXPERIMENT_PORT", "8004"))
    print("=" * 80)
    print("🧪 Starting Quantum Experiment Agent (Development)")
    print(f"  Model: {model_name('EXPERIMENT')}")
    print(f"  URL: http://{host}:{port}")
    print("  Implemented: p=1 QAOA Max-Cut (2–8 nodes)")
    print("=" * 80)
    server.run(host=host, port=port, context_store=PlatformContextStore())


if __name__ == "__main__":
    run()
