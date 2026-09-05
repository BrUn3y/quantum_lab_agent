from beeai_framework.tools import Tool
from beeai_framework.tools.types import StringToolOutput, ToolRunOptions
from beeai_framework.emitter import Emitter
from beeai_framework.context import RunContext
from pydantic import BaseModel, Field
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2
from qiskit import QuantumCircuit, transpile
from qiskit.primitives import StatevectorSampler
from qiskit.qasm2 import dumps as qasm2_dumps
from typing import Optional
import asyncio
import time

class QuantumInput(BaseModel):
    qasm_code: str = Field(description="Quantum circuit code. Can be OpenQASM 2.0/3.0 OR Qiskit Python code. The system automatically detects the format and converts if necessary.")
    use_real_device: bool = Field(default=False, description="If True, uses real quantum hardware (QPU). If False, uses simulator.")
    backend_name: str = Field(default="", description="Specific backend name to use (optional). If empty, automatically selected.")
    shots: int = Field(default=1024, ge=1, description="Number of circuit executions (default: 1024).")
    wait_for_results: bool = Field(default=False, description="If True, waits for the job to finish and shows results. If False, only returns the Job ID immediately.")
    max_wait_time: int = Field(default=300, description="Maximum wait time in seconds (default: 300 = 5 minutes).")
    job_tags: list[str] = Field(
        default_factory=lambda: ["quantum-circuit"],
        description="Short descriptive tags attached to the IBM Quantum job.",
    )

