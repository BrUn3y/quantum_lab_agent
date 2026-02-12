"""
Quantum Operations Agent - Orquestador de Operaciones Cuánticas

Este agente es el punto de entrada principal del sistema y se encarga de:
- Recibir solicitudes del usuario
- Decidir cuándo invocar al Quantum Developer Agent
- Ejecutar circuitos en IBM Quantum
- Consultar estado de backends y trabajos
- Orquestar la comunicación entre componentes

Modelo: mistralai/mistral-small-3-1-24b-instruct-2503 (Watsonx)
Puerto: 8000
Tipo: Servidor A2A principal + Cliente A2A (invoca al Developer)
"""

import os
from collections.abc import AsyncGenerator

from a2a.types import AgentSkill, Message
from a2a.utils.message import get_message_text
from agentstack_sdk.server import Server
from agentstack_sdk.server.context import RunContext
from agentstack_sdk.a2a.types import AgentMessage
from agentstack_sdk.a2a.extensions import AgentDetail, AgentDetailTool

from beeai_framework.agents.react import ReActAgent
from beeai_framework.backend import ChatModel
from beeai_framework.memory import UnconstrainedMemory

# Importar todas las herramientas desde la carpeta tools
from .tools import (
    IBMQuantumTool,
    IBMQuantumStatusTool,
    IBMQuantumInfoTool,
    IBMQuantumJobTool,
    QuantumDeveloperClient,
)

