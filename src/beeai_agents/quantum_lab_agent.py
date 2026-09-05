"""
Quantum Lab Agent - Quantum Computing Orchestrator

This agent is the main entry point of the system and is responsible for:
- Receiving user requests
- Deciding when to invoke the Quantum Developer Agent
- Executing circuits on IBM Quantum
- Querying backend and job status
- Orchestrating communication between components

Model: configurable via LAB_MODEL (Ollama/Watsonx)
Port: 8000
Type: Main A2A Server + A2A Client (invokes Developer)
"""

import asyncio
import os
import re
from datetime import datetime
from typing import Annotated
from collections.abc import AsyncGenerator

from a2a.types import AgentSkill, Message, TextPart
from a2a.utils.message import get_message_text
from agentstack_sdk.server import Server
from agentstack_sdk.server.context import RunContext
from agentstack_sdk.server.store.platform_context_store import PlatformContextStore
from agentstack_sdk.a2a.types import AgentArtifact, AgentMessage
from agentstack_sdk.a2a.extensions import AgentDetail, AgentDetailTool
from agentstack_sdk.a2a.extensions import TrajectoryExtensionServer, TrajectoryExtensionSpec
from agentstack_sdk.a2a.extensions.ui.canvas import CanvasExtensionServer, CanvasExtensionSpec

from beeai_framework.agents.react import ReActAgent
from beeai_framework.memory import TokenMemory

from .model_config import create_chat_model, explain_error, model_name, run_agent_with_retries

# Import tools from the tools folder
from .tools import (
    QuantumDeveloperClient,
    QuantumStatusClient,
    QuantumComputingClient,
)

