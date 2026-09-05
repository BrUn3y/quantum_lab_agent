"""
Quantum Status Agent - Quantum Status Query Specialist

This agent is a specialist in:
- Querying available quantum computers on IBM Quantum
- Obtaining detailed technical information about backends
- Querying status and results of quantum jobs
- Listing user's recent jobs

Model: configurable via STATUS_MODEL (Ollama/Watsonx)
Port: 8002
Type: AgentStack Server with A2A (ReActAgent with query tools)
"""

import os
import re
import tempfile
import time
from typing import Annotated
from collections.abc import AsyncGenerator
from pathlib import Path

from a2a.types import AgentSkill, Message, TextPart
from a2a.utils.message import get_message_text
from agentstack_sdk.server import Server
from agentstack_sdk.server.context import RunContext
from agentstack_sdk.server.store.platform_context_store import PlatformContextStore
from agentstack_sdk.a2a.types import AgentArtifact, AgentMessage
from agentstack_sdk.a2a.extensions import AgentDetail, AgentDetailTool
from agentstack_sdk.a2a.extensions import TrajectoryExtensionServer, TrajectoryExtensionSpec
from agentstack_sdk.a2a.extensions.ui.canvas import CanvasExtensionServer, CanvasExtensionSpec
from agentstack_sdk.platform.file import File

from beeai_framework.agents.react import ReActAgent
from beeai_framework.agents.react.runners.default.prompts import SystemPromptTemplateInput
from beeai_framework.memory import UnconstrainedMemory
from beeai_framework.template import PromptTemplate

from .model_config import create_chat_model, explain_error, model_name, run_agent_with_retries
from .backend_visualization import BACKEND_CANVAS_MARKER

# Import query tools
from .tools import (
    IBMQuantumStatusTool,
    IBMQuantumInfoTool,
    IBMQuantumJobTool,
    IBMQuantumJobComparisonTool,
)

