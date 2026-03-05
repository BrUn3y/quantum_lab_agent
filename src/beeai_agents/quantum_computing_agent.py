"""
Quantum Computing Agent - Specialist in Quantum Circuit Execution

This agent is a specialist in:
- Execute QASM/Qiskit code on IBM quantum computers
- Manage execution on simulators and real hardware
- Provide detailed information on executed jobs
- Automatic circuit transpilation

Model: mistralai/mistral-small-3-1-24b-instruct-2503 (Watsonx)
Port: 8003
Type: AgentStack Server with A2A (ReActAgent with IBMQuantumTool)
"""

import os
from typing import Annotated
from collections.abc import AsyncGenerator

from a2a.types import AgentSkill, Message
from a2a.utils.message import get_message_text
from agentstack_sdk.server import Server
from agentstack_sdk.server.context import RunContext
from agentstack_sdk.server.store.platform_context_store import PlatformContextStore
from agentstack_sdk.a2a.types import AgentMessage
from agentstack_sdk.a2a.extensions import AgentDetail, AgentDetailTool
from agentstack_sdk.a2a.extensions import TrajectoryExtensionServer, TrajectoryExtensionSpec

from beeai_framework.agents.react import ReActAgent
from beeai_framework.backend import ChatModel
from beeai_framework.memory import UnconstrainedMemory

# Import the execution tool
from .tools import IBMQuantumTool

# Instructions for the Computing Agent (without custom template to avoid parsing errors)
COMPUTING_INSTRUCTIONS = """You are the Quantum Computing Agent. You execute quantum circuits on IBM Quantum.

⚠️ CRITICAL RULE: Your response MUST ALWAYS include the Job ID prominently.

STEPS:
1. Extract QASM code from user request
2. Identify backend (if specified, otherwise use ibm_kyiv)
3. Execute with ibm_quantum_executor
4. In your final response, ALWAYS include:
   - ⚠️ **Job ID: [the_real_job_id]** (in bold and with warning emoji)
   - Backend used
   - Shots
   - Results (if available)

RESPONSE FORMAT:
```
🚀 Circuit executed successfully

⚠️ **Job ID: abc123xyz456** ← THIS IS MANDATORY

Backend: ibm_torino
Shots: 1024
Status: DONE

[Results if available]
```

The Job ID is CRITICAL because quantum computers take time to respond and the user needs the ID to query results later.
"""

# Agent details for AgentStack
COMPUTING_AGENT_DETAIL = AgentDetail(
    user_greeting="⚡ Hello! I'm the Quantum Computing Agent. I execute quantum circuits on IBM Quantum simulators and real hardware, managing transpilation and providing Job IDs for tracking.",
    version="1.0.0",
    framework="BeeAI + Watsonx + A2A",
    author={"name": "Edgar Bruney"},
    tools=[
        AgentDetailTool(
            name="IBM Quantum Executor",
            description="Executes QASM/Qiskit code on IBM quantum computers (simulators or real hardware) with automatic transpilation."
        )
    ],
)

# Skills exposed by the agent
COMPUTING_AGENT_SKILLS = [
    AgentSkill(
        id="quantum-circuit-execution",
        name="Quantum Circuit Execution",
        description="Executes quantum circuits on IBM Quantum simulators or real hardware with automatic transpilation management.",
        tags=["Quantum Computing", "IBM Quantum", "Circuit Execution", "QASM", "Qiskit"],
        examples=[
            "Execute this QASM code on ibm_torino",
            "Execute this circuit on ibm_brisbane",
            "Execute the circuit on the ibm_kyiv simulator",
            "Run this QASM code on real quantum hardware",
            "Execute this circuit with 2048 shots on ibm_osaka"
        ]
    )
]

# Crear servidor AgentStack
server = Server()

def create_computing_agent():
    """Creates an instance of the Quantum Computing Agent with Mistral Small using ReActAgent"""
    # Configure Watsonx with Mistral Small
    llm = ChatModel.from_name(
        f"watsonx:{os.getenv('WATSONX_COMPUTING_MODEL', 'mistralai/mistral-small-3-1-24b-instruct-2503')}"
    )
    
    # Create the agent using ReActAgent
    return ReActAgent(
        llm=llm,
        tools=[IBMQuantumTool()],
        memory=UnconstrainedMemory(),
    )

