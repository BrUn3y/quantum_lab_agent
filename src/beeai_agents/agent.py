import os
import asyncio
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
from beeai_framework.middleware.trajectory import GlobalTrajectoryMiddleware

from .tools import (
    IBMQuantumTool,
    IBMQuantumStatusTool,
    IBMQuantumInfoTool,
    IBMQuantumJobTool,
)

# Configuración del Agente Cuántico con ReAct
QUANTUM_INSTRUCTIONS = """Eres un Experto en Computación Cuántica de IBM.

USA HERRAMIENTAS SOLO CUANDO SEA NECESARIO:
- Si piden "ejemplo" o "explica": Responde directamente, NO uses herramientas
- Si piden "ejecuta": Usa ibm_quantum_operator
- Si preguntan "qué computadoras": Usa ibm_quantum_status
- Si dan Job ID: Usa ibm_quantum_job

CÓDIGO QASM 2.0:
OPENQASM 2.0;
include "qelib1.inc";
qreg q[N];
creg c[N];
h q[0];
cx q[0],q[1];
measure q -> c;

REGLAS: NO bucles for, máximo 5 qubits, simulador por defecto."""

QUANTUM_AGENT_DETAIL = AgentDetail(
    user_greeting="¡Hola! Soy tu asistente de Computación Cuántica de IBM 🔬⚛️",
    version="1.0.0",
    framework="BeeAI",
    author={"name": "Edgar Bruney"},
    tools=[
        AgentDetailTool(
            name="IBM Quantum Status",
            description="Consulta las computadoras cuánticas disponibles y el estado de sus colas de trabajo."
        ),
        AgentDetailTool(
            name="IBM Quantum Info",
            description="Obtiene información detallada de una computadora cuántica específica."
        ),
        AgentDetailTool(
            name="IBM Quantum Operator",
            description="Ejecuta circuitos cuánticos en simuladores o hardware real de IBM Quantum."
        ),
        AgentDetailTool(
            name="IBM Quantum Job",
            description="Consulta el estado y resultados de trabajos cuánticos usando el Job ID."
        )
    ],
)

QUANTUM_AGENT_SKILLS = [
    AgentSkill(
        id="quantum-lab-agent",
        name="Quantum Lab Agent",
        description="Agente especializado en diseño y ejecución de circuitos cuánticos usando IBM Quantum.",
        tags=["Quantum Computing", "IBM Quantum", "Circuit Design"],
        examples=[
            "¿Qué computadoras cuánticas están disponibles?",
            "Muéstrame el estado de las colas de IBM Quantum",
            "Dame información detallada de ibm_brisbane",
            "¿Cuáles son las propiedades de ibm_kyoto?",
            "Muéstrame mis trabajos recientes",
            "¿Cuál es el estado del trabajo d671cklbujdc73cvbp30?",
            "Dame un ejemplo de un estado de Bell y ejecútalo en el simulador",
            "Crea un circuito de superposición con 2 qubits",
            "Explícame qué es el entrelazamiento cuántico con un ejemplo",
            "Ejecuta un circuito de teleportación cuántica en hardware real"
        ]
    )
]

server = Server()

def create_quantum_agent():
    """Crea una instancia del agente cuántico con BeeAI ReActAgent usando Watsonx"""
    # Configurar Watsonx con Mistral
    llm = ChatModel.from_name(
        f"watsonx:{os.getenv('WATSONX_MODEL', 'mistralai/mistral-small-3-1-24b-instruct-2503')}"
    )
    
    return ReActAgent(
        llm=llm,
        tools=[IBMQuantumStatusTool(), IBMQuantumInfoTool(), IBMQuantumJobTool(), IBMQuantumTool()],
        memory=UnconstrainedMemory(),
    )

@server.agent(name="Quantum Lab Agent", detail=QUANTUM_AGENT_DETAIL, skills=QUANTUM_AGENT_SKILLS)
async def quantum_lab_agent(input: Message, context: RunContext) -> AsyncGenerator[AgentMessage, None]:
    """Handler principal del agente cuántico integrado con AgentStack"""
    user_query = get_message_text(input)
    print(f"--- Quantum Agent received query: '{user_query}' ---")

    agent = create_quantum_agent()
    
    # Ejecutar el agente con middleware de trayectoria
    run_context = await agent.run(user_query).middleware(GlobalTrajectoryMiddleware())

    print(f"--- Quantum Agent finished processing. ---")
    
    try:
        # ReActAgentOutput tiene diferentes atributos
        # Intentar múltiples formas de extraer el resultado
        if hasattr(run_context, 'messages') and run_context.messages:
            # Obtener el último mensaje
            last_message = run_context.messages[-1]
            if hasattr(last_message, 'text'):
                final_answer = last_message.text
            elif hasattr(last_message, 'content'):
                final_answer = last_message.content
            else:
                final_answer = str(last_message)
        elif hasattr(run_context, 'output'):
            output = run_context.output
            # output es una lista de mensajes
            if isinstance(output, list) and output:
                last_msg = output[-1]
                if hasattr(last_msg, 'text'):
                    final_answer = last_msg.text
                elif hasattr(last_msg, 'content'):
                    final_answer = last_msg.content
                else:
                    final_answer = str(last_msg)
            elif hasattr(output, 'text'):
                final_answer = output.text
            elif hasattr(output, 'content'):
                final_answer = output.content
            else:
                final_answer = str(output)
        else:
            # Fallback: convertir a string
            final_answer = str(run_context)
            
    except Exception as e:
        final_answer = f"Error: No pude procesar tu solicitud cuántica. Detalles: {e}"
        print(f"--- DEBUG: Failed to parse quantum response. ---")
        print(f"--- DEBUG: run_context type: {type(run_context)} ---")
        print(f"--- DEBUG: run_context attributes: {dir(run_context)} ---")

    # Asegurar que final_answer sea string
    yield AgentMessage(text=str(final_answer) if final_answer else "No response")

def run():
    """Inicia el servidor con el agente cuántico"""
    print("Starting Quantum Lab Agent server...")
    print("  🔬 Quantum Lab Agent - IBM Quantum Computing")
    server.run(host=os.getenv("HOST", "127.0.0.1"), port=int(os.getenv("PORT", 8000)))

# Función standalone para testing directo
async def test_quantum_agent():
    """Función de prueba para ejecutar el agente directamente"""
    user_input = "Dame un ejemplo de un estado de Bell y ejecútalo en el simulador."
    
    agent = create_quantum_agent()
    response = await agent.run(user_input)
    
    print("=== QUANTUM AGENT RESPONSE ===")
    if hasattr(response, 'result'):
        print(response.result)
    else:
        print(response)
    print("==============================")

if __name__ == "__main__":
    run()

# Made with Bob
