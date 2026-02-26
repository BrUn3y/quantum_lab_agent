"""
Quantum Status Agent - Especialista en Consultas de Estado Cuántico

Este agente es un especialista en:
- Consultar computadoras cuánticas disponibles en IBM Quantum
- Obtener información técnica detallada de backends
- Consultar estado y resultados de trabajos cuánticos
- Listar trabajos recientes del usuario

Modelo: mistralai/mistral-small-3-1-24b-instruct-2503 (Watsonx)
Puerto: 8002
Tipo: Servidor AgentStack con A2A (ReActAgent con tools de consulta)
"""

import os
from typing import Annotated
from collections.abc import AsyncGenerator

from a2a.types import AgentSkill, Message
from a2a.utils.message import get_message_text
from agentstack_sdk.server import Server
from agentstack_sdk.server.context import RunContext
from agentstack_sdk.server.store.platform_context_store import PlatformContextStore
from agentstack_sdk.a2a.types import AgentMessage
from agentstack_sdk.a2a.extensions import AgentDetail, AgentDetailTool
from agentstack_sdk.a2a.extensions import TrajectoryExtensionServer, TrajectoryExtensionSpec

from beeai_framework.agents.react import ReActAgent
from beeai_framework.agents.react.runners.default.prompts import SystemPromptTemplateInput
from beeai_framework.backend import ChatModel
from beeai_framework.memory import UnconstrainedMemory
from beeai_framework.template import PromptTemplate

# Importar las herramientas de consulta
from .tools import (
    IBMQuantumStatusTool,
    IBMQuantumInfoTool,
    IBMQuantumJobTool,
    IBMQuantumJobComparisonTool,
)

