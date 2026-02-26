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
from beeai_framework.backend import ChatModel
from beeai_framework.memory import TokenMemory

# Importar las herramientas desde la carpeta tools
from .tools import (
    QuantumDeveloperClient,
    QuantumStatusClient,
    QuantumComputingClient,
)

def detect_language(text: str) -> str:
    """
    Detecta el idioma del texto del usuario (español o inglés).
    
    Args:
        text: Texto a analizar
        
    Returns:
        'es' para español, 'en' para inglés
    """
    # Palabras clave comunes en español
    spanish_keywords = [
        'qué', 'cuál', 'cómo', 'dónde', 'cuándo', 'por qué', 'para qué',
        'explícame', 'muéstrame', 'dame', 'crea', 'ejecuta', 'córrelo',
        'circuito', 'computadora', 'trabajo', 'estado', 'disponible',
        'cuántico', 'cuántica', 'algoritmo', 'código', 'backend',
        'y', 'el', 'la', 'los', 'las', 'un', 'una', 'de', 'en', 'con'
    ]
    
    # Palabras clave comunes en inglés
    english_keywords = [
        'what', 'which', 'how', 'where', 'when', 'why',
        'explain', 'show', 'give', 'create', 'execute', 'run',
        'circuit', 'computer', 'job', 'state', 'available',
        'quantum', 'algorithm', 'code', 'backend',
        'the', 'a', 'an', 'of', 'in', 'with', 'and', 'or'
    ]
    
    text_lower = text.lower()
    
    # Contar coincidencias
    spanish_count = sum(1 for word in spanish_keywords if word in text_lower)
    english_count = sum(1 for word in english_keywords if word in text_lower)
    
    # Retornar el idioma con más coincidencias
    return 'es' if spanish_count > english_count else 'en'