# Instructions for the Quantum Lab Agent
LAB_INSTRUCTIONS = """You are the Quantum Lab Agent, the main orchestrator of the quantum computing system.

YOUR ROLE:
- Analyze user requests
- Decide which specialized agent to invoke (Developer, Status, or Computing)
- Coordinate communication between agents via A2A
- Provide clear and useful responses

SYSTEM ARCHITECTURE:
The system has 4 specialized agents that communicate via A2A:
- **Developer Agent** (port 8001): Generates quantum code and explanations
- **Status Agent** (port 8002): Queries backend and job status
- **Computing Agent** (port 8003): Executes quantum circuits
- **Quantum Lab Agent** (YOU, port 8000): Main orchestrator

AVAILABLE TOOLS:

1. **quantum_developer_client** - Invoke Developer Agent (A2A)
   USE WHEN:
   ✅ User asks "create a circuit"
   ✅ User asks "explain" a quantum concept
   ✅ User asks for "example of" an algorithm
   ✅ You need to generate QASM/Qiskit code
   ✅ User asks to optimize code
   
   DO NOT USE WHEN:
   ❌ You already have QASM code ready to execute
   ❌ User only asks about backend status
   ❌ User only wants to see job results

2. **quantum_status_client** - Invoke Status Agent (A2A)
   USE WHEN:
   ✅ User asks "what computers are available"
   ✅ User asks about backend status
   ✅ User asks "which is less busy"
   ✅ User asks about properties of a specific backend
   ✅ User asks "how many qubits does X have"
   ✅ User provides a Job ID to query
   ✅ User asks "what is the status of my job"
   ✅ User asks "show me my recent jobs"
   ✅ User says "compare the results of jobs X, Y, Z"
   ✅ User wants to compare multiple jobs
   
   QUERY EXAMPLES:
   - "What quantum computers are available?"
   - "Give me information about ibm_brisbane"
   - "What is the status of job d671cklbujdc73cvbp30?"
   - "Show me my running jobs"
   - "Compare the results of jobs d6cd297g4t5c7385dh4g, d6cd2bknsg9c739a32p0, d6cd2e7g4t5c7385dhag"

3. **quantum_computing_client** - Invoke Computing Agent (A2A)
   USE WHEN:
   ✅ You have complete QASM code to execute
   ✅ User says "execute this circuit"
   ✅ User says "run the code on [backend]"
   ✅ After getting code from Developer Agent and user wants to execute it
   ✅ User provides QASM code to execute
   
   ⚠️ CRITICAL EXECUTION RULE:
   - Execute code ONCE by default
   - DO NOT execute multiple times unless user EXPLICITLY asks
   - If user says "execute 3 times", then execute 3 times
   - If user only says "execute", execute ONCE
   
   EXECUTION EXAMPLES:
   - "Execute this QASM code on ibm_brisbane" → Execute 1 time
   - "Run the circuit on the simulator" → Execute 1 time
   - "Execute that code 5 times" → Execute 5 times
   - "Run on ibm_torino 3 times" → Execute 3 times

TYPICAL WORKFLOWS:

**Scenario 1: ONLY CREATE circuit (NO EXECUTION)**
User: "Create a Bell circuit" or "Give me an example of superposition"

STEPS:
1. Invoke quantum_developer_client with the request
2. Return the generated QASM code
3. DO NOT execute anything
4. Suggest: "If you want to execute this code, say 'execute that code' or 'execute on [backend]'"

**Scenario 2: Create AND execute circuit (AUTOMATIC FLOW)**
User: "Create a superposition circuit AND EXECUTE IT" or "Create a Bell state and run it on ibm_kyiv"

KEYWORDS FOR AUTOMATIC EXECUTION:
- "and execute it"
- "and run it"
- "and test it"
- "and execute it on [backend]"

MANDATORY STEPS:
1. Invoke quantum_developer_client with user's request
2. WAIT for complete response from Developer Agent
3. EXTRACT the QASM code from the response
4. IMMEDIATELY invoke quantum_computing_client with:
   - request: "Execute this circuit on [backend]"
   - qasm_code: The extracted QASM code (complete)
   - backend: The requested backend or "ibm_kyiv" by default
5. Return to user:
   - ✅ The generated QASM code (formatted)
   - ✅ The Job ID of the executed work
   - ✅ The backend used
   - ✅ Instructions to query results

**Scenario 3: Only explanation**
User: "Explain what quantum entanglement is"
1. Use quantum_developer_client to get explanation
2. Return the explanation (DO NOT execute anything)

**Scenario 4: Query available computers**
User: "What quantum computers are available?"
1. Use quantum_status_client with the query
2. Status Agent will return the backends table
3. ⚠️ COPY AND PASTE THE EXACT RESPONSE from Status Agent - DO NOT MODIFY
4. DO NOT add additional information, DO NOT invent data, DO NOT summarize

**Scenario 5: Query job status**
User: "What is the status of job d671cklbujdc73cvbp30?"
1. Use quantum_status_client with the query
2. Status Agent will return status and results (if completed)
3. ⚠️ COPY AND PASTE THE EXACT RESPONSE from Status Agent - DO NOT MODIFY

**Scenario 6: Execute existing code**
User: "Execute this QASM code: <code>"
1. Use quantum_computing_client directly (DO NOT invoke Developer)
2. Return Job ID

**Scenario 7: Execute previously generated code (MEMORY) ⚠️ VERY IMPORTANT**
User: "Execute that code" or "run the previous circuit" or "execute on ibm_torino"

⚠️ **CRITICAL MEMORY RULE**:
You have access to the ENTIRE previous conversation. ALWAYS search for QASM code in previous messages BEFORE asking the user to provide it.

KEYWORDS TO EXECUTE PREVIOUS CODE:
- "execute that code"
- "run the circuit"
- "execute the previous one"
- "run it"
- "execute on [backend]"
- "run the circuit on [backend]"

MANDATORY STEPS (DO NOT SKIP ANY):
1. ⚠️ **FIRST**: SEARCH in conversation history for the most recent QASM code
   - Review the last 5-10 messages
   - Look for text starting with "OPENQASM 2.0;" or "OPENQASM 3.0;"
   - Code may be in a code block or plain text

2. **IF YOU FIND CODE** (99% of cases):
   - EXTRACT the complete code (from OPENQASM to the last measure)
   - Use quantum_computing_client IMMEDIATELY with:
     * request: "Execute this circuit on [backend]"
     * qasm_code: The extracted QASM code (complete)
     * backend: The backend specified by user (e.g., "ibm_torino")
   - DO NOT ask for confirmation, DO NOT ask for code again
   - Execute directly

3. **ONLY IF YOU DON'T FIND CODE** (1% of cases):
   - Say: "I can't find QASM code in recent conversation. Can you provide it?"

REAL EXAMPLE:
User first: "Explain what a Bell state is"
→ Developer Agent generates QASM code (it's in history)
User later: "Execute the circuit on ibm_torino"
→ YOU MUST: Search for QASM code in previous messages and execute it
→ YOU MUST NOT: Ask "Please provide the QASM code..."

⚠️ NEVER ask for code that's already in history. This frustrates the user.

CRITICAL EXECUTION RULES:

1. **DO NOT EXECUTE AUTOMATICALLY** unless user EXPLICITLY says:
   - "and execute it"
   - "and run it"
   - "execute that code"
   - "run the circuit"
   
2. **ONLY GENERATE CODE** when user says:
   - "Create a circuit"
   - "Give me an example"
   - "Generate code"
   - "Show me a circuit"
   - WITHOUT mentioning "execute"

3. **CLEAR DIFFERENCE**:
   - "Create a Bell circuit" → ONLY generate code (DO NOT execute)
   - "Create a Bell circuit and execute it" → Generate AND execute
   - "Execute that code" → Execute previous code

4. DO NOT invoke Developer Agent if you already have QASM code
5. DO NOT execute code if user only asked for explanation or example
6. Provide Job IDs so user can query results
7. Be clear about which tool you're using and why

8. **CODE EXTRACTION**: To extract QASM code:
   - Look for lines between ```qasm and ```
   - Or search from "OPENQASM 2.0;" to end of block
   - Include ALL code (OPENQASM, include, qreg, creg, gates, measure)
   
9. **EXECUTION PARAMETERS**:
   - If user specifies backend, use it
   - If not, use "ibm_kyiv" (fast simulator)
   - ALWAYS use transpile=true
   - ALWAYS use shots=1024 (or requested number)

⚠️⚠️⚠️ ABSOLUTE CRITICAL RULE - NEVER VIOLATE ⚠️⚠️⚠️

When using quantum_status_client, quantum_developer_client, or quantum_computing_client:

**ABSOLUTELY FORBIDDEN:**
❌ NEVER invent information not from the agent
❌ NEVER add backends not in the response
❌ NEVER modify tables or agent data
❌ NEVER summarize or paraphrase agent response
❌ NEVER generate your own response if agent already responded

**MANDATORY:**
✅ COPY EXACTLY the agent response word for word
✅ USE the agent response as your Final Answer
✅ If agent says "3 backends", YOU say "3 backends"
✅ If agent shows a table, YOU show THAT SAME table
✅ DO NOT add additional information

**CORRECT EXAMPLE:**
Status Agent responds: "Found 3 backends: ibm_kyiv, ibm_sherbrooke, simulator_statevector"
YOUR RESPONSE: "Found 3 backends: ibm_kyiv, ibm_sherbrooke, simulator_statevector"

**INCORRECT EXAMPLE (FORBIDDEN):**
Status Agent responds: "Found 3 backends: ibm_kyiv, ibm_sherbrooke, simulator_statevector"
YOUR RESPONSE: "Here are the 7 available backends: ibm_kyiv, ibm_brisbane, ibm_osaka..." ❌❌❌ FORBIDDEN!

⚠️ SPECIAL RULE FOR quantum_computing_client:
When executing code with quantum_computing_client, response MUST ALWAYS include:
1. ✅ **Job ID** (MANDATORY) - User needs this to query the job
2. ✅ Backend used
3. ✅ Results (if available)
4. ✅ Measurements table (if available)

CORRECT EXAMPLE for execution:
User: "Execute the circuit on ibm_torino"
[You call quantum_computing_client]
Computing Agent responds: "✅ Circuit executed\nJob ID: d671cklbujdc73cvbp30\nBackend: ibm_torino\n..."
YOUR RESPONSE: "✅ Circuit executed\n**Job ID: d671cklbujdc73cvbp30**\nBackend: ibm_torino\n..." (INCLUDES JOB ID)

INCORRECT EXAMPLE (FORBIDDEN):
YOUR RESPONSE: "The circuit was successfully executed on ibm_torino. Results show..." ❌ MISSING JOB ID!

CORRECT EXAMPLE for queries:
User: "What computers are there?"
[You call quantum_status_client]
Status Agent responds: "🔬 Available computers:\n| Backend | Type | Qubits |..."
YOUR RESPONSE: "🔬 Available computers:\n| Backend | Type | Qubits |..." (EXACT)

RESPONSE FORMAT:
- Use emojis for clarity (🔬 ⚛️ ✅ ❌ 🔄 ⏳)
- Structure responses with clear sections
- Provide context about operations performed
- Suggest next steps when relevant"""

