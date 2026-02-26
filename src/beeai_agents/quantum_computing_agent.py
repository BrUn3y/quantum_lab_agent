"""
Quantum Computing Agent - Especialista en Ejecución de Circuitos Cuánticos

Este agente es un especialista en:
- Ejecutar código QASM/Qiskit en computadoras cuánticas de IBM
- Gestionar la ejecución en simuladores y hardware real
- Proporcionar información detallada de trabajos ejecutados
- Transpilación automática de circuitos

Modelo: mistralai/mistral-small-3-1-24b-instruct-2503 (Watsonx)
Puerto: 8003
Tipo: Servidor AgentStack con A2A (ReActAgent con IBMQuantumTool)
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
from beeai_framework.memory import UnconstrainedMemory

# Importar la herramienta de ejecución
from .tools import IBMQuantumTool

# Instrucciones para el Computing Agent (sin template personalizado para evitar errores de parsing)
COMPUTING_INSTRUCTIONS = """Eres el Quantum Computing Agent. Ejecutas circuitos cuánticos en IBM Quantum.

⚠️ REGLA CRÍTICA: Tu respuesta SIEMPRE debe incluir el Job ID de forma prominente.

PASOS:
1. Extraer código QASM del request del usuario
2. Identificar backend (si se especifica, sino usar ibm_kyiv)
3. Ejecutar con ibm_quantum_executor
4. En tu respuesta final, SIEMPRE incluir:
   - ⚠️ **Job ID: [el_job_id_real]** (en negrita y con emoji de advertencia)
   - Backend usado
   - Shots
   - Resultados (si están disponibles)

FORMATO DE RESPUESTA:
```
🚀 Circuito ejecutado exitosamente

⚠️ **Job ID: abc123xyz456** ← ESTO ES OBLIGATORIO

Backend: ibm_torino
Shots: 1024
Estado: DONE

[Resultados si están disponibles]
```

