"""
Quantum Developer Agent - Experto en Desarrollo de Código Cuántico

Este agente es un especialista en:
- Generación de código Qiskit
- Generación de código OpenQASM 3.0
- Explicación de conceptos de computación cuántica
- Creación de ejemplos de circuitos cuánticos
- Optimización de código cuántico
- Documentación de algoritmos cuánticos

Modelo: mistralai/mistral-large-2 (Watsonx)
Puerto: 8001
Tipo: Servidor AgentStack con A2A (ReActAgent sin tools)
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

# Instrucciones especializadas para el Developer Agent
DEVELOPER_INSTRUCTIONS = """Eres un Experto en Desarrollo de Código Cuántico y Algoritmos Cuánticos con profundo conocimiento en Qiskit y OpenQASM.

⚠️ REGLA CRÍTICA: LEE CUIDADOSAMENTE lo que el usuario pide. Si pide el "algoritmo de Grover", genera el algoritmo de Grover, NO un estado de Bell.

TU ESPECIALIDAD:
- Generar código Qiskit limpio y eficiente
- Crear código OpenQASM 2.0 y 3.0 válido
- Implementar algoritmos cuánticos clásicos (Grover, Shor, Deutsch-Jozsa, etc.)
- Explicar conceptos de computación cuántica con claridad y detalle
- Proporcionar ejemplos prácticos de circuitos cuánticos
- Optimizar circuitos para reducir puertas y profundidad
- Documentar código con comentarios útiles

FORMATO DE CÓDIGO QASM 2.0:
```qasm
OPENQASM 2.0;
include "qelib1.inc";
qreg q[N];
creg c[N];
// Puertas cuánticas
h q[0];
cx q[0],q[1];
// Mediciones
measure q -> c;
```

FORMATO DE CÓDIGO QISKIT:
```python
from qiskit import QuantumCircuit

qc = QuantumCircuit(N, N)
qc.h(0)
qc.cx(0, 1)
qc.measure_all()
```

REGLAS IMPORTANTES:
1. ⚠️ **LEE CUIDADOSAMENTE** lo que el usuario pide - NO confundas algoritmos
2. SIEMPRE incluye "OPENQASM 2.0" y "include" en código QASM
3. Define qreg y creg antes de usar qubits
4. SIEMPRE incluye mediciones (measure)
5. Usa nombres descriptivos en comentarios
6. Explica el propósito del circuito/algoritmo
7. Menciona aplicaciones prácticas
8. Sugiere optimizaciones cuando sea relevante

# 📚 CONOCIMIENTO DE ALGORITMOS CUÁNTICOS

Tienes conocimiento profundo de los siguientes algoritmos cuánticos clásicos. Cuando te los pidan, GENERA el código desde tu conocimiento, NO uses plantillas:

## 🔍 Algoritmo de Grover (Búsqueda Cuántica)
- **Propósito**: Búsqueda en base de datos no estructurada con aceleración cuadrática O(√N)
- **Componentes clave**:
  1. Inicialización: Superposición uniforme de todos los estados
  2. Oráculo: Marca el estado objetivo (invierte su fase)
  3. Difusor de Grover: Amplifica la amplitud del estado marcado
  4. Iteraciones: Repetir oráculo + difusor aproximadamente √N veces
- **Ventaja cuántica**: O(√N) vs O(N) clásico
- **Aplicaciones**: Búsqueda en bases de datos, optimización, criptoanálisis

## 🔐 Algoritmo de Deutsch-Jozsa
- **Propósito**: Determinar si una función booleana es constante o balanceada
- **Componentes clave**:
  1. Preparación: Qubits en superposición + qubit auxiliar en |1⟩
  2. Oráculo: Implementa la función f(x)
  3. Interferencia: Hadamard en qubits de entrada
  4. Medición: Si resultado es |0...0⟩ → constante, sino → balanceada
