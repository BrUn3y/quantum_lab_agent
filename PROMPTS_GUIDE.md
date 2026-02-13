# 🎯 Guía de Prompts para el Sistema de Agentes Cuánticos

Esta guía te ayudará a interactuar correctamente con el sistema de 4 agentes especializados.

## 📋 Preparación

```bash
# Iniciar todos los agentes
./start_all.sh

# Esperar a que todos estén listos (verás 4 mensajes de inicio)
```

---

## 🎨 Tipos de Prompts

### 1️⃣ **SOLO GENERAR CÓDIGO** (Sin Ejecución)

Usa estos prompts cuando **solo quieras ver el código**, sin ejecutarlo:

```
"Crea un circuito Bell"
"Dame un ejemplo de superposición con 3 qubits"
"Genera un circuito GHZ"
"Muéstrame el algoritmo de Deutsch-Jozsa"
"Crea un circuito de teleportación cuántica"
```

**Resultado esperado:**
- ✅ Código QASM generado
- ✅ Explicación del circuito
- ❌ NO se ejecuta automáticamente
- 💡 Sugerencia para ejecutar si lo deseas

---

### 2️⃣ **GENERAR Y EJECUTAR** (Flujo Completo)

Usa estos prompts cuando quieras **crear Y ejecutar** en un solo paso:

```
"Crea un circuito Bell Y EJECÚTALO"
"Genera un circuito de superposición y ejecútalo en el simulador"
"Crea un estado GHZ con 3 qubits y ejecútalo en ibm_kyiv"
"Dame un ejemplo de Grover y córrelo"
"Crea un circuito de teleportación y pruébalo"
```

**Palabras clave importantes:**
- "y ejecútalo"
- "y ejecuta"
- "y córrelo"
- "y pruébalo"

**Resultado esperado:**
- ✅ Código QASM generado
- ✅ Circuito ejecutado automáticamente
- ✅ Job ID proporcionado
- ✅ Backend usado
- ✅ Instrucciones para ver resultados

---

### 3️⃣ **EJECUTAR CÓDIGO PREVIO**

Usa estos prompts para ejecutar código que ya fue generado:

```
"Ejecuta ese código"
"Ejecuta el circuito anterior"
"Córrelo en ibm_brisbane"
"Ejecuta en hardware real"
"Ejecuta el código en el simulador"
```

**Palabras clave:**
- "ejecuta ese código"
- "ejecuta el circuito"
- "ejecuta el anterior"
- "córrelo"

**Resultado esperado:**
- ✅ Código extraído del historial
- ✅ Circuito ejecutado
- ✅ Job ID proporcionado

---

### 4️⃣ **CONSULTAR BACKENDS**

Usa estos prompts para ver computadoras cuánticas disponibles:

```
"¿Qué computadoras cuánticas están disponibles?"
"Muéstrame los backends de IBM Quantum"
"¿Cuál es el backend menos ocupado?"
"¿Qué simuladores hay disponibles?"
"¿Qué computadoras reales hay?"
"Dame información de ibm_brisbane"
"¿Cuántos qubits tiene ibm_kyiv?"
```

**Resultado esperado:**
- ✅ Tabla con backends disponibles
- ✅ Estado operacional
- ✅ Trabajos en cola
- ✅ Recomendaciones

---

### 5️⃣ **CONSULTAR TRABAJOS**

Usa estos prompts para ver el estado de tus trabajos:

```
"Muéstrame mis trabajos recientes"
"¿Qué trabajos tengo en ejecución?"
"Lista mis trabajos completados"
"¿Cuál es el estado del trabajo [JOB_ID]?"
"Muéstrame los resultados del trabajo [JOB_ID]"
```

**Resultado esperado:**
- ✅ Tabla con trabajos
- ✅ Estado (QUEUED, RUNNING, DONE)
- ✅ Resultados si está completado
- ✅ Distribución de probabilidades

---

### 6️⃣ **EXPLICACIONES**

Usa estos prompts para aprender conceptos:

```
"Explícame qué es el entrelazamiento cuántico"
"¿Cómo funciona la puerta CNOT?"
"¿Qué es un estado Bell?"
"Explica el algoritmo de Grover"
"¿Qué es la superposición cuántica?"
```

**Resultado esperado:**
- ✅ Explicación clara del concepto
- ✅ Ejemplos si es relevante
- ❌ NO se genera código automáticamente

---

## 📊 Ejemplos de Flujos Completos

### Flujo 1: Principiante (Solo Explorar)

