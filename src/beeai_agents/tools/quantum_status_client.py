"""
Quantum Status Client Tool - A2A Client to invoke the Quantum Status Agent

This tool allows the Quantum Lab Agent to communicate with the
Quantum Status Agent to request queries about quantum computer status,
backend information, and job status using the A2AAgent from BeeAI Framework.
"""

from beeai_framework.tools import Tool
from beeai_framework.tools.types import StringToolOutput, ToolRunOptions
from beeai_framework.emitter import Emitter
from beeai_framework.context import RunContext
from beeai_framework.adapters.a2a.agents import A2AAgent
from beeai_framework.memory import UnconstrainedMemory
from pydantic import BaseModel, Field
from typing import Optional
import os

from .a2a_response import extract_final_text

class StatusClientInput(BaseModel):
    """Input schema for Quantum Status Client"""
    query: str = Field(
        description="""
        Query for the Quantum Status Agent. Can be:
        - "What quantum computers are available?"
        - "Give me information about [backend_name]"
        - "What is the status of job [job_id]?"
        - "Show me my recent jobs"
        - "What jobs do I have running?"
        - "Which is the least busy backend?"
        
        The Status Agent will interpret the query and use the appropriate tool.
        """
    )

class QuantumStatusClient(Tool[StatusClientInput]):
    """
    A2A Client to communicate with the Quantum Status Agent.
    
    This tool allows the Quantum Lab Agent to invoke the Status Agent
    to get information about quantum computers, backends, and jobs.
    """
    
    @property
    def name(self) -> str:
        return "quantum_status_client"
    
    @property
    def description(self) -> str:
        return """
Invokes the Quantum Status Agent for quantum computer and job status queries.

STATUS AGENT CAPABILITIES:
- List available quantum computers (hardware + simulators)
- Get detailed technical information about specific backends
- Query job status (QUEUED, RUNNING, DONE, ERROR)
- Get results from completed jobs
- List user's recent jobs with filters

WHEN TO USE THIS TOOL:
✅ User asks "what computers are available?"
✅ User asks "give me information about [backend]"
✅ User asks "what is the status of job [job_id]?"
✅ User asks "show me my jobs"
✅ User asks "what jobs do I have running?"
✅ User asks "which is the least busy?"
✅ User asks "how many qubits does [backend] have?"

❌ DO NOT use for:
- Executing quantum circuits (use ibm_quantum_operator)
- Generating QASM/Qiskit code (use quantum_developer_client)

QUERY EXAMPLES:

1. List available computers:
   {"query": "What quantum computers are available?"}

2. Specific backend information:
   {"query": "Give me detailed information about ibm_brisbane"}

3. Job status:
   {"query": "What is the status of job d671cklbujdc73cvbp30?"}

4. List recent jobs:
   {"query": "Show me my recent jobs"}

5. Running jobs:
   {"query": "What jobs do I have running currently?"}

6. Least busy backend:
   {"query": "Which is the least busy backend?"}

OUTPUT:
- Formatted tables with backend information
- Job status and results
- Recommendations based on availability
- Detailed technical backend information
"""
    
    @property
    def input_schema(self) -> type[StatusClientInput]:
        return StatusClientInput

    def _create_emitter(self) -> Emitter:
        """Creates and returns an emitter instance for the tool."""
        return Emitter()

    async def _run(
        self,
        input: StatusClientInput,
        options: Optional[ToolRunOptions] = None,
        context: Optional[RunContext] = None
    ) -> StringToolOutput:
        """
        Invokes the Quantum Status Agent via A2A using BeeAI Framework.
        
        Sends the query to the Status Agent and returns the response
        with status information, backends, or jobs.
        """
        try:
            # Status Agent configuration
            status_host = os.getenv("STATUS_HOST", "127.0.0.1")
            status_port = int(os.getenv("STATUS_PORT", 8002))
            status_url = f"http://{status_host}:{status_port}"
            
            print(f"🔄 [Status Client] Sending query to Status Agent at {status_url}")
            print(f"📝 [Status Client] Query: {input.query[:100]}...")
            
            # Create A2A client using BeeAI Framework
            a2a_agent = A2AAgent(
                url=status_url,
                memory=UnconstrainedMemory()
            )
            
            # Execute query to Status Agent
            response = await a2a_agent.run(input.query)
            
            # Extract text from response
            status_response = extract_final_text(response)
            
            if not status_response:
                return StringToolOutput(
                    result="⚠️ The Status Agent did not return a valid response."
                )
            
            print(f"✅ [Status Client] Received response ({len(status_response)} chars)")
            
            # Build formatted response
            result_text = "📊 **Response from Quantum Status Agent:**\n\n"
            result_text += status_response
            result_text += "\n\n---\n"
            result_text += "💡 **Note:** This information was obtained from the specialized Status Agent.\n"
            
            return StringToolOutput(result=result_text)
            
        except ConnectionError as e:
            status_host = os.getenv("STATUS_HOST", "127.0.0.1")
            status_port = os.getenv("STATUS_PORT", "8002")
            error_text = f"❌ Could not connect to Quantum Status Agent.\n\n"
            error_text += f"**Verify that:**\n"
            error_text += f"1. The Status Agent is running\n"
            error_text += f"2. It is listening on {status_host}:{status_port}\n"
            error_text += f"3. No firewall is blocking the connection\n\n"
            error_text += f"**To start the Status Agent:**\n"
            error_text += f"```bash\n"
            error_text += f"python3 -m beeai_agents.quantum_status_agent\n"
            error_text += f"```\n\n"
            error_text += f"Error: {str(e)}"
            return StringToolOutput(result=error_text)
            
        except TimeoutError:
            error_text = "⏱️ Timeout waiting for Status Agent response.\n\n"
            error_text += "The Status Agent is taking too long to respond. "
            error_text += "This can happen with very complex queries or if the IBM Quantum service is slow."
            return StringToolOutput(result=error_text)
            
        except Exception as e:
            error_text = f"❌ Error communicating with Status Agent: {str(e)}\n\n"
            error_text += f"Error type: {type(e).__name__}\n"
            error_text += f"Technical details: {str(e)}"
            return StringToolOutput(result=error_text)