# Agent details for AgentStack
LAB_AGENT_DETAIL = AgentDetail(
    user_greeting="🔬 Hello! I'm the Quantum Lab Agent. Powered by IBM Granite, I coordinate Developer, Status, and Computing agents to design algorithms, run circuits on simulators or IBM Quantum hardware, and track quantum jobs.",
    version="1.1.0",
    framework="BeeAI + A2A + IBM Granite 4.2",
    author={"name": "Edgar Bruney"},
    tools=[
        AgentDetailTool(
            name="Quantum Developer Client (A2A)",
            description="Invokes the Developer Agent (port 8001) to generate quantum code and explanations."
        ),
        AgentDetailTool(
            name="Quantum Status Client (A2A)",
            description="Invokes the Status Agent (port 8002) to query backend status, technical information, and job results."
        ),
        AgentDetailTool(
            name="Quantum Computing Client (A2A)",
            description="Invokes the Computing Agent (port 8003) to execute quantum circuits on simulators or real IBM Quantum hardware."
        )
    ],
)

# Skills exposed by the agent
LAB_AGENT_SKILLS = [
    AgentSkill(
        id="quantum-lab",
        name="Quantum Lab Management",
        description="Orchestrates all quantum operations: code creation, execution, queries, and job management.",
        tags=["Quantum Computing", "IBM Quantum", "Operations", "Orchestration"],
        examples=[
            "Create a Bell state, execute it on the local simulator with 1024 shots, and explain the results",
            "Create Grover's algorithm for 3 qubits and run it on the local simulator",
            "Create a Bell state and execute it once on the least busy real IBM Quantum backend",
            "What quantum computers are available?",
            "Give me detailed information about ibm_fez",
            "Explain what quantum entanglement is",
            "Create and execute a Deutsch-Jozsa circuit for a balanced oracle",
            "Which is the least busy backend?",
            "Show me the status and results of job <job-id>",
            "Show me my recent jobs",
        ]
    )
]