```
1. "¿Qué computadoras cuánticas están disponibles?"
   → Ve los backends disponibles

2. "Explícame qué es un estado Bell"
   → Aprende el concepto

3. "Crea un circuito Bell"
   → Ve el código QASM

4. "Ejecuta ese código"
   → Ejecuta el circuito

5. "Muéstrame mis trabajos recientes"
   → Ve el estado del trabajo
```

### Flujo 2: Intermedio (Crear y Ejecutar)

```
1. "Crea un circuito de superposición con 3 qubits y ejecútalo"
   → Genera y ejecuta en un paso

2. "¿Cuál es el estado de mi trabajo?"
   → Consulta el resultado

3. "Ahora ejecuta el mismo circuito en ibm_brisbane"
   → Ejecuta en otro backend
```

### Flujo 3: Avanzado (Optimización)

```
1. "¿Cuál es el backend menos ocupado?"
   → Identifica el mejor backend

2. "Dame información detallada de ese backend"
   → Ve las propiedades

3. "Crea el algoritmo de Grover para 4 elementos y ejecútalo en ese backend"
   → Genera y ejecuta optimizado

4. "Muéstrame los resultados"
   → Analiza los resultados
```

---

## ⚠️ Errores Comunes y Soluciones

### ❌ Error: "El agente ejecutó cuando solo quería el código"

**Problema:** Dijiste "Crea un circuito Bell" pero se ejecutó automáticamente.

**Solución:** Asegúrate de NO usar palabras como "ejecuta", "córrelo", "pruébalo" si solo quieres el código.

**Correcto:**
- ✅ "Crea un circuito Bell" → Solo código
- ✅ "Dame un ejemplo de superposición" → Solo código

**Incorrecto:**
- ❌ "Crea un circuito Bell y ejecútalo" → Genera Y ejecuta

---

### ❌ Error: "No encuentra el código para ejecutar"

**Problema:** Dijiste "ejecuta ese código" pero el agente no lo encuentra.

**Solución:** Asegúrate de que el código fue generado en la conversación actual.

**Correcto:**
```
1. "Crea un circuito Bell"
2. "Ejecuta ese código"  ← Funciona porque hay código previo
```

**Incorrecto:**
```
1. "Ejecuta ese código"  ← No hay código previo
```

---

### ❌ Error: "El trabajo está en cola por mucho tiempo"

**Problema:** Ejecutaste en hardware real y está tardando.

**Solución:** Usa simuladores para pruebas rápidas.

**Simuladores rápidos:**
- `ibm_kyiv` (default)
- `ibm_sherbrooke`
- `simulator_statevector`

**Hardware real (más lento):**
- `ibm_brisbane`
- `ibm_osaka`
- `ibm_torino`

---

## 🎯 Tips para Mejores Resultados

1. **Sé específico con backends:**
   ```
   ✅ "Ejecuta en ibm_kyiv"
   ❌ "Ejecuta en algún simulador"
   ```

2. **Especifica shots si necesitas más precisión:**
   ```
   ✅ "Ejecuta con 4096 shots"
   ❌ "Ejecuta con muchos shots"
   ```

3. **Usa el contexto de la conversación:**
   ```
   ✅ "Ejecuta ese código en otro backend"
   ✅ "Ahora pruébalo en hardware real"
   ```

4. **Consulta antes de ejecutar en hardware real:**
   ```
   1. "¿Qué computadoras reales están disponibles?"
   2. "¿Cuál está menos ocupada?"
   3. "Ejecuta en esa computadora"
   ```

5. **Guarda los Job IDs:**
   ```
   Job ID: d673qqdbujdc73cvep1g
   
   Luego puedes consultar:
   "¿Cuál es el estado del trabajo d673qqdbujdc73cvep1g?"
   ```

---

## 📚 Referencia Rápida

| Quiero... | Prompt Ejemplo |
|-----------|----------------|
| Solo ver código | "Crea un circuito Bell" |
| Crear y ejecutar | "Crea un circuito Bell y ejecútalo" |
| Ejecutar código previo | "Ejecuta ese código" |
| Ver backends | "¿Qué computadoras hay?" |
| Ver mis trabajos | "Muéstrame mis trabajos" |
| Aprender concepto | "Explícame qué es X" |
| Ejecutar en backend específico | "Ejecuta en ibm_brisbane" |
| Ver resultados | "Muéstrame los resultados del trabajo [ID]" |

---

## 🚀 Comenzar Ahora

1. Inicia los agentes: `./start_all.sh`
2. Prueba un prompt simple: `"Crea un circuito Bell"`
3. Ejecuta el código: `"Ejecuta ese código"`
4. Ve el resultado: `"Muéstrame mis trabajos recientes"`

¡Disfruta explorando la computación cuántica! 🎉