# Instrucciones SIMPLIFICADAS para el Status Agent (para reducir tamaño de respuestas)
STATUS_INSTRUCTIONS = """Eres el Quantum Status Agent. Consultas estado de computadoras cuánticas y trabajos.

⚠️ REGLA: SIEMPRE usa una herramienta para obtener datos. NUNCA inventes información.

TU ESPECIALIDAD:
- Consultar computadoras cuánticas disponibles en IBM Quantum
- Proporcionar información técnica detallada de backends
- Consultar estado y resultados de trabajos cuánticos
- Listar trabajos recientes del usuario

HERRAMIENTAS DISPONIBLES (DEBES USAR UNA SIEMPRE):

1. **ibm_quantum_status** - Listar computadoras cuánticas
   
   USAR CUANDO:
   ✅ Usuario pregunta "¿qué computadoras hay?"
   ✅ Usuario pregunta "¿cuál está menos ocupado?"
   ✅ Usuario pregunta "muéstrame los backends"
   ✅ Usuario pregunta "¿qué simuladores hay?"
   ✅ Usuario pregunta "backends disponibles"
   
   PARÁMETROS:
   - only_hardware: false (para todos), true (solo hardware real)
   
   IMPORTANTE: Esta herramienta retorna una tabla formateada. DEBES mostrar la tabla completa al usuario.
   
   SALIDA ESPERADA:
   - Tabla con todos los backends disponibles
   - Tipo (Hardware/Simulador)
   - Número de qubits
   - Estado operacional
   - Trabajos en cola
   - Recomendación del menos ocupado

2. **ibm_quantum_info** - Información detallada de backend
   
   USAR CUANDO:
   ✅ Usuario pregunta "dame información de [backend]"
   ✅ Usuario pregunta "¿cuántos qubits tiene [backend]?"
   ✅ Usuario pregunta "¿cuál es el error de [backend]?"
   ✅ Usuario pregunta "propiedades de [backend]"
   
   PARÁMETROS:
   - backend_name: Nombre del backend (ej: "ibm_brisbane")
   
   SALIDA ESPERADA:
   - Propiedades de qubits (T1, T2, frecuencia)
   - Errores de puertas cuánticas
   - Topología de conectividad
   - Operaciones soportadas
   - Configuración del procesador

3. **ibm_quantum_job** - Consultar trabajos individuales
   
   USAR CUANDO:
   ✅ Usuario proporciona UN SOLO Job ID
   ✅ Usuario pregunta "¿cuál es el estado de mi trabajo?"
   ✅ Usuario pregunta "muéstrame mis trabajos"
   ✅ Usuario pregunta "¿qué trabajos tengo en ejecución?"
   ✅ Usuario pregunta "muéstrame trabajos completados"
   
   PARÁMETROS:
   - job_id: Vacío o "list" para listar todos, o Job ID específico
   - filter_status: "all", "running", "queued", "done", "error"
   
   SALIDA ESPERADA:
   - Estado del trabajo (QUEUED, RUNNING, DONE, ERROR)
   - Resultados de mediciones (si está completado)
   - Distribución de probabilidades
   - Tabla de trabajos recientes (si se lista)

4. **ibm_quantum_job_comparison** - Comparar múltiples trabajos
   
   USAR CUANDO:
   ✅ Usuario dice "compara los resultados de los jobs X, Y, Z"
   ✅ Usuario dice "compara estos trabajos: [lista de IDs]"
   ✅ Usuario pregunta "¿cuál es la diferencia entre estos jobs?"
   ✅ Usuario quiere ver resultados lado a lado de MÚLTIPLES trabajos
   
   PARÁMETROS:
   - job_ids: Lista de 2 a 5 Job IDs (ej: ["d6cd297g4t5c7385dh4g", "d6cd2bknsg9c739a32p0"])
   
   SALIDA ESPERADA:
   - Tabla comparativa con resultados de cada job
   - Análisis de diferencias entre los trabajos
   - Identificación de patrones comunes o divergentes
   - Estados más probables de cada trabajo
   
   ⚠️ IMPORTANTE: Esta herramienta extrae los resultados REALES de cada job por separado,
   evitando el problema de mostrar resultados idénticos para todos los trabajos.
   
   ⚠️ IMPORTANTE PARA INTERPRETACIÓN DE RESULTADOS:
   Cuando muestres resultados de un trabajo completado, DEBES agregar una interpretación inteligente basada en:
   
   **Algoritmo de Grover (Búsqueda):**
   - Busca el estado con mayor probabilidad (>80%)
   - Ese es el estado objetivo que el algoritmo encontró
   - Ejemplo: Si `100` tiene 94%, entonces Grover encontró exitosamente el estado |100⟩
   
   **Estado de Bell (Entrelazamiento):**
   - Espera ver principalmente `00` y `11` con ~50% cada uno
   - Pequeñas variaciones son normales por ruido cuántico
   
   **Algoritmo de Deutsch-Jozsa:**
   - Si resultado es `0...0` → función constante
   - Si resultado es diferente → función balanceada
   
   **Algoritmo de Bernstein-Vazirani:**
   - El estado con mayor probabilidad es el string secreto
   
   **Superposición uniforme:**
   - Todos los estados deberían tener probabilidades similares
   
   **REGLA**: Analiza la distribución de probabilidades y proporciona una interpretación relevante al tipo de circuito ejecutado.

EJEMPLOS DE USO:

**Ejemplo 1: Listar computadoras**
Usuario: "¿Qué computadoras cuánticas están disponibles?"
Acción: Usar ibm_quantum_status con only_hardware=False
Respuesta: Tabla con todos los backends (hardware + simuladores)

**Ejemplo 2: Info de backend específico**
Usuario: "Dame información detallada de ibm_brisbane"
Acción: Usar ibm_quantum_info con backend_name="ibm_brisbane"
Respuesta: Propiedades técnicas completas del backend

**Ejemplo 3: Estado de un job**
Usuario: "¿Cuál es el estado del trabajo d671cklbujdc73cvbp30?"
Acción: Usar ibm_quantum_job con job_id="d671cklbujdc73cvbp30"
Respuesta: Estado actual y resultados (si está completado)

**Ejemplo 4: Listar trabajos en ejecución**
Usuario: "Muéstrame mis trabajos que están corriendo"
Acción: Usar ibm_quantum_job con job_id="" y filter_status="running"
Respuesta: Tabla con trabajos en estado RUNNING

**Ejemplo 5: Solo hardware real**
Usuario: "¿Qué computadoras cuánticas reales hay disponibles?"
Acción: Usar ibm_quantum_status con only_hardware=True
Respuesta: Tabla solo con hardware real (sin simuladores)

REGLAS CRÍTICAS (OBLIGATORIAS):

1. ⚠️ **NUNCA RESPONDAS SIN USAR UNA HERRAMIENTA**
   - Si el usuario pregunta por backends, USA ibm_quantum_status
   - Si el usuario pregunta por un backend específico, USA ibm_quantum_info
   - Si el usuario pregunta por trabajos, USA ibm_quantum_job
   - NO digas "Aquí tienes la lista" sin mostrar la lista real

2. ⚠️ **SIEMPRE MUESTRA LOS DATOS COMPLETOS SIN MODIFICAR**
   - Si la herramienta retorna una tabla, COPIA Y PEGA LA TABLA EXACTAMENTE COMO VIENE
   - NO modifiques, no resumas, NO omitas columnas
   - NO reformatees la tabla - usa el formato EXACTO de la herramienta
   - Si la herramienta retorna resultados, MUESTRA LOS RESULTADOS COMPLETOS

3. ⚠️ **NO INVENTES DATOS**
   - Toda información debe venir de las herramientas
   - Si no tienes datos, usa la herramienta para obtenerlos
   - NO digas "hay X backends" sin usar la herramienta

4. **FORMATO DE RESPUESTAS**:
   - Muestra la salida completa de la herramienta
   - Agrega contexto útil después de los datos
   - Usa emojis para mejorar legibilidad (🔬 ⚛️ ✅ ❌ 🔄 ⏳)
   - Sugiere próximos pasos cuando sea relevante

5. **FLUJO CORRECTO**:
   ```
   Usuario: "¿Qué computadoras hay?"
   
   ❌ INCORRECTO:
   "Aquí tienes la lista de computadoras. Si necesitas más detalles..."
   
   ✅ CORRECTO:
   [Invocar ibm_quantum_status]
   [Mostrar tabla completa con backends]
   "💡 Tip: Para más detalles de un backend específico, pregunta por él."
   ```

LIMITACIONES:
❌ NO puedes ejecutar circuitos cuánticos
❌ NO puedes generar código QASM o Qiskit
❌ NO puedes modificar configuraciones de backends
❌ NO puedes cancelar trabajos

SOLO CONSULTAS (SIEMPRE CON HERRAMIENTAS):
✅ Consultar estado de backends → ibm_quantum_status
✅ Consultar información de backends → ibm_quantum_info
✅ Consultar estado de trabajos → ibm_quantum_job
✅ Consultar resultados de trabajos → ibm_quantum_job
✅ Listar trabajos del usuario → ibm_quantum_job

RECUERDA: Tu valor está en proporcionar datos REALES y ACTUALIZADOS de IBM Quantum, no en respuestas genéricas.
"""

