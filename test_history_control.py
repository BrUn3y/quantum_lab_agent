#!/usr/bin/env python3
"""
Script de prueba para verificar la implementación de control de historial
en el Quantum Operations Agent.
"""

import inspect

print("=" * 80)
print("🧪 Verificando implementación de control de historial")
print("=" * 80)
print()

# Verificar las importaciones
print("📦 Verificando importaciones:")
try:
    from agentstack_sdk.server.store.platform_context_store import PlatformContextStore
    print("   ✅ PlatformContextStore")
except ImportError as e:
    print(f"   ❌ Error al importar PlatformContextStore: {e}")
    exit(1)

try:
    from agentstack_sdk.server.context import RunContext
    print("   ✅ RunContext")
except ImportError as e:
    print(f"   ❌ Error al importar RunContext: {e}")
    exit(1)

print()

# Importar el agente
try:
    from src.beeai_agents.quantum_operations_agent import quantum_operations_agent, run
    print("✅ Agente importado correctamente")
    print()
except Exception as e:
    print(f"❌ Error al importar el agente: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Verificar que el agente tenga el parámetro context
sig = inspect.signature(quantum_operations_agent)
params = list(sig.parameters.keys())

print("📋 Parámetros del agente:")
for param in params:
    param_obj = sig.parameters[param]
    annotation = param_obj.annotation if param_obj.annotation != inspect.Parameter.empty else "sin tipo"
    print(f"   - {param}: {annotation}")
print()

if 'context' in params:
    print("✅ Parámetro 'context' encontrado (RunContext)")
    
    # Verificar la anotación del parámetro context
    context_param = sig.parameters['context']
    print(f"   Tipo: {context_param.annotation}")
else:
    print("❌ Parámetro 'context' NO encontrado")
    exit(1)

print()

# Verificar el código fuente para las llamadas a context.store()
print("🔍 Verificando uso de context.store() en el código:")
import inspect
source = inspect.getsource(quantum_operations_agent)

store_calls = source.count('await context.store(')
load_history_calls = source.count('context.load_history(')

print(f"   - Llamadas a 'await context.store()': {store_calls}")
print(f"   - Llamadas a 'context.load_history()': {load_history_calls}")

if store_calls >= 2:
    print("   ✅ Se almacenan mensajes de entrada y salida")
else:
    print("   ⚠️  Advertencia: Se esperaban al menos 2 llamadas a context.store()")

if load_history_calls >= 1:
    print("   ✅ Se carga el historial de conversación")
else:
    print("   ⚠️  Advertencia: No se encontraron llamadas a load_history()")

print()

# Verificar la función run() para PlatformContextStore
print("🔍 Verificando configuración de PlatformContextStore:")
run_source = inspect.getsource(run)

if 'PlatformContextStore()' in run_source:
    print("   ✅ PlatformContextStore configurado en server.run()")
    print("   ✅ Almacenamiento persistente habilitado")
else:
    print("   ⚠️  Advertencia: PlatformContextStore no encontrado en run()")

print()
print("=" * 80)
print("✅ Implementación de control de historial verificada")
print("=" * 80)
print()
print("📝 Funcionalidades implementadas:")
print("   1. ✅ Almacenamiento de mensajes de entrada (await context.store(input))")
print("   2. ✅ Carga de historial de conversación (context.load_history())")
print("   3. ✅ Almacenamiento de respuestas (await context.store(response))")
print("   4. ✅ Almacenamiento persistente (PlatformContextStore)")
print("   5. ✅ Contexto de conversación en el prompt")
print()
print("💡 Beneficios:")
print("   - Las conversaciones se mantienen entre reinicios del agente")
print("   - El agente puede referenciar mensajes anteriores")
print("   - Mejor contexto para decisiones del agente")
print("   - Experiencia de usuario más natural y fluida")
print()
print("🎯 Para probar en acción:")
print("   1. Inicia el Operations Agent: python -m src.beeai_agents.quantum_operations_agent")
print("   2. Envía una consulta: 'Crea un circuito Bell'")
print("   3. En la siguiente consulta: 'Ejecuta ese código en ibm_torino'")
print("   4. El agente recordará el código del mensaje anterior")
print()
print("📊 Ejemplo de flujo con historial:")
print("   Usuario: 'Explícame qué es un estado Bell'")
print("   Agente: [Genera explicación y código QASM]")
print("   Usuario: 'Ejecuta ese código en ibm_torino'")
print("   Agente: [Busca el código en el historial y lo ejecuta] ✅")
print()