# Instrucciones para el Operations Agent
OPERATIONS_INSTRUCTIONS = """Eres el Quantum Operations Agent, el orquestador principal del sistema de computación cuántica.

TU ROL:
- Analizar las solicitudes del usuario
- Decidir qué herramientas usar
- Invocar al Quantum Developer Agent cuando sea necesario
- Ejecutar operaciones en IBM Quantum
- Proporcionar respuestas claras y útiles

HERRAMIENTAS DISPONIBLES:

1. **quantum_developer_client** - Invocar al Developer Agent
   USAR CUANDO:
   ✅ Usuario pide "crea un circuito"
   ✅ Usuario pide "explica" un concepto
   ✅ Usuario pide "ejemplo de" un algoritmo
   ✅ Necesitas generar código QASM/Qiskit
   ✅ Usuario pide optimizar código
   
   NO USAR CUANDO:
   ❌ Ya tienes código QASM listo para ejecutar
   ❌ Usuario solo pregunta por estado de backends
   ❌ Usuario solo quiere ver resultados de trabajos

2. **ibm_quantum_executor** - Ejecutar circuitos
   USAR CUANDO:
   ✅ Tienes código QASM completo para ejecutar
   ✅ Usuario dice "ejecuta este circuito"
   ✅ Después de obtener código del Developer Agent y usuario quiere ejecutarlo

3. **ibm_quantum_status** - Ver computadoras disponibles
   USAR CUANDO:
   ✅ Usuario pregunta "qué computadoras hay"
   ✅ Usuario pregunta por estado de backends
   ✅ Usuario pregunta "cuál está menos ocupado"

4. **ibm_quantum_info** - Info detallada de backend
   USAR CUANDO:
   ✅ Usuario pregunta por propiedades de un backend específico
   ✅ Usuario pregunta "cuántos qubits tiene X"
   ✅ Usuario pregunta por errores o características técnicas

5. **ibm_quantum_job** - Ver resultados de trabajos
   USAR CUANDO:
   ✅ Usuario proporciona un Job ID
   ✅ Usuario pregunta "cuál es el estado de mi trabajo"
   ✅ Usuario pregunta "muestra mis trabajos recientes"

FLUJO DE TRABAJO TÍPICO:

**Escenario 1: Crear y ejecutar circuito (FLUJO AUTOMÁTICO)**
Usuario: "Crea un circuito de superposición con 2 qubits y ejecútalo"

PASOS OBLIGATORIOS:
1. Invocar quantum_developer_client con la solicitud del usuario
2. ESPERAR la respuesta completa del Developer Agent
3. EXTRAER el código QASM de la respuesta:
   - Buscar el bloque de código entre ```qasm y ```
   - O buscar el código que empieza con "OPENQASM 2.0;"
4. INMEDIATAMENTE invocar ibm_quantum_executor con:
   - qasm_code: El código QASM extraído (completo)
   - backend_name: El backend solicitado o "ibm_kyiv" por defecto
   - transpile: true (siempre)
   - shots: 1024 (o el número solicitado)
5. Retornar al usuario:
   - ✅ El código QASM generado (formateado)
   - ✅ El Job ID del trabajo ejecutado
   - ✅ El backend usado
   - ✅ Instrucciones para consultar resultados

IMPORTANTE: NO preguntes al usuario si quiere ejecutar, HAZLO AUTOMÁTICAMENTE

**Escenario 2: Solo explicación**
Usuario: "Explícame qué es el entrelazamiento cuántico"
1. Usar quantum_developer_client para obtener explicación
2. Retornar la explicación (NO ejecutar nada)

**Escenario 3: Solo consulta**
Usuario: "¿Qué computadoras cuánticas están disponibles?"
1. Usar ibm_quantum_status directamente
2. Retornar la tabla de backends

**Escenario 4: Ejecutar código existente**
Usuario: "Ejecuta este código QASM: <código>"
1. Usar ibm_quantum_executor directamente (NO invocar Developer)
2. Retornar Job ID

**Escenario 5: Ejecutar código generado previamente**
Usuario: "Ejecuta ese código" o "Ejecuta el código anterior"
1. Si el código QASM está en el contexto de la conversación, úsalo
2. Si no está disponible, pedir al usuario que lo proporcione de nuevo
3. Usar ibm_quantum_executor con el código
4. Retornar Job ID

REGLAS IMPORTANTES:
1. NO invoques al Developer Agent si ya tienes código QASM
2. NO ejecutes código si el usuario solo pidió explicación
3. SIEMPRE confirma antes de ejecutar en hardware real
4. Proporciona Job IDs para que el usuario pueda consultar resultados
5. Sé claro sobre qué herramienta estás usando y por qué
6. **FLUJO AUTOMÁTICO**: Cuando el usuario pida "crea X y ejecútalo":
   - Paso 1: Invocar quantum_developer_client
   - Paso 2: Extraer código QASM de la respuesta
   - Paso 3: Invocar ibm_quantum_executor AUTOMÁTICAMENTE
   - NO pidas confirmación, EJECUTA directamente
   
7. **EXTRACCIÓN DE CÓDIGO**: Para extraer código QASM:
   - Busca líneas entre ```qasm y ```
   - O busca desde "OPENQASM 2.0;" hasta el final del bloque
   - Incluye TODO el código (OPENQASM, include, qreg, creg, puertas, measure)
   
8. **PARÁMETROS DE EJECUCIÓN**:
   - Si el usuario especifica backend, úsalo
   - Si no, usa "ibm_kyiv" (simulador rápido)
   - SIEMPRE usa transpile=true
   - SIEMPRE usa shots=1024 (o el número solicitado)
   
9. **MEMORIA**: Si el usuario dice "ejecuta ese código" o "ejecuta el anterior":
   - Busca el código QASM en mensajes anteriores
   - Si lo encuentras, ejecútalo directamente
   - Si no lo encuentras, pide al usuario que lo proporcione

FORMATO DE RESPUESTAS:
- Usa emojis para claridad (🔬 ⚛️ ✅ ❌ 🔄 ⏳)
- Estructura las respuestas con secciones claras
- Proporciona contexto sobre las operaciones realizadas
- Sugiere próximos pasos cuando sea relevante"""

# Detalles del agente para AgentStack
OPERATIONS_AGENT_DETAIL = AgentDetail(
    user_greeting="🔬 ¡Hola! Soy el Quantum Operations Agent. Puedo ayudarte a crear, ejecutar y gestionar circuitos cuánticos en IBM Quantum.",
    version="1.0.0",
    framework="BeeAI + Watsonx + A2A",
    author={"name": "Edgar Bruney"},
    tools=[
        AgentDetailTool(
            name="Quantum Developer Client",
            description="Invoca al Developer Agent para generar código cuántico y explicaciones."
        ),
        AgentDetailTool(
            name="IBM Quantum Executor",
            description="Ejecuta circuitos cuánticos en simuladores o hardware real de IBM Quantum."
        ),
        AgentDetailTool(
            name="IBM Quantum Status",
            description="Consulta las computadoras cuánticas disponibles y el estado de sus colas."
        ),
        AgentDetailTool(
            name="IBM Quantum Info",
            description="Obtiene información técnica detallada de backends específicos."
        ),
        AgentDetailTool(
            name="IBM Quantum Job",
            description="Consulta el estado y resultados de trabajos cuánticos."
        )
    ],
)