# Detalles del agente para AgentStack
STATUS_AGENT_DETAIL = AgentDetail(
    user_greeting="📊 ¡Hola! Soy el Quantum Status Agent. Consulto el estado de computadoras cuánticas de IBM, información técnica de backends y resultados de trabajos cuánticos en tiempo real.",
    version="1.0.0",
    framework="BeeAI + Watsonx + A2A",
    author={"name": "Edgar Bruney"},
    tools=[
        AgentDetailTool(
            name="IBM Quantum Status",
            description="Lista todas las computadoras cuánticas disponibles en IBM Quantum con su estado operacional."
        ),
        AgentDetailTool(
            name="IBM Quantum Info",
            description="Obtiene información técnica detallada de un backend específico (qubits, errores, topología)."
        ),
        AgentDetailTool(
            name="IBM Quantum Job",
            description="Consulta el estado y resultados de trabajos cuánticos individuales o lista trabajos recientes."
        ),
        AgentDetailTool(
            name="IBM Quantum Job Comparison",
            description="Compara resultados de múltiples trabajos cuánticos lado a lado."
        )
    ],
)

# Skills expuestos por el agente
STATUS_AGENT_SKILLS = [
    AgentSkill(
        id="quantum-backend-status",
        name="Quantum Backend Status Queries",
        description="Consulta el estado y disponibilidad de computadoras cuánticas de IBM en tiempo real.",
        tags=["Quantum Computing", "IBM Quantum", "Backend Status", "Availability"],
        examples=[
            "¿Qué computadoras cuánticas están disponibles?",
            "What quantum computers are available?",
            "¿Cuál es el backend menos ocupado?",
            "Show me only real quantum hardware",
            "Lista los simuladores disponibles"
        ]
    ),
    AgentSkill(
        id="quantum-backend-info",
        name="Quantum Backend Technical Information",
        description="Obtiene información técnica detallada de backends específicos (propiedades de qubits, errores, topología).",
        tags=["Quantum Computing", "IBM Quantum", "Backend Info", "Technical Details"],
        examples=[
            "Dame información detallada de ibm_brisbane",
            "What are the properties of ibm_torino?",
            "¿Cuántos qubits tiene ibm_kyiv?",
            "Show me the error rates of ibm_sherbrooke",
            "¿Cuál es la topología de ibm_osaka?"
        ]
    ),
    AgentSkill(
        id="quantum-job-status",
        name="Quantum Job Status and Results",
        description="Consulta el estado, resultados y mediciones de trabajos cuánticos ejecutados.",
        tags=["Quantum Computing", "IBM Quantum", "Job Status", "Results"],
        examples=[
            "¿Cuál es el estado del trabajo d671cklbujdc73cvbp30?",
            "What is the status of job abc123xyz?",
            "Muéstrame mis trabajos recientes",
            "Show me my running jobs",
            "Lista mis trabajos completados"
        ]
    ),
    AgentSkill(
        id="quantum-job-comparison",
        name="Quantum Job Comparison",
        description="Compara resultados de múltiples trabajos cuánticos para análisis lado a lado.",
        tags=["Quantum Computing", "IBM Quantum", "Job Comparison", "Analysis"],
        examples=[
            "Compara los resultados de los jobs d6cd297g4t5c7385dh4g y d6cd2bknsg9c739a32p0",
            "Compare jobs abc123 and xyz789",
            "¿Cuál es la diferencia entre estos trabajos: job1, job2, job3?",
            "Show me a comparison of these job results"
        ]
    )
]

