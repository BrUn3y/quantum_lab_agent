"""
Quantum Developer Client Tool - Cliente A2A para invocar al Quantum Developer Agent

Esta herramienta permite al Quantum Operations Agent comunicarse con el
Quantum Developer Agent para solicitar generación de código, explicaciones
y optimizaciones de circuitos cuánticos usando el A2AAgent de BeeAI Framework.
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
        Solicitud para el Quantum Developer Agent. Puede ser:
        - "Crea un circuito de [descripción]" para generar código
        - "Explica [concepto cuántico]" para obtener explicaciones
        - "Optimiza este código: [código]" para optimización
        - "Dame un ejemplo de [algoritmo]" para ejemplos
        """
    )
    format: str = Field(
        default="qasm",
        description="Formato de código deseado: 'qasm' para OpenQASM 2.0, 'qiskit' para código Python Qiskit"
    )

class QuantumDeveloperClient(Tool[DeveloperClientInput]):
    """
    Cliente A2A para comunicarse con el Quantum Developer Agent.
    
    Este tool permite al Quantum Operations Agent invocar al Developer Agent
    para obtener código cuántico, explicaciones y optimizaciones.
    """
    
    @property
    def name(self) -> str:
        return "quantum_developer_client"
    
    @property
    def description(self) -> str:
        return """
Invoca al Quantum Developer Agent para generar código cuántico o explicaciones.

CAPACIDADES:
- Genera código OpenQASM 2.0 o Qiskit según lo solicitado
- Explica conceptos de computación cuántica con ejemplos
- Optimiza circuitos cuánticos existentes
- Proporciona ejemplos de algoritmos cuánticos conocidos
- Documenta código con comentarios claros

CUÁNDO USAR ESTA HERRAMIENTA:
✅ Cuando el usuario pide "crea un circuito"
✅ Cuando necesitas código QASM para ejecutar
✅ Cuando piden "explica" un concepto cuántico
✅ Cuando solicitan "ejemplo de" un algoritmo
✅ Cuando necesitas optimizar código existente

❌ NO usar para:
- Ejecutar circuitos (usa ibm_quantum_executor)
- Consultar estado de backends (usa ibm_quantum_status)
- Ver resultados de trabajos (usa ibm_quantum_job)

EJEMPLOS DE USO:

1. Generar código de superposición:
   {
     "request": "Crea un circuito de superposición con 3 qubits",
     "format": "qasm"
   }

2. Explicar entrelazamiento:
   {
     "request": "Explica qué es el entrelazamiento cuántico con un ejemplo",
     "format": "qasm"
   }

3. Ejemplo de algoritmo:
   {
     "request": "Dame un ejemplo del algoritmo de Grover",
     "format": "qiskit"
   }

4. Optimizar circuito:
   {
     "request": "Optimiza este circuito QASM: OPENQASM 2.0; include 'qelib1.inc'; qreg q[2]; creg c[2]; h q[0]; h q[1]; cx q[0],q[1]; h q[0]; h q[1]; measure q->c;",
     "format": "qasm"
   }

SALIDA:
- Código QASM o Qiskit completo y ejecutable
- Explicaciones claras de conceptos
- Comentarios y documentación
- Sugerencias de optimización
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
        Invoca al Quantum Developer Agent vía A2A usando BeeAI Framework.
        
        Envía la solicitud al Developer Agent y retorna la respuesta
        con código generado o explicaciones.
        """
        try:
            # Configuración del Developer Agent
            developer_host = os.getenv("DEVELOPER_HOST", "127.0.0.1")
            developer_port = int(os.getenv("DEVELOPER_PORT", 8001))
            developer_url = f"http://{developer_host}:{developer_port}"
            
            # Construir el mensaje para el Developer Agent
            # Incluir el formato deseado en la solicitud
            full_request = input.request
            if input.format.lower() == "qiskit":
                full_request += "\n\nPor favor, proporciona el código en formato Qiskit (Python)."
            else:
                full_request += "\n\nPor favor, proporciona el código en formato OpenQASM 2.0."
            
            print(f"🔄 [Developer Client] Sending request to Developer Agent at {developer_url}")
            print(f"📝 [Developer Client] Request: {input.request[:100]}...")
            
            # Crear cliente A2A usando BeeAI Framework
            a2a_agent = A2AAgent(
                url=developer_url,
                memory=UnconstrainedMemory()
            )
            
            # Ejecutar la solicitud al Developer Agent
            response = await a2a_agent.run(full_request)
            
            # Extraer el texto de la respuesta
            developer_response = response.last_message.text if hasattr(response, 'last_message') else str(response)
            
            if not developer_response:
                return StringToolOutput(
                    result="⚠️ El Developer Agent no retornó una respuesta válida."
                )
            
            print(f"✅ [Developer Client] Received response ({len(developer_response)} chars)")
            
            # Construir la respuesta formateada
            result_text = "🎯 **Respuesta del Quantum Developer Agent:**\n\n"
            result_text += developer_response
            result_text += "\n\n---\n"
            result_text += "💡 **Nota:** Este código fue generado por el Developer Agent especializado.\n"
            
            if "OPENQASM" in developer_response or "qreg" in developer_response:
                result_text += "✅ Código QASM detectado. Puedes ejecutarlo con `ibm_quantum_executor`.\n"
            
            return StringToolOutput(result=result_text)
            
        except ConnectionError as e:
            dev_host = os.getenv("DEVELOPER_HOST", "127.0.0.1")
            dev_port = os.getenv("DEVELOPER_PORT", "8001")
            error_text = f"❌ No se pudo conectar al Quantum Developer Agent.\n\n"
            error_text += f"**Verifica que:**\n"
            error_text += f"1. El Developer Agent esté ejecutándose\n"
            error_text += f"2. Esté escuchando en {dev_host}:{dev_port}\n"
            error_text += f"3. No haya firewall bloqueando la conexión\n\n"
            error_text += f"**Para iniciar el Developer Agent:**\n"
            error_text += f"```bash\n"
            error_text += f"python3 -m beeai_agents.quantum_developer_agent\n"
            error_text += f"```\n\n"
            error_text += f"Error: {str(e)}"
            return StringToolOutput(result=error_text)
            
        except TimeoutError:
            error_text = "⏱️ Timeout al esperar respuesta del Developer Agent.\n\n"
            error_text += "El Developer Agent está tardando demasiado en responder. "
            error_text += "Esto puede ocurrir con solicitudes muy complejas."
            return StringToolOutput(result=error_text)
            
        except Exception as e:
            error_text = f"❌ Error al comunicarse con el Developer Agent: {str(e)}\n\n"
            error_text += f"Tipo de error: {type(e).__name__}\n"
            error_text += f"Detalles técnicos: {str(e)}"
            return StringToolOutput(result=error_text)