# SIMPLIFIED instructions for Status Agent (to reduce response size)
STATUS_INSTRUCTIONS = """You are the Quantum Status Agent. You query the status of quantum computers and jobs.

⚠️ RULE: ALWAYS use a tool to get data. NEVER invent information.

YOUR SPECIALTY:
- Query available quantum computers on IBM Quantum
- Provide detailed technical information about backends
- Query status and results of quantum jobs
- List user's recent jobs

AVAILABLE TOOLS (YOU MUST ALWAYS USE ONE):

1. **ibm_quantum_status** - List quantum computers
   
   USE WHEN:
   ✅ User asks "what computers are available?"
   ✅ User asks "which is the least busy?"
   ✅ User asks "show me the backends"
   ✅ User asks "what simulators are there?"
   ✅ User asks "available backends"
   
   PARAMETERS:
   - only_hardware: false (for all), true (only real hardware)
   
   IMPORTANT: This tool returns a formatted table. You MUST show the complete table to the user.
   
   EXPECTED OUTPUT:
   - Table with all available backends
   - Type (Hardware/Simulator)
   - Number of qubits
   - Operational status
   - Jobs in queue
   - Recommendation for least busy

2. **ibm_quantum_info** - Detailed backend information
   
   USE WHEN:
   ✅ User asks "give me information about [backend]"
   ✅ User asks "how many qubits does [backend] have?"
   ✅ User asks "what is the error rate of [backend]?"
   ✅ User asks "properties of [backend]"
   
   PARAMETERS:
   - backend_name: Backend name (e.g., "ibm_brisbane")
   
   EXPECTED OUTPUT:
   - Qubit properties (T1, T2, frequency)
   - Quantum gate errors
   - Connectivity topology
   - Supported operations
   - Processor configuration

3. **ibm_quantum_job** - Query individual jobs
   
   USE WHEN:
   ✅ User provides A SINGLE Job ID
   ✅ User asks "what is the status of my job?"
   ✅ User asks "show me my jobs"
   ✅ User asks "what jobs do I have running?"
   ✅ User asks "show me completed jobs"
   
   PARAMETERS:
   - job_id: Empty or "list" to list all, or specific Job ID
   - filter_status: "all", "running", "queued", "done", "error"
   
   EXPECTED OUTPUT:
   - Job status (QUEUED, RUNNING, DONE, ERROR)
   - Measurement results (if completed)
   - Probability distribution
   - Recent jobs table (if listing)

4. **ibm_quantum_job_comparison** - Compare multiple jobs
   
   USE WHEN:
   ✅ User says "compare the results of jobs X, Y, Z"
   ✅ User says "compare these jobs: [list of IDs]"
   ✅ User asks "what is the difference between these jobs?"
   ✅ User wants to see side-by-side results of MULTIPLE jobs
   
   PARAMETERS:
   - job_ids: List of 2 to 5 Job IDs (e.g., ["d6cd297g4t5c7385dh4g", "d6cd2bknsg9c739a32p0"])
   
   EXPECTED OUTPUT:
   - Comparative table with results from each job
   - Analysis of differences between jobs
   - Identification of common or divergent patterns
   - Most probable states from each job
   
   ⚠️ IMPORTANT: This tool extracts the REAL results from each job separately,
   avoiding the problem of showing identical results for all jobs.
   
   ⚠️ IMPORTANT FOR RESULT INTERPRETATION:
   When showing results from a completed job, you MUST add intelligent interpretation based on:
   
   **Grover's Algorithm (Search):**
   - Look for the state with highest probability (>80%)
   - That is the target state the algorithm found
   - Example: If `100` has 94%, then Grover successfully found state |100⟩
   
   **Bell State (Entanglement):**
   - Expect to see mainly `00` and `11` with ~50% each
   - Small variations are normal due to quantum noise
   
   **Deutsch-Jozsa Algorithm:**
   - If result is `0...0` → constant function
   - If result is different → balanced function
   
   **Bernstein-Vazirani Algorithm:**
   - The state with highest probability is the secret string
   
   **Uniform Superposition:**
   - All states should have similar probabilities
   
   **RULE**: Analyze the probability distribution and provide relevant interpretation for the type of circuit executed.

USAGE EXAMPLES:

**Example 1: List computers**
User: "What quantum computers are available?"
Action: Use ibm_quantum_status with only_hardware=False
Response: Table with all backends (hardware + simulators)

**Example 2: Specific backend info**
User: "Give me detailed information about ibm_brisbane"
Action: Use ibm_quantum_info with backend_name="ibm_brisbane"
Response: Complete technical properties of the backend

**Example 3: Job status**
User: "What is the status of job d671cklbujdc73cvbp30?"
Action: Use ibm_quantum_job with job_id="d671cklbujdc73cvbp30"
Response: Current status and results (if completed)

**Example 4: List running jobs**
User: "Show me my running jobs"
Action: Use ibm_quantum_job with job_id="" and filter_status="running"
Response: Table with jobs in RUNNING state

**Example 5: Only real hardware**
User: "What real quantum computers are available?"
Action: Use ibm_quantum_status with only_hardware=True
Response: Table with only real hardware (no simulators)

CRITICAL RULES (MANDATORY):

1. ⚠️ **NEVER RESPOND WITHOUT USING A TOOL**
   - If user asks about backends, USE ibm_quantum_status
   - If user asks about a specific backend, USE ibm_quantum_info
   - If user asks about jobs, USE ibm_quantum_job
   - DO NOT say "Here is the list" without showing the actual list

2. ⚠️ **ALWAYS SHOW COMPLETE DATA WITHOUT MODIFICATION**
   - If the tool returns a table, COPY AND PASTE THE TABLE EXACTLY AS IT COMES
   - DO NOT modify, do not summarize, DO NOT omit columns
   - DO NOT reformat the table - use the EXACT format from the tool
   - If the tool returns results, SHOW THE COMPLETE RESULTS

3. ⚠️ **DO NOT INVENT DATA**
   - All information must come from the tools
   - If you don't have data, use the tool to get it
   - DO NOT say "there are X backends" without using the tool

4. **RESPONSE FORMAT**:
   - Show the complete output from the tool
   - Add useful context after the data
   - Use emojis to improve readability (🔬 ⚛️ ✅ ❌ 🔄 ⏳)
   - Suggest next steps when relevant

5. **CORRECT FLOW**:
   ```
   User: "What computers are available?"
   
   ❌ INCORRECT:
   "Here is the list of computers. If you need more details..."
   
   ✅ CORRECT:
   [Invoke ibm_quantum_status]
   [Show complete table with backends]
   "💡 Tip: For more details about a specific backend, ask about it."
   ```

LIMITATIONS:
❌ You CANNOT execute quantum circuits
❌ You CANNOT generate QASM or Qiskit code
❌ You CANNOT modify backend configurations
❌ You CANNOT cancel jobs

ONLY QUERIES (ALWAYS WITH TOOLS):
✅ Query backend status → ibm_quantum_status
✅ Query backend information → ibm_quantum_info
✅ Query job status → ibm_quantum_job
✅ Query job results → ibm_quantum_job
✅ List user's jobs → ibm_quantum_job

REMEMBER: Your value is in providing REAL and UP-TO-DATE data from IBM Quantum, not generic responses.
"""