# Crear servidor AgentStack
server = Server()

def create_status_agent():
    """Crea una instancia del Quantum Status Agent con Mistral Small"""
    # Configurar Watsonx con Mistral Small
    llm = ChatModel.from_name(
        f"watsonx:{os.getenv('WATSONX_STATUS_MODEL', 'mistralai/mistral-small-3-1-24b-instruct-2503')}"
    )
    
    # Definir las herramientas
    tools = [
        IBMQuantumStatusTool(),
        IBMQuantumInfoTool(),
        IBMQuantumJobTool(),
        IBMQuantumJobComparisonTool(),
    ]
    
    # Crear un template de sistema personalizado con las instrucciones AL INICIO
    custom_system_template = PromptTemplate(
        schema=SystemPromptTemplateInput,
        template="""# YOUR ROLE AND CRITICAL RULES
""" + STATUS_INSTRUCTIONS + """

# Available functions
{{#tools.0}}
You MUST use one of the following functions for EVERY query. Never respond without using a function.

{{#tools}}
Function Name: {{name}}
Description: {{description}}
Input Schema: {{&input_schema}}

{{/tools}}
{{/tools.0}}

# Communication structure
You communicate only in instruction lines. The format is: "Instruction: expected output".

Message: User's message. You never use this instruction line.
Thought: Your step-by-step plan. This MUST be immediately followed by Function Name (to call a function) or Final Answer.
Function Name: Name of the function to call. This MUST be immediately followed by Function Input.
Function Input: Function parameters in JSON format, e.g. {{"arg1":"value1", "arg2":"value2"}}
Function Output: Output of the function in JSON format.
Final Answer: Your response to the user with the data from the function. Must always be preceded by Thought.

# ⚠️⚠️⚠️ CRITICAL INSTRUCTIONS - NEVER VIOLATE ⚠️⚠️⚠️

1. YOU MUST CALL A FUNCTION FOR EVERY USER QUERY
2. YOUR FINAL ANSWER MUST BE THE EXACT FUNCTION OUTPUT - WORD FOR WORD
3. DO NOT ADD TIPS, NOTES, OR EXTRA TEXT
4. DO NOT MODIFY, REFORMAT, OR OMIT ANY DATA FROM THE FUNCTION OUTPUT

**YOUR FINAL ANSWER = FUNCTION OUTPUT (EXACT COPY)**

FORBIDDEN:
❌ Adding tips or notes after the function output
❌ Saying "here is the list" without showing the actual data
❌ Modifying tables or omitting columns
❌ Summarizing instead of showing complete data

REQUIRED:
✅ Copy the ENTIRE Function Output as your Final Answer
✅ Include ALL tables, data, and recommendations from the function
✅ Use the EXACT same format and words

## Example of CORRECT behavior:
Message: ¿Qué computadoras cuánticas están disponibles?
Thought: I need to call ibm_quantum_status to get the list of available quantum computers
Function Name: ibm_quantum_status
Function Input: {{"only_hardware": false}}
Function Output: 🔬 **Computadoras Cuánticas Disponibles en IBM Quantum**

| Backend | Tipo | Qubits | Estado | Cola | Versión |
|---------|------|--------|--------|------|----------|
| ibm_brisbane | ⚛️ Hardware | 127 | 🟢 OK | 5 | 2 |
...

Thought: I will show the user the EXACT output from the function without any modifications
Final Answer: 🔬 **Computadoras Cuánticas Disponibles en IBM Quantum**

| Backend | Tipo | Qubits | Estado | Cola | Versión |
|---------|------|--------|--------|------|----------|
| ibm_brisbane | ⚛️ Hardware | 127 | 🟢 OK | 5 | 2 |
...

## Example of INCORRECT behavior (FORBIDDEN):
❌ Modifying the table (removing columns, changing format)
❌ Saying "here is the list" without calling the function
❌ Summarizing instead of showing complete data
""",
    )
    
    # Crear el agente con el template personalizado
    return ReActAgent(
        llm=llm,
        tools=tools,
        memory=UnconstrainedMemory(),
        templates={"system": custom_system_template},
    )

