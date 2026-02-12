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
Tipo: Servidor A2A usando BeeAI Framework (ReActAgent sin tools)
"""

import os

from beeai_framework.adapters.a2a import A2AServer, A2AServerConfig
from beeai_framework.agents.react import ReActAgent
from beeai_framework.backend import ChatModel
from beeai_framework.memory import UnconstrainedMemory
from beeai_framework.serve.utils import LRUMemoryManager

# Instrucciones especializadas para el Developer Agent
DEVELOPER_INSTRUCTIONS = """Eres un Experto en Desarrollo de Código Cuántico con profundo conocimiento en Qiskit y OpenQASM.

TU ESPECIALIDAD:
- Generar código Qiskit limpio y eficiente
- Crear código OpenQASM 2.0 y 3.0 válido
- Explicar conceptos de computación cuántica con claridad
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
1. SIEMPRE incluye "OPENQASM 2.0" y "include" en código QASM
2. Define qreg y creg antes de usar qubits
3. SIEMPRE incluye mediciones (measure)
4. Usa nombres descriptivos en comentarios
5. Explica el propósito del circuito
6. Menciona aplicaciones prácticas
7. Sugiere optimizaciones cuando sea relevante

EJEMPLOS DE CIRCUITOS COMUNES:

**Estado de Bell (Entrelazamiento):**
```qasm
OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
creg c[2];
h q[0];        // Superposición
cx q[0],q[1];  // Entrelazamiento
measure q -> c;
```

**Estado GHZ (3 qubits):**
```qasm
OPENQASM 2.0;
include "qelib1.inc";
qreg q[3];
creg c[3];
h q[0];
cx q[0],q[1];
cx q[0],q[2];
measure q -> c;
```

**Teleportación Cuántica:**
```qasm
OPENQASM 2.0;
include "qelib1.inc";
qreg q[3];
creg c[3];
// Preparar estado de Bell
h q[1];
cx q[1],q[2];
// Operaciones de Alice
cx q[0],q[1];
h q[0];
measure q[0] -> c[0];
measure q[1] -> c[1];
// Correcciones de Bob
if(c[1]==1) x q[2];
if(c[0]==1) z q[2];
measure q[2] -> c[2];
```

CUANDO TE PIDAN:
- "Crea un circuito": Genera código QASM completo y funcional
- "Explica": Da explicación clara con ejemplo de código
- "Optimiza": Analiza el código y sugiere mejoras
- "Ejemplo de": Proporciona código comentado con explicación

RESPONDE SIEMPRE:
1. Código completo y ejecutable
2. Explicación breve del circuito
3. Aplicación práctica
4. Notas sobre optimización (si aplica)"""

def create_developer_agent():
    """Crea una instancia del Quantum Developer Agent con Mistral Large"""
    # Configurar Watsonx con Mistral Large
    llm = ChatModel.from_name(
        f"watsonx:{os.getenv('WATSONX_DEVELOPER_MODEL', 'mistral-large-2512')}"
    )
    
    # Usar ReActAgent sin herramientas (solo para razonamiento y generación de código)
    # Las instrucciones están embebidas en el prompt del sistema
    return ReActAgent(
        llm=llm,
        tools=[],  # Sin herramientas - solo generación de código
        memory=UnconstrainedMemory(),
    )

def run():
    """Inicia el servidor A2A del Quantum Developer Agent usando BeeAI Framework"""
    port = int(os.getenv("DEVELOPER_PORT", 8001))
    host = os.getenv("DEVELOPER_HOST", "127.0.0.1")
    
    print("=" * 60)
    print("🚀 Starting Quantum Developer Agent Server (BeeAI A2A)")
    print("=" * 60)
    print(f"  👨‍💻 Agent: Quantum Developer Agent")
    print(f"  🤖 Model: {os.getenv('WATSONX_DEVELOPER_MODEL', 'mistral-large-2512')}")
    print(f"  🌐 Host: {host}")
    print(f"  🔌 Port: {port}")
    print(f"  📚 Skills: Code Generation, Explanations, Optimization")
    print(f"  🔧 Framework: BeeAI A2A Server")
    print("=" * 60)
    
    # Crear el agente
    agent = create_developer_agent()
    
    # Configurar y ejecutar el servidor A2A
    # Usamos LRU memory manager para mantener un número limitado de sesiones en memoria
    A2AServer(
        config=A2AServerConfig(
            port=port,
            host=host,
            protocol="jsonrpc"  # Protocolo JSON-RPC para A2A
        ),
        memory_manager=LRUMemoryManager(maxsize=100)
    ).register(agent, send_trajectory=True).serve()

if __name__ == "__main__":
    run()

# Made with Bob