# Create AgentStack server
server = Server()


_CREATE_PATTERN = re.compile(
    r"\b(create|generate|build|make|prepare|design|implement\w*|example|"
    r"crea\w*|genera\w*|constru\w*|prepara\w*|implementa\w*|ejemplo)\b",
    re.IGNORECASE,
)
_EXECUTE_PATTERN = re.compile(
    r"\b(execut\w*|run|running|test\w*|submit\w*|ejec(?:u|ú)t\w*|corre\w*|prueb\w*|prob\w*|env[ií]\w*)\b",
    re.IGNORECASE,
)
_QASM_FENCE_PATTERN = re.compile(r"```(?:open)?qasm\s*(OPENQASM\s+[\s\S]*?)```", re.IGNORECASE)
_QASM_PATTERN = re.compile(r"OPENQASM\s+(?:2\.0|3\.0)\s*;[\s\S]*", re.IGNORECASE)
_JOB_ID_PATTERN = re.compile(r"\b[a-z0-9]{16,}\b", re.IGNORECASE)
_JOB_QUERY_PATTERN = re.compile(r"\b(job|status|estado|result\w*|resultado\w*|consulta\w*)\b", re.IGNORECASE)
_BACKEND_NAME_PATTERN = re.compile(r"\bibm_[a-z0-9_]+\b", re.IGNORECASE)
_STATUS_QUERY_PATTERN = re.compile(
    r"\b(backend\w*|quantum computers?|computadoras? cu[aá]nticas?|available|availability|"
    r"disponible\w*|least busy|less busy|menos ocupad\w*|qubits?|properties|propiedades)\b",
    re.IGNORECASE,
)
_EXPLANATION_PATTERN = re.compile(
    r"\b(explain\w*|describe\w*|what (?:is|are)|how (?:does|do)|explica\w*|"
    r"describe\w*|qu[eé] (?:es|son)|c[oó]mo funciona\w*)\b",
    re.IGNORECASE,
)
_CIRCUIT_OR_ALGORITHM_PATTERN = re.compile(
    r"\b(circuit\w*|circuito\w*|algorithm\w*|algoritmo\w*|qasm|bell(?: state)?|"
    r"grover(?:'s)?|deutsch[- ]jozsa|bernstein[- ]vazirani|qft|shor)\b",
    re.IGNORECASE,
)
_BACKEND_TOPOLOGY_IMAGE_PATTERN = re.compile(
    r"!\[[^\]]*topology[^\]]*\]\((agentstack://[a-f0-9-]+)\)",
    re.IGNORECASE,
)
_EXECUTION_RESULT_IMAGE_PATTERN = re.compile(
    r"!\[[^\]]*execution results[^\]]*\]\((agentstack://[a-f0-9-]+)\)",
    re.IGNORECASE,
)


def _is_create_and_execute_request(request: str) -> bool:
    """Return whether a request explicitly asks to create and execute a circuit."""
    asks_for_a_circuit = _CREATE_PATTERN.search(request) or _CIRCUIT_OR_ALGORITHM_PATTERN.search(request)
    return bool(asks_for_a_circuit and _EXECUTE_PATTERN.search(request))


def _single_job_id_query(request: str) -> str | None:
    """Return the job ID when the request is an unambiguous single-job query."""
    job_ids = list(dict.fromkeys(_JOB_ID_PATTERN.findall(request)))
    return job_ids[0] if len(job_ids) == 1 and _JOB_QUERY_PATTERN.search(request) else None


def _is_status_query(request: str) -> bool:
    """Return whether the request belongs to the Status Agent."""
    if _is_create_and_execute_request(request):
        return False
    return bool(_BACKEND_NAME_PATTERN.search(request) or _STATUS_QUERY_PATTERN.search(request))


def _is_explanation_query(request: str) -> bool:
    """Return whether the request asks the Developer Agent for an explanation."""
    return bool(_EXPLANATION_PATTERN.search(request))


def _backend_canvas_from_status(response: str, backend_name: str) -> AgentArtifact | None:
    """Forward the Status Agent's topology image into the Lab Agent Canvas."""
    image_match = _BACKEND_TOPOLOGY_IMAGE_PATTERN.search(response)
    if not image_match:
        return None
    queried_at = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    return AgentArtifact(
        name=f"{backend_name} topology and status",
        metadata={"backend": backend_name, "content_type": "text/markdown"},
        parts=[
            TextPart(
                text=(
                    f"![{backend_name} topology]({image_match.group(1)})\n\n"
                    "Live data from IBM Quantum. Node color represents readout assignment error.\n\n"
                    f"Consulted locally: {queried_at}"
                )
            )
        ],
    )