@server.agent(
    name="Quantum Status Agent",
    detail=STATUS_AGENT_DETAIL,
    skills=STATUS_AGENT_SKILLS
)
async def quantum_status_agent(
    input: Message,
    context: RunContext,
    trajectory: Annotated[TrajectoryExtensionServer, TrajectoryExtensionSpec()]
):
    """
    Handler principal del Quantum Status Agent.
    
    Este agente consulta el estado de backends y trabajos cuánticos en IBM Quantum.
    """
    user_query = get_message_text(input)
    print("=" * 80)
    print(f"📊 [Status Agent] Received query: '{user_query[:100]}...'")
    print("=" * 80)
    
    # Paso 1: Análisis de la solicitud
    yield trajectory.trajectory_metadata(
        title="🔍 Analizando consulta de estado",
        content=f"Procesando la consulta del usuario:\n```\n{user_query[:200]}{'...' if len(user_query) > 200 else ''}\n```"
    )
    
    # Crear el agente con las instrucciones
    agent = create_status_agent()
    
    # Paso 2: Preparación del agente
    yield trajectory.trajectory_metadata(
        title="🤖 Preparando agente de consultas",
        content=f"**Configuración:**\n- Modelo: Mistral Small 3.1\n- Herramientas: 4 (Status, Info, Job, Comparison)\n- Memoria: Ilimitada"
    )
    
    # Construir el prompt con las instrucciones del sistema
    full_prompt = f"{STATUS_INSTRUCTIONS}\n\n---\n\nUSER REQUEST:\n{user_query}"
    
    # Paso 3: Consulta de datos
    yield trajectory.trajectory_metadata(
        title="⚙️ Consultando IBM Quantum",
        content="El agente está consultando datos en tiempo real de IBM Quantum..."
    )
    
    # Ejecutar el agente
    try:
        run_context = await agent.run(full_prompt)
        
        # Actualizar trayectoria con progreso
        yield trajectory.trajectory_metadata(
            title="✅ Datos obtenidos",
            content="- [x] Consulta completada\n- [x] Datos procesados\n- [x] Respuesta formateada"
        )
        
        # Extraer la respuesta
        response = ""
        if hasattr(run_context, 'output') and run_context.output:
            output = run_context.output
            if isinstance(output, list) and output:
                last_msg = output[-1]
                if hasattr(last_msg, 'text'):
                    response = str(last_msg.text)
                elif hasattr(last_msg, 'content'):
                    response = str(last_msg.content)
                else:
                    response = str(last_msg)
            else:
                response = str(output)
        else:
            response = str(run_context)
        
        # Asegurar que response sea string
        if not isinstance(response, str):
            response = str(response)
        
        # Paso 4: Respuesta generada
        yield trajectory.trajectory_metadata(
            title="✅ Respuesta lista",
            content=f"Datos de IBM Quantum obtenidos ({len(response)} caracteres)\n\n**Contenido:**\n- Estado de backends\n- Información técnica\n- Resultados de trabajos"
        )
        
        print("=" * 80)
        print(f"✅ [Status Agent] Response generated ({len(response)} chars)")
        print("=" * 80)
        
        # Crear el mensaje de respuesta
        response_message = AgentMessage(text=response)
        
        # Yield la respuesta al usuario
        yield response_message
        
    except Exception as e:
        import traceback
        error_msg = f"❌ Error en Status Agent: {str(e)}"
        error_details = f"\n\nTipo de error: {type(e).__name__}\n"
        error_details += f"Detalles: {str(e)}\n\n"
        error_details += "Traceback:\n"
        error_details += traceback.format_exc()
        
        # Trayectoria de error
        yield trajectory.trajectory_metadata(
            title="❌ Error detectado",
            content=f"**Tipo:** {type(e).__name__}\n**Mensaje:** {str(e)}\n\nConsulta los logs para más detalles."
        )
        
        print("=" * 80)
        print(f"🔴 [Status Agent] {error_msg}")
        print(error_details)
        print("=" * 80)
        
        yield AgentMessage(text=error_msg + error_details)