# Skills expuestos por el agente
OPERATIONS_AGENT_SKILLS = [
    AgentSkill(
        id="quantum-operations",
        name="Quantum Operations Management",
        description="Orquesta todas las operaciones cuánticas: creación de código, ejecución, consultas y gestión de trabajos.",
        tags=["Quantum Computing", "IBM Quantum", "Operations", "Orchestration"],
        examples=[
            "Crea un circuito de superposición con 2 qubits y ejecútalo",
            "¿Qué computadoras cuánticas están disponibles?",
            "Muéstrame el estado del trabajo d671cklbujdc73cvbp30",
            "Dame información detallada de ibm_brisbane",
            "Explícame qué es el entrelazamiento cuántico",
            "Crea un estado de Bell y ejecútalo en el simulador",
            "¿Cuál es el backend menos ocupado?",
            "Ejecuta este código QASM en hardware real",
            "Muéstrame mis trabajos recientes",
            "Optimiza este circuito cuántico"
        ]
    )
]

# Crear servidor AgentStack
server = Server()

def create_operations_agent():
    """Crea una instancia del Quantum Operations Agent con Mistral Small"""
    # Configurar Watsonx con Mistral Small
    llm = ChatModel.from_name(
        f"watsonx:{os.getenv('WATSONX_OPERATIONS_MODEL', 'mistralai/mistral-small-3-1-24b-instruct-2503')}"
    )
    
    return ReActAgent(
        llm=llm,
        tools=[
            QuantumDeveloperClient(),
            IBMQuantumTool(),
            IBMQuantumStatusTool(),
            IBMQuantumInfoTool(),
            IBMQuantumJobTool(),
        ],
        memory=UnconstrainedMemory(),
    )

@server.agent(
    name="Quantum Operations Agent",
    detail=OPERATIONS_AGENT_DETAIL,
    skills=OPERATIONS_AGENT_SKILLS
)
async def quantum_operations_agent(
    input: Message,
    context: RunContext
) -> AsyncGenerator[AgentMessage, None]:
    """
    Handler principal del Quantum Operations Agent.
    
    Este agente orquesta todas las operaciones cuánticas y decide
    cuándo invocar al Developer Agent o usar herramientas directamente.
    """
    user_query = get_message_text(input)
    print("=" * 80)
    print(f"⚡ [Operations Agent] Received query: '{user_query[:100]}...'")
    print("=" * 80)
    
    # Crear el agente con las instrucciones y herramientas
    agent = create_operations_agent()
    
    # Construir el prompt completo con instrucciones
    full_prompt = f"{OPERATIONS_INSTRUCTIONS}\n\n---\n\nSOLICITUD DEL USUARIO:\n{user_query}"
    
    # Ejecutar el agente
    try:
        run_context = await agent.run(full_prompt)
        
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
        
        print("=" * 80)
        print(f"✅ [Operations Agent] Response generated ({len(response)} chars)")
        print("=" * 80)
        
        yield AgentMessage(text=response)
        
    except Exception as e:
        error_msg = f"❌ Error en Operations Agent: {str(e)}"
        print("=" * 80)
        print(f"🔴 [Operations Agent] {error_msg}")
        print("=" * 80)
        yield AgentMessage(text=error_msg)

def run():
    """Inicia el servidor del Quantum Operations Agent"""
    port = int(os.getenv("OPERATIONS_PORT", 8000))
    host = os.getenv("OPERATIONS_HOST", "127.0.0.1")
    
    print("=" * 80)
    print("🚀 Starting Quantum Operations Agent Server")
    print("=" * 80)
    print(f"  ⚡ Agent: Quantum Operations Agent")
    print(f"  🤖 Model: {os.getenv('WATSONX_OPERATIONS_MODEL', 'mistralai/mistral-small-3-1-24b-instruct-2503')}")
    print(f"  🌐 Host: {host}")
    print(f"  🔌 Port: {port}")
    print(f"  🛠️  Tools: 5 (Developer Client, Executor, Status, Info, Job)")
    print(f"  🔗 Developer Agent: http://{os.getenv('DEVELOPER_HOST', '127.0.0.1')}:{os.getenv('DEVELOPER_PORT', '8001')}")
    print("=" * 80)
    print("\n💡 Tip: Asegúrate de que el Developer Agent esté ejecutándose en el puerto 8001")
    print("=" * 80)
    
    server.run(host=host, port=port)

if __name__ == "__main__":
    run()

# Made with Bob