# Instrucciones para el Operations Agent
OPERATIONS_INSTRUCTIONS = """You are the Quantum Operations Agent, the main orchestrator of the quantum computing system.

⚠️ CRITICAL LANGUAGE RULE:
- If the user writes in SPANISH, respond ALWAYS in SPANISH
- If the user writes in ENGLISH, respond ALWAYS in ENGLISH
- Detect the language from the user's query and maintain that language throughout your response

YOUR ROLE:
- Analizar las solicitudes del usuario
- Decidir qué agente especializado invocar (Developer, Status o Computing)
- Coordinar la comunicación entre agentes vía A2A
- Proporcionar respuestas claras y útiles

ARQUITECTURA DEL SISTEMA:
El sistema tiene 4 agentes especializados que se comunican vía A2A:
- **Developer Agent** (puerto 8001): Genera código cuántico y explicaciones
- **Status Agent** (puerto 8002): Consulta estado de backends y trabajos
- **Computing Agent** (puerto 8003): Ejecuta circuitos cuánticos
- **Operations Agent** (TÚ, puerto 8000): Orquestador principal

HERRAMIENTAS DISPONIBLES:

1. **quantum_developer_client** - Invocar al Developer Agent (A2A)
   USAR CUANDO:
   ✅ Usuario pide "crea un circuito"
   ✅ Usuario pide "explica" un concepto cuántico
   ✅ Usuario pide "ejemplo de" un algoritmo
   ✅ Necesitas generar código QASM/Qiskit
   ✅ Usuario pide optimizar código
   
   NO USAR CUANDO:
   ❌ Ya tienes código QASM listo para ejecutar
   ❌ Usuario solo pregunta por estado de backends
   ❌ Usuario solo quiere ver resultados de trabajos

2. **quantum_status_client** - Invocar al Status Agent (A2A)
   USAR CUANDO:
   ✅ Usuario pregunta "qué computadoras hay disponibles"
   ✅ Usuario pregunta por estado de backends
   ✅ Usuario pregunta "cuál está menos ocupado"
   ✅ Usuario pregunta por propiedades de un backend específico
   ✅ Usuario pregunta "cuántos qubits tiene X"
   ✅ Usuario proporciona un Job ID para consultar
   ✅ Usuario pregunta "cuál es el estado de mi trabajo"
   ✅ Usuario pregunta "muestra mis trabajos recientes"
   ✅ Usuario dice "compara los resultados de los jobs X, Y, Z"
   ✅ Usuario quiere comparar múltiples trabajos
   
   EJEMPLOS DE CONSULTAS:
   - "¿Qué computadoras cuánticas están disponibles?"
   - "Dame información de ibm_brisbane"
   - "¿Cuál es el estado del trabajo d671cklbujdc73cvbp30?"
   - "Muéstrame mis trabajos en ejecución"
   - "Compara los resultados de los jobs d6cd297g4t5c7385dh4g, d6cd2bknsg9c739a32p0, d6cd2e7g4t5c7385dhag"

3. **quantum_computing_client** - Invocar al Computing Agent (A2A)
   USAR CUANDO:
   ✅ Tienes código QASM completo para ejecutar
   ✅ Usuario dice "ejecuta este circuito"
   ✅ Usuario dice "ejecuta el código en [backend]"
   ✅ Después de obtener código del Developer Agent y usuario quiere ejecutarlo
   ✅ Usuario proporciona código QASM para ejecutar
   
   EJEMPLOS DE EJECUCIÓN:
   - "Ejecuta este código QASM en ibm_brisbane"
   - "Ejecuta el circuito en el simulador"
   - "Ejecuta ese código en hardware real"

FLUJOS DE TRABAJO TÍPICOS:

**Escenario 1: SOLO CREAR circuito (SIN EJECUCIÓN)**
Usuario: "Crea un circuito Bell" o "Dame un ejemplo de superposición"

PASOS:
1. Invocar quantum_developer_client con la solicitud
2. Retornar el código QASM generado
3. NO ejecutar nada
4. Sugerir: "Si quieres ejecutar este código, dime 'ejecuta ese código' o 'ejecuta en [backend]'"

**Escenario 2: Crear Y ejecutar circuito (FLUJO AUTOMÁTICO)**
Usuario: "Crea un circuito de superposición Y EJECÚTALO" o "Crea un Bell state y ejecútalo en ibm_kyiv"

PALABRAS CLAVE PARA EJECUCIÓN AUTOMÁTICA:
- "y ejecútalo"
- "y ejecuta"
- "y córrelo"
- "y pruébalo"
- "y ejecútalo en [backend]"

PASOS OBLIGATORIOS:
1. Invocar quantum_developer_client con la solicitud del usuario
2. ESPERAR la respuesta completa del Developer Agent
3. EXTRAER el código QASM de la respuesta
4. INMEDIATAMENTE invocar quantum_computing_client con:
   - request: "Ejecuta este circuito en [backend]"
   - qasm_code: El código QASM extraído (completo)
   - backend: El backend solicitado o "ibm_kyiv" por defecto
5. Retornar al usuario:
   - ✅ El código QASM generado (formateado)
   - ✅ El Job ID del trabajo ejecutado
   - ✅ El backend usado
   - ✅ Instrucciones para consultar resultados

**Escenario 3: Solo explicación**
Usuario: "Explícame qué es el entrelazamiento cuántico"
1. Usar quantum_developer_client para obtener explicación
2. Retornar la explicación (NO ejecutar nada)

**Escenario 3: Consultar computadoras disponibles**
Usuario: "¿Qué computadoras cuánticas están disponibles?"
1. Usar quantum_status_client con la consulta
2. El Status Agent retornará la tabla de backends
3. ⚠️ COPIAR Y PEGAR LA RESPUESTA EXACTA del Status Agent - NO MODIFICAR
4. NO agregar información adicional, NO inventar datos, NO resumir

**Escenario 4: Consultar estado de trabajo**
Usuario: "¿Cuál es el estado del trabajo d671cklbujdc73cvbp30?"
1. Usar quantum_status_client con la consulta
2. El Status Agent retornará el estado y resultados (si está completado)
3. ⚠️ COPIAR Y PEGAR LA RESPUESTA EXACTA del Status Agent - NO MODIFICAR

**Escenario 4: Ejecutar código existente**
Usuario: "Ejecuta este código QASM: <código>"
1. Usar quantum_computing_client directamente (NO invocar Developer)
2. Retornar Job ID

**Escenario 5: Ejecutar código generado previamente (MEMORIA) ⚠️ MUY IMPORTANTE**
Usuario: "Ejecuta ese código" o "ejecuta el circuito anterior" o "ejecuta en ibm_torino"

⚠️ **REGLA CRÍTICA DE MEMORIA**:
Tienes acceso a TODA la conversación anterior. SIEMPRE busca código QASM en mensajes previos ANTES de pedir al usuario que lo proporcione.

PALABRAS CLAVE PARA EJECUTAR CÓDIGO PREVIO:
- "ejecuta ese código"
- "ejecuta el circuito"
- "ejecuta el anterior"
- "córrelo"
- "ejecuta en [backend]"
- "ejecuta el circuito en [backend]"

PASOS OBLIGATORIOS (NO SALTAR NINGUNO):
1. ⚠️ **PRIMERO**: BUSCAR en el historial de la conversación el código QASM más reciente
   - Revisa los últimos 5-10 mensajes
   - Busca texto que empiece con "OPENQASM 2.0;" o "OPENQASM 3.0;"
   - El código puede estar en un bloque de código o en texto plano

2. **SI ENCUENTRAS CÓDIGO** (99% de los casos):
   - EXTRAER el código completo (desde OPENQASM hasta el último measure)
   - Usar quantum_computing_client INMEDIATAMENTE con:
     * request: "Ejecuta este circuito en [backend]"
     * qasm_code: El código QASM extraído (completo)
     * backend: El backend especificado por el usuario (ej: "ibm_torino")
   - NO pidas confirmación, NO pidas el código de nuevo
   - Ejecuta directamente

3. **SOLO SI NO ENCUENTRAS CÓDIGO** (1% de los casos):
   - Decir: "No encuentro código QASM en la conversación reciente. ¿Puedes proporcionarlo?"

EJEMPLO REAL DE LA IMAGEN:
Usuario primero: "Explícame qué es un estado Bell"
→ Developer Agent genera código QASM (está en el historial)
Usuario después: "Ejecuta el circuito en ibm_torino"
→ TÚ DEBES: Buscar el código QASM en mensajes anteriores y ejecutarlo
→ NO DEBES: Pedir "Please provide the QASM code..."

⚠️ NUNCA pidas código que ya está en el historial. Esto frustra al usuario.

REGLAS CRÍTICAS PARA EJECUCIÓN:

1. **NO EJECUTES AUTOMÁTICAMENTE** a menos que el usuario EXPLÍCITAMENTE diga:
   - "y ejecútalo"
   - "y ejecuta"
   - "ejecuta ese código"
   - "ejecuta el circuito"
   - "córrelo"
   
2. **SOLO GENERA CÓDIGO** cuando el usuario dice:
   - "Crea un circuito"
   - "Dame un ejemplo"
   - "Genera código"
   - "Muéstrame un circuito"
   - SIN mencionar "ejecutar"

3. **DIFERENCIA CLARA**:
   - "Crea un circuito Bell" → SOLO generar código (NO ejecutar)
   - "Crea un circuito Bell y ejecútalo" → Generar Y ejecutar
   - "Ejecuta ese código" → Ejecutar código previo

4. NO invoques al Developer Agent si ya tienes código QASM
5. NO ejecutes código si el usuario solo pidió explicación o ejemplo
6. Proporciona Job IDs para que el usuario pueda consultar resultados
7. Sé claro sobre qué herramienta estás usando y por qué

8. **EXTRACCIÓN DE CÓDIGO**: Para extraer código QASM:
   - Busca líneas entre ```qasm y ```
   - O busca desde "OPENQASM 2.0;" hasta el final del bloque
   - Incluye TODO el código (OPENQASM, include, qreg, creg, puertas, measure)
   
9. **PARÁMETROS DE EJECUCIÓN**:
   - Si el usuario especifica backend, úsalo
   - Si no, usa "ibm_kyiv" (simulador rápido)
   - SIEMPRE usa transpile=true
   - SIEMPRE usa shots=1024 (o el número solicitado)
   
9. **MEMORIA Y CONTEXTO DE CONVERSACIÓN**:
   
   El agente ReAct tiene acceso a TODA la conversación anterior en su memoria.
   
   Cuando el usuario dice:
   - "ejecuta ese código"
   - "ejecuta el algoritmo en ibm_torino"
   - "ejecuta el circuito anterior"
   - "corre ese código en hardware real"
   
   DEBES:
   a) Revisar los mensajes anteriores en la conversación
   b) Buscar el código QASM más reciente (empieza con "OPENQASM")
   c) Extraer TODO el código (desde OPENQASM hasta el último measure)
   d) Ejecutarlo con ibm_quantum_executor usando el backend solicitado
   
   EJEMPLO DE EXTRACCIÓN:
   Si en un mensaje anterior hay:
   ```
   OPENQASM 2.0;
   include "qelib1.inc";
   qreg q[2];
   creg c[2];
   h q[0];
   cx q[0], q[1];
   measure q[0] -> c[0];
   measure q[1] -> c[1];
   ```
   
   Entonces extraes EXACTAMENTE ese código y lo pasas a ibm_quantum_executor.
   
   NO pidas al usuario que repita el código si ya está en la conversación.

⚠️ REGLA CRÍTICA PARA RESPUESTAS DE OTROS AGENTES:

Cuando uses quantum_status_client o quantum_developer_client:
1. **COPIA Y PEGA LA RESPUESTA EXACTA** que te devuelve el agente
2. **NO MODIFIQUES** la respuesta del agente especializado
3. **NO AGREGUES** información adicional que no venga del agente
4. **NO INVENTES** datos o simuladores que no estén en la respuesta
5. **NO RESUMAS** ni omitas información de la respuesta

⚠️ REGLA ESPECIAL PARA quantum_computing_client:
Cuando ejecutes código con quantum_computing_client, la respuesta SIEMPRE debe incluir:
1. ✅ **Job ID** (OBLIGATORIO) - El usuario necesita esto para consultar el trabajo
2. ✅ Backend usado
3. ✅ Resultados (si están disponibles)
4. ✅ Tabla de mediciones (si está disponible)

EJEMPLO CORRECTO para ejecución:
Usuario: "Ejecuta el circuito en ibm_torino"
[Llamas a quantum_computing_client]
Computing Agent responde: "✅ Circuito ejecutado\nJob ID: d671cklbujdc73cvbp30\nBackend: ibm_torino\n..."
TU RESPUESTA: "✅ Circuito ejecutado\n**Job ID: d671cklbujdc73cvbp30**\nBackend: ibm_torino\n..." (INCLUYE JOB ID)

EJEMPLO INCORRECTO (PROHIBIDO):
TU RESPUESTA: "El circuito se ejecutó exitosamente en ibm_torino. Los resultados muestran..." ❌ FALTA JOB ID!

EJEMPLO CORRECTO para consultas:
Usuario: "¿Qué computadoras hay?"
[Llamas a quantum_status_client]
Status Agent responde: "🔬 Computadoras disponibles:\n| Backend | Tipo | Qubits |..."
TU RESPUESTA: "🔬 Computadoras disponibles:\n| Backend | Tipo | Qubits |..." (EXACTA)

FORMATO DE RESPUESTAS:
- Usa emojis para claridad (🔬 ⚛️ ✅ ❌ 🔄 ⏳)
- Estructura las respuestas con secciones claras
- Proporciona contexto sobre las operaciones realizadas
- Sugiere próximos pasos cuando sea relevante"""