_JOB_ID_PATTERN = re.compile(r"\b[a-z0-9]{16,}\b", re.IGNORECASE)
_BACKEND_NAME_PATTERN = re.compile(r"\bibm_[a-z0-9_]+\b", re.IGNORECASE)
_BACKEND_LIST_PATTERN = re.compile(
    r"\b(available|availability|quantum computers?|backends?|least busy|less busy|"
    r"disponible\w*|computadoras? cu[aá]nticas?|menos ocupad\w*)\b",
    re.IGNORECASE,
)
_HARDWARE_ONLY_PATTERN = re.compile(r"\b(real|hardware|f[ií]sic\w*)\b", re.IGNORECASE)

# Agent details for AgentStack
STATUS_AGENT_DETAIL = AgentDetail(
    user_greeting="📊 Hello! I'm the Quantum Status Agent. I query the status of IBM quantum computers, technical backend information, and quantum job results in real-time.",
    version="1.0.0",
    framework="BeeAI + A2A (Watsonx/Ollama)",
    author={"name": "Edgar Bruney"},
    tools=[
        AgentDetailTool(
            name="IBM Quantum Status",
            description="Lists all available quantum computers on IBM Quantum with their operational status."
        ),
        AgentDetailTool(
            name="IBM Quantum Info",
            description="Gets detailed technical information about a specific backend (qubits, errors, topology)."
        ),
        AgentDetailTool(
            name="IBM Quantum Job",
            description="Queries the status and results of individual quantum jobs or lists recent jobs."
        ),
        AgentDetailTool(
            name="IBM Quantum Job Comparison",
            description="Compares results from multiple quantum jobs side by side."
        )
    ],
)

# Skills exposed by the agent
STATUS_AGENT_SKILLS = [
    AgentSkill(
        id="quantum-backend-status",
        name="Quantum Backend Status Queries",
        description="Queries the status and availability of IBM quantum computers in real-time.",
        tags=["Quantum Computing", "IBM Quantum", "Backend Status", "Availability"],
        examples=[
            "What quantum computers are available?",
            "Which is the least busy backend?",
            "Show me only real quantum hardware",
            "List available simulators",
            "What backends are operational?"
        ]
    ),
    AgentSkill(
        id="quantum-backend-info",
        name="Quantum Backend Technical Information",
        description="Gets detailed technical information about specific backends (qubit properties, errors, topology).",
        tags=["Quantum Computing", "IBM Quantum", "Backend Info", "Technical Details"],
        examples=[
            "Give me detailed information about ibm_fez",
            "What are the properties of ibm_torino?",
            "How many qubits does ibm_kyiv have?",
            "Show me the error rates of ibm_sherbrooke",
            "What is the topology of ibm_osaka?"
        ]
    ),
    AgentSkill(
        id="quantum-job-status",
        name="Quantum Job Status and Results",
        description="Queries the status, results, and measurements of executed quantum jobs.",
        tags=["Quantum Computing", "IBM Quantum", "Job Status", "Results"],
        examples=[
            "What is the status of job d671cklbujdc73cvbp30?",
            "What is the status of job abc123xyz?",
            "Show me my recent jobs",
            "Show me my running jobs",
            "List my completed jobs"
        ]
    ),
    AgentSkill(
        id="quantum-job-comparison",
        name="Quantum Job Comparison",
        description="Compares results from multiple quantum jobs for side-by-side analysis.",
        tags=["Quantum Computing", "IBM Quantum", "Job Comparison", "Analysis"],
        examples=[
            "Compare the results of jobs d6cd297g4t5c7385dh4g and d6cd2bknsg9c739a32p0",
            "Compare jobs abc123 and xyz789",
            "What is the difference between these jobs: job1, job2, job3?",
            "Show me a comparison of these job results"
        ]
    )
]