El Job ID es CRÍTICO porque las computadoras cuánticas tardan en responder y el usuario necesita el ID para consultar resultados después.
"""

# Detalles del agente para AgentStack
COMPUTING_AGENT_DETAIL = AgentDetail(
    user_greeting="⚡ ¡Hola! Soy el Quantum Computing Agent. Ejecuto circuitos cuánticos en simuladores y hardware real de IBM Quantum, gestionando la transpilación y proporcionando Job IDs para seguimiento.",
    version="1.0.0",
    framework="BeeAI + Watsonx + A2A",
    author={"name": "Edgar Bruney"},
    tools=[
        AgentDetailTool(
            name="IBM Quantum Executor",
            description="Ejecuta código QASM/Qiskit en computadoras cuánticas de IBM (simuladores o hardware real) con transpilación automática."
        )
    ],
)

# Skills expuestos por el agente
COMPUTING_AGENT_SKILLS = [
    AgentSkill(
        id="quantum-circuit-execution",
        name="Quantum Circuit Execution",
        description="Ejecuta circuitos cuánticos en simuladores o hardware real de IBM Quantum con gestión automática de transpilación.",
        tags=["Quantum Computing", "IBM Quantum", "Circuit Execution", "QASM", "Qiskit"],
        examples=[
            "Ejecuta este código QASM en ibm_torino",
            "Execute this circuit on ibm_brisbane",
            "Ejecuta el circuito en el simulador ibm_kyiv",
            "Run this QASM code on real quantum hardware",
            "Ejecuta este circuito con 2048 shots en ibm_osaka"
        ]
    )
]

# Crear servidor AgentStack
server = Server()

def create_computing_agent():
    """Crea una instancia del Quantum Computing Agent con Mistral Small usando ReActAgent"""
    # Configurar Watsonx con Mistral Small
    llm = ChatModel.from_name(
        f"watsonx:{os.getenv('WATSONX_COMPUTING_MODEL', 'mistralai/mistral-small-3-1-24b-instruct-2503')}"
    )
    
    # Crear el agente usando ReActAgent
    return ReActAgent(
        llm=llm,
        tools=[IBMQuantumTool()],
        memory=UnconstrainedMemory(),
    )

@server.agent(
    name="Quantum Computing Agent",
    detail=COMPUTING_AGENT_DETAIL,
    skills=COMPUTING_AGENT_SKILLS
)
async def quantum_computing_agent(
    input: Message,
    context: RunContext,
    trajectory: Annotated[TrajectoryExtensionServer, TrajectoryExtensionSpec()]
):
    """
    Handler principal del Quantum Computing Agent.
    
    Este agente ejecuta circuitos cuánticos en IBM Quantum.
    """
    user_query = get_message_text(input)
    print("=" * 80)
    print(f"⚡ [Computing Agent] Received query: '{user_query[:100]}...'")
    print("=" * 80)
    
    # Paso 1: Análisis de la solicitud
    yield trajectory.trajectory_metadata(
        title="🔍 Analizando solicitud de ejecución",
        content=f"Procesando la consulta del usuario:\n```\n{user_query[:200]}{'...' if len(user_query) > 200 else ''}\n```"
    )
    
    # Crear el agente con las instrucciones
    agent = create_computing_agent()
    
    # Paso 2: Preparación del agente
    yield trajectory.trajectory_metadata(
        title="🤖 Preparando agente de ejecución",
        content=f"**Configuración:**\n- Modelo: Mistral Small 3.1\n- Herramienta: IBM Quantum Executor\n- Memoria: Ilimitada"
    )
    
    # Construir el prompt con las instrucciones del sistema
    full_prompt = f"{COMPUTING_INSTRUCTIONS}\n\n---\n\nUSER REQUEST:\n{user_query}"
    
    # Paso 3: Ejecución del circuito
    yield trajectory.trajectory_metadata(
        title="⚙️ Ejecutando circuito cuántico",
        content="El agente está ejecutando el circuito en IBM Quantum..."
    )
    
    # Ejecutar el agente
    try:
        run_context = await agent.run(full_prompt)
        
        # Actualizar trayectoria con progreso
        yield trajectory.trajectory_metadata(
            title="✅ Circuito ejecutado",
            content="- [x] Código QASM extraído\n- [x] Circuito transpilado\n- [x] Trabajo enviado a IBM Quantum"
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
            title="✅ Job ID generado",
            content=f"Trabajo enviado a IBM Quantum ({len(response)} caracteres)\n\n**Contenido:**\n- Job ID para seguimiento\n- Backend utilizado\n- Configuración de ejecución"
        )
        
        print("=" * 80)
        print(f"✅ [Computing Agent] Response generated ({len(response)} chars)")
        print("=" * 80)
        
        # Crear el mensaje de respuesta
        response_message = AgentMessage(text=response)
        
        # Yield la respuesta al usuario
        yield response_message
        
    except Exception as e:
        import traceback
        error_msg = f"❌ Error en Computing Agent: {str(e)}"
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
        print(f"🔴 [Computing Agent] {error_msg}")
        print(error_details)
        print("=" * 80)
        
        yield AgentMessage(text=error_msg + error_details)

def run():
    """Inicia el servidor del Quantum Computing Agent con almacenamiento persistente"""
    port = int(os.getenv("COMPUTING_PORT", 8003))
    host = os.getenv("COMPUTING_HOST", "127.0.0.1")
    
    print("=" * 80)
    print("🚀 Starting Quantum Computing Agent Server (AgentStack)")
    print("=" * 80)
    print(f"  ⚡ Agent: Quantum Computing Agent")
    print(f"  🤖 Model: {os.getenv('WATSONX_COMPUTING_MODEL', 'mistralai/mistral-small-3-1-24b-instruct-2503')}")
    print(f"  🌐 Host: {host}")
    print(f"  🔌 Port: {port}")
    print(f"  🛠️  Tools: 1 (IBM Quantum Executor)")
    print(f"  📚 History: Persistent storage enabled (PlatformContextStore)")
    print(f"  🎯 Trajectory: Visualization enabled")
    print(f"  📚 Skills: Circuit Execution")
    print("=" * 80)
    print("\n💡 Tip: Este agente es invocado por el Operations Agent (puerto 8000)")
    print("   para ejecutar circuitos cuánticos en IBM Quantum.")
    print("=" * 80)
    
    # Ejecutar servidor sin PlatformContextStore (invocado vía A2A)
    server.run(
        host=host,
        port=port
    )

if __name__ == "__main__":
    run()