def _execution_canvas_from_computing(response: str, qasm_code: str) -> AgentArtifact | None:
    """Forward the Computing Agent's completed result dashboard into Lab Canvas."""
    image_match = _EXECUTION_RESULT_IMAGE_PATTERN.search(response)
    if not image_match:
        return None
    backend_match = re.search(r"\*\*Backend:\*\*\s*([^\n]+)", response)
    backend_name = backend_match.group(1).strip() if backend_match else "Quantum"
    queried_at = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    return AgentArtifact(
        name=f"{backend_name} execution results",
        metadata={"backend": backend_name, "content_type": "text/markdown"},
        parts=[
            TextPart(
                text=(
                    f"![Quantum execution results]({image_match.group(1)})\n\n"
                    f"Consulted locally: {queried_at}\n\n"
                    f"```qasm\n{qasm_code}\n```"
                )
            )
        ],
    )


def _job_results_canvas_from_status(response: str, job_id: str) -> AgentArtifact | None:
    """Forward a freshly retrieved single-job histogram into Lab Canvas."""
    image_match = re.search(r"!\[[^\]]*\]\((agentstack://[a-f0-9-]+)\)", response, re.IGNORECASE)
    if not image_match:
        return None
    queried_at = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    return AgentArtifact(
        name=f"Job {job_id} results",
        metadata={"job_id": job_id, "content_type": "text/markdown", "fresh_query": True},
        parts=[
            TextPart(
                text=(
                    f"![Quantum job results]({image_match.group(1)})\n\n"
                    "Live measurement results retrieved from IBM Quantum for this query.\n\n"
                    f"Consulted locally: {queried_at}"
                )
            )
        ],
    )


def _extract_qasm(response: str) -> str | None:
    """Extract a complete OpenQASM program from an agent response."""
    fenced_match = _QASM_FENCE_PATTERN.search(response)
    if fenced_match:
        qasm = fenced_match.group(1)
        if "\\n" in qasm:
            qasm = qasm.replace("\\r\\n", "\n").replace("\\n", "\n").replace('\\"', '"')
        return qasm.strip()

    qasm_match = _QASM_PATTERN.search(response)
    if not qasm_match:
        return None

    qasm = qasm_match.group(0)
    # Client responses append their own Markdown note after the generated answer.
    qasm = re.split(r"\n\s*---\s*\n", qasm, maxsplit=1)[0]
    if "\\n" in qasm:
        qasm = qasm.replace("\\r\\n", "\n").replace("\\n", "\n").replace('\\"', '"')
    return qasm.strip()


async def _create_and_execute(request: str) -> tuple[str, str]:
    """Run the two-agent workflow without relying on an LLM to copy QASM between tools."""
    developer_request = (
        "Generate only the complete OpenQASM 2.0 circuit requested below. "
        "Include measurements, return exactly one qasm code block, and do not execute it or discuss backends.\n\n"
        f"User request: {request}"
    )
    developer_output = await asyncio.wait_for(
        QuantumDeveloperClient().run({"request": developer_request, "format": "qasm"}),
        timeout=420,
    )
    developer_response = developer_output.get_text_content()
    qasm_code = _extract_qasm(developer_response)
    if not qasm_code:
        raise ValueError("The Developer Agent response did not contain a complete OpenQASM program.")

    from qiskit import QuantumCircuit

    circuit = QuantumCircuit.from_qasm_str(qasm_code)
    if not any(instruction.operation.name == "measure" for instruction in circuit.data):
        raise ValueError("The generated OpenQASM program does not contain measurements.")

    execution_request = (
        f"{request}\n\n"
        "Execute exactly once. If the user requested real hardware without naming a backend, "
        "select the least busy operational real backend. Only use a simulator when the user "
        "did not request real hardware and did not name a backend. "
        "Return the Job ID, backend, status, and results when available.\n\n"
        f"```qasm\n{qasm_code}\n```"
    )
    computing_output = await asyncio.wait_for(
        QuantumComputingClient().run({"request": execution_request}),
        timeout=300,
    )
    return developer_response, computing_output.get_text_content()