# Temporary directory shared with tools for quantum PNGs
_QUANTUM_PNG_DIR = os.path.join(tempfile.gettempdir(), "quantum_lab_pngs")

# Pattern to detect PNG markers in tool output
# Format: __QUANTUM_PNG__<file_path>__END_PNG__
_PNG_MARKER_PATTERN = re.compile(
    r'__QUANTUM_PNG__([^\n]+?)__END_PNG__'
)


async def _upload_png_and_replace(text: str) -> str:
    """
    Searches for __QUANTUM_PNG__ markers in text, reads the temporary PNG file,
    uploads it to AgentStack using File.create() and replaces the marker with
    image markdown using agentstack:// URL.
    
    If the LLM modified/truncated the marker, also searches for recent PNGs
    in the temporary directory (created in the last 120 seconds).
    """
    result = text
    uploaded_paths = set()
    
    # Strategy 1: Search for explicit markers in text
    matches = list(_PNG_MARKER_PATTERN.finditer(text))
    for match in reversed(matches):  # reversed to not shift indices
        png_path = match.group(1).strip()
        try:
            with open(png_path, 'rb') as f:
                png_bytes = f.read()
            
            png_name = os.path.basename(png_path).replace('.png', '')
            uploaded = await File.create(
                filename=f"{png_name}.png",
                content=png_bytes,
                content_type="image/png",
            )
            
            img_markdown = f"\n![Quantum Histogram](agentstack://{uploaded.id})\n"
            result = result[:match.start()] + img_markdown + result[match.end():]
            uploaded_paths.add(png_path)
            print(f"[Status Agent] PNG uploaded (marker): {png_name}.png → agentstack://{uploaded.id}")
            
            try:
                os.remove(png_path)
            except Exception:
                pass
                
        except Exception as e:
            print(f"[Status Agent] Error uploading PNG '{png_path}': {e}")
            result = result[:match.start()] + result[match.end():]
    
    # Strategy 2: Search for recent PNGs in temporary directory
    # (in case the LLM modified/truncated the marker)
    try:
        if os.path.exists(_QUANTUM_PNG_DIR):
            now = time.time()
            for fname in sorted(os.listdir(_QUANTUM_PNG_DIR)):
                if not fname.endswith('.png'):
                    continue
                fpath = os.path.join(_QUANTUM_PNG_DIR, fname)
                if fpath in uploaded_paths:
                    continue
                # Only PNGs created in the last 120 seconds
                if now - os.path.getmtime(fpath) > 120:
                    continue
                try:
                    with open(fpath, 'rb') as f:
                        png_bytes = f.read()
                    
                    png_name = fname.replace('.png', '')
                    uploaded = await File.create(
                        filename=fname,
                        content=png_bytes,
                        content_type="image/png",
                    )
                    
                    result += f"\n![Quantum Histogram](agentstack://{uploaded.id})\n"
                    print(f"[Status Agent] PNG uploaded (directory): {fname} → agentstack://{uploaded.id}")
                    
                    try:
                        os.remove(fpath)
                    except Exception:
                        pass
                        
                except Exception as e:
                    print(f"[Status Agent] Error uploading PNG from directory '{fpath}': {e}")
    except Exception as e:
        print(f"[Status Agent] Error scanning PNG directory: {e}")
    
    return result


async def _create_backend_canvas(text: str, backend_name: str) -> tuple[str, AgentArtifact | None]:
    """Upload a generated backend dashboard and prepare its Canvas artifact."""
    match = BACKEND_CANVAS_MARKER.search(text)
    clean_text = BACKEND_CANVAS_MARKER.sub("", text).rstrip()
    if not match:
        return clean_text, None

    dashboard_path = Path(match.group(1).strip()).resolve()
    allowed_directory = (Path(tempfile.gettempdir()) / "quantum_lab_pngs").resolve()
    if dashboard_path.parent != allowed_directory or not dashboard_path.is_file():
        return clean_text + "\n\n⚠️ The topology image could not be loaded safely.", None

    try:
        uploaded = await File.create(
            filename=f"{backend_name}_topology.png",
            content=dashboard_path.read_bytes(),
            content_type="image/png",
        )
        queried_at = time.strftime("%Y-%m-%d %H:%M:%S %Z")
        artifact = AgentArtifact(
            name=f"{backend_name} topology and status",
            description=f"Live IBM Quantum topology and health summary for {backend_name}.",
            metadata={"backend": backend_name, "content_type": "text/markdown"},
            parts=[
                TextPart(
                    text=(
                        f"![{backend_name} topology](agentstack://{uploaded.id})\n\n"
                        "Live data from IBM Quantum. Node color represents readout assignment error.\n\n"
                        f"Consulted locally: {queried_at}"
                    )
                )
            ],
        )
        clean_text += (
            "\n\n## 🗺️ Visual topology and health summary\n\n"
            f"![{backend_name} topology](agentstack://{uploaded.id})\n\n"
            "The dashboard is also available in Canvas."
        )
        return clean_text, artifact
    except Exception as error:
        return clean_text + f"\n\n⚠️ Canvas upload failed: {explain_error(error)}", None
    finally:
        dashboard_path.unlink(missing_ok=True)


