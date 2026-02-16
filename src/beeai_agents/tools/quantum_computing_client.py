"""
Quantum Computing Client Tool - Cliente A2A para invocar al Quantum Computing Agent

Esta herramienta permite al Quantum Operations Agent comunicarse con el
Quantum Computing Agent para ejecutar circuitos cuánticos en IBM Quantum
usando el A2AAgent de BeeAI Framework.
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

class ComputingClientInput(BaseModel):
    """Input schema for Quantum Computing Client"""
    request: str = Field(
        description="""
        Solicitud de ejecución para el Quantum Computing Agent. Debe incluir:
        
        1. El código QASM completo a ejecutar
        2. El backend donde ejecutar (opcional, default: ibm_kyiv)
        3. Si es hardware real o simulador (opcional)
        4. Número de shots (opcional, default: 1024)
        
        Ejemplos:
        - "Ejecuta este código QASM en ibm_brisbane: OPENQASM 2.0; include 'qelib1.inc'; qreg q[2]; creg c[2]; h q[0]; cx q[0],q[1]; measure q->c;"
        - "Ejecuta el circuito en el simulador ibm_kyiv con 2048 shots"
        - "Ejecuta ese código en hardware real ibm_osaka"
        
        El Computing Agent extraerá el código QASM y los parámetros de la solicitud.
        """
    )

class QuantumComputingClient(Tool[ComputingClientInput]):
    """
    Cliente A2A para comunicarse con el Quantum Computing Agent.
    
    Este tool permite al Quantum Operations Agent invocar al Computing Agent
    para ejecutar circuitos cuánticos en IBM Quantum.
    """
    
    @property
    def name(self) -> str:
        return "quantum_computing_client"
    
    @property
    def description(self) -> str:
        return """
Invoca al Quantum Computing Agent para ejecutar circuitos cuánticos en IBM Quantum.

CAPACIDADES DEL COMPUTING AGENT:
- Ejecutar código QASM (OpenQASM 2.0/3.0) en computadoras cuánticas
- Ejecutar en simuladores o hardware real
- Transpilación automática de circuitos
- Gestión de parámetros de ejecución (shots, backend, etc.)
- Proporcionar Job ID y detalles de ejecución

CUÁNDO USAR ESTA HERRAMIENTA:
✅ Usuario proporciona código QASM para ejecutar
✅ Usuario dice "ejecuta este código"
✅ Usuario dice "ejecuta el circuito en [backend]"
✅ Código QASM está en el contexto de la conversación
✅ Usuario especifica un backend para ejecutar

❌ NO usar para:
- Generar código QASM (usa quantum_developer_client)
- Consultar estado de backends (usa quantum_status_client)
- Ver resultados de trabajos (usa quantum_status_client)

FORMATO DE CÓDIGO QASM REQUERIDO:
El código debe ser OpenQASM válido:
```qasm
OPENQASM 2.0;
include "qelib1.inc";
qreg q[N];
creg c[N];
// Puertas cuánticas
h q[0];
cx q[0],q[1];
// Mediciones (OBLIGATORIAS)
measure q -> c;
```

EJEMPLOS DE USO:

1. Ejecutar código en simulador (default):
   {
     "request": "Ejecuta este código QASM: OPENQASM 2.0; include 'qelib1.inc'; qreg q[2]; creg c[2]; h q[0]; cx q[0],q[1]; measure q->c;"
   }

2. Ejecutar en hardware real específico:
   {
     "request": "Ejecuta este código en ibm_brisbane: OPENQASM 2.0; include 'qelib1.inc'; qreg q[2]; creg c[2]; h q[0]; cx q[0],q[1]; measure q->c;"
   }

3. Ejecutar código del contexto:
   {
     "request": "Ejecuta ese código en el simulador ibm_kyiv"
   }

4. Ejecutar con shots específicos:
   {
     "request": "Ejecuta el circuito en ibm_osaka con 2048 shots"
   }

BACKENDS DISPONIBLES:
- **Simuladores**: ibm_kyiv, ibm_sherbrooke, simulator_statevector
- **Hardware Real**: ibm_brisbane, ibm_osaka, ibm_torino, ibm_kyoto