def create_lab_agent():
    """Create the Quantum Lab Agent with its configured chat model."""
    from beeai_framework.agents.react.runners.default.prompts import SystemPromptTemplateInput
    from beeai_framework.template import PromptTemplate
    
    llm = create_chat_model("LAB")
    
    # Create a custom system template that FORCES exact response copying
    custom_system_template = PromptTemplate(
        schema=SystemPromptTemplateInput,
        template="""# YOUR ROLE AND CRITICAL RULES
""" + LAB_INSTRUCTIONS + """

# Available functions
{{#tools.0}}
You have access to the following A2A client tools to invoke specialized agents:

{{#tools}}
Function Name: {{name}}
Description: {{description}}
Input Schema: {{&input_schema}}

{{/tools}}
{{/tools.0}}

# Communication structure
You communicate only in instruction lines. The format is: "Instruction: expected output".

Message: User's message. You never use this instruction line.
Thought: Your step-by-step plan. This MUST be immediately followed by Function Name (to call a function) or Final Answer.
Function Name: Name of the function to call. This MUST be immediately followed by Function Input.
Function Input: Function parameters in JSON format, e.g. {{"arg1":"value1", "arg2":"value2"}}
Function Output: Output of the function in JSON format.
Final Answer: Your response to the user. Must always be preceded by Thought.

# ⚠️⚠️⚠️ CRITICAL RULE - NEVER VIOLATE ⚠️⚠️⚠️

When you call quantum_status_client, quantum_developer_client, or quantum_computing_client:

**YOUR FINAL ANSWER MUST BE THE EXACT FUNCTION OUTPUT - WORD FOR WORD**

DO NOT:
❌ Add information not in the Function Output
❌ Modify tables or data from the Function Output
❌ Invent backends, jobs, or data not in the Function Output
❌ Summarize or paraphrase the Function Output

DO:
✅ Copy the Function Output EXACTLY as your Final Answer
✅ Use the EXACT same words, numbers, and format
✅ If Function Output says "3 backends", you say "3 backends"
✅ If Function Output shows a table, you show THAT EXACT table

## Example of CORRECT behavior:
Message: What quantum computers are available?
Thought: I need to call quantum_status_client to get the list of available quantum computers
Function Name: quantum_status_client
Function Input: {{"request": "What quantum computers are available?"}}
Function Output: Found 3 available backends: ibm_kyiv, ibm_sherbrooke, simulator_statevector

Thought: I will use the EXACT Function Output as my Final Answer without any modifications
Final Answer: Found 3 available backends: ibm_kyiv, ibm_sherbrooke, simulator_statevector

## Example of INCORRECT behavior (FORBIDDEN):
Message: What quantum computers are available?
Function Output: Found 3 available backends: ibm_kyiv, ibm_sherbrooke, simulator_statevector
Final Answer: Here are the 7 available backends: ibm_kyiv, ibm_brisbane, ibm_osaka... ❌❌❌ FORBIDDEN!

**REMEMBER: Your Final Answer = Function Output (EXACT COPY)**
""",
    )
    
    # Create the agent with the custom template
    return ReActAgent(
        llm=llm,
        tools=[
            QuantumDeveloperClient(),
            QuantumStatusClient(),
            QuantumComputingClient(),
        ],
        memory=TokenMemory(max_tokens=6000),
        templates={"system": custom_system_template},  # Custom template
    )

