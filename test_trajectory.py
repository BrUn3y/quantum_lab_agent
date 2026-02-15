#!/usr/bin/env python3
"""
Script de prueba para verificar la implementación de trayectorias
en el Quantum Operations Agent.
"""

import asyncio
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

async def test_trajectory():
    """Prueba la visualización de trayectorias del Operations Agent"""
    
    print("=" * 80)
    print("🧪 Probando implementación de trayectorias")
    print("=" * 80)
    
    # Verificar que las variables de entorno estén configuradas
    required_vars = [
        "WATSONX_URL",
        "WATSONX_APIKEY",
        "WATSONX_PROJECT_ID",
        "IBM_QUANTUM_TOKEN"
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        print(f"❌ Faltan variables de entorno: {', '.join(missing_vars)}")
        return
    
    print("✅ Variables de entorno configuradas")
    print()
    
    # Importar el agente
    try:
        from src.beeai_agents.quantum_operations_agent import (
            quantum_operations_agent,
            server
        )
        print("✅ Agente importado correctamente")
        print()
    except Exception as e:
        print(f"❌ Error al importar el agente: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Verificar que el agente tenga el parámetro trajectory
    import inspect
    sig = inspect.signature(quantum_operations_agent)
    params = list(sig.parameters.keys())
    
    print("📋 Parámetros del agente:")
    for param in params:
        print(f"   - {param}")
    print()
    
    if 'trajectory' in params:
        print("✅ Parámetro 'trajectory' encontrado")
    else:
        print("❌ Parámetro 'trajectory' NO encontrado")
        return
    
    # Verificar las importaciones
    print()
    print("📦 Verificando importaciones:")
    try:
        from agentstack_sdk.a2a.extensions import TrajectoryExtensionServer, TrajectoryExtensionSpec
        print("   ✅ TrajectoryExtensionServer")
        print("   ✅ TrajectoryExtensionSpec")
    except ImportError as e:
        print(f"   ❌ Error al importar extensiones de trayectoria: {e}")
        return
    
    print()
    print("=" * 80)
    print("✅ Implementación de trayectorias verificada correctamente")
    print("=" * 80)
    print()
    print("💡 Para probar en acción:")
    print("   1. Inicia el Operations Agent: python -m src.beeai_agents.quantum_operations_agent")
    print("   2. Inicia los otros agentes (Developer, Status, Computing)")
    print("   3. Envía una consulta desde la UI de AgentStack")
    print("   4. Observa los pasos de trayectoria en la interfaz")
    print()
    print("📝 Ejemplo de consulta:")
    print('   "Crea un circuito de superposición con 2 qubits y ejecútalo"')
    print()
    print("🎯 Pasos de trayectoria esperados:")
    print("   1. 🔍 Analizando solicitud")
    print("   2. 🤖 Preparando agente ReAct")
    print("   3. ⚙️ Ejecutando razonamiento")
    print("   4. ✅ Procesamiento completado")
    print("   5. ✅ Respuesta generada")
    print()

if __name__ == "__main__":
    asyncio.run(test_trajectory())

# Made with Bob
