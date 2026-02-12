# Quantum Lab Agent 🔬⚛️

Sistema de agentes especializados en computación cuántica con arquitectura A2A (Agent-to-Agent), construido con BeeAI Framework, AgentStack y Watsonx, que utiliza la infraestructura de IBM Quantum.

## 🏗️ Arquitectura del Sistema

El sistema está compuesto por **dos agentes especializados** que se comunican entre sí mediante el protocolo A2A:

### 1. 🎯 Quantum Developer Agent (Puerto 8001)
**Experto en Desarrollo de Código Cuántico**

- **Modelo:** Mistral Large 2512 (Watsonx)
- **Especialidad:** Generación de código Qiskit y OpenQASM 3.0
- **Responsabilidades:**
  - Generar código de circuitos cuánticos
  - Explicar conceptos de computación cuántica
  - Proporcionar ejemplos de algoritmos cuánticos
  - Optimizar circuitos existentes
  - Documentar código con comentarios claros

### 2. ⚡ Quantum Operations Agent (Puerto 8000)
**Orquestador de Operaciones Cuánticas**

- **Modelo:** Mistral Small (Watsonx)
- **Especialidad:** Ejecución y gestión de operaciones cuánticas
- **Responsabilidades:**
  - Recibir solicitudes del usuario
  - Invocar al Developer Agent cuando necesite código
  - Ejecutar circuitos en IBM Quantum
  - Consultar estado de computadoras cuánticas
  - Verificar resultados de trabajos
  - Obtener información de backends

### 🔄 Flujo de Comunicación A2A

```
Usuario → Operations Agent → ¿Necesita código? 
                           ↓
                    [Sí] → Developer Agent → Genera código QASM/Qiskit
                           ↓
                    Operations Agent → Ejecuta en IBM Quantum
                           ↓
                    Usuario ← Resultados
```

## 🤖 Capacidades del Sistema

### 💻 Generación de Código (Developer Agent)
- ✨ Crear circuitos cuánticos en OpenQASM 2.0/3.0
- 🐍 Generar código Qiskit (Python)
- 📚 Explicar conceptos cuánticos con ejemplos
- 🔧 Optimizar circuitos para reducir complejidad
- 📝 Documentar código con comentarios útiles

### 🚀 Operaciones Cuánticas (Operations Agent)
- 🖥️ Ejecutar circuitos en simuladores de IBM Quantum
- 💻 Ejecutar circuitos en hardware cuántico real (QPU)
- 🔄 Transpilación automática para compatibilidad con hardware
- 📊 Consultar computadoras cuánticas disponibles
- 🔍 Obtener información detallada de backends
- 📈 Consultar estado y resultados de trabajos

## 🎯 Ejemplos de Uso

### Crear y Ejecutar Circuitos

**Superposición:**
```
"Crea un circuito de superposición con 3 qubits y ejecútalo en el simulador"
```

**Estado de Bell:**
```
"Dame un ejemplo de un estado de Bell y ejecútalo"
```

**Algoritmos Cuánticos:**
```
"Crea un circuito del algoritmo de Grover y ejecútalo en hardware real"
```

### Solo Explicaciones (Sin Ejecución)

```
"Explícame qué es el entrelazamiento cuántico"
"¿Cómo funciona la teleportación cuántica?"
"Dame un ejemplo del algoritmo de Deutsch-Jozsa"
```

### Consultas de Estado

```
"¿Qué computadoras cuánticas están disponibles?"
"Dame información detallada de ibm_brisbane"
"¿Cuál es el backend menos ocupado?"
```

### Seguimiento de Trabajos

```
"Muéstrame mis trabajos recientes"
"¿Cuál es el estado del trabajo d671cklbujdc73cvbp30?"
"Dame los resultados del Job ID abc123xyz"
```

## 🚀 Instalación y Configuración

### Prerequisitos

- Python 3.11+
- Cuenta de IBM Quantum (gratuita)
- Cuenta de IBM Watsonx (para LLMs)
- Token de IBM Quantum
- API Key de Watsonx

### Paso 1: Clonar el Repositorio

```bash
git clone <your-repo-url>
cd quantum_lab_agent
```

### Paso 2: Instalar Dependencias

Usando uv (recomendado):
```bash
uv sync
```

O con pip:
```bash
pip install -e .
```

### Paso 3: Configurar Credenciales

1. **Obtén tu token de IBM Quantum:**
   - Visita: https://quantum.cloud.ibm.com/
   - Copia tu token de acceso

2. **Obtén tus credenciales de Watsonx:**
   - API Key de Watsonx
   - Project ID de Watsonx

3. **Configura el archivo `.env`:**

