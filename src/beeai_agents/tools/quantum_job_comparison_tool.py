"""
Quantum Job Comparison Tool - Compara resultados de múltiples trabajos cuánticos

Esta herramienta permite comparar los resultados de 2 o más trabajos cuánticos
para identificar diferencias en las distribuciones de probabilidad.
Genera histogramas PNG guardados en archivos temporales para visualización inline.
"""

from beeai_framework.tools import Tool
from beeai_framework.tools.types import StringToolOutput, ToolRunOptions
from beeai_framework.emitter import Emitter
from beeai_framework.context import RunContext
from pydantic import BaseModel, Field
from qiskit_ibm_runtime import QiskitRuntimeService
from typing import Optional, List, Dict
import io
import os
import tempfile
import uuid

# Matplotlib con backend no-GUI
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

# Directorio temporal para PNGs cuánticos (compartido con el Status Agent)
QUANTUM_PNG_DIR = os.path.join(tempfile.gettempdir(), "quantum_lab_pngs")
os.makedirs(QUANTUM_PNG_DIR, exist_ok=True)


class QuantumJobComparisonInput(BaseModel):
    """Input schema for quantum job comparison"""
    job_ids: List[str] = Field(
        description="Lista de Job IDs a comparar (mínimo 2, máximo 5). Ejemplo: ['d6cd297g4t5c7385dh4g', 'd6cd2bknsg9c739a32p0']"
    )


def _save_comparison_png(jobs_data: List[Dict], name: str) -> Optional[str]:
    """
    Genera un histograma comparativo y lo guarda en un archivo temporal.
    Retorna la ruta del archivo PNG o None si falla.
    """
    try:
        valid_jobs = [j for j in jobs_data if j.get('counts')]
        if not valid_jobs:
            return None

        # Obtener todos los estados únicos
        all_states = set()
        for job_data in valid_jobs:
            all_states.update(job_data['counts'].keys())
        all_states = sorted(all_states)

        n_jobs = len(valid_jobs)
        n_states = len(all_states)

        # Colores para cada job
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']

        # Crear figura
        fig, ax = plt.subplots(figsize=(max(10, n_states * 1.2), 6))
        fig.patch.set_facecolor('#0d1117')
        ax.set_facecolor('#161b22')

        # Posiciones de las barras
        x = np.arange(n_states)
        width = 0.8 / n_jobs

        for i, job_data in enumerate(valid_jobs):
            counts = job_data['counts']
            total = sum(counts.values())
            percentages = [(counts.get(state, 0) / total) * 100 for state in all_states]

            offset = (i - n_jobs / 2 + 0.5) * width
            bars = ax.bar(
                x + offset,
                percentages,
                width,
                label=f"Job {i+1}: ...{job_data['job_id'][-12:]}",
                color=colors[i % len(colors)],
                alpha=0.85,
                edgecolor='white',
                linewidth=0.5
            )

            # Etiquetas de valor en barras altas
            for bar, pct in zip(bars, percentages):
                if pct > 3:
                    ax.text(
                        bar.get_x() + bar.get_width() / 2,
                        bar.get_height() + 0.3,
                        f'{pct:.1f}%',
                        ha='center', va='bottom',
                        fontsize=7, color='white', fontweight='bold'
                    )

        # Estilo del gráfico
        ax.set_xlabel('Estado Cuántico', color='white', fontsize=12)
        ax.set_ylabel('Porcentaje (%)', color='white', fontsize=12)
        ax.set_title('📊 Comparación de Resultados de Trabajos Cuánticos', color='white', fontsize=14, pad=15)
        ax.set_xticks(x)
        ax.set_xticklabels(all_states, color='white', fontsize=10, fontfamily='monospace')
        ax.tick_params(colors='white')
        ax.spines['bottom'].set_color('#30363d')
        ax.spines['left'].set_color('#30363d')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.yaxis.grid(True, alpha=0.2, color='#30363d')
        ax.set_axisbelow(True)

        # Leyenda
        ax.legend(
            loc='upper right',
            facecolor='#21262d',
            edgecolor='#30363d',
            labelcolor='white',
            fontsize=9
        )

        plt.tight_layout()

        # Guardar en archivo temporal
        png_path = os.path.join(QUANTUM_PNG_DIR, f"{name}.png")
        plt.savefig(png_path, format='png', dpi=120, bbox_inches='tight',
                    facecolor=fig.get_facecolor())
        plt.close(fig)
        print(f"[ComparisonTool] PNG guardado: {png_path}")
        return png_path

    except Exception as e:
        print(f"[ComparisonTool] Error generando PNG: {e}")
        try:
            plt.close('all')
        except Exception:
            pass
        return None


