"""
Quantum Status Client Tool - Cliente A2A para invocar al Quantum Status Agent

Esta herramienta permite al Quantum Operations Agent comunicarse con el
Quantum Status Agent para solicitar consultas de estado de computadoras
cuánticas, información de backends y estado de trabajos usando el A2AAgent de BeeAI Framework.
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

class StatusClientInput(BaseModel):
    """Input schema for Quantum Status Client"""
    query: str = Field(
        description="""
        Consulta para el Quantum Status Agent. Puede ser:
        - "¿Qué computadoras cuánticas están disponibles?"
        - "Dame información de [backend_name]"
        - "¿Cuál es el estado del trabajo [job_id]?"
        - "Muéstrame mis trabajos recientes"
        - "¿Qué trabajos tengo en ejecución?"
        - "¿Cuál es el backend menos ocupado?"
        
        El Status Agent interpretará la consulta y usará la herramienta apropiada.
        """
    )

class QuantumStatusClient(Tool[StatusClientInput]):
    """
    Cliente A2A para comunicarse con el Quantum Status Agent.
    
    Este tool permite al Quantum Operations Agent invocar al Status Agent
    para obtener información sobre computadoras cuánticas, backends y trabajos.
    """
    
    @property
    def name(self) -> str:
        return "quantum_status_client"
    
    @property
    def description(self) -> str:
        return """
Invoca al Quantum Status Agent para consultas de estado de computadoras cuánticas y trabajos.

CAPACIDADES DEL STATUS AGENT:
- Listar computadoras cuánticas disponibles (hardware + simuladores)
- Obtener información técnica detallada de backends específicos
- Consultar estado de trabajos (QUEUED, RUNNING, DONE, ERROR)
- Obtener resultados de trabajos completados
- Listar trabajos recientes del usuario con filtros

CUÁNDO USAR ESTA HERRAMIENTA:
✅ Usuario pregunta "¿qué computadoras hay disponibles?"
✅ Usuario pregunta "dame información de [backend]"
✅ Usuario pregunta "¿cuál es el estado del trabajo [job_id]?"
✅ Usuario pregunta "muéstrame mis trabajos"
✅ Usuario pregunta "¿qué trabajos tengo en ejecución?"
✅ Usuario pregunta "¿cuál está menos ocupado?"
✅ Usuario pregunta "¿cuántos qubits tiene [backend]?"

❌ NO usar para:
- Ejecutar circuitos cuánticos (usa ibm_quantum_executor)
- Generar código QASM/Qiskit (usa quantum_developer_client)

EJEMPLOS DE CONSULTAS:

1. Listar computadoras disponibles:
   {"query": "¿Qué computadoras cuánticas están disponibles?"}

2. Información de backend específico:
   {"query": "Dame información detallada de ibm_brisbane"}

3. Estado de un trabajo:
   {"query": "¿Cuál es el estado del trabajo d671cklbujdc73cvbp30?"}

4. Listar trabajos recientes:
   {"query": "Muéstrame mis trabajos recientes"}

5. Trabajos en ejecución:
   {"query": "¿Qué trabajos tengo corriendo actualmente?"}

6. Backend menos ocupado:
   {"query": "¿Cuál es el backend menos ocupado?"}

SALIDA:
- Tablas formateadas con información de backends
- Estado y resultados de trabajos
- Recomendaciones basadas en disponibilidad
- Información técnica detallada de backends
"""
    
    @property
    def input_schema(self) -> type[StatusClientInput]:
        return StatusClientInput

    def _create_emitter(self) -> Emitter:
        """Creates and returns an emitter instance for the tool."""
        return Emitter()

    async def _run(
        self,
        input: StatusClientInput,
        options: Optional[ToolRunOptions] = None,
        context: Optional[RunContext] = None
    ) -> StringToolOutput:
        """
        Invoca al Quantum Status Agent vía A2A usando BeeAI Framework.
        
        Envía la consulta al Status Agent y retorna la respuesta
        con información de estado, backends o trabajos.
        """
        try:
            # Configuración del Status Agent
            status_host = os.getenv("STATUS_HOST", "127.0.0.1")
            status_port = int(os.getenv("STATUS_PORT", 8002))
            status_url = f"http://{status_host}:{status_port}"
            
            print(f"🔄 [Status Client] Sending query to Status Agent at {status_url}")
            print(f"📝 [Status Client] Query: {input.query[:100]}...")
            
            # Crear cliente A2A usando BeeAI Framework
            a2a_agent = A2AAgent(
                url=status_url,
                memory=UnconstrainedMemory()
            )
            
            # Ejecutar la consulta al Status Agent
            response = await a2a_agent.run(input.query)
            
            # Extraer el texto de la respuesta
            status_response = response.last_message.text if hasattr(response, 'last_message') else str(response)
            
            if not status_response:
                return StringToolOutput(
                    result="⚠️ El Status Agent no retornó una respuesta válida."
                )
            
            print(f"✅ [Status Client] Received response ({len(status_response)} chars)")
            
            # Construir la respuesta formateada
            result_text = "📊 **Respuesta del Quantum Status Agent:**\n\n"
            result_text += status_response
            result_text += "\n\n---\n"
            result_text += "💡 **Nota:** Esta información fue obtenida del Status Agent especializado.\n"
            
            return StringToolOutput(result=result_text)
            
        except ConnectionError as e:
            status_host = os.getenv("STATUS_HOST", "127.0.0.1")
            status_port = os.getenv("STATUS_PORT", "8002")
            error_text = f"❌ No se pudo conectar al Quantum Status Agent.\n\n"
            error_text += f"**Verifica que:**\n"
            error_text += f"1. El Status Agent esté ejecutándose\n"
            error_text += f"2. Esté escuchando en {status_host}:{status_port}\n"
            error_text += f"3. No haya firewall bloqueando la conexión\n\n"
            error_text += f"**Para iniciar el Status Agent:**\n"
            error_text += f"```bash\n"
            error_text += f"python3 -m beeai_agents.quantum_status_agent\n"
            error_text += f"```\n\n"
            error_text += f"Error: {str(e)}"
            return StringToolOutput(result=error_text)
            
        except TimeoutError:
            error_text = "⏱️ Timeout al esperar respuesta del Status Agent.\n\n"
            error_text += "El Status Agent está tardando demasiado en responder. "
            error_text += "Esto puede ocurrir con consultas muy complejas o si el servicio de IBM Quantum está lento."
            return StringToolOutput(result=error_text)
            
        except Exception as e:
            error_text = f"❌ Error al comunicarse con el Status Agent: {str(e)}\n\n"
            error_text += f"Tipo de error: {type(e).__name__}\n"
            error_text += f"Detalles técnicos: {str(e)}"
            return StringToolOutput(result=error_text)