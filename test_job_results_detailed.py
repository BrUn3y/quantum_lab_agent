"""
Script para probar la extracción de resultados de trabajos cuánticos
"""
from qiskit_ibm_runtime import QiskitRuntimeService
from dotenv import load_dotenv
import os

# Cargar variables de entorno
load_dotenv()

# Job ID del trabajo completado
JOB_ID = "d673qqdbujdc73cvep1g"

print("=" * 80)
print("🔬 Analizando Resultados del Trabajo Cuántico")
print("=" * 80)
print(f"Job ID: {JOB_ID}\n")

# Inicializar servicio
service = QiskitRuntimeService(channel="ibm_quantum_platform")

# Obtener el trabajo
job = service.job(JOB_ID)

print(f"📊 Estado: {job.status()}")
print(f"🖥️  Backend: {job.backend().name}")
print()

# Obtener resultados
result = job.result()

print("=" * 80)
print("📋 Estructura del Resultado")
print("=" * 80)
print(f"Tipo de resultado: {type(result).__name__}")
print(f"Atributos disponibles: {dir(result)}")
print()

# Explorar result.data
if hasattr(result, 'data'):
    print("=" * 80)
    print("📦 Explorando result.data")
    print("=" * 80)
    print(f"Número de elementos en data: {len(result.data)}")
    
    if result.data:
        pub_result = result.data[0]
        print(f"Tipo de data[0]: {type(pub_result).__name__}")
        print(f"Atributos de data[0]: {[attr for attr in dir(pub_result) if not attr.startswith('_')]}")
        print()
        
        # Intentar acceder a diferentes atributos
        print("=" * 80)
        print("🔍 Buscando Mediciones")
        print("=" * 80)
        
        # Lista de posibles atributos donde pueden estar las mediciones
        possible_attrs = ['meas', 'c', 'measurements', 'counts', 'data', 'values', 'results']
        
        for attr_name in possible_attrs:
            if hasattr(pub_result, attr_name):
                attr_value = getattr(pub_result, attr_name)
                print(f"\n✅ Encontrado: {attr_name}")
                print(f"   Tipo: {type(attr_value).__name__}")
                print(f"   Valor: {attr_value}")
                
                # Si es un objeto con métodos, mostrarlos
                if hasattr(attr_value, '__dict__'):
                    print(f"   Atributos: {[a for a in dir(attr_value) if not a.startswith('_')]}")
                
                # Intentar obtener conteos
                if hasattr(attr_value, 'get_counts'):
                    try:
                        counts = attr_value.get_counts()
                        print(f"   📊 Conteos: {counts}")
                    except Exception as e:
                        print(f"   ⚠️  Error al obtener conteos: {e}")
                
                # Si es un array, mostrar forma y primeros elementos
                if hasattr(attr_value, 'shape'):
                    print(f"   📐 Forma: {attr_value.shape}")
                    print(f"   📊 Primeros elementos: {attr_value[:5] if len(attr_value) > 5 else attr_value}")

# Explorar metadata
if hasattr(result, 'metadata'):
    print("\n" + "=" * 80)
    print("📋 Metadata")
    print("=" * 80)
    metadata = result.metadata[0] if isinstance(result.metadata, list) else result.metadata
    print(f"Tipo: {type(metadata).__name__}")
    if isinstance(metadata, dict):
        for key, value in metadata.items():
            print(f"  {key}: {value}")

print("\n" + "=" * 80)
print("✅ Análisis Completo")
print("=" * 80)
