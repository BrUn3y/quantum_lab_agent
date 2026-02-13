from beeai_framework.tools import Tool
from beeai_framework.tools.types import StringToolOutput, ToolRunOptions
from beeai_framework.emitter import Emitter
from beeai_framework.context import RunContext
from pydantic import BaseModel, Field
from qiskit_ibm_runtime import QiskitRuntimeService
from typing import Optional
import json

class QuantumJobInput(BaseModel):
    """Input schema for quantum job status and results"""
    job_id: str = Field(
        default="",
        description="ID del trabajo cuántico (ej: 'd671cklbujdc73cvbp30'). Si está vacío o es 'list', muestra todos los trabajos recientes del usuario."
    )
    filter_status: str = Field(
        default="all",
        description="Filtrar trabajos por estado: 'all' (todos), 'running' (en ejecución), 'queued' (en cola), 'done' (completados), 'error' (con error)"
    )

class IBMQuantumJobTool(Tool[QuantumJobInput]):
    """Tool for checking quantum job status and retrieving results."""
    
    @property
    def name(self) -> str:
        return "ibm_quantum_job"
    
    @property
    def description(self) -> str:
        return """
Consulta el estado y resultados de TUS trabajos cuánticos en IBM Quantum.

USAR ESTA HERRAMIENTA CUANDO:
✅ Usuario pregunta "¿cuáles son mis trabajos?"
✅ Usuario pregunta "muéstrame mis trabajos en ejecución"
✅ Usuario pregunta "lista mis trabajos cuánticos"
✅ Usuario pregunta "¿qué trabajos tengo en cola?"
✅ Usuario pregunta "muéstrame mis trabajos completados"
✅ Usuario proporciona un Job ID específico

NO USAR PARA:
❌ Consultar backends disponibles (usa ibm_quantum_status)
❌ Ver estado de computadoras cuánticas (usa ibm_quantum_status)
❌ Información de backends (usa ibm_quantum_info)

PARÁMETROS:
- job_id: Vacío o "list" para listar todos, o Job ID específico
- filter_status: "all", "running", "queued", "done", "error"

EJEMPLOS:
1. Listar todos los trabajos:
   {"job_id": "", "filter_status": "all"}

2. Solo trabajos en ejecución:
   {"job_id": "", "filter_status": "running"}

3. Solo trabajos en cola:
   {"job_id": "", "filter_status": "queued"}

4. Trabajo específico:
   {"job_id": "d673qqdbujdc73cvep1g", "filter_status": "all"}
"""
    
    @property
    def input_schema(self) -> type[QuantumJobInput]:
        return QuantumJobInput

    def _create_emitter(self) -> Emitter:
        """Creates and returns an emitter instance for the tool."""
        return Emitter()

    async def _run(
        self, 
        input: QuantumJobInput, 
        options: Optional[ToolRunOptions] = None, 
        context: Optional[RunContext] = None
    ) -> StringToolOutput:
        """Check quantum job status and retrieve results."""
        try:
            # Inicializa el servicio - usa la instancia guardada
            service = QiskitRuntimeService(channel="ibm_quantum_platform")
            
            if not input.job_id or input.job_id.lower() == "list":
                # Mostrar trabajos recientes con filtro
                return await self._list_recent_jobs(service, input.filter_status)
            
            # Obtener trabajo específico
            try:
                job = service.job(input.job_id)
            except Exception as e:
                return StringToolOutput(
                    result=f"❌ No se pudo encontrar el trabajo con ID '{input.job_id}'.\n\n"
                           f"Error: {str(e)}\n\n"
                           f"Verifica que el Job ID sea correcto o usa job_id vacío para ver todos tus trabajos."
                )
            
            # Construir reporte del trabajo
            result_text = f"# 📊 Estado del Trabajo Cuántico\n\n"
            result_text += f"**Job ID:** `{job.job_id()}`\n\n"
            
            # Información básica
            result_text += "## 📋 Información Básica\n\n"
            result_text += "| Propiedad | Valor |\n"
            result_text += "|-----------|-------|\n"
            
            # Backend
            backend_name = job.backend().name if hasattr(job, 'backend') else "N/A"
            result_text += f"| **Backend** | {backend_name} |\n"
            
            # Estado del trabajo
            status = job.status()
            status_emoji = {
                'QUEUED': '⏳',
                'RUNNING': '🔄',
                'COMPLETED': '✅',
                'DONE': '✅',
                'CANCELLED': '❌',
                'ERROR': '🔴'
            }
            status_name = str(status) if not hasattr(status, 'name') else status.name
            emoji = status_emoji.get(status_name, '❓')
            result_text += f"| **Estado** | {emoji} {status_name} |\n"
            
            # Tiempo de creación
            if hasattr(job, 'creation_date'):
                result_text += f"| **Creado** | {job.creation_date} |\n"
            
            # Tiempo en cola
            if hasattr(status, 'queue_position') and status.queue_position is not None:
                result_text += f"| **Posición en cola** | {status.queue_position} |\n"
            
            result_text += "\n"
            
            # Resultados (si están disponibles)
            if status_name in ['COMPLETED', 'DONE']:
                result_text += "## 🎯 Resultados\n\n"
                
                try:
                    result = job.result()
                    results_found = False
                    
                    # Método 1: SamplerV2 con BitArray - result._pub_results
                    if hasattr(result, '_pub_results') and result._pub_results:
                        try:
                            pub_result = result._pub_results[0]
                            
                            # Acceder a data.c que contiene el BitArray
                            if hasattr(pub_result, 'data') and hasattr(pub_result.data, 'c'):
                                bit_array = pub_result.data.c
                                
                                # Obtener conteos del BitArray
                                if hasattr(bit_array, 'get_counts'):
                                    counts = bit_array.get_counts()
                                    
                                    result_text += "### 📊 Resultados de Mediciones\n\n"
                                    result_text += "| Estado Cuántico | Conteo | Porcentaje |\n"
                                    result_text += "|-----------------|--------|------------|\n"
                                    
                                    total = sum(counts.values())
                                    for state, count in sorted(counts.items(), key=lambda x: x[1], reverse=True)[:15]:
                                        percentage = (count / total) * 100
                                        result_text += f"| `{state}` | {count:,} | {percentage:.2f}% |\n"
                                    
                                    result_text += f"\n**Total de mediciones:** {total:,}\n\n"
                                    results_found = True
                        except Exception as e:
                            result_text += f"⚠️ Error al procesar BitArray: {str(e)}\n\n"
                    
                    # Método 2: Formato antiguo - result.data
                    if not results_found and hasattr(result, 'data') and result.data:
                        try:
                            pub_result = result.data[0]
                            
                            # Buscar atributos de mediciones en PubResult
                            measurements = None
                            
                            # Intentar diferentes atributos comunes
                            for attr_name in ['meas', 'c', 'measurements', 'counts']:
                                if hasattr(pub_result, attr_name):
                                    measurements = getattr(pub_result, attr_name)
                                    if measurements is not None:
                                        break
                            
                            if measurements is not None:
                                result_text += "### 📊 Resultados de Mediciones\n\n"
                                result_text += "| Estado Cuántico | Conteo | Porcentaje |\n"
                                result_text += "|-----------------|--------|------------|\n"
                                
                                # Procesar los datos de mediciones
                                if hasattr(measurements, 'get_counts'):
                                    counts = measurements.get_counts()
                                elif isinstance(measurements, dict):
                                    counts = measurements
                                else:
                                    counts = {}
                                
                                if counts:
                                    total = sum(counts.values())
                                    for state, count in sorted(counts.items(), key=lambda x: x[1], reverse=True)[:15]:
                                        percentage = (count / total) * 100
                                        result_text += f"| `{state}` | {count:,} | {percentage:.2f}% |\n"
                                    
                                    result_text += f"\n**Total de mediciones:** {total:,}\n\n"
                                    results_found = True
                        except Exception as e:
                            result_text += f"⚠️ Error al procesar resultados: {str(e)}\n\n"
                    
                    # Método 3: quasi_dists (formato muy antiguo)
                    if not results_found and hasattr(result, 'quasi_dists') and result.quasi_dists:
                        result_text += "### 📊 Distribución de Probabilidades\n\n"
                        result_text += "| Estado Cuántico | Probabilidad | Conteo (aprox) |\n"
                        result_text += "|-----------------|--------------|----------------|\n"
                        
                        quasi_dist = result.quasi_dists[0]
                        total_shots = 4096
                        
                        for state, prob in sorted(quasi_dist.items(), key=lambda x: x[1], reverse=True)[:15]:
                            binary_state = bin(state)[2:].zfill(2)
                            count = int(prob * total_shots)
                            percentage = prob * 100
                            result_text += f"| `{binary_state}` | {percentage:.2f}% | ~{count} |\n"
                        
                        if len(quasi_dist) > 15:
                            result_text += f"\n*Mostrando 15 de {len(quasi_dist)} estados*\n"
                        
                        result_text += "\n"
                        results_found = True
                    
                    # Si aún no se encontraron resultados
                    if not results_found:
                        result_text += "⚠️ **Resultados de mediciones no disponibles en el formato esperado.**\n\n"
                        result_text += "El trabajo se completó exitosamente. Los resultados pueden requerir procesamiento adicional.\n\n"
                        
                        # Mostrar información de depuración
                        result_text += "**Información de depuración:**\n"
                        result_text += f"- Tipo de resultado: `{type(result).__name__}`\n"
                        if hasattr(result, 'data'):
                            result_text += f"- Tiene data: Sí ({len(result.data)} elementos)\n"
                            if result.data:
                                result_text += f"- Tipo de data[0]: `{type(result.data[0]).__name__}`\n"
                        result_text += "\n"
                    
                    # Información de ejecución
                    if hasattr(result, 'metadata') and result.metadata:
                        metadata = result.metadata[0] if isinstance(result.metadata, list) else result.metadata
                        
                        if isinstance(metadata, dict) and 'execution' in metadata:
                            exec_info = metadata['execution']
                            if hasattr(exec_info, 'execution_spans'):
                                result_text += "### ⏱️ Información de Ejecución\n\n"
                                spans = exec_info.execution_spans
                                if spans:
                                    span = spans[0]
                                    result_text += f"- **Inicio:** {span.start}\n"
                                    result_text += f"- **Fin:** {span.stop}\n"
                                    result_text += f"- **Shots ejecutados:** {span.size:,}\n\n"
                    
                    result_text += "✅ **Trabajo completado exitosamente**\n\n"
                    
                    if results_found:
                        result_text += "💡 **Interpretación:** Los estados cuánticos muestran la distribución de probabilidades de las mediciones.\n"
                        result_text += "Para un estado de Bell, esperarías ver principalmente `00` y `11` con probabilidades similares (~50% cada uno).\n\n"
                    else:
                        result_text += "💡 **Nota:** Para ver los resultados detallados, es posible que necesites usar la API de Qiskit directamente.\n\n"
                    
                except Exception as e:
                    result_text += f"⚠️ No se pudieron obtener los resultados detallados: {str(e)}\n\n"
            
            elif status_name == 'QUEUED':
                result_text += "⏳ **El trabajo está en cola esperando ejecución.**\n\n"
                if hasattr(status, 'queue_position'):
                    result_text += f"Posición en cola: {status.queue_position}\n"
                result_text += "Vuelve a consultar en unos minutos.\n\n"
            
            elif status_name == 'RUNNING':
                result_text += "🔄 **El trabajo se está ejecutando actualmente.**\n\n"
                result_text += "Los resultados estarán disponibles pronto.\n\n"
            
            elif status_name == 'CANCELLED':
                result_text += "❌ **El trabajo fue cancelado.**\n\n"
            
            elif status_name == 'ERROR':
                result_text += "🔴 **El trabajo terminó con error.**\n\n"
                if hasattr(status, 'error_message'):
                    result_text += f"**Error:** {status.error_message}\n\n"
            
            # Información adicional
            result_text += "---\n\n"
            result_text += "💡 **Tip:** Guarda el Job ID para consultar los resultados más tarde.\n"
            
            return StringToolOutput(result=result_text)
            
        except Exception as e:
            error_text = f"❌ Error al consultar el trabajo: {str(e)}\n\n"
            error_text += "Verifica que:\n"
            error_text += "- El Job ID sea correcto\n"
            error_text += "- Tu token de IBM Quantum sea válido\n"
            error_text += "- Tengas acceso al trabajo solicitado\n"
            return StringToolOutput(result=error_text)
    
    async def _list_recent_jobs(self, service: QiskitRuntimeService, filter_status: str = "all") -> StringToolOutput:
        """List recent jobs for the user with optional status filter."""
        try:
            # Obtener los últimos 20 trabajos para tener suficientes después del filtro
            jobs = service.jobs(limit=20)
            
            if not jobs:
                return StringToolOutput(
                    result="📭 No tienes trabajos recientes en IBM Quantum.\n\n"
                           "Ejecuta un circuito cuántico para crear tu primer trabajo."
                )
            
            # Filtrar trabajos según el estado solicitado
            filtered_jobs = []
            status_map = {
                'running': ['RUNNING'],
                'queued': ['QUEUED'],
                'done': ['DONE', 'COMPLETED'],
                'error': ['ERROR', 'CANCELLED']
            }
            
            for job in jobs:
                status = str(job.status())
                if filter_status == "all":
                    filtered_jobs.append(job)
                elif filter_status.lower() in status_map:
                    if status in status_map[filter_status.lower()]:
                        filtered_jobs.append(job)
            
            if not filtered_jobs:
                filter_msg = f" con estado '{filter_status}'" if filter_status != "all" else ""
                return StringToolOutput(
                    result=f"📭 No tienes trabajos{filter_msg} en IBM Quantum.\n\n"
                           "Ejecuta un circuito cuántico para crear tu primer trabajo."
                )
            
            # Título según el filtro
            if filter_status == "all":
                title = "# 📋 Todos Tus Trabajos Cuánticos\n\n"
            elif filter_status == "running":
                title = "# 🔄 Tus Trabajos en Ejecución\n\n"
            elif filter_status == "queued":
                title = "# ⏳ Tus Trabajos en Cola\n\n"
            elif filter_status == "done":
                title = "# ✅ Tus Trabajos Completados\n\n"
            elif filter_status == "error":
                title = "# 🔴 Tus Trabajos con Error\n\n"
            else:
                title = "# 📋 Tus Trabajos Cuánticos\n\n"
            
            result_text = title
            result_text += f"**Total encontrados:** {len(filtered_jobs)}\n\n"
            result_text += "| Job ID | Backend | Estado | Creado |\n"
            result_text += "|--------|---------|--------|--------|\n"
            
            status_emoji = {
                'QUEUED': '⏳',
                'RUNNING': '🔄',
                'COMPLETED': '✅',
                'DONE': '✅',
                'CANCELLED': '❌',
                'ERROR': '🔴'
            }
            
            for job in filtered_jobs[:10]:  # Mostrar máximo 10
                job_id = job.job_id()[:20] + "..."  # Truncar para la tabla
                backend = job.backend().name if hasattr(job, 'backend') else "N/A"
                status = job.status()
                status_name = str(status) if not hasattr(status, 'name') else status.name
                emoji = status_emoji.get(status_name, '❓')
                created = str(job.creation_date)[:16] if hasattr(job, 'creation_date') else "N/A"
                
                result_text += f"| `{job_id}` | {backend} | {emoji} {status_name} | {created} |\n"
            
            if len(filtered_jobs) > 10:
                result_text += f"\n*Mostrando 10 de {len(filtered_jobs)} trabajos*\n"
            
            result_text += "\n"
            result_text += "💡 **Para ver detalles de un trabajo específico**, proporciona el Job ID completo.\n"
            
            # Agregar sugerencias según el filtro
            if filter_status == "running" or filter_status == "queued":
                result_text += "⏱️ **Tip:** Estos trabajos aún están procesándose. Consulta más tarde para ver los resultados.\n"
            elif filter_status == "done":
                result_text += "✅ **Tip:** Usa el Job ID para ver los resultados detallados de cada trabajo.\n"
            
            return StringToolOutput(result=result_text)
            
        except Exception as e:
            return StringToolOutput(
                result=f"❌ Error al listar trabajos: {str(e)}"
            )

# Made with Bob
