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
        description="Si es True, SOLO muestra hardware real (excluye simuladores). Por defecto muestra TODO (hardware + simuladores)."
    )

class IBMQuantumStatusTool(Tool[QuantumStatusInput]):
    """Tool for checking available IBM Quantum computers and their queue status."""
    
    @property
    def name(self) -> str:
        return "ibm_quantum_status"
    
    @property
    def description(self) -> str:
        return "Consulta las computadoras cuánticas disponibles en IBM Quantum y el estado de sus colas de trabajo."
    
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
            # Inicializa el servicio - sin especificar instancia, usa la guardada
            print("[IBMQuantumStatusTool] Inicializando servicio de IBM Quantum...")
            service = QiskitRuntimeService(channel="ibm_quantum_platform")
            
            # Obtener todos los backends disponibles
            # Si only_hardware=False (default), busca TODOS (hardware + simuladores)
            # Si only_hardware=True, solo busca hardware real
            print(f"[IBMQuantumStatusTool] Buscando backends (only_hardware={input.only_hardware})...")
            
            if input.only_hardware:
                # Solo hardware real, sin simuladores
                backends = service.backends(simulator=False)
            else:
                # TODOS los backends disponibles (hardware + simuladores)
                backends = service.backends()
            
            print(f"[IBMQuantumStatusTool] Backends encontrados: {len(backends)}")
            
            if not backends:
                print("[IBMQuantumStatusTool] ⚠️ No se encontraron backends")
                return StringToolOutput(
                    result="⚠️ No se encontraron computadoras cuánticas disponibles en este momento."
                )
            
            # Construir el reporte en formato tabla
            result_text = "🔬 **Computadoras Cuánticas Disponibles en IBM Quantum**\n\n"
            
            # Encabezado de la tabla
            result_text += "| Backend | Tipo | Qubits | Estado | Cola | Versión |\n"
            result_text += "|---------|------|--------|--------|------|----------|\n"
            
            # Datos de cada backend
            for backend in backends:
                name = backend.name
                tipo = "🖥️ Simulador" if backend.simulator else "⚛️ Hardware"
                qubits = str(backend.num_qubits) if hasattr(backend, 'num_qubits') else "N/A"
                
                status = backend.status()
                estado = "🟢 OK" if status.operational else "🔴 Down"
                
                cola = str(status.pending_jobs) if hasattr(status, 'pending_jobs') else "N/A"
                version = str(backend.version) if hasattr(backend, 'version') else "N/A"
                
                result_text += f"| {name} | {tipo} | {qubits} | {estado} | {cola} | {version} |\n"
            
            result_text += "\n"
            
            # Agregar recomendación
            result_text += "\n💡 **Recomendación:** "
            
            # Encontrar el backend con menos trabajos en cola
            real_backends = [b for b in backends if not b.simulator]
            if real_backends:
                least_busy = min(
                    real_backends, 
                    key=lambda b: b.status().pending_jobs if hasattr(b.status(), 'pending_jobs') else float('inf')
                )
                pending = least_busy.status().pending_jobs if hasattr(least_busy.status(), 'pending_jobs') else 0
                result_text += f"El backend menos ocupado es **{least_busy.name}** con {pending} trabajos en cola."
            else:
                result_text += "Usa un simulador para pruebas rápidas sin espera."
            
            return StringToolOutput(result=result_text)
            
        except Exception as e:
            print(f"[IBMQuantumStatusTool] ❌ Error: {str(e)}")
            print(f"[IBMQuantumStatusTool] Traceback:\n{traceback.format_exc()}")
            error_text = f"❌ Error al consultar el estado de las computadoras cuánticas: {str(e)}\n\n"
            error_text += "Verifica que tu token de IBM Quantum sea válido y tenga los permisos necesarios."
            return StringToolOutput(result=error_text)

# Made with Bob
