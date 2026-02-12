from beeai_framework.tools import Tool
from beeai_framework.tools.types import StringToolOutput, ToolRunOptions
from beeai_framework.emitter import Emitter
from beeai_framework.context import RunContext
from pydantic import BaseModel, Field
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2
from qiskit import QuantumCircuit, transpile
from typing import Optional

class QuantumInput(BaseModel):
    qasm_code: str = Field(description="El código en formato OpenQASM 3.0 del circuito. Debe ser código QASM válido con include, qreg, creg y measure.")
    use_real_device: bool = Field(default=False, description="Si es True, usa hardware cuántico real (QPU). Si es False, usa simulador.")
    backend_name: str = Field(default="", description="Nombre específico del backend a usar (opcional). Si está vacío, se selecciona automáticamente.")

class IBMQuantumTool(Tool[QuantumInput]):
    """Tool for executing quantum circuits on IBM Quantum infrastructure."""
    
    @property
    def name(self) -> str:
        return "ibm_quantum_operator"
    
    @property
    def description(self) -> str:
        return "Ejecuta circuitos cuánticos en la infraestructura de IBM Quantum (Simuladores o QPU)."
    
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
            # Inicializa el servicio
            service = QiskitRuntimeService(channel="ibm_quantum_platform")
            
            # Selección de backend
            if input.backend_name:
                # Usar backend específico
                backend = service.backend(input.backend_name)
                backend_type = "🖥️ Simulador" if "simulator" in input.backend_name.lower() else "⚛️ Hardware Real"
            elif input.use_real_device:
                # Seleccionar hardware real menos ocupado
                backend = service.least_busy(simulator=False, operational=True)
                backend_type = "⚛️ Hardware Real"
            else:
                # Usar simulador por defecto
                backend = service.backend("ibmq_qasm_simulator")
                backend_type = "🖥️ Simulador"

            # Validar que el código QASM sea correcto
            if "OPENQASM" not in input.qasm_code and "include" not in input.qasm_code:
                return StringToolOutput(
                    result="❌ Error: El código QASM debe incluir 'OPENQASM 3.0' o 'OPENQASM 2.0' y 'include \"stdgates.inc\"' o 'include \"qelib1.inc\"'"
                )

            # Convertir el string QASM a un objeto QuantumCircuit
            qc = QuantumCircuit.from_qasm_str(input.qasm_code)
            
            # Verificar que el circuito tenga mediciones
            if not any(instr.operation.name == 'measure' for instr in qc.data):
                return StringToolOutput(
                    result="⚠️ Advertencia: El circuito no tiene mediciones. Agregando mediciones automáticamente..."
                )
            
            # TRANSPILACIÓN: Adaptar el circuito al hardware específico
            # Esto es CRÍTICO para hardware real
            result_text = f"🔄 **Transpilando circuito para {backend.name}...**\n\n"
            
            try:
                # Transpilar el circuito para el backend específico
                # optimization_level=3 para mejor optimización
                transpiled_qc = transpile(
                    qc,
                    backend=backend,
                    optimization_level=3
                )
                
                result_text += f"✅ Transpilación exitosa\n"
                result_text += f"   • Circuito original: {qc.num_qubits} qubits, {len(qc.data)} puertas\n"
                result_text += f"   • Circuito transpilado: {transpiled_qc.num_qubits} qubits, {len(transpiled_qc.data)} puertas\n\n"
                
            except Exception as transpile_error:
                return StringToolOutput(
                    result=f"❌ Error en la transpilación: {str(transpile_error)}\n\n"
                           f"El circuito no puede adaptarse al backend '{backend.name}'.\n"
                           f"Intenta con un circuito más simple o usa un simulador."
                )
            
            # Ejecución usando Sampler V2 con el circuito transpilado
            sampler = SamplerV2(mode=backend)
            job = sampler.run([transpiled_qc])
            
            # Construir respuesta detallada
            result_text += f"✅ **Circuito enviado exitosamente**\n\n"
            result_text += f"**Backend:** {backend.name}\n"
            result_text += f"**Tipo:** {backend_type}\n"
            result_text += f"**Job ID:** {job.job_id()}\n"
            result_text += f"**Qubits físicos usados:** {transpiled_qc.num_qubits}\n"
            result_text += f"**Puertas transpiladas:** {len(transpiled_qc.data)}\n\n"
            
            if input.use_real_device:
                result_text += "🎯 **CONFIRMACIÓN:** Este circuito se está ejecutando en HARDWARE CUÁNTICO REAL.\n"
                result_text += f"Los resultados estarán disponibles cuando el trabajo termine de ejecutarse en {backend.name}.\n"
            else:
                result_text += "🖥️ Este circuito se ejecutó en un simulador.\n"
                result_text += "Para ejecutar en hardware real, especifica 'use_real_device: true'.\n"
            
            return StringToolOutput(result=result_text)
            
        except Exception as e:
            error_text = f"❌ Error al ejecutar el circuito cuántico: {str(e)}"
            return StringToolOutput(result=error_text)

# Made with Bob