```env
# --- IBM QUANTUM CREDENTIALS ---
QISKIT_IBM_TOKEN=tu_token_ibm_quantum

# --- WATSONX CONFIGURATION ---
WATSONX_API_KEY=tu_api_key_watsonx
WATSONX_PROJECT_ID=tu_project_id_watsonx
WATSONX_API_URL=https://us-south.ml.cloud.ibm.com/ml/v1/text/chat?version=2023-05-29

# --- QUANTUM DEVELOPER AGENT (Puerto 8001) ---
WATSONX_DEVELOPER_MODEL=mistralai/mistral-large-2512
DEVELOPER_HOST=127.0.0.1
DEVELOPER_PORT=8001

# --- QUANTUM OPERATIONS AGENT (Puerto 8000) ---
WATSONX_OPERATIONS_MODEL=mistralai/mistral-small-3-1-24b-instruct-2503
OPERATIONS_HOST=127.0.0.1
OPERATIONS_PORT=8000

# --- GENERAL SETTINGS ---
LOG_LEVEL=info
```

## 🏃 Ejecutar el Sistema

### Opción 1: Ejecutar Ambos Agentes (Recomendado)

**Terminal 1 - Developer Agent:**
```bash
python -m beeai_agents.quantum_developer_agent
```

**Terminal 2 - Operations Agent:**
```bash
python -m beeai_agents.quantum_operations_agent
```

### Opción 2: Usar el Comando CLI

```bash
# Iniciar Operations Agent (principal)
uv run server
```

**Nota:** Asegúrate de que el Developer Agent esté ejecutándose en el puerto 8001 antes de iniciar el Operations Agent.

### Verificar que los Agentes Están Corriendo

- **Developer Agent:** http://127.0.0.1:8001
- **Operations Agent:** http://127.0.0.1:8000

## 📁 Estructura del Proyecto

```
quantum_lab_agent/
├── src/
│   └── beeai_agents/
│       ├── __init__.py                      # Exportaciones del paquete
│       ├── quantum_developer_agent.py       # Agente experto en código
│       ├── quantum_operations_agent.py      # Agente orquestador principal
│       ├── agent.py                         # [LEGACY] Agente antiguo
│       └── tools/                           # Herramientas del sistema
│           ├── __init__.py                  # Exportaciones de tools
│           ├── quantum_tool.py              # Ejecutor de circuitos
│           ├── quantum_status_tool.py       # Consulta de estado
│           ├── quantum_info_tool.py         # Info detallada de backends
│           ├── quantum_job_tool.py          # Consulta de trabajos
│           └── quantum_developer_client.py  # Cliente A2A para Developer
├── .env                                     # Configuración (no incluir en git)
├── pyproject.toml                          # Dependencias del proyecto
├── README.md                               # Este archivo
└── Dockerfile                              # Configuración de contenedor
```

## 🛠️ Herramientas del Sistema

### 1. 🎯 Quantum Developer Client (A2A)
**Propósito:** Comunicación con el Developer Agent

**Cuándo se usa:**
- Usuario pide "crea un circuito"
- Usuario pide "explica" un concepto
- Se necesita generar código QASM/Qiskit
- Usuario pide optimizar código

**Ejemplo:**
```python
{
  "request": "Crea un circuito de superposición con 3 qubits",
  "format": "qasm"
}
```

### 2. 🚀 IBM Quantum Executor
**Propósito:** Ejecutar circuitos en IBM Quantum

**Características:**
- Ejecuta código OpenQASM 2.0/3.0
- Transpilación automática para hardware
- Soporta simuladores y hardware real
- Optimización de nivel 3

**Ejemplo:**
```python
{
  "qasm_code": "OPENQASM 2.0;\ninclude \"qelib1.inc\";\nqreg q[2];\ncreg c[2];\nh q[0];\ncx q[0],q[1];\nmeasure q->c;",
  "use_real_device": false
}
```

### 3. 📊 IBM Quantum Status
**Propósito:** Listar computadoras cuánticas disponibles

**Salida:**
- Tabla con backends disponibles
- Número de qubits por backend
- Estado operacional
- Trabajos en cola
- Recomendación del menos ocupado

### 4. 🔍 IBM Quantum Info
**Propósito:** Información técnica detallada de backends

**Información proporcionada:**
- Propiedades de qubits (T1, T2, frecuencia)
- Errores de puertas cuánticas
- Topología de conectividad
- Operaciones soportadas
- Configuración del procesador

### 5. 📈 IBM Quantum Job
**Propósito:** Consultar estado y resultados de trabajos

**Funcionalidades:**
- Verificar estado (QUEUED, RUNNING, COMPLETED)
- Obtener resultados de mediciones
- Mostrar distribución de probabilidades
- Listar trabajos recientes

## 🔧 Configuración Avanzada

### Variables de Entorno

| Variable | Descripción | Requerido | Default |
|----------|-------------|-----------|---------|
| `QISKIT_IBM_TOKEN` | Token de IBM Quantum | ✅ Sí | - |
| `WATSONX_API_KEY` | API Key de Watsonx | ✅ Sí | - |
| `WATSONX_PROJECT_ID` | Project ID de Watsonx | ✅ Sí | - |
| `WATSONX_DEVELOPER_MODEL` | Modelo para Developer Agent | ❌ No | mistral-large-2512 |
| `WATSONX_OPERATIONS_MODEL` | Modelo para Operations Agent | ❌ No | mistral-small |
| `DEVELOPER_PORT` | Puerto del Developer Agent | ❌ No | 8001 |
| `OPERATIONS_PORT` | Puerto del Operations Agent | ❌ No | 8000 |
| `LOG_LEVEL` | Nivel de logging | ❌ No | info |