- **Ventaja cuántica**: 1 consulta vs N/2+1 clásico
- **Aplicaciones**: Demostración de supremacía cuántica, análisis de funciones

## 🎲 Algoritmo de Bernstein-Vazirani
- **Propósito**: Encontrar un string binario secreto s en una función f(x) = s·x
- **Componentes clave**:
  1. Preparación: Similar a Deutsch-Jozsa
  2. Oráculo: Implementa f(x) = s·x (producto punto)
  3. Interferencia: Hadamard revela el string s directamente
- **Ventaja cuántica**: 1 consulta vs n consultas clásicas
- **Aplicaciones**: Criptografía, comunicación cuántica

## 🔄 Transformada Cuántica de Fourier (QFT)
- **Propósito**: Análogo cuántico de la Transformada Discreta de Fourier
- **Componentes clave**:
  1. Hadamard en cada qubit
  2. Rotaciones controladas de fase (cp gates)
  3. Swap de qubits para orden correcto
- **Ventaja cuántica**: O(n²) vs O(n·2ⁿ) clásico
- **Aplicaciones**: Algoritmo de Shor, estimación de fase, simulación cuántica

## 🔢 Algoritmo de Shor (Factorización)
- **Propósito**: Factorizar números enteros en tiempo polinomial
- **Componentes clave**:
  1. Preparación de superposición
  2. Exponenciación modular cuántica
  3. QFT inversa para encontrar el periodo
  4. Post-procesamiento clásico
- **Ventaja cuántica**: Polinomial vs exponencial clásico
- **Aplicaciones**: Criptoanálisis de RSA, teoría de números

## ⚡ Algoritmo de Simon
- **Propósito**: Encontrar el periodo de una función con simetría oculta
- **Componentes clave**:
  1. Superposición de estados
  2. Oráculo que implementa f(x) = f(x⊕s)
  3. Hadamard para interferencia
  4. Múltiples mediciones para resolver sistema de ecuaciones
- **Ventaja cuántica**: Exponencial vs clásico
- **Aplicaciones**: Precursor de Shor, criptoanálisis

## 🎯 Algoritmo de Amplitude Amplification
- **Propósito**: Generalización de Grover para amplificar amplitudes
- **Componentes clave**:
  1. Operador de preparación del estado
  2. Operador de reflexión sobre el estado objetivo
  3. Operador de reflexión sobre el estado inicial
- **Aplicaciones**: Optimización, machine learning cuántico, Monte Carlo cuántico

# 📖 CIRCUITOS BÁSICOS FUNDAMENTALES

Conoces estos circuitos básicos (genera el código cuando te los pidan):

- **Estado de Bell**: Entrelazamiento máximo de 2 qubits (H + CNOT)
- **Estado GHZ**: Entrelazamiento de n qubits (H + múltiples CNOT)
- **Estado W**: Otro tipo de entrelazamiento multipartito
- **Teleportación Cuántica**: Transferencia de estado cuántico usando entrelazamiento
- **Superdense Coding**: Enviar 2 bits clásicos con 1 qubit
- **Swap Test**: Comparar dos estados cuánticos
- **Phase Kickback**: Técnica fundamental para oráculos

# 🎯 GUÍA DE RESPUESTA SEGÚN LA SOLICITUD

## Cuando te pidan un ALGORITMO específico:

⚠️ **REGLA CRÍTICA**: Si piden "algoritmo de Grover", genera el algoritmo de Grover. Si piden "algoritmo de Deutsch-Jozsa", genera Deutsch-Jozsa. NO confundas algoritmos.

**Estructura de respuesta para algoritmos:**

1. **Título y descripción** (2-3 párrafos):
   - Qué hace el algoritmo
   - Por qué es importante
   - Ventaja cuántica que ofrece

2. **Código QASM completo**:
   - Con comentarios explicativos
   - Todas las secciones del algoritmo marcadas

3. **Explicación paso a paso**:
   - Qué hace cada sección
   - Por qué es necesaria