def _create_job_results_canvas(response: str, job_id: str) -> AgentArtifact | None:
    """Expose an uploaded job histogram in Canvas for single-job queries."""
    image_match = re.search(r"!\[[^\]]*\]\((agentstack://[a-f0-9-]+)\)", response, re.IGNORECASE)
    if not image_match:
        return None
    queried_at = time.strftime("%Y-%m-%d %H:%M:%S %Z")
    return AgentArtifact(
        name=f"Job {job_id} results",
        description=f"Measurement outcomes for IBM Quantum job {job_id}.",
        metadata={"job_id": job_id, "content_type": "text/markdown"},
        parts=[
            TextPart(
                text=(
                    f"![Quantum job results]({image_match.group(1)})\n\n"
                    "Live measurement results retrieved from IBM Quantum.\n\n"
                    f"Consulted locally: {queried_at}"
                )
            )
        ],
    )


# Create AgentStack server
server = Server()

def create_status_agent():
    """Create the Quantum Status Agent with its configured chat model."""
    llm = create_chat_model("STATUS")
    
    # Define the tools
    tools = [
        IBMQuantumStatusTool(),
        IBMQuantumInfoTool(),
        IBMQuantumJobTool(),
        IBMQuantumJobComparisonTool(),
    ]
    
    # Create a custom system template with instructions AT THE BEGINNING
    custom_system_template = PromptTemplate(
        schema=SystemPromptTemplateInput,
        template="""# YOUR ROLE AND CRITICAL RULES
""" + STATUS_INSTRUCTIONS + """

# Available functions
{{#tools.0}}
You MUST use one of the following functions for EVERY query. Never respond without using a function.

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
Final Answer: Your response to the user with the data from the function. Must always be preceded by Thought.

# ⚠️⚠️⚠️ CRITICAL INSTRUCTIONS - NEVER VIOLATE ⚠️⚠️⚠️

1. YOU MUST CALL A FUNCTION FOR EVERY USER QUERY
2. YOUR FINAL ANSWER MUST BE THE EXACT FUNCTION OUTPUT - WORD FOR WORD
3. DO NOT ADD TIPS, NOTES, OR EXTRA TEXT
4. DO NOT MODIFY, REFORMAT, OR OMIT ANY DATA FROM THE FUNCTION OUTPUT

**YOUR FINAL ANSWER = FUNCTION OUTPUT (EXACT COPY)**

FORBIDDEN:
❌ Adding tips or notes after the function output
❌ Saying "here is the list" without showing the actual data
❌ Modifying tables or omitting columns
❌ Summarizing instead of showing complete data

REQUIRED:
✅ Copy the ENTIRE Function Output as your Final Answer
✅ Include ALL tables, data, and recommendations from the function
✅ Use the EXACT same format and words

## Example of CORRECT behavior:
Message: What quantum computers are available?
Thought: I need to call ibm_quantum_status to get the list of available quantum computers
Function Name: ibm_quantum_status
Function Input: {{"only_hardware": false}}
Function Output: 🔬 **Available Quantum Computers on IBM Quantum**

| Backend | Type | Qubits | Status | Queue | Version |
|---------|------|--------|--------|------|----------|
| ibm_brisbane | ⚛️ Hardware | 127 | 🟢 OK | 5 | 2 |
...

Thought: I will show the user the EXACT output from the function without any modifications
Final Answer: 🔬 **Available Quantum Computers on IBM Quantum**

| Backend | Type | Qubits | Status | Queue | Version |
|---------|------|--------|--------|------|----------|
| ibm_brisbane | ⚛️ Hardware | 127 | 🟢 OK | 5 | 2 |
...

## Example of INCORRECT behavior (FORBIDDEN):
❌ Modifying the table (removing columns, changing format)
❌ Saying "here is the list" without calling the function
❌ Summarizing instead of showing complete data
""",
    )
    
    # Create the agent with the custom template
    return ReActAgent(
        llm=llm,
        tools=tools,
        memory=UnconstrainedMemory(),
        templates={"system": custom_system_template},
    )

