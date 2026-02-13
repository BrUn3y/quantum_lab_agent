# 🔧 Guía de Troubleshooting

## ❌ Error: "Invalid input argument for Model 'mistralai/mistral-small-3-1-24b-instruct-2503'"

### Síntoma
```
litellm.exceptions.BadRequestError: WatsonxException - 
{"errors":[{"code":"invalid_input_argument","message":"Invalid input argument for Model 
'mistralai/mistral-small-3-1-24b-instruct-2503'...
```

### Causa
El nombre del modelo Mistral Small puede ser incorrecto o no estar disponible en tu instancia de Watsonx.

### Solución

#### Opción 1: Usar Mistral Small Correcto

Edita tu archivo `.env` y cambia el modelo:

```env
# Intenta con este nombre (sin el sufijo -2503)
WATSONX_COMPUTING_MODEL=mistralai/mistral-small-3-1-24b-instruct
WATSONX_STATUS_MODEL=mistralai/mistral-small-3-1-24b-instruct
WATSONX_OPERATIONS_MODEL=mistralai/mistral-small-3-1-24b-instruct
```

#### Opción 2: Usar Mistral Large para Todos

Si Mistral Small no está disponible, usa Mistral Large:

```env
WATSONX_DEVELOPER_MODEL=mistralai/mistral-large-2512
WATSONX_COMPUTING_MODEL=mistralai/mistral-large-2512
WATSONX_STATUS_MODEL=mistralai/mistral-large-2512
WATSONX_OPERATIONS_MODEL=mistralai/mistral-large-2512
```

#### Opción 3: Verificar Modelos Disponibles

Consulta la documentación de Watsonx para ver qué modelos están disponibles en tu región:
https://cloud.ibm.com/apidocs/watsonx-ai#text-chat

Modelos comunes de Mistral en Watsonx:
- `mistralai/mistral-large-2512`
- `mistralai/mistral-large-2`
- `mistralai/mistral-small`
- `mistralai/mistral-7b-instruct-v0-3`

### Después de Cambiar

1. Guarda el archivo `.env`
2. Reinicia todos los agentes:
   ```bash
   # Detén todos (Ctrl+C en cada terminal)
   # Reinicia:
   ./start_all.sh
   ```

---

## ⚠️ Warning: "Instance was not set at service instantiation"

### Síntoma
```
qiskit_runtime_service.__init__:WARNING: Instance was not set at service instantiation. 
Free and trial plan instances will be prioritized.
```

### Causa
Qiskit no tiene una instancia específica configurada.

### Solución
Este es solo un warning y no afecta la funcionalidad. Qiskit automáticamente seleccionará la instancia disponible.

Si quieres eliminarlo, puedes especificar la instancia en el código, pero no es necesario para el funcionamiento básico.

---

## 🔄 Error: "Agent ejecuta cuando solo quiero código"

### Síntoma
Dices "Crea un circuito Bell" y el agente lo ejecuta automáticamente.

### Solución
Asegúrate de haber reiniciado el Operations Agent después de los cambios:

```bash
# Detén el Operations Agent (Ctrl+C)
./start_operations.sh
```

Usa prompts claros:
- ✅ "Crea un circuito Bell" → Solo código
- ✅ "Crea un circuito Bell y ejecútalo" → Código + ejecución

---

## 📊 Error: "Status Agent no muestra datos"

### Síntoma
El Status Agent responde "Aquí tienes la lista" sin mostrar la lista real.

### Solución
Reinicia el Status Agent:

```bash
# Detén el Status Agent (Ctrl+C)
./start_status.sh
```

---

## 💻 Error: "Developer Agent no da explicación completa"

### Síntoma
El Developer Agent responde "Aquí tienes la explicación" sin dar la explicación.

### Solución
Reinicia el Developer Agent:

```bash
# Detén el Developer Agent (Ctrl+C)
./start_developer.sh
```

---

## 🔌 Error: "Connection refused" o "Port already in use"

### Síntoma
```
Error: Address already in use
```

### Solución

#### Opción 1: Matar procesos en los puertos
```bash
# Encuentra procesos en los puertos
lsof -ti:8000,8001,8002,8003

# Mata los procesos
kill -9 $(lsof -ti:8000,8001,8002,8003)
```

#### Opción 2: Cambiar puertos
Edita `.env`:
```env
OPERATIONS_PORT=9000
DEVELOPER_PORT=9001
STATUS_PORT=9002
COMPUTING_PORT=9003
```

---

## 🔑 Error: "Invalid IBM Quantum token"

### Síntoma
```
Error: Invalid token
```

### Solución
1. Verifica tu token en https://quantum.cloud.ibm.com/
2. Actualiza `.env`:
   ```env
   QISKIT_IBM_TOKEN=tu_token_correcto
   ```
3. Reinicia los agentes

---

## 🌐 Error: "Watsonx API error"

### Síntoma
```
Error: 401 Unauthorized
```

### Solución
1. Verifica tus credenciales de Watsonx
2. Actualiza `.env`:
   ```env
   WATSONX_API_KEY=tu_api_key
   WATSONX_PROJECT_ID=tu_project_id
   ```
3. Reinicia los agentes

---

## 🐛 Debugging General

### Ver logs detallados

Edita `.env`:
```env
LOG_LEVEL=debug
```

### Verificar que todos los agentes están corriendo

```bash
# Deberías ver 4 procesos
ps aux | grep quantum
```

### Verificar puertos abiertos

```bash
# Deberías ver 8000, 8001, 8002, 8003
lsof -i :8000,8001,8002,8003
```

### Reiniciar todo desde cero

```bash
# 1. Detén todos los agentes (Ctrl+C en cada terminal)

# 2. Mata cualquier proceso residual
kill -9 $(lsof -ti:8000,8001,8002,8003)

# 3. Verifica tu .env
cat .env

# 4. Reinicia todos
./start_all.sh
```

---

## 📞 Soporte

Si el problema persiste:

1. Verifica que tienes las credenciales correctas
2. Revisa los logs de cada agente
3. Asegúrate de que los modelos están disponibles en tu región de Watsonx
4. Consulta la documentación de Watsonx: https://cloud.ibm.com/apidocs/watsonx-ai

---

## ✅ Checklist de Verificación

Antes de reportar un problema, verifica:

- [ ] Archivo `.env` configurado correctamente
- [ ] Token de IBM Quantum válido
- [ ] Credenciales de Watsonx válidas
- [ ] Modelos correctos en `.env`
- [ ] Puertos disponibles (8000-8003)
- [ ] Todos los agentes reiniciados después de cambios
- [ ] Logs revisados para errores específicos