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
        description="Nombre del backend de IBM Quantum (ej: 'ibm_brisbane', 'ibm_kyoto', 'ibmq_qasm_simulator')"
    )

class IBMQuantumInfoTool(Tool[QuantumInfoInput]):
    """Tool for getting detailed information about a specific IBM Quantum computer."""
    
    @property
    def name(self) -> str:
        return "ibm_quantum_info"
    
    @property
    def description(self) -> str:
        return "Obtiene información detallada de una computadora cuántica específica de IBM Quantum, incluyendo configuración, topología, y características técnicas."
    
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
            # Inicializa el servicio
            service = QiskitRuntimeService(channel="ibm_quantum_platform")
            
            # Obtener el backend específico
            try:
                backend = service.backend(input.backend_name)
            except Exception as e:
                return StringToolOutput(
                    result=f"❌ Backend '{input.backend_name}' no encontrado.\n\n"
                           f"Usa la herramienta 'ibm_quantum_status' para ver los backends disponibles."
                )
            
            # Construir reporte detallado
            result_text = f"# 🔬 Información Detallada: **{backend.name}**\n\n"
            
            # Información básica
            result_text += "## 📊 Información Básica\n\n"
            result_text += "| Propiedad | Valor |\n"
            result_text += "|-----------|-------|\n"
            result_text += f"| **Nombre** | {backend.name} |\n"
            result_text += f"| **Tipo** | {'🖥️ Simulador' if backend.simulator else '⚛️ Hardware Real'} |\n"
            
            if hasattr(backend, 'num_qubits'):
                result_text += f"| **Qubits** | {backend.num_qubits} |\n"
            
            if hasattr(backend, 'version'):
                result_text += f"| **Versión** | {backend.version} |\n"
            
            if hasattr(backend, 'online_date'):
                result_text += f"| **Fecha Online** | {backend.online_date} |\n"
            
            # Estado operacional
            status = backend.status()
            result_text += f"| **Estado** | {'🟢 Operacional' if status.operational else '🔴 No Operacional'} |\n"
            
            if hasattr(status, 'pending_jobs'):
                result_text += f"| **Trabajos en Cola** | {status.pending_jobs} |\n"
            
            if hasattr(status, 'status_msg'):
                result_text += f"| **Mensaje de Estado** | {status.status_msg} |\n"
            
            result_text += "\n"
            
            # Configuración del procesador (solo para hardware real)
            if not backend.simulator and hasattr(backend, 'configuration'):
                config = backend.configuration()
                result_text += "## ⚙️ Configuración del Procesador\n\n"
                result_text += "| Propiedad | Valor |\n"
                result_text += "|-----------|-------|\n"
                
                if hasattr(config, 'processor_type'):
                    proc_type = config.processor_type
                    if isinstance(proc_type, dict):
                        result_text += f"| **Familia** | {proc_type.get('family', 'N/A')} |\n"
                        result_text += f"| **Revisión** | {proc_type.get('revision', 'N/A')} |\n"
                
                if hasattr(config, 'max_shots'):
                    result_text += f"| **Max Shots** | {config.max_shots:,} |\n"
                
                if hasattr(config, 'max_experiments'):
                    result_text += f"| **Max Experimentos** | {config.max_experiments} |\n"
                
                if hasattr(config, 'sample_name'):
                    result_text += f"| **Nombre de Muestra** | {config.sample_name} |\n"
                
                result_text += "\n"
            
            # Propiedades del backend
            if hasattr(backend, 'properties'):
                try:
                    props = backend.properties()
                    if props:
                        result_text += "## 📈 Propiedades Cuánticas\n\n"
                        
                        # Información de qubits
                        if hasattr(props, 'qubits') and props.qubits:
                            result_text += "### Qubits\n\n"
                            result_text += "| Qubit | T1 (μs) | T2 (μs) | Frecuencia (GHz) | Error de Lectura |\n"
                            result_text += "|-------|---------|---------|------------------|------------------|\n"
                            
                            for i, qubit_props in enumerate(props.qubits[:10]):  # Mostrar primeros 10
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
                                result_text += f"\n*Mostrando 10 de {len(props.qubits)} qubits*\n"
                            
                            result_text += "\n"
                        
                        # Información de puertas
                        if hasattr(props, 'gates') and props.gates:
                            result_text += "### Puertas Cuánticas\n\n"
                            result_text += "| Puerta | Qubits | Error | Duración (ns) |\n"
                            result_text += "|--------|--------|-------|---------------|\n"
                            
                            gate_count = 0
                            for gate in props.gates:
                                if gate_count >= 15:  # Limitar a 15 puertas
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
                                result_text += f"\n*Mostrando 15 de {len(props.gates)} puertas*\n"
                            
                            result_text += "\n"
                        
                        # Última actualización
                        if hasattr(props, 'last_update_date'):
                            result_text += f"**Última actualización de propiedades:** {props.last_update_date}\n\n"
                
                except Exception as e:
                    result_text += f"⚠️ No se pudieron obtener las propiedades detalladas: {str(e)}\n\n"
            
            # Información de topología/conectividad
            if hasattr(backend, 'coupling_map'):
                try:
                    coupling_map = backend.coupling_map
                    if coupling_map:
                        result_text += "## 🔗 Topología de Conectividad\n\n"
                        result_text += f"**Conexiones totales:** {len(coupling_map)}\n\n"
                        
                        if len(coupling_map) <= 20:
                            result_text += "**Mapa de conexiones:**\n"
                            for edge in coupling_map:
                                result_text += f"- Q{edge[0]} ↔ Q{edge[1]}\n"
                        else:
                            result_text += f"*Demasiadas conexiones para mostrar ({len(coupling_map)}). El backend tiene una topología compleja.*\n"
                        
                        result_text += "\n"
                except Exception:
                    pass
            
            # Instrucciones soportadas
            if hasattr(backend, 'target'):
                try:
                    target = backend.target
                    if target and hasattr(target, 'operations'):
                        operations = list(target.operations)
                        result_text += "## 🎯 Operaciones Soportadas\n\n"
                        result_text += f"**Total de operaciones:** {len(operations)}\n\n"
                        result_text += "**Operaciones disponibles:** "
                        result_text += ", ".join(f"`{op}`" for op in operations[:20])
                        if len(operations) > 20:
                            result_text += f", ... (+{len(operations) - 20} más)"
                        result_text += "\n\n"
                except Exception:
                    pass
            
            # Nota final
            result_text += "---\n\n"
            result_text += "💡 **Nota:** Esta información se actualiza periódicamente. "
            result_text += "Para datos en tiempo real, consulta el estado con `ibm_quantum_status`.\n"
            
            return StringToolOutput(result=result_text)
            
        except Exception as e:
            error_text = f"❌ Error al obtener información del backend '{input.backend_name}': {str(e)}\n\n"
            error_text += "Verifica que:\n"
            error_text += "- El nombre del backend sea correcto\n"
            error_text += "- Tu token de IBM Quantum sea válido\n"
            error_text += "- Tengas acceso al backend solicitado\n"
            return StringToolOutput(result=error_text)

# Made with Bob