@server.agent(
    name="Quantum Computing Agent",
    detail=COMPUTING_AGENT_DETAIL,
    skills=COMPUTING_AGENT_SKILLS
)
async def quantum_computing_agent(
    input: Message,
    context: RunContext,
    trajectory: Annotated[TrajectoryExtensionServer, TrajectoryExtensionSpec()]
):
    """
    Main handler for the Quantum Computing Agent.
    
    This agent executes quantum circuits on IBM Quantum.
    """
    user_query = get_message_text(input)
    print("=" * 80)
    print(f"⚡ [Computing Agent] Received query: '{user_query[:100]}...'")
    print("=" * 80)
    
    # Step 1: Request analysis
    yield trajectory.trajectory_metadata(
        title="🔍 Analyzing execution request",
        content=f"Processing user query:\n```\n{user_query[:200]}{'...' if len(user_query) > 200 else ''}\n```"
    )
    
    # Create the agent with instructions
    agent = create_computing_agent()
    
    # Step 2: Agent preparation
    yield trajectory.trajectory_metadata(
        title="🤖 Preparing execution agent",
        content=f"**Configuration:**\n- Model: Mistral Small 3.1\n- Tool: IBM Quantum Executor\n- Memory: Unconstrained"
    )
    
    # Build the prompt with system instructions
    full_prompt = f"{COMPUTING_INSTRUCTIONS}\n\n---\n\nUSER REQUEST:\n{user_query}"
    
    # Step 3: Circuit execution
    yield trajectory.trajectory_metadata(
        title="⚙️ Executing quantum circuit",
        content="The agent is executing the circuit on IBM Quantum..."
    )
    
    # Execute the agent
    try:
        run_context = await agent.run(full_prompt)
        
        # Update trajectory with progress
        yield trajectory.trajectory_metadata(
            title="✅ Circuit executed",
            content="- [x] QASM code extracted\n- [x] Circuit transpiled\n- [x] Job submitted to IBM Quantum"
        )
        
        # Extraer la respuesta
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
        
        # Asegurar que response sea string
        if not isinstance(response, str):
            response = str(response)
        
        # Step 4: Response generated
        yield trajectory.trajectory_metadata(
            title="✅ Job ID generated",
            content=f"Job submitted to IBM Quantum ({len(response)} characters)\n\n**Content:**\n- Job ID for tracking\n- Backend used\n- Execution configuration"
        )
        
        print("=" * 80)
        print(f"✅ [Computing Agent] Response generated ({len(response)} chars)")
        print("=" * 80)
        
        # Create the response message
        response_message = AgentMessage(text=response)
        
        # Yield la respuesta al usuario
        yield response_message
        
    except Exception as e:
        import traceback
        error_msg = f"❌ Error in Computing Agent: {str(e)}"
        error_details = f"\n\nError type: {type(e).__name__}\n"
        error_details += f"Details: {str(e)}\n\n"
        error_details += "Traceback:\n"
        error_details += traceback.format_exc()
        
        # Error trajectory
        yield trajectory.trajectory_metadata(
            title="❌ Error detected",
            content=f"**Type:** {type(e).__name__}\n**Message:** {str(e)}\n\nCheck logs for more details."
        )
        
        print("=" * 80)
        print(f"🔴 [Computing Agent] {error_msg}")
        print(error_details)
        print("=" * 80)
        
        yield AgentMessage(text=error_msg + error_details)

def run():
    """Starts the Quantum Computing Agent server with persistent storage"""
    port = int(os.getenv("COMPUTING_PORT", 8003))
    host = os.getenv("COMPUTING_HOST", "127.0.0.1")
    
    print("=" * 80)
    print("🚀 Starting Quantum Computing Agent Server (AgentStack)")
    print("=" * 80)
    print(f"  ⚡ Agent: Quantum Computing Agent")
    print(f"  🤖 Model: {os.getenv('WATSONX_COMPUTING_MODEL', 'mistralai/mistral-small-3-1-24b-instruct-2503')}")
    print(f"  🌐 Host: {host}")
    print(f"  🔌 Port: {port}")
    print(f"  🛠️  Tools: 1 (IBM Quantum Executor)")
    print(f"  📚 History: Persistent storage enabled (PlatformContextStore)")
    print(f"  🎯 Trajectory: Visualization enabled")
    print(f"  📚 Skills: Circuit Execution")
    print("=" * 80)
    print("\n💡 Tip: This agent is invoked by the Lab Agent (port 8000)")
    print("   to execute quantum circuits on IBM Quantum.")
    print("=" * 80)
    
    # Run server without PlatformContextStore (invoked via A2A)
    server.run(
        host=host,
        port=port
    )

if __name__ == "__main__":
    run()