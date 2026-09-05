"""
Quantum Computing Client Tool - A2A Client to invoke the Quantum Computing Agent

This tool allows the Quantum Lab Agent to communicate with the
Quantum Computing Agent to execute quantum circuits on IBM Quantum
using the BeeAI Framework A2AAgent.
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

class ComputingClientInput(BaseModel):
    """Input schema for Quantum Computing Client"""
    request: str = Field(
        description="""
        Execution request for the Quantum Computing Agent. Must include:
        
        1. The complete QASM code to execute
        2. The backend to execute on (optional, default: ibm_kyiv)
        3. Whether it's real hardware or simulator (optional)
        4. Number of shots (optional, default: 1024)
        
        Examples:
        - "Execute this QASM code in ibm_brisbane: OPENQASM 2.0; include 'qelib1.inc'; qreg q[2]; creg c[2]; h q[0]; cx q[0],q[1]; measure q->c;"
        - "Execute the circuit on the ibm_kyiv simulator with 2048 shots"
        - "Execute that code on the ibm_osaka real hardware"
        
        The Computing Agent will extract the QASM code and parameters from the request.
        """
    )

class QuantumComputingClient(Tool[ComputingClientInput]):
    """
    A2A Client to communicate with the Quantum Computing Agent.
    
    This tool allows the Quantum Lab Agent to invoke the Computing Agent
    to execute quantum circuits on IBM Quantum.
    """
    
    @property
    def name(self) -> str:
        return "quantum_computing_client"
    
    @property
    def description(self) -> str:
        return """
Invokes the Quantum Computing Agent to execute quantum circuits on IBM Quantum.

COMPUTING AGENT CAPABILITIES:
- Execute QASM code (OpenQASM 2.0/3.0) on quantum computers
- Execute on simulators or real hardware
- Automatic circuit transpilation
- Execution parameter management (shots, backend, etc.)
- Provide Job ID and execution details

WHEN TO USE THIS TOOL:
✅ User provides QASM code to execute
✅ User says "execute this code"
✅ User says "execute the circuit on [backend]"
✅ QASM code is in the conversation context
✅ User specifies a backend for execution

❌ DO NOT use for:
- Generating QASM code (use quantum_developer_client)
- Querying backend status (use quantum_status_client)
- Viewing job results (use quantum_status_client)

REQUIRED QASM CODE FORMAT:
The code must be valid OpenQASM:
```qasm
OPENQASM 2.0;
include "qelib1.inc";
qreg q[N];
creg c[N];
// Quantum gates
h q[0];
cx q[0],q[1];
// Measurements (MANDATORY)
measure q -> c;
```

USAGE EXAMPLES:

1. Execute code on simulator (default):
   {
     "request": "Execute this QASM code: OPENQASM 2.0; include 'qelib1.inc'; qreg q[2]; creg c[2]; h q[0]; cx q[0],q[1]; measure q->c;"
   }

2. Execute on specific real hardware:
   {
     "request": "Execute this code on ibm_brisbane: OPENQASM 2.0; include 'qelib1.inc'; qreg q[2]; creg c[2]; h q[0]; cx q[0],q[1]; measure q->c;"
   }

3. Execute code from context:
   {
     "request": "Execute that code on the ibm_kyiv simulator"
   }

4. Execute with specific shots:
   {
     "request": "Execute the circuit on ibm_osaka with 2048 shots"
   }

AVAILABLE BACKENDS:
- **Simulators**: ibm_kyiv, ibm_sherbrooke, simulator_statevector
- **Real Hardware**: ibm_brisbane, ibm_osaka, ibm_torino, ibm_kyoto

OUTPUT:
- Full Job ID of the executed job
- Backend used (simulator or real hardware)
- Number of shots
- Transpilation status
- Instructions to consult results

TYPICAL FLOW:
1. Lab Agent receives execution request
2. Invokes quantum_computing_client with code and parameters
3. Computing Agent executes the circuit
4. Returns Job ID and details
5. User can consult results with quantum_status_client
"""
    
    @property
    def input_schema(self) -> type[ComputingClientInput]:
        return ComputingClientInput

    def _create_emitter(self) -> Emitter:
        """Creates and returns an emitter instance for the tool."""
        return Emitter()

    async def _run(
        self,
        input: ComputingClientInput,
        options: Optional[ToolRunOptions] = None,
        context: Optional[RunContext] = None
    ) -> StringToolOutput:
        """
        Invokes the Quantum Computing Agent via A2A using the BeeAI Framework.
        
        Sends the execution request to the Computing Agent and returns
        the Job ID and execution details.
        """
        try:
            # Computing Agent Configuration
            computing_host = os.getenv("COMPUTING_HOST", "127.0.0.1")
            computing_port = int(os.getenv("COMPUTING_PORT", 8003))
            computing_url = f"http://{computing_host}:{computing_port}"
            
            print(f"🔄 [Computing Client] Sending execution request to Computing Agent at {computing_url}")
            print(f"📝 [Computing Client] Request: {input.request[:100]}...")
            
            # Create A2A client using BeeAI Framework
            a2a_agent = A2AAgent(
                url=computing_url,
                memory=UnconstrainedMemory()
            )
            
            # Add critical instructions about Job ID to the request
            enhanced_request = f"""{input.request}

⚠️ IMPORTANT: Your response MUST include the Job ID prominently in this format:
⚠️ **Job ID: [the_real_job_id]**

The Job ID is critical because the user needs it to consult results later."""
            
            # Execute the request to the Computing Agent with enhanced instructions
            response = await a2a_agent.run(enhanced_request)
            
            # Extract the response text
            computing_response = extract_final_text(response)
            
            if not computing_response:
                return StringToolOutput(
                    result="⚠️ The Computing Agent did not return a valid response."
                )
            
            print(f"✅ [Computing Client] Received response ({len(computing_response)} chars)")
            
            # Build the formatted response
            result_text = "🚀 **Response from the Quantum Computing Agent:**\n\n"
            result_text += computing_response
            result_text += "\n\n---\n"
            result_text += "💡 **Note:** The circuit was executed by the specialized Computing Agent.\n"
            result_text += "To consult the status and results, use the Status Agent with the provided Job ID.\n"
            
            return StringToolOutput(result=result_text)
            
        except ConnectionError as e:
            computing_host = os.getenv("COMPUTING_HOST", "127.0.0.1")
            computing_port = os.getenv("COMPUTING_PORT", "8003")
            error_text = f"❌ Could not connect to the Quantum Computing Agent.\n\n"
            error_text += f"**Check that:**\n"
            error_text += f"1. The Computing Agent is running\n"
            error_text += f"2. It is listening on {computing_host}:{computing_port}\n"
            error_text += f"3. There is no firewall blocking the connection\n\n"
            error_text += f"**To start the Computing Agent:**\n"
            error_text += f"```bash\n"
            error_text += f"python3 -m beeai_agents.quantum_computing_agent\n"
            error_text += f"```\n\n"
            error_text += f"Error: {str(e)}"
            return StringToolOutput(result=error_text)
            
        except TimeoutError:
            error_text = "⏱️ Timeout waiting for response from the Computing Agent.\n\n"
            error_text += "The Computing Agent is taking too long to respond. "
            error_text += "This can happen if the IBM Quantum service is slow or if there are network issues."
            return StringToolOutput(result=error_text)
            
        except Exception as e:
            error_text = f"❌ Error communicating with the Computing Agent: {str(e)}\n\n"
            error_text += f"Error type: {type(e).__name__}\n"
            error_text += f"Technical details: {str(e)}"
            return StringToolOutput(result=error_text)