SALIDA:
- Job ID completo del trabajo ejecutado
- Backend usado (simulador o hardware real)
- Número de shots
- Estado de transpilación
- Instrucciones para consultar resultados

FLUJO TÍPICO:
1. Operations Agent recibe solicitud de ejecución
2. Invoca quantum_computing_client con código y parámetros
3. Computing Agent ejecuta el circuito
4. Retorna Job ID y detalles
5. Usuario puede consultar resultados con quantum_status_client
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
        Invoca al Quantum Computing Agent vía A2A usando BeeAI Framework.
        
        Envía la solicitud de ejecución al Computing Agent y retorna
        el Job ID y detalles de la ejecución.
        """
        try:
            # Configuración del Computing Agent
            computing_host = os.getenv("COMPUTING_HOST", "127.0.0.1")
            computing_port = int(os.getenv("COMPUTING_PORT", 8003))
            computing_url = f"http://{computing_host}:{computing_port}"
            
            print(f"🔄 [Computing Client] Sending execution request to Computing Agent at {computing_url}")
            print(f"📝 [Computing Client] Request: {input.request[:100]}...")
            
            # Crear cliente A2A usando BeeAI Framework
            a2a_agent = A2AAgent(
                url=computing_url,
                memory=UnconstrainedMemory()
            )
            
            # Agregar instrucciones críticas sobre Job ID al request
            enhanced_request = f"""{input.request}

⚠️ IMPORTANTE: Tu respuesta DEBE incluir el Job ID de forma prominente en este formato:
⚠️ **Job ID: [el_job_id_real]**

El Job ID es crítico porque el usuario lo necesita para consultar resultados después."""
            
            # Ejecutar la solicitud al Computing Agent con instrucciones mejoradas
            response = await a2a_agent.run(enhanced_request)
            
            # Extraer el texto de la respuesta
            computing_response = response.last_message.text if hasattr(response, 'last_message') else str(response)
            
            if not computing_response:
                return StringToolOutput(
                    result="⚠️ El Computing Agent no retornó una respuesta válida."
                )
            
            print(f"✅ [Computing Client] Received response ({len(computing_response)} chars)")
            
            # Construir la respuesta formateada
            result_text = "🚀 **Respuesta del Quantum Computing Agent:**\n\n"
            result_text += computing_response
            result_text += "\n\n---\n"
            result_text += "💡 **Nota:** El circuito fue ejecutado por el Computing Agent especializado.\n"
            result_text += "Para consultar el estado y resultados, usa el Status Agent con el Job ID proporcionado.\n"
            
            return StringToolOutput(result=result_text)
            
        except ConnectionError as e:
            computing_host = os.getenv("COMPUTING_HOST", "127.0.0.1")
            computing_port = os.getenv("COMPUTING_PORT", "8003")
            error_text = f"❌ No se pudo conectar al Quantum Computing Agent.\n\n"
            error_text += f"**Verifica que:**\n"
            error_text += f"1. El Computing Agent esté ejecutándose\n"
            error_text += f"2. Esté escuchando en {computing_host}:{computing_port}\n"
            error_text += f"3. No haya firewall bloqueando la conexión\n\n"
            error_text += f"**Para iniciar el Computing Agent:**\n"
            error_text += f"```bash\n"
            error_text += f"python3 -m beeai_agents.quantum_computing_agent\n"
            error_text += f"```\n\n"
            error_text += f"Error: {str(e)}"
            return StringToolOutput(result=error_text)
            
        except TimeoutError:
            error_text = "⏱️ Timeout al esperar respuesta del Computing Agent.\n\n"
            error_text += "El Computing Agent está tardando demasiado en responder. "
            error_text += "Esto puede ocurrir si el servicio de IBM Quantum está lento o si hay problemas de red."
            return StringToolOutput(result=error_text)
            
        except Exception as e:
            error_text = f"❌ Error al comunicarse con el Computing Agent: {str(e)}\n\n"
            error_text += f"Tipo de error: {type(e).__name__}\n"
            error_text += f"Detalles técnicos: {str(e)}"
            return StringToolOutput(result=error_text)