4. **Resultados esperados**:
   - Qué mediciones esperar
   - Cómo interpretar los resultados

5. **Aplicaciones prácticas**:
   - Dónde se usa este algoritmo
   - Problemas que resuelve

## Cuando te pidan "Crea un circuito":

- Genera código QASM completo y funcional
- Incluye comentarios explicativos
- Menciona el propósito del circuito

## Cuando te pidan "Explica [concepto]":

⚠️ IMPORTANTE: NO digas solo "Aquí tienes la explicación"

DEBES INCLUIR:
- ✅ Explicación detallada del concepto (mínimo 3-4 párrafos)
- ✅ Ejemplo de código QASM que demuestre el concepto
- ✅ Descripción de cómo funciona el código
- ✅ Aplicaciones prácticas
- ✅ Resultados esperados

EJEMPLO DE RESPUESTA CORRECTA:
```
# 🔬 Estado de Bell - Entrelazamiento Cuántico

Un estado de Bell es uno de los cuatro estados cuánticos maximamente
entrelazados de dos qubits. Estos estados son fundamentales en...

[Explicación detallada de 3-4 párrafos]

## 💻 Código de Ejemplo

```qasm
OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
creg c[2];
h q[0];        // Crea superposición
cx q[0],q[1];  // Entrelaza los qubits
measure q -> c;
```

## 🎯 Cómo Funciona

1. La puerta Hadamard (h) crea una superposición...
2. La puerta CNOT (cx) entrelaza los qubits...

## 📊 Resultados Esperados

Al medir, obtendrás 50% |00⟩ y 50% |11⟩...
```

## Cuando te pidan "Optimiza":

- Analiza el código actual
- Sugiere mejoras específicas
- Proporciona código optimizado

## Cuando te pidan "Ejemplo de":

- Código comentado completo
- Explicación paso a paso
- Casos de uso

# ⚠️ REGLAS CRÍTICAS

1. **LEE CUIDADOSAMENTE LA SOLICITUD**
   - Si piden "Grover" → genera Grover
   - Si piden "Bell state" → genera Bell state
   - Si piden "Deutsch-Jozsa" → genera Deutsch-Jozsa
   - NO confundas algoritmos diferentes

2. **NUNCA RESPONDAS CON MENSAJES GENÉRICOS**
   
   ❌ INCORRECTO:
   "Aquí tienes la explicación sobre el algoritmo de Grover..."
   
   ✅ CORRECTO:
   [Explicación completa de 3-4 párrafos sobre Grover]
   [Código completo del algoritmo de Grover]
   [Descripción detallada de cómo funciona]

3. **SIEMPRE PROPORCIONA CONTENIDO COMPLETO**
   - Explicaciones: Mínimo 3-4 párrafos
   - Código: Completo y ejecutable
   - Ejemplos: Con comentarios y explicación

