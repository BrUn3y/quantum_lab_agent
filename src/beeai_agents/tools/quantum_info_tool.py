from beeai_framework.tools import Tool
from beeai_framework.tools.types import StringToolOutput, ToolRunOptions
from beeai_framework.emitter import Emitter
from beeai_framework.context import RunContext
from pydantic import BaseModel, Field
from qiskit_ibm_runtime import QiskitRuntimeService
from typing import Optional

class QuantumInfoInput(BaseModel):
    """Input schema for quantum computer detailed information"""
    backend_name: str = Field(
        description="IBM Quantum backend name (e.g., 'ibm_brisbane', 'ibm_kyoto', 'ibmq_qasm_simulator')"
    )

class IBMQuantumInfoTool(Tool[QuantumInfoInput]):
    """Tool for getting detailed information about a specific IBM Quantum computer."""
    
    @property
    def name(self) -> str:
        return "ibm_quantum_info"
    
    @property
    def description(self) -> str:
        return "Gets detailed information about a specific IBM Quantum computer, including configuration, topology, and technical characteristics."
    
    @property
    def input_schema(self) -> type[QuantumInfoInput]:
        return QuantumInfoInput

    def _create_emitter(self) -> Emitter:
        """Creates and returns an emitter instance for the tool."""
        return Emitter()

    async def _run(
        self,
        input: QuantumInfoInput,
        options: Optional[ToolRunOptions] = None,
        context: Optional[RunContext] = None
    ) -> StringToolOutput:
        """Get detailed information about a specific quantum computer."""
        try:
            # Initialize service - uses saved instance
            service = QiskitRuntimeService(channel="ibm_quantum_platform")
            
            # Get specific backend
            try:
                backend = service.backend(input.backend_name)
            except Exception as e:
                return StringToolOutput(
                    result=f"❌ Backend '{input.backend_name}' not found.\n\n"
                           f"Use the 'ibm_quantum_status' tool to see available backends."
                )
            
            # Build detailed report
            result_text = f"# 🔬 Detailed Information: **{backend.name}**\n\n"
            
            # Basic information
            result_text += "## 📊 Basic Information\n\n"
            result_text += "| Property | Value |\n"
            result_text += "|----------|-------|\n"
            result_text += f"| **Name** | {backend.name} |\n"
            result_text += f"| **Type** | {'🖥️ Simulator' if backend.simulator else '⚛️ Real Hardware'} |\n"
            
            if hasattr(backend, 'num_qubits'):
                result_text += f"| **Qubits** | {backend.num_qubits} |\n"
            
            if hasattr(backend, 'version'):
                result_text += f"| **Version** | {backend.version} |\n"
            
            if hasattr(backend, 'online_date'):
                result_text += f"| **Online Date** | {backend.online_date} |\n"
            
            # Operational status
            status = backend.status()
            result_text += f"| **Status** | {'🟢 Operational' if status.operational else '🔴 Not Operational'} |\n"
            
            if hasattr(status, 'pending_jobs'):
                result_text += f"| **Jobs in Queue** | {status.pending_jobs} |\n"
            
            if hasattr(status, 'status_msg'):
                result_text += f"| **Status Message** | {status.status_msg} |\n"
            
            result_text += "\n"
            
            # Processor configuration (only for real hardware)
            if not backend.simulator and hasattr(backend, 'configuration'):
                config = backend.configuration()
                result_text += "## ⚙️ Processor Configuration\n\n"
                result_text += "| Property | Value |\n"
                result_text += "|----------|-------|\n"
                
                if hasattr(config, 'processor_type'):
                    proc_type = config.processor_type
                    if isinstance(proc_type, dict):
                        result_text += f"| **Family** | {proc_type.get('family', 'N/A')} |\n"
                        result_text += f"| **Revision** | {proc_type.get('revision', 'N/A')} |\n"
                
                if hasattr(config, 'max_shots'):
                    result_text += f"| **Max Shots** | {config.max_shots:,} |\n"
                
                if hasattr(config, 'max_experiments'):
                    result_text += f"| **Max Experiments** | {config.max_experiments} |\n"
                
                if hasattr(config, 'sample_name'):
                    result_text += f"| **Sample Name** | {config.sample_name} |\n"
                
                result_text += "\n"
            
            # Backend properties
            if hasattr(backend, 'properties'):
                try:
                    props = backend.properties()
                    if props:
                        result_text += "## 📈 Quantum Properties\n\n"
                        
                        # Qubit information
                        if hasattr(props, 'qubits') and props.qubits:
                            result_text += "### Qubits\n\n"
                            result_text += "| Qubit | T1 (μs) | T2 (μs) | Frequency (GHz) | Readout Error |\n"
                            result_text += "|-------|---------|---------|-----------------|---------------|\n"
                            
                            for i, qubit_props in enumerate(props.qubits[:10]):  # Show first 10
                                t1 = "N/A"
                                t2 = "N/A"
                                freq = "N/A"
                                readout_error = "N/A"
                                
                                for prop in qubit_props:
                                    if prop.name == 'T1':
                                        t1 = f"{prop.value:.2f}"
                                    elif prop.name == 'T2':
                                        t2 = f"{prop.value:.2f}"
                                    elif prop.name == 'frequency':
                                        freq = f"{prop.value:.3f}"
                                    elif prop.name == 'readout_error':
                                        readout_error = f"{prop.value:.4f}"
                                
                                result_text += f"| Q{i} | {t1} | {t2} | {freq} | {readout_error} |\n"
                            
                            if len(props.qubits) > 10:
                                result_text += f"\n*Showing 10 of {len(props.qubits)} qubits*\n"
                            
                            result_text += "\n"
                        
                        # Gate information
                        if hasattr(props, 'gates') and props.gates:
                            result_text += "### Quantum Gates\n\n"
                            result_text += "| Gate | Qubits | Error | Duration (ns) |\n"
                            result_text += "|------|--------|-------|---------------|\n"
                            
                            gate_count = 0
                            for gate in props.gates:
                                if gate_count >= 15:  # Limit to 15 gates
                                    break
                                
                                gate_name = gate.gate
                                qubits = str(gate.qubits)
                                
                                error = "N/A"
                                duration = "N/A"
                                
                                for param in gate.parameters:
                                    if param.name == 'gate_error':
                                        error = f"{param.value:.6f}"
                                    elif param.name == 'gate_length':
                                        duration = f"{param.value:.2f}"
                                
                                result_text += f"| {gate_name} | {qubits} | {error} | {duration} |\n"
                                gate_count += 1
                            
                            if len(props.gates) > 15:
                                result_text += f"\n*Showing 15 of {len(props.gates)} gates*\n"
                            
                            result_text += "\n"
                        
                        # Last update
                        if hasattr(props, 'last_update_date'):
                            result_text += f"**Last properties update:** {props.last_update_date}\n\n"
                
                except Exception as e:
                    result_text += f"⚠️ Could not get detailed properties: {str(e)}\n\n"
            
            # Topology/connectivity information
            if hasattr(backend, 'coupling_map'):
                try:
                    coupling_map = backend.coupling_map
                    if coupling_map:
                        result_text += "## 🔗 Connectivity Topology\n\n"
                        result_text += f"**Total connections:** {len(coupling_map)}\n\n"
                        
                        if len(coupling_map) <= 20:
                            result_text += "**Connection map:**\n"
                            for edge in coupling_map:
                                result_text += f"- Q{edge[0]} ↔ Q{edge[1]}\n"
                        else:
                            result_text += f"*Too many connections to display ({len(coupling_map)}). Backend has complex topology.*\n"
                        
                        result_text += "\n"
                except Exception:
                    pass
            
            # Supported instructions
            if hasattr(backend, 'target'):
                try:
                    target = backend.target
                    if target and hasattr(target, 'operation_names'):
                        operations = list(target.operation_names)
                        result_text += "## 🎯 Supported Operations\n\n"
                        result_text += f"**Total operations:** {len(operations)}\n\n"
                        result_text += "**Available operations:** "
                        result_text += ", ".join(f"`{op}`" for op in operations[:20])
                        if len(operations) > 20:
                            result_text += f", ... (+{len(operations) - 20} more)"
                        result_text += "\n\n"
                except Exception:
                    pass
            
            # Final note
            result_text += "---\n\n"
            result_text += "💡 **Note:** This information is updated periodically. "
            result_text += "For real-time data, check status with `ibm_quantum_status`.\n"
            
            return StringToolOutput(result=result_text)
            
        except Exception as e:
            error_text = f"❌ Error getting backend information '{input.backend_name}': {str(e)}\n\n"
            error_text += "Verify that:\n"
            error_text += "- The backend name is correct\n"
            error_text += "- Your IBM Quantum token is valid\n"
            error_text += "- You have access to the requested backend\n"
            return StringToolOutput(result=error_text)