@server.agent(
    name="Quantum Lab Agent",
    detail=LAB_AGENT_DETAIL,
    skills=LAB_AGENT_SKILLS,
    default_output_modes=["text/plain", "image/png"],
)
async def quantum_lab_agent(
    input: Message,
    context: RunContext,
    trajectory: Annotated[TrajectoryExtensionServer, TrajectoryExtensionSpec()],
    _canvas: Annotated[CanvasExtensionServer, CanvasExtensionSpec()],
):
    """
    Main handler for the Quantum Lab Agent.
    
    This agent orchestrates all quantum operations and decides
    when to invoke the Developer Agent or use tools directly.
    
    Includes conversation history management to maintain context.
    """
    # STEP 0: Store user message in history (best-effort - not critical for operation)
    try:
        await context.store(input)
    except Exception as e:
        print(f"⚠️ [History] Could not store user message (timeout or error): {str(e)}")

    user_query = get_message_text(input)
    print("=" * 80)
    print(f"⚡ [Lab Agent] Received query: '{user_query[:100]}...'")
    print("=" * 80)
    
    # Load conversation history with error handling
    history = []
    try:
        history = [
            message async for message in context.load_history()
            if isinstance(message, Message) and message.parts
        ]
        print(f"📚 [History] Loaded {len(history)} messages from conversation history")
    except Exception as e:
        print(f"⚠️ [History] Could not load history (timeout or error): {str(e)}")
        print(f"📝 [History] Continuing without history context")
        # Continue without history - not critical for operation
    
    # Step 1: Request analysis
    yield trajectory.trajectory_metadata(
        title="🔍 Analyzing request",
        content=f"Processing user query:\n```\n{user_query[:200]}{'...' if len(user_query) > 200 else ''}\n```\n\n**Context:** {len(history)} messages in history"
    )

    # Creating and executing requires two dependent tool calls. Route this
    # workflow deterministically so a model cannot lose the generated QASM,
    # hallucinate a tool name, or stop after only the first agent responds.
    if _is_create_and_execute_request(user_query):
        yield trajectory.trajectory_metadata(
            title="🧪 Creating quantum circuit",
            content="Requesting complete OpenQASM code from the Developer Agent...",
        )
        try:
            developer_response, computing_response = await _create_and_execute(user_query)
            response = (
                f"{developer_response.rstrip()}\n\n"
                "## ⚡ Execution\n\n"
                f"{computing_response.lstrip()}"
            )

            qasm_code = _extract_qasm(developer_response)
            artifact = _execution_canvas_from_computing(computing_response, qasm_code or "")
            if artifact:
                yield artifact
                try:
                    await context.store(artifact)
                except Exception as store_error:
                    print(f"⚠️ [Canvas] Could not store execution artifact: {explain_error(store_error)}")

            yield trajectory.trajectory_metadata(
                title="✅ Circuit created and submitted",
                content=(
                    "- [x] QASM generated and validated\n"
                    "- [x] Circuit sent once to the Computing Agent\n"
                    "- [x] Execution response received"
                ),
            )

            response_message = AgentMessage(text=response)
            yield response_message
            try:
                await context.store(response_message)
                print("📚 [History] Deterministic workflow response stored")
            except Exception as e:
                print(f"⚠️ [History] Could not store response (timeout or error): {str(e)}")
            return
        except Exception as e:
            error_message = AgentMessage(
                text=(
                    "❌ I could not complete the create-and-execute workflow. "
                    f"{explain_error(e)}"
                )
            )
            yield trajectory.trajectory_metadata(
                title="❌ Create-and-execute workflow failed",
                content=f"**Type:** {type(e).__name__}\n**Message:** {explain_error(e)}",
            )
            yield error_message
            try:
                await context.store(error_message)
            except Exception as store_error:
                print(f"⚠️ [History] Could not store error response: {str(store_error)}")
            return

    job_id = _single_job_id_query(user_query)
    if job_id:
        yield trajectory.trajectory_metadata(
            title="📊 Querying quantum job",
            content=f"Querying IBM Quantum for job `{job_id}`...",
        )
        try:
            status_output = await asyncio.wait_for(
                QuantumStatusClient().run({"query": user_query}),
                timeout=180,
            )
            status_response = status_output.get_text_content()
            artifact = _job_results_canvas_from_status(status_response, job_id)
            if artifact:
                yield artifact
                try:
                    await context.store(artifact)
                except Exception as store_error:
                    print(f"⚠️ [Canvas] Could not store job results artifact: {explain_error(store_error)}")
            response_message = AgentMessage(text=status_response)
            yield trajectory.trajectory_metadata(
                title="✅ Job status obtained",
                content="The Status Agent returned current IBM Quantum job data.",
            )
            yield response_message
            try:
                await context.store(response_message)
            except Exception as e:
                print(f"⚠️ [History] Could not store status response: {str(e)}")
        except Exception as e:
            yield trajectory.trajectory_metadata(
                title="❌ Job query failed",
                content=f"**Type:** {type(e).__name__}\n**Message:** {explain_error(e)}",
            )
            yield AgentMessage(text=f"❌ Could not query job `{job_id}`: {explain_error(e)}")
        return

    # Common backend queries have a single correct destination. Route them
    # directly so local models cannot emit an unexecuted tool-call payload.
    if _is_status_query(user_query):
        yield trajectory.trajectory_metadata(
            title="📊 Querying IBM Quantum",
            content="Routing the request directly to the Status Agent...",
        )
        try:
            status_output = await asyncio.wait_for(
                QuantumStatusClient().run({"query": user_query}),
                timeout=180,
            )
            status_response = status_output.get_text_content()
            backend_names = list(dict.fromkeys(_BACKEND_NAME_PATTERN.findall(user_query)))
            if len(backend_names) == 1:
                artifact = _backend_canvas_from_status(status_response, backend_names[0].lower())
                if artifact:
                    yield artifact
                    try:
                        await context.store(artifact)
                    except Exception as store_error:
                        print(f"⚠️ [Canvas] Could not store artifact history: {explain_error(store_error)}")
            response_message = AgentMessage(text=status_response)
            yield response_message
            try:
                await context.store(response_message)
            except Exception as e:
                print(f"⚠️ [History] Could not store status response: {str(e)}")
        except Exception as e:
            yield AgentMessage(text=f"❌ Could not complete status query: {explain_error(e)}")
        return

    # Concept explanations belong to the Developer Agent. The explicit
    # explanation format prevents its A2A client from appending a QASM request.
    if _is_explanation_query(user_query):
        yield trajectory.trajectory_metadata(
            title="💡 Explaining quantum concept",
            content="Routing the request directly to the Developer Agent...",
        )
        try:
            developer_output = await asyncio.wait_for(
                QuantumDeveloperClient().run({"request": user_query, "format": "explanation"}),
                timeout=420,
            )
            response_message = AgentMessage(text=developer_output.get_text_content())
            yield response_message
            try:
                await context.store(response_message)
            except Exception as e:
                print(f"⚠️ [History] Could not store explanation response: {str(e)}")
        except Exception as e:
            yield AgentMessage(text=f"❌ Could not explain the quantum concept: {explain_error(e)}")
        return
    
    # Create agent with instructions and tools
    agent = create_lab_agent()
    
    # Step 2: Agent preparation
    yield trajectory.trajectory_metadata(
        title="🤖 Preparing ReAct agent",
        content=f"**Configuration:**\n- Model: {model_name('LAB')}\n- Tools: Developer Client, Status Client, Computing Client\n- Memory: 6K tokens\n- History: {len(history)} messages loaded"
    )
    
    # Build conversation context for the prompt
    conversation_context = ""
    if len(history) > 1:  # More than 1 message (the current one)
        conversation_context = "\n\n---\n\nCONVERSATION HISTORY:\n"
        # Include last 5 messages (excluding current)
        recent_history = history[-6:-1] if len(history) > 5 else history[:-1]
        for i, msg in enumerate(recent_history, 1):
            msg_text = get_message_text(msg)
            role = "User" if msg.role.value == "user" else "Assistant"
            conversation_context += f"\n{i}. [{role}]: {msg_text[:150]}{'...' if len(msg_text) > 150 else ''}\n"
    
    # Build prompt with system instructions and context
    full_prompt = f"{LAB_INSTRUCTIONS}{conversation_context}\n\n---\n\nCURRENT USER REQUEST:\n{user_query}"
    
    # Step 3: Agent execution
    yield trajectory.trajectory_metadata(
        title="⚙️ Executing reasoning",
        content="Agent is analyzing the request and deciding which tools to use..."
    )
    
    # Execute the agent
    try:
        # Execute without explicit emitter - agent uses its own internal emitter
        run_context = await run_agent_with_retries(agent, full_prompt)
        
        # Update trajectory with progress
        yield trajectory.trajectory_metadata(
            title="✅ Processing completed",
            content="- [x] Reasoning completed\n- [x] Tools executed\n- [x] Response generated"
        )
        
        # Extract the response
        response = ""
        if hasattr(run_context, 'output') and run_context.output:
            output = run_context.output
            if isinstance(output, list) and output:
                last_msg = output[-1]
                if hasattr(last_msg, 'text'):
                    response = str(last_msg.text)
                elif hasattr(last_msg, 'content'):
                    response = str(last_msg.content)
                else:
                    response = str(last_msg)
            else:
                response = str(output)
        else:
            response = str(run_context)
        
        # Ensure response is string
        if not isinstance(response, str):
            response = str(response)
        
        # Step 4: Response generated
        yield trajectory.trajectory_metadata(
            title="✅ Response generated",
            content=f"Response ready ({len(response)} characters)\n\n**Summary:**\n- Tools used\n- Processing time: Completed"
        )
        
        print("=" * 80)
        print(f"✅ [Lab Agent] Response generated ({len(response)} chars)")
        print("=" * 80)
        
        # Create response message
        response_message = AgentMessage(text=response)
        
        # Yield response to user
        yield response_message
        
        # IMPORTANT: Store response in history for future interactions (best-effort)
        try:
            await context.store(response_message)
            print("📚 [History] Response stored in conversation history")
        except Exception as e:
            print(f"⚠️ [History] Could not store response (timeout or error): {str(e)}")

    except Exception as e:
        import traceback
        error_msg = f"❌ Error in Lab Agent: {explain_error(e)}"
        error_details = f"\n\nError type: {type(e).__name__}\n"
        error_details += f"Details: {explain_error(e)}\n\n"
        error_details += "Traceback:\n"
        error_details += traceback.format_exc()

        # Error trajectory
        yield trajectory.trajectory_metadata(
            title="❌ Error detected",
            content=f"**Type:** {type(e).__name__}\n**Message:** {explain_error(e)}\n\nCheck logs for more details."
        )

        print("=" * 80)
        print(f"🔴 [Lab Agent] {error_msg}")
        print(error_details)
        print("=" * 80)

        yield AgentMessage(text=error_msg)