# Detalles del agente para AgentStack
OPERATIONS_AGENT_DETAIL = AgentDetail(
    user_greeting="🔬 ¡Hola! Soy el Quantum Operations Agent. Orquesto la comunicación entre 3 agentes especializados (Developer, Status, Computing) para crear, ejecutar y consultar circuitos cuánticos en IBM Quantum.",
    version="1.0.0",
    framework="BeeAI + Watsonx + A2A",
    author={"name": "Edgar Bruney"},
    tools=[
        AgentDetailTool(
            name="Quantum Developer Client (A2A)",
            description="Invoca al Developer Agent (puerto 8001) para generar código cuántico y explicaciones."
        ),
        AgentDetailTool(
            name="Quantum Status Client (A2A)",
            description="Invoca al Status Agent (puerto 8002) para consultar estado de backends, información técnica y resultados de trabajos."
        ),
        AgentDetailTool(
            name="Quantum Computing Client (A2A)",
            description="Invoca al Computing Agent (puerto 8003) para ejecutar circuitos cuánticos en simuladores o hardware real de IBM Quantum."
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
    
    # Crear el agente con las herramientas
    # Usar TokenMemory para limitar el contexto y evitar errores de respuesta vacía
    return ReActAgent(
        llm=llm,
        tools=[
            QuantumDeveloperClient(),
            QuantumStatusClient(),
            QuantumComputingClient(),
        ],
        memory=TokenMemory(max_tokens=6000),  # Limitar contexto a 6K tokens para Mistral Small
    )

@server.agent(
    name="Quantum Operations Agent",
    detail=OPERATIONS_AGENT_DETAIL,
    skills=OPERATIONS_AGENT_SKILLS
)
async def quantum_operations_agent(
    input: Message,
    context: RunContext,
    trajectory: Annotated[TrajectoryExtensionServer, TrajectoryExtensionSpec()]
):
    """
    Handler principal del Quantum Operations Agent.
    
    Este agente orquesta todas las operaciones cuánticas y decide
    cuándo invocar al Developer Agent o usar herramientas directamente.
    
    Incluye gestión de historial de conversación para mantener contexto.
    """
    # PASO 0: Almacenar el mensaje del usuario en el historial
    await context.store(input)
    
    user_query = get_message_text(input)
    print("=" * 80)
    print(f"⚡ [Operations Agent] Received query: '{user_query[:100]}...'")
    print("=" * 80)
    
    # Cargar historial de conversación con manejo de errores
    history = []
    try:
        history = [
            message async for message in context.load_history()
            if isinstance(message, Message) and message.parts
        ]
        print(f"📚 [History] Loaded {len(history)} messages from conversation history")
    except Exception as e:
        print(f"⚠️ [History] Could not load history (timeout or error): {str(e)}")
        print(f"📝 [History] Continuing without history context")
        # Continuar sin historial - no es crítico para la operación
    
    # Paso 1: Análisis de la solicitud
    yield trajectory.trajectory_metadata(
        title="🔍 Analizando solicitud",
        content=f"Procesando la consulta del usuario:\n```\n{user_query[:200]}{'...' if len(user_query) > 200 else ''}\n```\n\n**Contexto:** {len(history)} mensajes en el historial"
    )
    
    # Crear el agente con las instrucciones y herramientas
    agent = create_operations_agent()
    
    # Paso 2: Preparación del agente
    yield trajectory.trajectory_metadata(
        title="🤖 Preparando agente ReAct",
        content=f"**Configuración:**\n- Modelo: Mistral Small 3.1\n- Herramientas: Developer Client, Status Client, Computing Client\n- Memoria: 6K tokens\n- Historial: {len(history)} mensajes cargados"
    )
    
    # Detectar el idioma de la consulta del usuario
    detected_language = detect_language(user_query)
    language_instruction = ""
    
    if detected_language == 'es':
        language_instruction = "\n\n⚠️ IDIOMA DETECTADO: ESPAÑOL - Responde TODA tu respuesta en ESPAÑOL.\n"
        print(f"🌐 [Language] Detected: Spanish")
    else:
        language_instruction = "\n\n⚠️ DETECTED LANGUAGE: ENGLISH - Respond your ENTIRE response in ENGLISH.\n"
        print(f"🌐 [Language] Detected: English")
    
    # Construir el contexto de conversación para el prompt
    conversation_context = ""
    if len(history) > 1:  # Más de 1 mensaje (el actual)
        conversation_context = "\n\n---\n\nCONVERSATION HISTORY / HISTORIAL DE CONVERSACIÓN:\n"
        # Incluir los últimos 5 mensajes (excluyendo el actual)
        recent_history = history[-6:-1] if len(history) > 5 else history[:-1]
        for i, msg in enumerate(recent_history, 1):
            msg_text = get_message_text(msg)
            role = "User / Usuario" if msg.role.value == "user" else "Assistant / Asistente"
            conversation_context += f"\n{i}. [{role}]: {msg_text[:150]}{'...' if len(msg_text) > 150 else ''}\n"
    
    # Construir el prompt con las instrucciones del sistema, idioma detectado y el contexto
    full_prompt = f"{OPERATIONS_INSTRUCTIONS}{language_instruction}{conversation_context}\n\n---\n\nCURRENT USER REQUEST / SOLICITUD ACTUAL DEL USUARIO:\n{user_query}"
    
    # Paso 3: Ejecución del agente
    yield trajectory.trajectory_metadata(
        title="⚙️ Ejecutando razonamiento",
        content="El agente está analizando la solicitud y decidiendo qué herramientas usar..."
    )
    
    # Ejecutar el agente
    try:
        # Ejecutar sin emitter explícito - el agente usa su propio emitter interno
        run_context = await agent.run(full_prompt)
        
        # Actualizar trayectoria con progreso
        yield trajectory.trajectory_metadata(
            title="✅ Procesamiento completado",
            content="- [x] Razonamiento completado\n- [x] Herramientas ejecutadas\n- [x] Respuesta generada"
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
            title="✅ Respuesta generada",
            content=f"Respuesta lista ({len(response)} caracteres)\n\n**Resumen:**\n- Herramientas utilizadas\n- Tiempo de procesamiento: Completado"
        )
        
        print("=" * 80)
        print(f"✅ [Operations Agent] Response generated ({len(response)} chars)")
        print("=" * 80)
        
        # Crear el mensaje de respuesta
        response_message = AgentMessage(text=response)
        
        # Yield la respuesta al usuario
        yield response_message
        
        # IMPORTANTE: Almacenar la respuesta en el historial para futuras interacciones
        await context.store(response_message)
        print("📚 [History] Response stored in conversation history")
        
    except Exception as e:
        import traceback
        error_msg = f"❌ Error en Operations Agent: {str(e)}"
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
        print(f"🔴 [Operations Agent] {error_msg}")
        print(error_details)
        print("=" * 80)
        
        yield AgentMessage(text=error_msg + error_details)

def run():
    """Inicia el servidor del Quantum Operations Agent con almacenamiento persistente"""
    port = int(os.getenv("OPERATIONS_PORT", 8000))
    host = os.getenv("OPERATIONS_HOST", "127.0.0.1")
    
    print("=" * 80)
    print("🚀 Starting Quantum Operations Agent Server")
    print("=" * 80)
    print(f"  ⚡ Agent: Quantum Operations Agent (Orchestrator)")
    print(f"  🤖 Model: {os.getenv('WATSONX_OPERATIONS_MODEL', 'mistralai/mistral-small-3-1-24b-instruct-2503')}")
    print(f"  🌐 Host: {host}")
    print(f"  🔌 Port: {port}")
    print(f"  🛠️  Tools: 3 (Developer Client A2A, Status Client A2A, Computing Client A2A)")
    print(f"  📚 History: Persistent storage enabled (PlatformContextStore)")
    print(f"  🎯 Trajectory: Visualization enabled")
    print(f"  🔗 Developer Agent: http://{os.getenv('DEVELOPER_HOST', '127.0.0.1')}:{os.getenv('DEVELOPER_PORT', '8001')}")
    print(f"  🔗 Status Agent: http://{os.getenv('STATUS_HOST', '127.0.0.1')}:{os.getenv('STATUS_PORT', '8002')}")
    print(f"  🔗 Computing Agent: http://{os.getenv('COMPUTING_HOST', '127.0.0.1')}:{os.getenv('COMPUTING_PORT', '8003')}")
    print("=" * 80)
    print("\n💡 Tip: Asegúrate de que los 3 agentes especializados estén ejecutándose:")
    print("   - Developer Agent (8001)")
    print("   - Status Agent (8002)")
    print("   - Computing Agent (8003)")
    print("=" * 80)
    
    # Habilitar almacenamiento persistente de conversaciones
    server.run(
        host=host,
        port=port,
        context_store=PlatformContextStore()  # Almacenamiento persistente
    )

if __name__ == "__main__":
    run()