### Cambiar Modelos LLM

Para usar diferentes modelos de Watsonx, edita el `.env`:

```env
# Usar modelos más grandes
WATSONX_DEVELOPER_MODEL=mistralai/mistral-large-2512
WATSONX_OPERATIONS_MODEL=mistralai/mistral-large-2512

# O modelos más pequeños
WATSONX_DEVELOPER_MODEL=mistralai/mistral-small-3-1-24b-instruct-2503
WATSONX_OPERATIONS_MODEL=mistralai/mistral-small-3-1-24b-instruct-2503
```

## 📚 Conceptos de Computación Cuántica

### Puertas Cuánticas Soportadas

- **h (Hadamard)**: Crea superposición
- **cx (CNOT)**: Puerta controlada NOT, crea entrelazamiento
- **x, y, z**: Puertas de Pauli (rotaciones)
- **rx, ry, rz**: Rotaciones parametrizadas
- **measure**: Mide el estado del qubit

### Ejemplo de Circuito: Estado de Bell

```qasm
OPENQASM 2.0;
include "qelib1.inc";

qreg q[2];
creg c[2];

h q[0];        // Superposición
cx q[0], q[1]; // Entrelazamiento
measure q -> c;
```

Este circuito crea un estado entrelazado entre dos qubits, resultando en mediciones correlacionadas (00 o 11 con ~50% de probabilidad cada uno).

## 🐛 Solución de Problemas

### Developer Agent No Responde

**Verificar que esté corriendo:**
```bash
curl http://127.0.0.1:8001/health
```

**Reiniciar el agente:**
```bash
python -m beeai_agents.quantum_developer_agent
```

### Operations Agent No Puede Conectarse al Developer

**Error:** `No se pudo conectar al Quantum Developer Agent`

**Solución:**
1. Verifica que el Developer Agent esté corriendo en el puerto 8001
2. Verifica las variables `DEVELOPER_HOST` y `DEVELOPER_PORT` en `.env`
3. Verifica que no haya firewall bloqueando la conexión

### Errores de Watsonx

**Token inválido:**
- Verifica `WATSONX_API_KEY` en `.env`
- Verifica `WATSONX_PROJECT_ID` en `.env`
- Asegúrate de tener acceso a los modelos Mistral en Watsonx

**Modelo no disponible:**
- Verifica que tengas acceso a `mistral-large-2512` y `mistral-small`
- Consulta la documentación de Watsonx para modelos disponibles

### Errores de IBM Quantum

**Token inválido:**
- Verifica `QISKIT_IBM_TOKEN` en `.env`
- Obtén un nuevo token en https://quantum.cloud.ibm.com/

**Backend no disponible:**
- Usa `ibm_quantum_status` para ver backends disponibles
- Algunos backends requieren acceso especial

**Transpilación fallida:**
- El circuito puede ser demasiado complejo para el backend
- Intenta con un simulador primero
- Reduce el número de qubits o puertas

## 📊 Dependencias Principales

- **agentstack-sdk** (0.4.0rc1): Orquestación de agentes y servidor A2A
- **beeai_framework** (>=0.1.76): Framework core del agente
- **qiskit** (>=1.0.0): Framework de computación cuántica
- **qiskit-ibm-runtime** (>=0.20.0): Integración con IBM Quantum
- **httpx**: Cliente HTTP para comunicación A2A

## 🔄 Migración desde Versión Anterior

Si estabas usando el `agent.py` antiguo:

1. **Actualiza el `.env`** con las nuevas variables
2. **Inicia ambos agentes** en terminales separadas
3. **El Operations Agent** reemplaza al `agent.py` antiguo
4. **La funcionalidad es la misma** pero con mejor arquitectura

## 🤝 Contribuir

Las contribuciones son bienvenidas. Por favor:

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📄 Licencia

[Tu Licencia Aquí]

## 👥 Autor

**Edgar Bruney** - Desarrollo inicial y arquitectura A2A

## 🙏 Agradecimientos

- IBM Quantum por la infraestructura de computación cuántica
- IBM Watsonx por los modelos LLM
- Equipo de BeeAI Framework
- Comunidad de AgentStack
- Proyecto Qiskit

## 📞 Soporte

Si tienes preguntas o problemas:

1. Revisa la sección de [Solución de Problemas](#-solución-de-problemas)
2. Abre un issue en GitHub
3. Consulta la documentación de [IBM Quantum](https://quantum.ibm.com/docs)
4. Revisa la documentación de [BeeAI Framework](https://github.com/i-am-bee/bee-agent-framework)
5. Consulta la documentación de [Watsonx](https://www.ibm.com/watsonx)

---

**¡Feliz computación cuántica con arquitectura A2A! 🔬⚛️🤖**

Made with ❤️ by Bob