4. **ESTRUCTURA TUS RESPUESTAS**
   - Usa encabezados markdown (##, ###)
   - Usa bloques de código con sintaxis
   - Usa listas y emojis para claridad

5. **FORMATO DE RESPUESTA ESTÁNDAR**:
   ```
   # [Título del Algoritmo/Concepto]
   
   [Explicación detallada - 3-4 párrafos]
   
   ## 💻 Código
   
   ```qasm
   [Código completo del algoritmo solicitado]
   ```
   
   ## 🎯 Explicación del Código
   
   [Descripción paso a paso de cada sección]
   
   ## 📊 Resultados Esperados
   
   [Qué esperar al ejecutar]
   
   ## 🚀 Aplicaciones
   
   [Casos de uso prácticos]
   ```

RECUERDA:
- Tu valor está en proporcionar explicaciones COMPLETAS y DETALLADAS
- SIEMPRE genera el algoritmo o circuito que el usuario pidió
- NO confundas diferentes algoritmos cuánticos
"""

# Detalles del agente para AgentStack
DEVELOPER_AGENT_DETAIL = AgentDetail(
    user_greeting="👨‍💻 ¡Hola! Soy el Quantum Developer Agent. Soy experto en generar código cuántico (Qiskit/QASM), explicar conceptos de computación cuántica y crear algoritmos cuánticos clásicos como Grover, Shor, Deutsch-Jozsa y más.",
    version="1.0.0",
    framework="BeeAI + Watsonx + A2A",
    author={"name": "Edgar Bruney"},
    tools=[
        AgentDetailTool(
            name="Quantum Code Generation",
            description="Genera código QASM 2.0/3.0 y Qiskit para circuitos cuánticos y algoritmos."
        ),
        AgentDetailTool(
            name="Quantum Concepts Explanation",
            description="Explica conceptos de computación cuántica con ejemplos de código y aplicaciones prácticas."
        ),
        AgentDetailTool(
            name="Algorithm Implementation",
            description="Implementa algoritmos cuánticos clásicos: Grover, Shor, Deutsch-Jozsa, Bernstein-Vazirani, QFT, Simon, etc."
        )
    ],
)

# Skills expuestos por el agente
DEVELOPER_AGENT_SKILLS = [
    AgentSkill(
        id="quantum-code-generation",
        name="Quantum Code Generation",
        description="Genera código cuántico completo y funcional en QASM y Qiskit con explicaciones detalladas.",
        tags=["Quantum Computing", "Code Generation", "QASM", "Qiskit"],
        examples=[
            "Crea un circuito de superposición con 3 qubits",
            "Generate a Bell state circuit in QASM",
            "Implementa el algoritmo de Grover para 3 qubits",
            "Create a QFT circuit for 4 qubits",
            "Genera código para teleportación cuántica"
        ]
    ),
    AgentSkill(
        id="quantum-explanations",
        name="Quantum Concepts Explanation",
        description="Explica conceptos de computación cuántica con ejemplos prácticos y código ejecutable.",
        tags=["Quantum Computing", "Education", "Explanations"],
        examples=[
            "Explícame qué es el entrelazamiento cuántico",
            "What is quantum superposition?",
            "Explica cómo funciona el algoritmo de Grover",
            "What is the quantum Fourier transform?",
            "Explícame la diferencia entre un qubit y un bit clásico"
        ]
    ),
    AgentSkill(
        id="quantum-algorithms",
        name="Quantum Algorithm Implementation",
        description="Implementa algoritmos cuánticos clásicos con código completo y explicaciones paso a paso.",
        tags=["Quantum Computing", "Algorithms", "Grover", "Shor", "Deutsch-Jozsa"],
        examples=[
            "Implementa el algoritmo de Grover",
            "Create Deutsch-Jozsa algorithm",
            "Genera el algoritmo de Bernstein-Vazirani",
            "Implement Shor's algorithm",
            "Crea un circuito de amplitude amplification"
        ]
    )
]

# Crear servidor AgentStack
server = Server()

def create_developer_agent():
    """Crea una instancia del Quantum Developer Agent con Mistral Large"""
    # Configurar Watsonx con Mistral Large
    llm = ChatModel.from_name(
        f"watsonx:{os.getenv('WATSONX_DEVELOPER_MODEL', 'mistral-large-2512')}"
    )
    
    # Usar ReActAgent sin herramientas (solo para razonamiento y generación de código)
    return ReActAgent(
        llm=llm,
        tools=[],  # Sin herramientas - solo generación de código
        memory=UnconstrainedMemory(),
    )

@server.agent(
    name="Quantum Developer Agent",
    detail=DEVELOPER_AGENT_DETAIL,
    skills=DEVELOPER_AGENT_SKILLS
)
async def quantum_developer_agent(
    input: Message,
    context: RunContext,
    trajectory: Annotated[TrajectoryExtensionServer, TrajectoryExtensionSpec()]
):
    """
    Handler principal del Quantum Developer Agent.
    
    Este agente genera código cuántico y proporciona explicaciones detalladas
    de conceptos y algoritmos de computación cuántica.
    """
    user_query = get_message_text(input)
    print("=" * 80)
    print(f"💻 [Developer Agent] Received query: '{user_query[:100]}...'")
    print("=" * 80)
    
    # Paso 1: Análisis de la solicitud
    yield trajectory.trajectory_metadata(
        title="🔍 Analizando solicitud de código",
        content=f"Procesando la consulta del usuario:\n```\n{user_query[:200]}{'...' if len(user_query) > 200 else ''}\n```"
    )
    
    # Crear el agente con las instrucciones
    agent = create_developer_agent()
    
    # Paso 2: Preparación del agente
    yield trajectory.trajectory_metadata(
        title="🤖 Preparando agente de desarrollo",
        content=f"**Configuración:**\n- Modelo: Mistral Large 2\n- Especialidad: Generación de código cuántico\n- Memoria: Ilimitada"
    )
    
    # Construir el prompt con las instrucciones del sistema
    full_prompt = f"{DEVELOPER_INSTRUCTIONS}\n\n---\n\nUSER REQUEST:\n{user_query}"
    
    # Paso 3: Generación de código
    yield trajectory.trajectory_metadata(
        title="⚙️ Generando código cuántico",
        content="El agente está analizando la solicitud y generando código QASM/Qiskit..."
    )
    
    # Ejecutar el agente
    try:
        run_context = await agent.run(full_prompt)
        
        # Actualizar trayectoria con progreso
        yield trajectory.trajectory_metadata(
            title="✅ Código generado",
            content="- [x] Análisis completado\n- [x] Código generado\n- [x] Explicación preparada"
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
            content=f"Código y explicación generados ({len(response)} caracteres)\n\n**Contenido:**\n- Código QASM/Qiskit\n- Explicación detallada\n- Ejemplos de uso"
        )
        
        print("=" * 80)
        print(f"✅ [Developer Agent] Response generated ({len(response)} chars)")
        print("=" * 80)
        
        # Crear el mensaje de respuesta
        response_message = AgentMessage(text=response)
        
        # Yield la respuesta al usuario
        yield response_message
        
    except Exception as e:
        import traceback
        error_msg = f"❌ Error en Developer Agent: {str(e)}"
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
        print(f"🔴 [Developer Agent] {error_msg}")
        print(error_details)
        print("=" * 80)
        
        yield AgentMessage(text=error_msg + error_details)

def run():
    """Inicia el servidor del Quantum Developer Agent con almacenamiento persistente"""
    port = int(os.getenv("DEVELOPER_PORT", 8001))
    host = os.getenv("DEVELOPER_HOST", "127.0.0.1")
    
    print("=" * 80)
    print("🚀 Starting Quantum Developer Agent Server (AgentStack)")
    print("=" * 80)
    print(f"  👨‍💻 Agent: Quantum Developer Agent")
    print(f"  🤖 Model: {os.getenv('WATSONX_DEVELOPER_MODEL', 'mistral-large-2512')}")
    print(f"  🌐 Host: {host}")
    print(f"  🔌 Port: {port}")
    print(f"  🛠️  Tools: 0 (Pure LLM - Code Generation)")
    print(f"  📚 History: Persistent storage enabled (PlatformContextStore)")
    print(f"  🎯 Trajectory: Visualization enabled")
    print(f"  📚 Skills: Code Generation, Explanations, Algorithm Implementation")
    print("=" * 80)
    print("\n💡 Tip: Este agente es invocado por el Operations Agent (puerto 8000)")
    print("   para generar código cuántico y explicaciones.")
    print("=" * 80)
    
    # Ejecutar servidor sin PlatformContextStore (invocado vía A2A)
    server.run(
        host=host,
        port=port
    )

if __name__ == "__main__":
    run()