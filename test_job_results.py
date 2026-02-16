#!/usr/bin/env python3
"""
Script de prueba para obtener resultados de un trabajo cuántico
"""
from qiskit_ibm_runtime import QiskitRuntimeService

# Job ID del trabajo completado
JOB_ID = "d671cklbujdc73cvbp30"

# Inicializar servicio
service = QiskitRuntimeService(channel="ibm_quantum_platform")

# Obtener el trabajo
job = service.job(JOB_ID)

print(f"Job ID: {job.job_id()}")
print(f"Status: {job.status()}")
print(f"Backend: {job.backend().name}")
print()

# Obtener resultados
result = job.result()

print("=== Explorando estructura de resultados ===")
print(f"Type: {type(result)}")
print(f"Dir: {[attr for attr in dir(result) if not attr.startswith('_')]}")
print()

# Intentar diferentes métodos para obtener los datos
if hasattr(result, 'quasi_dists'):
    print("✓ Tiene quasi_dists")
    print(f"  Type: {type(result.quasi_dists)}")
    print(f"  Length: {len(result.quasi_dists)}")
    if result.quasi_dists:
        print(f"  First item: {result.quasi_dists[0]}")

if hasattr(result, 'metadata'):
    print("✓ Tiene metadata")
    print(f"  Type: {type(result.metadata)}")
    if isinstance(result.metadata, list) and result.metadata:
        print(f"  First metadata keys: {result.metadata[0].keys() if isinstance(result.metadata[0], dict) else 'Not a dict'}")

if hasattr(result, 'data'):
    print("✓ Tiene data")
    print(f"  Type: {type(result.data)}")
    if isinstance(result.data, list) and result.data:
        print(f"  First data: {result.data[0]}")
        print(f"  First data type: {type(result.data[0])}")
        print(f"  First data dir: {[attr for attr in dir(result.data[0]) if not attr.startswith('_')]}")

print("\n=== Intentando obtener conteos ===")
try:
    # SamplerV2 devuelve PubResult
    if hasattr(result, 'data') and result.data:
        pub_result = result.data[0]
        print(f"PubResult type: {type(pub_result)}")
        
        # Buscar atributos de mediciones
        for attr in dir(pub_result):
            if not attr.startswith('_'):
                try:
                    value = getattr(pub_result, attr)
                    print(f"  {attr}: {type(value)} = {value if not callable(value) else 'callable'}")
                except Exception as e:
                    print(f"  {attr}: Error - {e}")
except Exception as e:
    print(f"Error: {e}")
