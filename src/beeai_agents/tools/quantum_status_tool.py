from beeai_framework.tools import Tool
from beeai_framework.tools.types import StringToolOutput, ToolRunOptions
from beeai_framework.emitter import Emitter
from beeai_framework.context import RunContext
from pydantic import BaseModel, Field
from qiskit_ibm_runtime import QiskitRuntimeService
from typing import Optional
import traceback

class QuantumStatusInput(BaseModel):
    """Input schema for quantum status tool - no parameters needed"""
    only_hardware: bool = Field(
        default=False,
        description="If True, ONLY shows real hardware (excludes simulators). By default shows EVERYTHING (hardware + simulators)."
    )

class IBMQuantumStatusTool(Tool[QuantumStatusInput]):
    """Tool for checking available IBM Quantum computers and their queue status."""
    
    @property
    def name(self) -> str:
        return "ibm_quantum_status"
    
    @property
    def description(self) -> str:
        return "Queries available quantum computers on IBM Quantum and their job queue status."
    
    @property
    def input_schema(self) -> type[QuantumStatusInput]:
        return QuantumStatusInput

    def _create_emitter(self) -> Emitter:
        """Creates and returns an emitter instance for the tool."""
        return Emitter()

    async def _run(
        self,
        input: QuantumStatusInput,
        options: Optional[ToolRunOptions] = None,
        context: Optional[RunContext] = None
    ) -> StringToolOutput:
        """Check available quantum computers and their queue status."""
        try:
            # Initialize service - without specifying instance, uses saved one
            print("[IBMQuantumStatusTool] Initializing IBM Quantum service...")
            service = QiskitRuntimeService(channel="ibm_quantum_platform")
            
            # Get all available backends
            # If only_hardware=False (default), searches for ALL (hardware + simulators)
            # If only_hardware=True, only searches for real hardware
            print(f"[IBMQuantumStatusTool] Searching backends (only_hardware={input.only_hardware})...")
            
            if input.only_hardware:
                # Only real hardware, no simulators
                backends = service.backends(simulator=False)
            else:
                # ALL available backends (hardware + simulators)
                backends = service.backends()
            
            print(f"[IBMQuantumStatusTool] Backends found: {len(backends)}")
            
            if not backends:
                print("[IBMQuantumStatusTool] ⚠️ No backends found")
                return StringToolOutput(
                    result="⚠️ No quantum computers found available at this time."
                )
            
            # Build report in table format
            result_text = "🔬 **Available Quantum Computers on IBM Quantum**\n\n"
            
            # Table header
            result_text += "| Backend | Type | Qubits | Status | Queue | Version |\n"
            result_text += "|---------|------|--------|--------|-------|----------|\n"
            
            # Data for each backend
            for backend in backends:
                name = backend.name
                type_str = "🖥️ Simulator" if backend.simulator else "⚛️ Hardware"
                qubits = str(backend.num_qubits) if hasattr(backend, 'num_qubits') else "N/A"
                
                status = backend.status()
                status_str = "🟢 OK" if status.operational else "🔴 Down"
                
                queue_str = str(status.pending_jobs) if hasattr(status, 'pending_jobs') else "N/A"
                version = str(backend.version) if hasattr(backend, 'version') else "N/A"
                
                result_text += f"| {name} | {type_str} | {qubits} | {status_str} | {queue_str} | {version} |\n"
            
            result_text += "\n"
            
            # Add recommendation
            result_text += "\n💡 **Recommendation:** "
            
            # Find backend with fewest jobs in queue
            real_backends = [b for b in backends if not b.simulator]
            if real_backends:
                least_busy = min(
                    real_backends,
                    key=lambda b: b.status().pending_jobs if hasattr(b.status(), 'pending_jobs') else float('inf')
                )
                pending = least_busy.status().pending_jobs if hasattr(least_busy.status(), 'pending_jobs') else 0
                result_text += f"The least busy backend is **{least_busy.name}** with {pending} jobs in queue."
            else:
                result_text += "Use a simulator for quick tests without waiting."
            
            return StringToolOutput(result=result_text)
            
        except Exception as e:
            print(f"[IBMQuantumStatusTool] ❌ Error: {str(e)}")
            print(f"[IBMQuantumStatusTool] Traceback:\n{traceback.format_exc()}")
            error_text = f"❌ Error querying quantum computer status: {str(e)}\n\n"
            error_text += "Verify that your IBM Quantum token is valid and has the necessary permissions."
            return StringToolOutput(result=error_text)