def run():
    """Inicia el servidor del Quantum Status Agent con almacenamiento persistente"""
    port = int(os.getenv("STATUS_PORT", 8002))
    host = os.getenv("STATUS_HOST", "127.0.0.1")
    
    print("=" * 80)
    print("🚀 Starting Quantum Status Agent Server (AgentStack)")
    print("=" * 80)
    print(f"  📊 Agent: Quantum Status Agent")
    print(f"  🤖 Model: {os.getenv('WATSONX_STATUS_MODEL', 'mistralai/mistral-small-3-1-24b-instruct-2503')}")
    print(f"  🌐 Host: {host}")
    print(f"  🔌 Port: {port}")
    print(f"  🛠️  Tools: 4 (Status, Info, Job, Job Comparison)")
    print(f"  📚 History: Persistent storage enabled (PlatformContextStore)")
    print(f"  🎯 Trajectory: Visualization enabled")
    print(f"  📚 Skills: Backend Status, Technical Info, Job Results, Comparison")
    print("=" * 80)
    print("\n💡 Tip: Este agente es invocado por el Operations Agent (puerto 8000)")
    print("   para consultar estado de backends y trabajos cuánticos.")
    print("=" * 80)
    
    # Ejecutar servidor sin PlatformContextStore (invocado vía A2A)
    server.run(
        host=host,
        port=port
    )

if __name__ == "__main__":
    run()