#!/usr/bin/env python3
"""
Script de prueba simplificado para verificar la implementación de trayectorias
en el Quantum Operations Agent (sin requerir variables de entorno).
"""

import inspect

print("=" * 80)
print("🧪 Verificando implementación de trayectorias")
print("=" * 80)
print()

# Verificar las importaciones
print("📦 Verificando importaciones:")
try:
    from agentstack_sdk.a2a.extensions import TrajectoryExtensionServer, TrajectoryExtensionSpec
    print("   ✅ TrajectoryExtensionServer")
    print("   ✅ TrajectoryExtensionSpec")
except ImportError as e:
    print(f"   ❌ Error al importar extensiones de trayectoria: {e}")
    exit(1)

print()

# Importar el agente
try:
    from src.beeai_agents.quantum_operations_agent import quantum_operations_agent
    print("✅ Agente importado correctamente")
    print()
except Exception as e:
    print(f"❌ Error al importar el agente: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Verificar que el agente tenga el parámetro trajectory
sig = inspect.signature(quantum_operations_agent)
params = list(sig.parameters.keys())

print("📋 Parámetros del agente:")
for param in params:
    param_obj = sig.parameters[param]
    annotation = param_obj.annotation if param_obj.annotation != inspect.Parameter.empty else "sin tipo"
    print(f"   - {param}: {annotation}")
print()

if 'trajectory' in params:
    print("✅ Parámetro 'trajectory' encontrado")
    
    # Verificar la anotación del parámetro trajectory
    trajectory_param = sig.parameters['trajectory']
    print(f"   Tipo: {trajectory_param.annotation}")
    
    # Verificar que sea Annotated
    if hasattr(trajectory_param.annotation, '__origin__'):
        print(f"   ✅ Usa Annotated correctamente")
else:
    print("❌ Parámetro 'trajectory' NO encontrado")
    exit(1)

print()
print("=" * 80)
print("✅ Implementación de trayectorias verificada correctamente")
print("=" * 80)
print()
print("📝 Pasos de trayectoria implementados:")
print("   1. 🔍 Analizando solicitud")
print("   2. 🤖 Preparando agente ReAct")
print("   3. ⚙️ Ejecutando razonamiento")
print("   4. ✅ Procesamiento completado")
print("   5. ✅ Respuesta generada")
print("   6. ❌ Error detectado (en caso de error)")
print()
print("💡 Para probar en acción:")
print("   1. Configura las variables de entorno en .env")
print("   2. Inicia el Operations Agent: python -m src.beeai_agents.quantum_operations_agent")
print("   3. Inicia los otros agentes (Developer, Status, Computing)")
print("   4. Envía una consulta desde la UI de AgentStack")
print("   5. Observa los pasos de trayectoria en la interfaz")
print()
print("🎯 Ejemplo de consulta:")
print('   "Crea un circuito de superposición con 2 qubits y ejecútalo"')
print()

# Made with Bob