@server.agent(
    name="Quantum Status Agent",
    detail=STATUS_AGENT_DETAIL,
    skills=STATUS_AGENT_SKILLS,
    default_output_modes=["text/plain", "image/png"],
)
async def quantum_status_agent(
    input: Message,
    context: RunContext,
    trajectory: Annotated[TrajectoryExtensionServer, TrajectoryExtensionSpec()],
    _canvas: Annotated[CanvasExtensionServer, CanvasExtensionSpec()],
):
    """
    Main handler for the Quantum Status Agent.
    
    This agent queries the status of backends and quantum jobs on IBM Quantum.
    """
    user_query = get_message_text(input)
    print("=" * 80)
    print(f"📊 [Status Agent] Received query: '{user_query[:100]}...'")
    print("=" * 80)
    
    # Step 1: Request analysis
    yield trajectory.trajectory_metadata(
        title="🔍 Analyzing status query",
        content=f"Processing user query:\n```\n{user_query[:200]}{'...' if len(user_query) > 200 else ''}\n```"
    )

    job_ids = list(dict.fromkeys(_JOB_ID_PATTERN.findall(user_query)))
    if len(job_ids) == 1:
        job_id = job_ids[0]
        yield trajectory.trajectory_metadata(
            title="📊 Querying IBM Quantum job",
            content=f"Retrieving current status for job `{job_id}`...",
        )
        try:
            tool_output = await IBMQuantumJobTool().run({"job_id": job_id, "filter_status": "all"})
            response = tool_output.get_text_content()
            if "__QUANTUM_PNG__" in response:
                response = await _upload_png_and_replace(response)
            artifact = _create_job_results_canvas(response, job_id)
            if artifact:
                yield artifact
                try:
                    await context.store(artifact)
                except Exception as store_error:
                    print(f"⚠️ [Canvas] Could not store job results artifact: {explain_error(store_error)}")
            yield trajectory.trajectory_metadata(
                title="✅ Job data obtained",
                content="IBM Quantum returned the current job status and available results.",
            )
            yield AgentMessage(text=response)
        except Exception as e:
            yield trajectory.trajectory_metadata(
                title="❌ Job query failed",
                content=f"**Type:** {type(e).__name__}\n**Message:** {explain_error(e)}",
            )
            yield AgentMessage(text=f"❌ Error querying job: {explain_error(e)}")
        return

    # Backend inventory and detail queries map directly to IBM Quantum tools.
    # Avoid an LLM tool-selection round trip that can emit malformed calls.
    backend_names = list(dict.fromkeys(_BACKEND_NAME_PATTERN.findall(user_query)))
    if len(backend_names) == 1:
        backend_name = backend_names[0].lower()
        yield trajectory.trajectory_metadata(
            title="🔬 Querying backend details",
            content=f"Retrieving live IBM Quantum data for `{backend_name}`...",
        )
        try:
            tool_output = await IBMQuantumInfoTool().run({"backend_name": backend_name})
            response, artifact = await _create_backend_canvas(tool_output.get_text_content(), backend_name)
            if artifact:
                yield trajectory.trajectory_metadata(
                    title="🗺️ Backend Canvas ready",
                    content="Generated a live topology map and backend health dashboard.",
                )
                yield artifact
                try:
                    await context.store(artifact)
                except Exception as store_error:
                    print(f"⚠️ [Canvas] Could not store artifact history: {explain_error(store_error)}")
            yield AgentMessage(text=response)
        except Exception as e:
            yield AgentMessage(text=f"❌ Error querying backend: {explain_error(e)}")
        return

    if _BACKEND_LIST_PATTERN.search(user_query):
        only_hardware = bool(_HARDWARE_ONLY_PATTERN.search(user_query))
        yield trajectory.trajectory_metadata(
            title="🔬 Querying available backends",
            content="Retrieving the live IBM Quantum backend list...",
        )
        try:
            tool_output = await IBMQuantumStatusTool().run({"only_hardware": only_hardware})
            yield AgentMessage(text=tool_output.get_text_content())
        except Exception as e:
            yield AgentMessage(text=f"❌ Error querying available backends: {explain_error(e)}")
        return
    
    # Create the agent with instructions
    agent = create_status_agent()
    
    # Step 2: Agent preparation
    yield trajectory.trajectory_metadata(
        title="🤖 Preparing query agent",
        content=f"**Configuration:**\n- Model: {model_name('STATUS')}\n- Tools: 4 (Status, Info, Job, Comparison)\n- Memory: Unlimited"
    )
    
    # Build prompt with system instructions
    full_prompt = f"{STATUS_INSTRUCTIONS}\n\n---\n\nUSER REQUEST:\n{user_query}"
    
    # Step 3: Data query
    yield trajectory.trajectory_metadata(
        title="⚙️ Querying IBM Quantum",
        content="Agent is querying real-time data from IBM Quantum..."
    )
    
    # Execute the agent
    try:
        run_context = await run_agent_with_retries(agent, full_prompt)
        
        # Update trajectory with progress
        yield trajectory.trajectory_metadata(
            title="✅ Data obtained",
            content="- [x] Query completed\n- [x] Data processed\n- [x] Response formatted"
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
        
        # Process PNG markers: upload images and replace with agentstack:// URLs
        # Check for explicit markers OR recent PNGs in temporary directory
        has_png_marker = '__QUANTUM_PNG__' in response
        has_recent_pngs = (
            os.path.exists(_QUANTUM_PNG_DIR) and
            any(
                f.endswith('.png') and (time.time() - os.path.getmtime(os.path.join(_QUANTUM_PNG_DIR, f))) < 120
                for f in os.listdir(_QUANTUM_PNG_DIR)
            )
        )
        if has_png_marker or has_recent_pngs:
            yield trajectory.trajectory_metadata(
                title="🖼️ Generating visualizations",
                content="Uploading PNG histograms to file server..."
            )
            try:
                response = await _upload_png_and_replace(response)
                print(f"[Status Agent] PNG markers processed successfully")
            except Exception as png_err:
                print(f"[Status Agent] Error processing PNG markers: {png_err}")
        
        # Step 4: Response generated
        yield trajectory.trajectory_metadata(
            title="✅ Response ready",
            content=f"IBM Quantum data obtained ({len(response)} characters)\n\n**Content:**\n- Backend status\n- Technical information\n- Job results"
        )
        
        print("=" * 80)
        print(f"✅ [Status Agent] Response generated ({len(response)} chars)")
        print("=" * 80)
        
        # Create response message
        response_message = AgentMessage(text=response)
        
        # Yield response to user
        yield response_message
        
    except Exception as e:
        import traceback
        error_msg = f"❌ Error in Status Agent: {explain_error(e)}"
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
        print(f"🔴 [Status Agent] {error_msg}")
        print(error_details)
        print("=" * 80)
        
        yield AgentMessage(text=error_msg)

def run():
    """Starts the Quantum Status Agent server with persistent storage"""
    port = int(os.getenv("STATUS_PORT", 8002))
    host = os.getenv("STATUS_HOST", "127.0.0.1")
    
    print("=" * 80)
    print("🚀 Starting Quantum Status Agent Server (AgentStack)")
    print("=" * 80)
    print(f"  📊 Agent: Quantum Status Agent")
    print(f"  🤖 Model: {model_name('STATUS')}")
    print(f"  🌐 Host: {host}")
    print(f"  🔌 Port: {port}")
    print(f"  🛠️  Tools: 4 (Status, Info, Job, Job Comparison)")
    print(f"  📚 History: Persistent storage enabled (PlatformContextStore)")
    print(f"  🎯 Trajectory: Visualization enabled")
    print(f"  📚 Skills: Backend Status, Technical Info, Job Results, Comparison")
    print("=" * 80)
    print("\n💡 Tip: This agent is invoked by the Lab Agent (port 8000)")
    print("   to query backend status and quantum jobs.")
    print("=" * 80)
    
    # Run server without PlatformContextStore (invoked via A2A)
    server.run(
        host=host,
        port=port
    )

if __name__ == "__main__":
    run()
