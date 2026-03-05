"""
Quantum Job Comparison Tool - Compares results from multiple quantum jobs

This tool allows comparing results from 2 or more quantum jobs
to identify differences in probability distributions.
Generates PNG histograms saved in temporary files for inline visualization.
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

# Matplotlib with non-GUI backend
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

# Temporary directory for quantum PNGs (shared with Status Agent)
QUANTUM_PNG_DIR = os.path.join(tempfile.gettempdir(), "quantum_lab_pngs")
os.makedirs(QUANTUM_PNG_DIR, exist_ok=True)


class QuantumJobComparisonInput(BaseModel):
    """Input schema for quantum job comparison"""
    job_ids: List[str] = Field(
        description="List of Job IDs to compare (minimum 2, maximum 5). Example: ['d6cd297g4t5c7385dh4g', 'd6cd2bknsg9c739a32p0']"
    )


def _save_comparison_png(jobs_data: List[Dict], name: str) -> Optional[str]:
    """
    Generates a comparative histogram and saves it to a temporary file.
    Returns the PNG file path or None if it fails.
    """
    try:
        valid_jobs = [j for j in jobs_data if j.get('counts')]
        if not valid_jobs:
            return None

        # Get all unique states
        all_states = set()
        for job_data in valid_jobs:
            all_states.update(job_data['counts'].keys())
        all_states = sorted(all_states)

        n_jobs = len(valid_jobs)
        n_states = len(all_states)

        # Colors for each job
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']

        # Create figure
        fig, ax = plt.subplots(figsize=(max(10, n_states * 1.2), 6))
        fig.patch.set_facecolor('#0d1117')
        ax.set_facecolor('#161b22')

        # Bar positions
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

            # Value labels on tall bars
            for bar, pct in zip(bars, percentages):
                if pct > 3:
                    ax.text(
                        bar.get_x() + bar.get_width() / 2,
                        bar.get_height() + 0.3,
                        f'{pct:.1f}%',
                        ha='center', va='bottom',
                        fontsize=7, color='white', fontweight='bold'
                    )

        # Chart style
        ax.set_xlabel('Quantum State', color='white', fontsize=12)
        ax.set_ylabel('Percentage (%)', color='white', fontsize=12)
        ax.set_title('📊 Quantum Job Results Comparison', color='white', fontsize=14, pad=15)
        ax.set_xticks(x)
        ax.set_xticklabels(all_states, color='white', fontsize=10, fontfamily='monospace')
        ax.tick_params(colors='white')
        ax.spines['bottom'].set_color('#30363d')
        ax.spines['left'].set_color('#30363d')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.yaxis.grid(True, alpha=0.2, color='#30363d')
        ax.set_axisbelow(True)

        # Legend
        ax.legend(
            loc='upper right',
            facecolor='#21262d',
            edgecolor='#30363d',
            labelcolor='white',
            fontsize=9
        )

        plt.tight_layout()

        # Save to temporary file
        png_path = os.path.join(QUANTUM_PNG_DIR, f"{name}.png")
        plt.savefig(png_path, format='png', dpi=120, bbox_inches='tight',
                    facecolor=fig.get_facecolor())
        plt.close(fig)
        print(f"[ComparisonTool] PNG saved: {png_path}")
        return png_path

    except Exception as e:
        print(f"[ComparisonTool] Error generating PNG: {e}")
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
Compares results from multiple quantum jobs on IBM Quantum.

USE THIS TOOL WHEN:
✅ User says "compare the results of jobs X, Y, Z"
✅ User says "compare these jobs: [list of IDs]"
✅ User asks "what is the difference between these jobs?"
✅ User wants to see results side by side

PARAMETERS:
- job_ids: List of 2 to 5 Job IDs to compare

EXAMPLE:
{"job_ids": ["d6cd297g4t5c7385dh4g", "d6cd2bknsg9c739a32p0", "d6cd2e7g4t5c7385dhag"]}

OUTPUT:
- Comparative table with results from each job
- Difference analysis
- Identification of common patterns
- Comparative PNG histogram
"""
    
    @property
    def input_schema(self) -> type[QuantumJobComparisonInput]:
        return QuantumJobComparisonInput

    def _create_emitter(self) -> Emitter:
        """Creates and returns an emitter instance for the tool."""
        return Emitter()

    def _extract_counts_from_job(self, job) -> Optional[Dict[str, int]]:
        """
        Extracts measurement counts from a quantum job.
        Handles different Qiskit result formats.
        """
        try:
            result = job.result()
            
            # Method 1: SamplerV2 with BitArray - result._pub_results
            if hasattr(result, '_pub_results') and result._pub_results:
                try:
                    pub_result = result._pub_results[0]
                    if hasattr(pub_result, 'data') and hasattr(pub_result.data, 'c'):
                        bit_array = pub_result.data.c
                        if hasattr(bit_array, 'get_counts'):
                            return bit_array.get_counts()
                except Exception:
                    pass
            
            # Method 2: Old format - result.data
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
            
            # Method 3: quasi_dists (very old format)
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
            # Validate number of jobs
            if len(input.job_ids) < 2:
                return StringToolOutput(
                    result="❌ At least 2 Job IDs are needed for comparison.\n\n"
                           "Example: {\"job_ids\": [\"job1\", \"job2\"]}"
                )
            
            if len(input.job_ids) > 5:
                return StringToolOutput(
                    result="❌ Maximum 5 Job IDs allowed for comparison.\n\n"
                           "Reduce the list to 5 jobs or less."
                )
            
            # Initialize service
            service = QiskitRuntimeService(channel="ibm_quantum_platform")
            
            # Collect information for each job separately
            jobs_data = []
            for job_id in input.job_ids:
                job_id = job_id.strip()
                try:
                    job = service.job(job_id)
                    status = job.status()
                    status_name = str(status) if not hasattr(status, 'name') else status.name
                    
                    # Only process completed jobs
                    if status_name not in ['COMPLETED', 'DONE']:
                        jobs_data.append({
                            'job_id': job_id,
                            'status': status_name,
                            'backend': job.backend().name if hasattr(job, 'backend') else "N/A",
                            'counts': None,
                            'error': f"Job not completed (status: {status_name})"
                        })
                        continue
                    
                    # Extract counts from THIS specific job
                    counts = self._extract_counts_from_job(job)
                    
                    jobs_data.append({
                        'job_id': job_id,
                        'status': status_name,
                        'backend': job.backend().name if hasattr(job, 'backend') else "N/A",
                        'counts': counts,
                        'error': None if counts else "Could not extract results"
                    })
                    
                except Exception as e:
                    jobs_data.append({
                        'job_id': job_id,
                        'status': 'ERROR',
                        'backend': 'N/A',
                        'counts': None,
                        'error': str(e)
                    })
            
            # Build comparison report
            result_text = "# 📊 Quantum Job Comparison\n\n"
            result_text += f"**Jobs compared:** {len(input.job_ids)}\n\n"
            
            # Basic information table
            result_text += "## 📋 Job Information\n\n"
            result_text += "| # | Job ID | Backend | Status |\n"
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
            
            # Check if there are jobs with errors
            jobs_with_errors = [j for j in jobs_data if j['error']]
            if jobs_with_errors:
                result_text += "## ⚠️ Warnings\n\n"
                for job_data in jobs_with_errors:
                    result_text += f"- **`{job_data['job_id']}`**: {job_data['error']}\n"
                result_text += "\n"
            
            # Compare results only for completed jobs with data
            valid_jobs = [j for j in jobs_data if j['counts'] is not None]
            
            if len(valid_jobs) < 2:
                result_text += "❌ **Not enough completed jobs with results to compare.**\n\n"
                result_text += "At least 2 jobs in DONE/COMPLETED status with available results are needed.\n"
                return StringToolOutput(result=result_text)
            
            # Table of individual results per job
            result_text += "## 🎯 Results by Job\n\n"
            
            for i, job_data in enumerate(valid_jobs, 1):
                result_text += f"### Job {i}: `{job_data['job_id']}`\n\n"
                result_text += "| Quantum State | Count | Percentage |\n"
                result_text += "|-----------------|--------|------------|\n"
                
                counts = job_data['counts']
                total = sum(counts.values())
                
                # Sort by count descending
                for state in sorted(counts.keys(), key=lambda x: counts[x], reverse=True)[:10]:
                    count = counts[state]
                    percentage = (count / total) * 100
                    result_text += f"| `{state}` | {count:,} | {percentage:.2f}% |\n"
                
                result_text += f"\n**Total measurements:** {total:,}\n\n"
            
            # Difference analysis
            result_text += "## 🔍 Difference Analysis\n\n"
            
            # Compare the most probable states
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
                result_text += "### Most probable states per job:\n\n"
                for i, ts in enumerate(top_states, 1):
                    result_text += f"- **Job {i} (`{ts['job_id']}`)**: State `{ts['state']}` with {ts['percentage']:.2f}% ({ts['count']:,} measurements)\n"
                result_text += "\n"
                
                # Check if all have the same dominant state
                unique_top_states = set(ts['state'] for ts in top_states)
                if len(unique_top_states) == 1:
                    result_text += "✅ **All jobs have the same dominant state**, indicating consistent results.\n\n"
                else:
                    result_text += "⚠️ **The jobs have different dominant states**, which may indicate:\n"
                    result_text += "- Different quantum circuits executed\n"
                    result_text += "- Variability due to quantum noise\n"
                    result_text += "- Different backends with distinct characteristics\n\n"
            
            # Generate comparative PNG and save to temporary file
            png_name = f"comparison_{input.job_ids[0][:8]}_{uuid.uuid4().hex[:8]}"
            png_path = _save_comparison_png(valid_jobs, png_name)
            if png_path:
                result_text += f"\n__QUANTUM_PNG__{png_path}__END_PNG__\n"
            
            # Conclusion
            result_text += "---\n\n"
            result_text += "💡 **Tip:** For more detailed analysis, consult each Job ID individually.\n"
            
            return StringToolOutput(result=result_text)
            
        except Exception as e:
            error_text = f"❌ Error comparing jobs: {str(e)}\n\n"
            error_text += "Verify that:\n"
            error_text += "- The Job IDs are correct\n"
            error_text += "- Your IBM Quantum token is valid\n"
            error_text += "- You have access to the requested jobs\n"
            return StringToolOutput(result=error_text)

# Made with Bob
