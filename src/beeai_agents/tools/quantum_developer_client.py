"""
Quantum Developer Client Tool - A2A Client to invoke the Quantum Developer Agent

This tool allows the Quantum Lab Agent to communicate with the
Quantum Developer Agent to request code generation, explanations,
and quantum circuit optimizations using the BeeAI Framework A2AAgent.
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

class DeveloperClientInput(BaseModel):
    """Input schema for Quantum Developer Client"""
    request: str = Field(
        description="""
        Request for the Quantum Developer Agent. It can be:
        - "Create a circuit for [description]" to generate code
        - "Explain [quantum concept]" to get explanations
        - "Optimize this code: [code]" for optimization
        - "Give me an example of [algorithm]" for examples
        """
    )
    format: str = Field(
        default="qasm",
        description="Response format: 'qasm', 'qiskit', or 'explanation'"
    )

class QuantumDeveloperClient(Tool[DeveloperClientInput]):
    """
    A2A Client to communicate with the Quantum Developer Agent.
    
    This tool allows the Quantum Lab Agent to invoke the Developer Agent
    to obtain quantum code, explanations, and optimizations.
    """
    
    @property
    def name(self) -> str:
        return "quantum_developer_client"
    
    @property
    def description(self) -> str:
        return """
Invokes the Quantum Developer Agent to generate quantum code or explanations.

CAPABILITIES:
- Generates OpenQASM 2.0 or Qiskit code as requested
- Explains quantum computing concepts with examples
- Optimizes existing quantum circuits
- Provides examples of well-known quantum algorithms
- Documents code with clear comments

WHEN TO USE THIS TOOL:
✅ When the user asks to "create a circuit"
✅ When you need QASM code to execute
✅ When they ask to "explain" a quantum concept
✅ When they request an "example of" an algorithm
✅ When you need to optimize existing code

❌ DO NOT use for:
- Executing circuits (use ibm_quantum_operator)
- Querying backend status (use ibm_quantum_status)
- Viewing job results (use ibm_quantum_job)

USAGE EXAMPLES:

1. Generate superposition code:
   {
     "request": "Create a superposition circuit with 3 qubits",
     "format": "qasm"
   }

2. Explain entanglement:
   {
     "request": "Explain what quantum entanglement is with an example",
     "format": "qasm"
   }

3. Algorithm example:
   {
     "request": "Give me an example of Grover's algorithm",
     "format": "qiskit"
   }

4. Optimize circuit:
   {
     "request": "Optimize this QASM circuit: OPENQASM 2.0; include 'qelib1.inc'; qreg q[2]; creg c[2]; h q[0]; h q[1]; cx q[0],q[1]; h q[0]; h q[1]; measure q->c;",
     "format": "qasm"
   }

OUTPUT:
- Complete and executable QASM or Qiskit code
- Clear explanations of concepts
- Comments and documentation
- Optimization suggestions
"""
    
    @property
    def input_schema(self) -> type[DeveloperClientInput]:
        return DeveloperClientInput

    def _create_emitter(self) -> Emitter:
        """Creates and returns an emitter instance for the tool."""
        return Emitter()

    async def _run(
        self,
        input: DeveloperClientInput,
        options: Optional[ToolRunOptions] = None,
        context: Optional[RunContext] = None
    ) -> StringToolOutput:
        """
        Invokes the Quantum Developer Agent via A2A using the BeeAI Framework.
        
        Sends the request to the Developer Agent and returns the response
        with generated code or explanations.
        """
        try:
            # Developer Agent Configuration
            developer_host = os.getenv("DEVELOPER_HOST", "127.0.0.1")
            developer_port = int(os.getenv("DEVELOPER_PORT", 8001))
            developer_url = f"http://{developer_host}:{developer_port}"
            
            # Build the message for the Developer Agent
            # Include the desired format in the request
            full_request = input.request
            if input.format.lower() == "qiskit":
                full_request += "\n\nPlease provide the code in Qiskit (Python) format."
            elif input.format.lower() == "qasm":
                full_request += "\n\nPlease provide the code in OpenQASM 2.0 format."
            
            print(f"🔄 [Developer Client] Sending request to Developer Agent at {developer_url}")
            print(f"📝 [Developer Client] Request: {input.request[:100]}...")
            
            # Create A2A client using BeeAI Framework
            a2a_agent = A2AAgent(
                url=developer_url,
                memory=UnconstrainedMemory()
            )
            
            # Execute the request to the Developer Agent
            response = await a2a_agent.run(full_request)
            
            # Extract the response text
            developer_response = response.last_message.text if hasattr(response, 'last_message') else str(response)
            
            if not developer_response:
                return StringToolOutput(
                    result="⚠️ The Developer Agent did not return a valid response."
                )
            
            print(f"✅ [Developer Client] Received response ({len(developer_response)} chars)")
            
            # Build the formatted response
            result_text = "🎯 **Response from the Quantum Developer Agent:**\n\n"
            result_text += developer_response
            result_text += "\n\n---\n"
            if input.format.lower() == "explanation":
                result_text += "💡 **Note:** This explanation was provided by the specialized Developer Agent.\n"
            else:
                result_text += "💡 **Note:** This code was generated by the specialized Developer Agent.\n"
            
            if "OPENQASM" in developer_response or "qreg" in developer_response:
                result_text += "✅ QASM code detected. You can execute it with `ibm_quantum_operator`.\n"
            
            return StringToolOutput(result=result_text)
            
        except ConnectionError as e:
            dev_host = os.getenv("DEVELOPER_HOST", "127.0.0.1")
            dev_port = os.getenv("DEVELOPER_PORT", "8001")
            error_text = f"❌ Could not connect to the Quantum Developer Agent.\n\n"
            error_text += f"**Check that:**\n"
            error_text += f"1. The Developer Agent is running\n"
            error_text += f"2. It is listening on {dev_host}:{dev_port}\n"
            error_text += f"3. There is no firewall blocking the connection\n\n"
            error_text += f"**To start the Developer Agent:**\n"
            error_text += f"```bash\n"
            error_text += f"python3 -m beeai_agents.quantum_developer_agent\n"
            error_text += f"```\n\n"
            error_text += f"Error: {str(e)}"
            return StringToolOutput(result=error_text)
            
        except TimeoutError:
            error_text = "⏱️ Timeout waiting for response from the Developer Agent.\n\n"
            error_text += "The Developer Agent is taking too long to respond. "
            error_text += "This can happen with very complex requests."
            return StringToolOutput(result=error_text)
            
        except Exception as e:
            error_text = f"❌ Error communicating with the Developer Agent: {str(e)}\n\n"
            error_text += f"Error type: {type(e).__name__}\n"
            error_text += f"Technical details: {str(e)}"
            return StringToolOutput(result=error_text)
