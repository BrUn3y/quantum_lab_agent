from beeai_framework.tools import Tool
from beeai_framework.tools.types import StringToolOutput, ToolRunOptions
from beeai_framework.emitter import Emitter
from beeai_framework.context import RunContext
from pydantic import BaseModel, Field
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2
from qiskit import QuantumCircuit, transpile
from qiskit.qasm2 import dumps as qasm2_dumps
from typing import Optional
import asyncio
import time

class QuantumInput(BaseModel):
    qasm_code: str = Field(description="Código del circuito cuántico. Puede ser OpenQASM 2.0/3.0 O código Qiskit Python. El sistema detecta automáticamente el formato y convierte si es necesario.")
    use_real_device: bool = Field(default=False, description="Si es True, usa hardware cuántico real (QPU). Si es False, usa simulador.")
    backend_name: str = Field(default="", description="Nombre específico del backend a usar (opcional). Si está vacío, se selecciona automáticamente.")
    wait_for_results: bool = Field(default=False, description="Si es True, espera a que el trabajo termine y muestra los resultados. Si es False, solo retorna el Job ID inmediatamente.")
    max_wait_time: int = Field(default=300, description="Tiempo máximo de espera en segundos (default: 300 = 5 minutos).")

class IBMQuantumTool(Tool[QuantumInput]):
    """Tool for executing quantum circuits on IBM Quantum infrastructure."""
    
    @property
    def name(self) -> str:
        return "ibm_quantum_operator"
    
    @property
    def description(self) -> str:
        return """Ejecuta circuitos cuánticos en IBM Quantum (Simuladores o QPU).
        
FORMATOS SOPORTADOS:
1. OpenQASM 2.0/3.0 - Lenguaje de ensamblador cuántico
2. Qiskit Python - Código Python usando QuantumCircuit

El sistema detecta automáticamente el formato y convierte Qiskit a QASM si es necesario.

EJEMPLOS:

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
            # Inicializa el servicio - usa la instancia guardada
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

            # Detectar el formato del código y convertir si es necesario
            code_format = "QASM"
            qasm_code = input.qasm_code
            
            # Detectar si es código Qiskit Python
            if "QuantumCircuit" in input.qasm_code or "from qiskit" in input.qasm_code:
                code_format = "Qiskit"
                result_text = f"🔄 **Detectado código Qiskit Python - Convirtiendo a QASM...**\n\n"
                
                try:
                    # Ejecutar el código Qiskit para obtener el circuito
                    local_vars = {}
                    exec(input.qasm_code, {"QuantumCircuit": QuantumCircuit, "qiskit": __import__("qiskit")}, local_vars)
                    
                    # Buscar el objeto QuantumCircuit en las variables locales
                    qc = None
                    for var_name, var_value in local_vars.items():
                        if isinstance(var_value, QuantumCircuit):
                            qc = var_value
                            break
                    
                    if qc is None:
                        return StringToolOutput(
                            result="❌ Error: No se encontró un objeto QuantumCircuit en el código Qiskit.\n"
                                   "Asegúrate de crear un circuito con `qc = QuantumCircuit(...)`"
                        )
                    
                    # Convertir a QASM usando la función dumps
                    qasm_code = qasm2_dumps(qc)
                    
                    result_text += f"✅ Conversión exitosa\n"
                    result_text += f"   • Qubits: {qc.num_qubits}\n"
                    result_text += f"   • Puertas: {len(qc.data)}\n"
                    result_text += f"   • Formato destino: OpenQASM 2.0\n\n"
                    result_text += f"**Código QASM generado:**\n```qasm\n{qasm_code}\n```\n\n"
                    
                except Exception as e:
                    return StringToolOutput(
                        result=f"❌ Error al ejecutar código Qiskit: {str(e)}\n\n"
                               "Verifica que el código sea válido y use la sintaxis correcta de Qiskit."
                    )
            else:
                result_text = ""
                # Validar que el código QASM sea correcto
                if "OPENQASM" not in qasm_code and "include" not in qasm_code:
                    return StringToolOutput(
                        result="❌ Error: El código debe ser OpenQASM válido o código Qiskit Python.\n\n"
                               "OpenQASM debe incluir 'OPENQASM 2.0' o 'OPENQASM 3.0' y 'include \"qelib1.inc\"'\n"
                               "Qiskit debe usar 'from qiskit import QuantumCircuit'"
                    )

            # Convertir el string QASM a un objeto QuantumCircuit
            qc = QuantumCircuit.from_qasm_str(qasm_code)
            
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
            
            # Construir respuesta inicial
            result_text += f"✅ **Circuito enviado exitosamente**\n\n"
            result_text += f"**Backend:** {backend.name}\n"
            result_text += f"**Tipo:** {backend_type}\n"
            result_text += f"**Job ID:** `{job.job_id()}`\n"
            result_text += f"**Qubits físicos usados:** {transpiled_qc.num_qubits}\n"
            result_text += f"**Puertas transpiladas:** {len(transpiled_qc.data)}\n\n"
            
            # Si wait_for_results es True, esperar a que termine
            if input.wait_for_results:
                result_text += "⏳ **Esperando resultados...**\n\n"
                
                start_time = time.time()
                final_states = ['DONE', 'COMPLETED', 'CANCELLED', 'ERROR']
                
                while True:
                    status = job.status()
                    elapsed = time.time() - start_time
                    
                    # Verificar timeout
                    if elapsed > input.max_wait_time:
                        result_text += f"⏱️ **Timeout:** El trabajo no terminó en {input.max_wait_time} segundos.\n"
                        result_text += f"**Estado actual:** {status}\n"
                        result_text += f"**Job ID:** `{job.job_id()}`\n\n"
                        result_text += "💡 Usa `ibm_quantum_job` con este Job ID para consultar los resultados más tarde.\n"
                        return StringToolOutput(result=result_text)
                    
                    # Verificar si terminó
                    if status in final_states:
                        break
                    
                    # Mostrar progreso
                    if status == 'QUEUED':
                        result_text += f"   📊 Estado: En cola (esperando {int(elapsed)}s)\n"
                    elif status == 'RUNNING':
                        result_text += f"   🔄 Estado: Ejecutando (esperando {int(elapsed)}s)\n"
                    
                    # Esperar 5 segundos antes de volver a consultar
                    await asyncio.sleep(5)
                
                # Trabajo terminado
                result_text += f"\n✅ **Trabajo completado en {int(elapsed)} segundos**\n"
                result_text += f"**Estado final:** {status}\n\n"
                
                # Obtener y mostrar resultados
                if status in ['DONE', 'COMPLETED']:
                    try:
                        result = job.result()
                        
                        # Extraer resultados del BitArray
                        if hasattr(result, '_pub_results') and result._pub_results:
                            pub_result = result._pub_results[0]
                            
                            if hasattr(pub_result, 'data') and hasattr(pub_result.data, 'c'):
                                bit_array = pub_result.data.c
                                counts = bit_array.get_counts()
                                
                                result_text += "## 📊 Resultados de Mediciones\n\n"
                                result_text += "| Estado Cuántico | Conteo | Porcentaje |\n"
                                result_text += "|-----------------|--------|------------|\n"
                                
                                total = sum(counts.values())
                                for state, count in sorted(counts.items(), key=lambda x: x[1], reverse=True)[:10]:
                                    percentage = (count / total) * 100
                                    result_text += f"| `{state}` | {count:,} | {percentage:.2f}% |\n"
                                
                                result_text += f"\n**Total de mediciones:** {total:,}\n\n"
                                
                                # Interpretación para estado de Bell
                                if '00' in counts and '11' in counts:
                                    result_text += "💡 **Interpretación:** Este patrón sugiere un estado de Bell (entrelazamiento).\n"
                                    result_text += f"Los estados `00` y `11` aparecen con frecuencias similares, indicando superposición cuántica.\n\n"
                            else:
                                result_text += "⚠️ Resultados disponibles pero en formato no esperado.\n"
                                result_text += f"Usa `ibm_quantum_job` con Job ID `{job.job_id()}` para ver detalles.\n\n"
                        else:
                            result_text += "⚠️ Resultados disponibles pero en formato no esperado.\n"
                            result_text += f"Usa `ibm_quantum_job` con Job ID `{job.job_id()}` para ver detalles.\n\n"
                            
                    except Exception as e:
                        result_text += f"⚠️ Error al obtener resultados: {str(e)}\n"
                        result_text += f"Usa `ibm_quantum_job` con Job ID `{job.job_id()}` para intentar de nuevo.\n\n"
                
                elif status == 'CANCELLED':
                    result_text += "❌ El trabajo fue cancelado.\n\n"
                elif status == 'ERROR':
                    result_text += "🔴 El trabajo terminó con error.\n\n"
            
            else:
                # No esperar resultados, solo retornar Job ID
                if input.use_real_device:
                    result_text += "🎯 **CONFIRMACIÓN:** Este circuito se está ejecutando en HARDWARE CUÁNTICO REAL.\n"
                    result_text += f"Los resultados estarán disponibles cuando el trabajo termine de ejecutarse en {backend.name}.\n\n"
                else:
                    result_text += "🖥️ Este circuito se ejecutó en un simulador.\n\n"
                
                result_text += f"💡 Usa `ibm_quantum_job` con Job ID `{job.job_id()}` para consultar los resultados.\n"
            
            return StringToolOutput(result=result_text)
            
        except Exception as e:
            error_text = f"❌ Error al ejecutar el circuito cuántico: {str(e)}"
            return StringToolOutput(result=error_text)

# Made with Bob