class IBMQuantumJobComparisonTool(Tool[QuantumJobComparisonInput]):
    """Tool for comparing results from multiple quantum jobs."""
    
    @property
    def name(self) -> str:
        return "ibm_quantum_job_comparison"
    
    @property
    def description(self) -> str:
        return """
Compara los resultados de múltiples trabajos cuánticos en IBM Quantum.

USAR ESTA HERRAMIENTA CUANDO:
✅ Usuario dice "compara los resultados de los jobs X, Y, Z"
✅ Usuario dice "compara estos trabajos: [lista de IDs]"
✅ Usuario pregunta "¿cuál es la diferencia entre estos jobs?"
✅ Usuario quiere ver resultados lado a lado

PARÁMETROS:
- job_ids: Lista de 2 a 5 Job IDs para comparar

EJEMPLO:
{"job_ids": ["d6cd297g4t5c7385dh4g", "d6cd2bknsg9c739a32p0", "d6cd2e7g4t5c7385dhag"]}

SALIDA:
- Tabla comparativa con resultados de cada job
- Análisis de diferencias
- Identificación de patrones comunes
- Histograma PNG comparativo
"""
    
    @property
    def input_schema(self) -> type[QuantumJobComparisonInput]:
        return QuantumJobComparisonInput

    def _create_emitter(self) -> Emitter:
        """Creates and returns an emitter instance for the tool."""
        return Emitter()

    def _extract_counts_from_job(self, job) -> Optional[Dict[str, int]]:
        """
        Extrae los conteos de mediciones de un trabajo cuántico.
        Maneja diferentes formatos de resultados de Qiskit.
        """
        try:
            result = job.result()
            
            # Método 1: SamplerV2 con BitArray - result._pub_results
            if hasattr(result, '_pub_results') and result._pub_results:
                try:
                    pub_result = result._pub_results[0]
                    if hasattr(pub_result, 'data') and hasattr(pub_result.data, 'c'):
                        bit_array = pub_result.data.c
                        if hasattr(bit_array, 'get_counts'):
                            return bit_array.get_counts()
                except Exception:
                    pass
            
            # Método 2: Formato antiguo - result.data
            if hasattr(result, 'data') and result.data:
                try:
                    pub_result = result.data[0]
                    for attr_name in ['meas', 'c', 'measurements', 'counts']:
                        if hasattr(pub_result, attr_name):
                            measurements = getattr(pub_result, attr_name)
                            if measurements is not None:
                                if hasattr(measurements, 'get_counts'):
                                    return measurements.get_counts()
                                elif isinstance(measurements, dict):
                                    return measurements
                except Exception:
                    pass
            
            # Método 3: quasi_dists (formato muy antiguo)
            if hasattr(result, 'quasi_dists') and result.quasi_dists:
                quasi_dist = result.quasi_dists[0]
                total_shots = 4096
                counts = {}
                for state, prob in quasi_dist.items():
                    binary_state = bin(state)[2:].zfill(2)
                    counts[binary_state] = int(prob * total_shots)
                return counts
            
            return None
            
        except Exception as e:
            print(f"Error extracting counts: {str(e)}")
            return None

    async def _run(
        self, 
        input: QuantumJobComparisonInput, 
        options: Optional[ToolRunOptions] = None, 
        context: Optional[RunContext] = None
    ) -> StringToolOutput:
        """Compare results from multiple quantum jobs."""
        try:
            # Validar número de jobs
            if len(input.job_ids) < 2:
                return StringToolOutput(
                    result="❌ Se necesitan al menos 2 Job IDs para comparar.\n\n"
                           "Ejemplo: {\"job_ids\": [\"job1\", \"job2\"]}"
                )
            
            if len(input.job_ids) > 5:
                return StringToolOutput(
                    result="❌ Máximo 5 Job IDs permitidos para comparación.\n\n"
                           "Reduce la lista a 5 trabajos o menos."
                )
            
            # Inicializar servicio
            service = QiskitRuntimeService(channel="ibm_quantum_platform")
            
            # Recopilar información de cada job por separado
            jobs_data = []
            for job_id in input.job_ids:
                job_id = job_id.strip()
                try:
                    job = service.job(job_id)
                    status = job.status()
                    status_name = str(status) if not hasattr(status, 'name') else status.name
                    
                    # Solo procesar jobs completados
                    if status_name not in ['COMPLETED', 'DONE']:
                        jobs_data.append({
                            'job_id': job_id,
                            'status': status_name,
                            'backend': job.backend().name if hasattr(job, 'backend') else "N/A",
                            'counts': None,
                            'error': f"Job no completado (estado: {status_name})"
                        })
                        continue
                    
                    # Extraer conteos de ESTE job específico
                    counts = self._extract_counts_from_job(job)
                    
                    jobs_data.append({
                        'job_id': job_id,
                        'status': status_name,
                        'backend': job.backend().name if hasattr(job, 'backend') else "N/A",
                        'counts': counts,
                        'error': None if counts else "No se pudieron extraer resultados"
                    })
                    
                except Exception as e:
                    jobs_data.append({
                        'job_id': job_id,
                        'status': 'ERROR',
                        'backend': 'N/A',
                        'counts': None,
                        'error': str(e)
                    })
            
            # Construir reporte de comparación
            result_text = "# 📊 Comparación de Trabajos Cuánticos\n\n"
            result_text += f"**Trabajos comparados:** {len(input.job_ids)}\n\n"
            
            # Tabla de información básica
            result_text += "## 📋 Información de Trabajos\n\n"
            result_text += "| # | Job ID | Backend | Estado |\n"
            result_text += "|---|--------|---------|--------|\n"
            
            for i, job_data in enumerate(jobs_data, 1):
                status_emoji = {
                    'COMPLETED': '✅',
                    'DONE': '✅',
                    'ERROR': '🔴',
                    'QUEUED': '⏳',
                    'RUNNING': '🔄'
                }
                emoji = status_emoji.get(job_data['status'], '❓')
                result_text += f"| {i} | `{job_data['job_id']}` | {job_data['backend']} | {emoji} {job_data['status']} |\n"
            
            result_text += "\n"
            
            # Verificar si hay jobs con errores
            jobs_with_errors = [j for j in jobs_data if j['error']]
            if jobs_with_errors:
                result_text += "## ⚠️ Advertencias\n\n"
                for job_data in jobs_with_errors:
                    result_text += f"- **`{job_data['job_id']}`**: {job_data['error']}\n"
                result_text += "\n"
            
            # Comparar resultados solo de jobs completados con datos
            valid_jobs = [j for j in jobs_data if j['counts'] is not None]
            
            if len(valid_jobs) < 2:
                result_text += "❌ **No hay suficientes trabajos completados con resultados para comparar.**\n\n"
                result_text += "Se necesitan al menos 2 trabajos en estado DONE/COMPLETED con resultados disponibles.\n"
                return StringToolOutput(result=result_text)
            
            # Tabla de resultados individuales por job
            result_text += "## 🎯 Resultados por Trabajo\n\n"
            
            for i, job_data in enumerate(valid_jobs, 1):
                result_text += f"### Job {i}: `{job_data['job_id']}`\n\n"
                result_text += "| Estado Cuántico | Conteo | Porcentaje |\n"
                result_text += "|-----------------|--------|------------|\n"
                
                counts = job_data['counts']
                total = sum(counts.values())
                
                # Ordenar por conteo descendente
                for state in sorted(counts.keys(), key=lambda x: counts[x], reverse=True)[:10]:
                    count = counts[state]
                    percentage = (count / total) * 100
                    result_text += f"| `{state}` | {count:,} | {percentage:.2f}% |\n"
                
                result_text += f"\n**Total de mediciones:** {total:,}\n\n"
            
            # Análisis de diferencias
            result_text += "## 🔍 Análisis de Diferencias\n\n"
            
            # Comparar los estados más probables
            top_states = []
            for job_data in valid_jobs:
                counts = job_data['counts']
                if counts:
                    top_state = max(counts.items(), key=lambda x: x[1])
                    total = sum(counts.values())
                    top_states.append({
                        'job_id': job_data['job_id'],
                        'state': top_state[0],
                        'count': top_state[1],
                        'percentage': (top_state[1] / total) * 100
                    })
            
            if top_states:
                result_text += "### Estados más probables por trabajo:\n\n"
                for i, ts in enumerate(top_states, 1):
                    result_text += f"- **Job {i} (`{ts['job_id']}`)**: Estado `{ts['state']}` con {ts['percentage']:.2f}% ({ts['count']:,} mediciones)\n"
                result_text += "\n"
                
                # Verificar si todos tienen el mismo estado dominante
                unique_top_states = set(ts['state'] for ts in top_states)
                if len(unique_top_states) == 1:
                    result_text += "✅ **Todos los trabajos tienen el mismo estado dominante**, lo que indica resultados consistentes.\n\n"
                else:
                    result_text += "⚠️ **Los trabajos tienen diferentes estados dominantes**, lo que puede indicar:\n"
                    result_text += "- Diferentes circuitos cuánticos ejecutados\n"
                    result_text += "- Variabilidad por ruido cuántico\n"
                    result_text += "- Diferentes backends con características distintas\n\n"
            
            # Generar PNG comparativo y guardar en archivo temporal
            png_name = f"comparison_{input.job_ids[0][:8]}_{uuid.uuid4().hex[:8]}"
            png_path = _save_comparison_png(valid_jobs, png_name)
            if png_path:
                result_text += f"\n__QUANTUM_PNG__{png_path}__END_PNG__\n"
            
            # Conclusión
            result_text += "---\n\n"
            result_text += "💡 **Tip:** Para análisis más detallado, consulta cada Job ID individualmente.\n"
            
            return StringToolOutput(result=result_text)
            
        except Exception as e:
            error_text = f"❌ Error al comparar trabajos: {str(e)}\n\n"
            error_text += "Verifica que:\n"
            error_text += "- Los Job IDs sean correctos\n"
            error_text += "- Tu token de IBM Quantum sea válido\n"
            error_text += "- Tengas acceso a los trabajos solicitados\n"
            return StringToolOutput(result=error_text)

# Made with Bob