class IBMQuantumTool(Tool[QuantumInput]):
    """Tool for executing quantum circuits on IBM Quantum infrastructure."""
    
    @property
    def name(self) -> str:
        return "ibm_quantum_operator"
    
    @property
    def description(self) -> str:
        return """Executes quantum circuits on IBM Quantum (Simulators or QPU).
        
SUPPORTED FORMATS:
1. OpenQASM 2.0/3.0 - Quantum assembly language
2. Qiskit Python - Python code using QuantumCircuit

The system automatically detects the format and converts Qiskit to QASM if necessary.

EXAMPLES:

OpenQASM:
```qasm
OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
creg c[2];
h q[0];
cx q[0],q[1];
measure q -> c;
```

Qiskit Python:
```python
from qiskit import QuantumCircuit
qc = QuantumCircuit(2, 2)
qc.h(0)
qc.cx(0, 1)
qc.measure_all()
```
"""
    
    @property
    def input_schema(self) -> type[QuantumInput]:
        return QuantumInput

    def _create_emitter(self) -> Emitter:
        """Creates and returns an emitter instance for the tool."""
        return Emitter()

    async def _run(
        self,
        input: QuantumInput,
        options: Optional[ToolRunOptions] = None,
        context: Optional[RunContext] = None
    ) -> StringToolOutput:
        """Execute quantum circuit on IBM Quantum infrastructure."""
        try:
            # Backend selection
            local_names = {"simulator", "local_simulator", "statevector_simulator", "ibmq_qasm_simulator"}
            use_local_simulator = not input.use_real_device and input.backend_name.lower() in local_names | {""}
            service = None
            backend = None
            if use_local_simulator:
                backend_name = "local_statevector_simulator"
                backend_type = "🖥️ Local Simulator"
            elif input.backend_name:
                # Use specific backend
                service = QiskitRuntimeService(channel="ibm_quantum_platform")
                backend = service.backend(input.backend_name)
                backend_name = backend.name
                backend_type = "🖥️ Simulator" if "simulator" in input.backend_name.lower() else "⚛️ Real Hardware"
            elif input.use_real_device:
                # Select least busy real hardware
                service = QiskitRuntimeService(channel="ibm_quantum_platform")
                backend = service.least_busy(simulator=False, operational=True)
                backend_name = backend.name
                backend_type = "⚛️ Real Hardware"

            # Detect code format and convert if necessary
            code_format = "QASM"
            qasm_code = input.qasm_code
            
            # Detect if it's Qiskit Python code
            if "QuantumCircuit" in input.qasm_code or "from qiskit" in input.qasm_code:
                code_format = "Qiskit"
                result_text = f"🔄 **Detected Qiskit Python code - Converting to QASM...**\n\n"
                
                try:
                    # Execute Qiskit code to get the circuit
                    local_vars = {}
                    exec(input.qasm_code, {"QuantumCircuit": QuantumCircuit, "qiskit": __import__("qiskit")}, local_vars)
                    
                    # Find QuantumCircuit object in local variables
                    qc = None
                    for var_name, var_value in local_vars.items():
                        if isinstance(var_value, QuantumCircuit):
                            qc = var_value
                            break
                    
                    if qc is None:
                        return StringToolOutput(
                            result="❌ Error: No QuantumCircuit object found in Qiskit code.\n"
                                   "Make sure to create a circuit with `qc = QuantumCircuit(...)`"
                        )
                    
                    # Convert to QASM using dumps function
                    qasm_code = qasm2_dumps(qc)
                    
                    result_text += f"✅ Conversion successful\n"
                    result_text += f"   • Qubits: {qc.num_qubits}\n"
                    result_text += f"   • Gates: {len(qc.data)}\n"
                    result_text += f"   • Target format: OpenQASM 2.0\n\n"
                    result_text += f"**Generated QASM code:**\n```qasm\n{qasm_code}\n```\n\n"
                    
                except Exception as e:
                    return StringToolOutput(
                        result=f"❌ Error executing Qiskit code: {str(e)}\n\n"
                               "Verify that the code is valid and uses correct Qiskit syntax."
                    )
            else:
                result_text = ""
                # Validate that QASM code is correct
                if "OPENQASM" not in qasm_code and "include" not in qasm_code:
                    return StringToolOutput(
                        result="❌ Error: Code must be valid OpenQASM or Qiskit Python code.\n\n"
                               "OpenQASM must include 'OPENQASM 2.0' or 'OPENQASM 3.0' and 'include \"qelib1.inc\"'\n"
                               "Qiskit must use 'from qiskit import QuantumCircuit'"
                    )

            # Convert QASM string to QuantumCircuit object
            qc = QuantumCircuit.from_qasm_str(qasm_code)
            
            # Verify circuit has measurements
            if not any(instr.operation.name == 'measure' for instr in qc.data):
                return StringToolOutput(
                    result="⚠️ Warning: Circuit has no measurements. Adding measurements automatically..."
                )
            
            # TRANSPILATION: Adapt circuit to specific hardware
            # This is CRITICAL for real hardware
            result_text = f"🔄 **Transpiling circuit for {backend_name}...**\n\n"
            
            try:
                # Transpile circuit for specific backend
                # optimization_level=3 for better optimization
                transpiled_qc = transpile(
                    qc,
                    backend=backend,
                    optimization_level=3
                )
                
                result_text += f"✅ Transpilation successful\n"
                result_text += f"   • Original circuit: {qc.num_qubits} qubits, {len(qc.data)} gates\n"
                result_text += f"   • Transpiled circuit: {transpiled_qc.num_qubits} qubits, {len(transpiled_qc.data)} gates\n\n"
                
            except Exception as transpile_error:
                return StringToolOutput(
                    result=f"❌ Transpilation error: {str(transpile_error)}\n\n"
                           f"Circuit cannot be adapted to backend '{backend.name}'.\n"
                           f"Try a simpler circuit or use a simulator."
                )
            
            # Execute locally for simulator requests; use IBM Runtime for QPU jobs.
            tags = list(dict.fromkeys(tag.strip() for tag in input.job_tags if tag.strip())) or ["quantum-circuit"]
            if use_local_simulator:
                sampler = StatevectorSampler()
            else:
                sampler = SamplerV2(mode=backend, options={"environment": {"job_tags": tags}})
            job = sampler.run([transpiled_qc], shots=input.shots)
            
            # Build initial response
            result_text += f"✅ **Circuit submitted successfully**\n\n"
            result_text += f"**Backend:** {backend_name}\n"
            result_text += f"**Type:** {backend_type}\n"
            result_text += f"**Job ID:** `{job.job_id()}`\n"
            result_text += f"**Tags:** {', '.join(f'`{tag}`' for tag in tags)}\n"
            result_text += f"**Shots:** {input.shots}\n"
            result_text += f"**Physical qubits used:** {transpiled_qc.num_qubits}\n"
            result_text += f"**Transpiled gates:** {len(transpiled_qc.data)}\n\n"
            
            if use_local_simulator:
                result = await asyncio.to_thread(job.result)
                pub_result = result[0]
                counts = pub_result.data.c.get_counts()
                result_text += "✅ **Local simulation completed**\n\n"
                result_text += "## 📊 Measurement Results\n\n"
                result_text += "| Quantum State | Count | Percentage |\n"
                result_text += "|---------------|-------|------------|\n"
                total = sum(counts.values())
                for state, count in sorted(counts.items(), key=lambda item: item[1], reverse=True)[:10]:
                    result_text += f"| `{state}` | {count:,} | {(count / total) * 100:.2f}% |\n"
                result_text += f"\n**Total measurements:** {total:,}\n"
                return StringToolOutput(result=result_text)

            # If wait_for_results is True, wait for completion
            if input.wait_for_results:
                result_text += "⏳ **Waiting for results...**\n\n"
                
                start_time = time.time()
                final_states = ['DONE', 'COMPLETED', 'CANCELLED', 'ERROR']
                
                while True:
                    raw_status = job.status()
                    status = str(raw_status) if not hasattr(raw_status, 'name') else raw_status.name
                    elapsed = time.time() - start_time

                    # Check timeout
                    if elapsed > input.max_wait_time:
                        result_text += f"⏱️ **Timeout:** Job did not finish in {input.max_wait_time} seconds.\n"
                        result_text += f"**Current status:** {status}\n"
                        result_text += f"**Job ID:** `{job.job_id()}`\n\n"
                        result_text += "💡 Use `ibm_quantum_job` with this Job ID to check results later.\n"
                        return StringToolOutput(result=result_text)

                    # Check if finished
                    if status in final_states:
                        break

                    # Show progress
                    if status == 'QUEUED':
                        result_text += f"   📊 Status: Queued (waiting {int(elapsed)}s)\n"
                    elif status == 'RUNNING':
                        result_text += f"   🔄 Status: Running (waiting {int(elapsed)}s)\n"

                    # Wait 5 seconds before checking again
                    await asyncio.sleep(5)

                # Job finished
                result_text += f"\n✅ **Job completed in {int(elapsed)} seconds**\n"
                result_text += f"**Final status:** {status}\n\n"

                # Get and show results
                if status in ['DONE', 'COMPLETED']:
                    try:
                        result = job.result()
                        
                        # Extract results from BitArray
                        if hasattr(result, '_pub_results') and result._pub_results:
                            pub_result = result._pub_results[0]
                            
                            if hasattr(pub_result, 'data') and hasattr(pub_result.data, 'c'):
                                bit_array = pub_result.data.c
                                counts = bit_array.get_counts()
                                
                                result_text += "## 📊 Measurement Results\n\n"
                                result_text += "| Quantum State | Count | Percentage |\n"
                                result_text += "|---------------|-------|------------|\n"
                                
                                total = sum(counts.values())
                                for state, count in sorted(counts.items(), key=lambda x: x[1], reverse=True)[:10]:
                                    percentage = (count / total) * 100
                                    result_text += f"| `{state}` | {count:,} | {percentage:.2f}% |\n"
                                
                                result_text += f"\n**Total measurements:** {total:,}\n\n"
                                
                                # Interpretation for Bell state
                                if '00' in counts and '11' in counts:
                                    result_text += "💡 **Interpretation:** This pattern suggests a Bell state (entanglement).\n"
                                    result_text += f"States `00` and `11` appear with similar frequencies, indicating quantum superposition.\n\n"
                            else:
                                result_text += "⚠️ Results available but in unexpected format.\n"
                                result_text += f"Use `ibm_quantum_job` with Job ID `{job.job_id()}` to see details.\n\n"
                        else:
                            result_text += "⚠️ Results available but in unexpected format.\n"
                            result_text += f"Use `ibm_quantum_job` with Job ID `{job.job_id()}` to see details.\n\n"
                            
                    except Exception as e:
                        result_text += f"⚠️ Error getting results: {str(e)}\n"
                        result_text += f"Use `ibm_quantum_job` with Job ID `{job.job_id()}` to try again.\n\n"
                
                elif status == 'CANCELLED':
                    result_text += "❌ Job was cancelled.\n\n"
                elif status == 'ERROR':
                    result_text += "🔴 Job finished with error.\n\n"
            
            else:
                # Don't wait for results, just return Job ID
                if input.use_real_device:
                    result_text += "🎯 **CONFIRMATION:** This circuit is running on REAL QUANTUM HARDWARE.\n"
                    result_text += f"Results will be available when the job finishes executing on {backend_name}.\n\n"
                else:
                    result_text += "🖥️ This circuit was executed on a simulator.\n\n"
                
                result_text += f"💡 Use `ibm_quantum_job` with Job ID `{job.job_id()}` to check results.\n"
            
            return StringToolOutput(result=result_text)
            
        except Exception as e:
            error_text = f"❌ Error executing quantum circuit: {str(e)}"
            return StringToolOutput(result=error_text)