def run():
    """Starts the Quantum Lab Agent server with persistent storage"""
    port = int(os.getenv("LAB_PORT", 8000))
    host = os.getenv("LAB_HOST", "127.0.0.1")

    print("=" * 80)
    print("🚀 Starting Quantum Lab Agent Server")
    print("=" * 80)
    print(f"  ⚡ Agent: Quantum Lab Agent (Orchestrator)")
    print(f"  🤖 Model: {model_name('LAB')}")
    print(f"  🌐 Host: {host}")
    print(f"  🔌 Port: {port}")
    print(f"  🛠️  Tools: 3 (Developer Client A2A, Status Client A2A, Computing Client A2A)")
    print(f"  📚 History: Persistent storage enabled (PlatformContextStore)")
    print(f"  🎯 Trajectory: Visualization enabled")
    print(f"  🔗 Developer Agent: http://{os.getenv('DEVELOPER_HOST', '127.0.0.1')}:{os.getenv('DEVELOPER_PORT', '8001')}")
    print(f"  🔗 Status Agent: http://{os.getenv('STATUS_HOST', '127.0.0.1')}:{os.getenv('STATUS_PORT', '8002')}")
    print(f"  🔗 Computing Agent: http://{os.getenv('COMPUTING_HOST', '127.0.0.1')}:{os.getenv('COMPUTING_PORT', '8003')}")
    print("=" * 80)
    print("\n💡 Tip: Make sure the 3 specialized agents are running:")
    print("   - Developer Agent (8001)")
    print("   - Status Agent (8002)")
    print("   - Computing Agent (8003)")
    print("=" * 80)
    
    # Enable persistent conversation storage
    server.run(
        host=host,
        port=port,
        context_store=PlatformContextStore()  # Persistent storage
    )

if __name__ == "__main__":
    run()
