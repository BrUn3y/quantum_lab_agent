from beeai_framework.tools import Tool
from beeai_framework.tools.types import StringToolOutput, ToolRunOptions
from beeai_framework.emitter import Emitter
from beeai_framework.context import RunContext
from pydantic import BaseModel, Field
from qiskit_ibm_runtime import QiskitRuntimeService
from typing import Optional
import json
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


def _save_job_histogram_png(counts: dict, job_id: str) -> Optional[str]:
    """
    Generates a PNG histogram of quantum job results
    and saves it to a temporary file.
    Returns the PNG file path or None if it fails.
    """
    try:
        if not counts:
            return None

        # Sort states by descending count (maximum 20 states)
        sorted_items = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:20]
        states = [item[0] for item in sorted_items]
        values = [item[1] for item in sorted_items]
        total = sum(counts.values())
        percentages = [(v / total) * 100 for v in values]

        # Create figure
        fig, ax = plt.subplots(figsize=(max(8, len(states) * 0.9), 5))
        fig.patch.set_facecolor('#0d1117')
        ax.set_facecolor('#161b22')

        # Gradient colors by probability (dark blue to light blue)
        cmap = plt.get_cmap('Blues')
        max_pct = max(percentages) if percentages else 1
        bar_colors = [cmap(0.4 + 0.6 * (p / max_pct)) for p in percentages]

        bars = ax.bar(
            range(len(states)),
            percentages,
            color=bar_colors,
            edgecolor='#30363d',
            linewidth=0.8
        )

        # Value labels on bars
        for bar, pct in zip(bars, percentages):
            if pct > 1:
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + 0.3,
                    f'{pct:.1f}%',
                    ha='center', va='bottom',
                    fontsize=8, color='white', fontweight='bold'
                )

        # Style
        ax.set_xlabel('Quantum State', color='white', fontsize=11)
        ax.set_ylabel('Percentage (%)', color='white', fontsize=11)
        short_id = f"...{job_id[-16:]}" if len(job_id) > 16 else job_id
        ax.set_title(f'📊 Job Results: {short_id}', color='white', fontsize=13, pad=12)
        ax.set_xticks(range(len(states)))
        ax.set_xticklabels(states, color='white', fontsize=9, fontfamily='monospace')
        ax.tick_params(colors='white')
        ax.spines['bottom'].set_color('#30363d')
        ax.spines['left'].set_color('#30363d')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.yaxis.grid(True, alpha=0.2, color='#30363d')
        ax.set_axisbelow(True)

        # Total note
        ax.text(
            0.99, 0.97,
            f'Total: {total:,} shots',
            transform=ax.transAxes,
            ha='right', va='top',
            fontsize=9, color='#8b949e'
        )

        plt.tight_layout()

        # Save to temporary file
        png_name = f"job_{job_id[:8]}_{uuid.uuid4().hex[:8]}"
        png_path = os.path.join(QUANTUM_PNG_DIR, f"{png_name}.png")
        plt.savefig(png_path, format='png', dpi=120, bbox_inches='tight',
                    facecolor=fig.get_facecolor())
        plt.close(fig)
        print(f"[JobTool] PNG saved: {png_path}")
        return png_path

    except Exception as e:
        print(f"[JobTool] Error generating PNG: {e}")
        try:
            plt.close('all')
        except Exception:
            pass
        return None


class QuantumJobInput(BaseModel):
    """Input schema for quantum job status and results"""
    job_id: str = Field(
        default="",
        description="Quantum job ID (e.g., 'd671cklbujdc73cvbp30'). If empty or 'list', shows all user's recent jobs."
    )
    filter_status: str = Field(
        default="all",
        description="Filter jobs by status: 'all' (all), 'running' (running), 'queued' (queued), 'done' (completed), 'error' (with error)"
    )

class IBMQuantumJobTool(Tool[QuantumJobInput]):
    """Tool for checking quantum job status and retrieving results."""
    
    @property
    def name(self) -> str:
        return "ibm_quantum_job"
    
    @property
    def description(self) -> str:
        return """
Queries the status and results of YOUR quantum jobs on IBM Quantum.

USE THIS TOOL WHEN:
✅ User asks "what are my jobs?"
✅ User asks "show me my running jobs"
✅ User asks "list my quantum jobs"
✅ User asks "what jobs do I have in queue?"
✅ User asks "show me my completed jobs"
✅ User provides a specific Job ID

DO NOT USE FOR:
❌ Query available backends (use ibm_quantum_status)
❌ View quantum computer status (use ibm_quantum_status)
❌ Backend information (use ibm_quantum_info)

PARAMETERS:
- job_id: Empty or "list" to list all, or specific Job ID
- filter_status: "all", "running", "queued", "done", "error"

EXAMPLES:
1. List all jobs:
   {"job_id": "", "filter_status": "all"}

2. Only running jobs:
   {"job_id": "", "filter_status": "running"}

3. Only queued jobs:
   {"job_id": "", "filter_status": "queued"}

4. Specific job:
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
            # Initialize service - uses saved instance
            service = QiskitRuntimeService(channel="ibm_quantum_platform")
            
            if not input.job_id or input.job_id.lower() == "list":
                # Show recent jobs with filter
                return await self._list_recent_jobs(service, input.filter_status)
            
            # Get specific job
            try:
                job = service.job(input.job_id)
            except Exception as e:
                return StringToolOutput(
                    result=f"❌ Could not find job with ID '{input.job_id}'.\n\n"
                           f"Error: {str(e)}\n\n"
                           f"Verify that the Job ID is correct or use empty job_id to see all your jobs."
                )
            
            # Build job report
            result_text = f"# 📊 Quantum Job Status\n\n"
            result_text += f"**Job ID:** `{job.job_id()}`\n\n"
            
            # Basic information
            result_text += "## 📋 Basic Information\n\n"
            result_text += "| Property | Value |\n"
            result_text += "|----------|-------|\n"
            
            # Backend
            backend_name = job.backend().name if hasattr(job, 'backend') else "N/A"
            result_text += f"| **Backend** | {backend_name} |\n"
            job_tags = getattr(job, "tags", None) or []
            if job_tags:
                result_text += f"| **Tags** | {', '.join(f'`{tag}`' for tag in job_tags)} |\n"
            
            # Job status
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
            result_text += f"| **Status** | {emoji} {status_name} |\n"
            
            # Creation time
            if hasattr(job, 'creation_date'):
                result_text += f"| **Created** | {job.creation_date} |\n"
            
            # Queue time
            if hasattr(status, 'queue_position') and status.queue_position is not None:
                result_text += f"| **Queue position** | {status.queue_position} |\n"
            
            result_text += "\n"
            
            # Results (if available)
            if status_name in ['COMPLETED', 'DONE']:
                result_text += "## 🎯 Results\n\n"
                
                # Variable to save counts and generate PNG later
                final_counts = None
                
                try:
                    result = job.result()
                    results_found = False
                    
                    # Method 1: SamplerV2 with BitArray - result._pub_results
                    if hasattr(result, '_pub_results') and result._pub_results:
                        try:
                            pub_result = result._pub_results[0]
                            
                            # Access data.c which contains the BitArray
                            if hasattr(pub_result, 'data') and hasattr(pub_result.data, 'c'):
                                bit_array = pub_result.data.c
                                
                                # Get counts from BitArray
                                if hasattr(bit_array, 'get_counts'):
                                    counts = bit_array.get_counts()
                                    
                                    result_text += "### 📊 Measurement Results\n\n"
                                    result_text += "| Quantum State | Count | Percentage |\n"
                                    result_text += "|---------------|-------|------------|\n"
                                    
                                    total = sum(counts.values())
                                    for state, count in sorted(counts.items(), key=lambda x: x[1], reverse=True)[:15]:
                                        percentage = (count / total) * 100
                                        result_text += f"| `{state}` | {count:,} | {percentage:.2f}% |\n"
                                    
                                    result_text += f"\n**Total measurements:** {total:,}\n\n"
                                    results_found = True
                                    final_counts = counts
                        except Exception as e:
                            result_text += f"⚠️ Error processing BitArray: {str(e)}\n\n"
                    
                    # Method 2: Old format - result.data
                    if not results_found and hasattr(result, 'data') and result.data:
                        try:
                            pub_result = result.data[0]
                            
                            # Search for measurement attributes in PubResult
                            measurements = None
                            
                            # Try different common attributes
                            for attr_name in ['meas', 'c', 'measurements', 'counts']:
                                if hasattr(pub_result, attr_name):
                                    measurements = getattr(pub_result, attr_name)
                                    if measurements is not None:
                                        break
                            
                            if measurements is not None:
                                result_text += "### 📊 Measurement Results\n\n"
                                result_text += "| Quantum State | Count | Percentage |\n"
                                result_text += "|---------------|-------|------------|\n"
                                
                                # Process measurement data
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
                                    
                                    result_text += f"\n**Total measurements:** {total:,}\n\n"
                                    results_found = True
                                    final_counts = counts
                        except Exception as e:
                            result_text += f"⚠️ Error processing results: {str(e)}\n\n"
                    
                    # Method 3: quasi_dists (very old format)
                    if not results_found and hasattr(result, 'quasi_dists') and result.quasi_dists:
                        result_text += "### 📊 Probability Distribution\n\n"
                        result_text += "| Quantum State | Probability | Count (approx) |\n"
                        result_text += "|---------------|-------------|----------------|\n"
                        
                        quasi_dist = result.quasi_dists[0]
                        total_shots = 4096
                        quasi_counts = {}
                        
                        for state, prob in sorted(quasi_dist.items(), key=lambda x: x[1], reverse=True)[:15]:
                            binary_state = bin(state)[2:].zfill(2)
                            count = int(prob * total_shots)
                            percentage = prob * 100
                            result_text += f"| `{binary_state}` | {percentage:.2f}% | ~{count} |\n"
                            quasi_counts[binary_state] = count
                        
                        if len(quasi_dist) > 15:
                            result_text += f"\n*Showing 15 of {len(quasi_dist)} states*\n"
                        
                        result_text += "\n"
                        results_found = True
                        final_counts = quasi_counts
                    
                    # If results still not found
                    if not results_found:
                        result_text += "⚠️ **Measurement results not available in expected format.**\n\n"
                        result_text += "Job completed successfully. Results may require additional processing.\n\n"
                        
                        # Show debug information
                        result_text += "**Debug information:**\n"
                        result_text += f"- Result type: `{type(result).__name__}`\n"
                        if hasattr(result, 'data'):
                            result_text += f"- Has data: Yes ({len(result.data)} elements)\n"
                            if result.data:
                                result_text += f"- Type of data[0]: `{type(result.data[0]).__name__}`\n"
                        result_text += "\n"
                    
                    # Execution information
                    if hasattr(result, 'metadata') and result.metadata:
                        metadata = result.metadata[0] if isinstance(result.metadata, list) else result.metadata
                        
                        if isinstance(metadata, dict) and 'execution' in metadata:
                            exec_info = metadata['execution']
                            if hasattr(exec_info, 'execution_spans'):
                                result_text += "### ⏱️ Execution Information\n\n"
                                spans = exec_info.execution_spans
                                if spans:
                                    span = spans[0]
                                    result_text += f"- **Start:** {span.start}\n"
                                    result_text += f"- **End:** {span.stop}\n"
                                    result_text += f"- **Shots executed:** {span.size:,}\n\n"
                    
                    result_text += "✅ **Job completed successfully**\n\n"
                    
                    if not results_found:
                        result_text += "💡 **Note:** To see detailed results, you may need to use the Qiskit API directly.\n\n"
                    
                    # Generate PNG histogram if there are results
                    if final_counts:
                        png_path = _save_job_histogram_png(final_counts, input.job_id)
                        if png_path:
                            result_text += f"\n__QUANTUM_PNG__{png_path}__END_PNG__\n"
                    
                except Exception as e:
                    result_text += f"⚠️ Could not get detailed results: {str(e)}\n\n"
            
            elif status_name == 'QUEUED':
                result_text += "⏳ **Job is queued waiting for execution.**\n\n"
                if hasattr(status, 'queue_position'):
                    result_text += f"Queue position: {status.queue_position}\n"
                result_text += "Check again in a few minutes.\n\n"
            
            elif status_name == 'RUNNING':
                result_text += "🔄 **Job is currently running.**\n\n"
                result_text += "Results will be available soon.\n\n"
            
            elif status_name == 'CANCELLED':
                result_text += "❌ **Job was cancelled.**\n\n"
            
            elif status_name == 'ERROR':
                result_text += "🔴 **Job finished with error.**\n\n"
                if hasattr(status, 'error_message'):
                    result_text += f"**Error:** {status.error_message}\n\n"
            
            # Additional information
            result_text += "---\n\n"
            result_text += "💡 **Tip:** Save the Job ID to check results later.\n"
            
            return StringToolOutput(result=result_text)
            
        except Exception as e:
            error_text = f"❌ Error querying job: {str(e)}\n\n"
            error_text += "Verify that:\n"
            error_text += "- The Job ID is correct\n"
            error_text += "- Your IBM Quantum token is valid\n"
            error_text += "- You have access to the requested job\n"
            return StringToolOutput(result=error_text)
    
    async def _list_recent_jobs(self, service: QiskitRuntimeService, filter_status: str = "all") -> StringToolOutput:
        """List recent jobs for the user with optional status filter."""
        try:
            # Get last 20 jobs to have enough after filtering
            jobs = service.jobs(limit=20)
            
            if not jobs:
                return StringToolOutput(
                    result="📭 You have no recent jobs on IBM Quantum.\n\n"
                           "Execute a quantum circuit to create your first job."
                )
            
            # Filter jobs by requested status
            filtered_jobs = []
            status_map = {
                'running': ['RUNNING'],
                'queued': ['QUEUED'],
                'done': ['DONE', 'COMPLETED'],
                'error': ['ERROR', 'CANCELLED']
            }
            
            for job in jobs:
                raw_status = job.status()
                status = str(raw_status) if not hasattr(raw_status, 'name') else raw_status.name
                if filter_status == "all":
                    filtered_jobs.append(job)
                elif filter_status.lower() in status_map:
                    if status in status_map[filter_status.lower()]:
                        filtered_jobs.append(job)
            
            if not filtered_jobs:
                filter_msg = f" with status '{filter_status}'" if filter_status != "all" else ""
                return StringToolOutput(
                    result=f"📭 You have no jobs{filter_msg} on IBM Quantum.\n\n"
                           "Execute a quantum circuit to create your first job."
                )
            
            # Title based on filter
            if filter_status == "all":
                title = "# 📋 All Your Quantum Jobs\n\n"
            elif filter_status == "running":
                title = "# 🔄 Your Running Jobs\n\n"
            elif filter_status == "queued":
                title = "# ⏳ Your Queued Jobs\n\n"
            elif filter_status == "done":
                title = "# ✅ Your Completed Jobs\n\n"
            elif filter_status == "error":
                title = "# 🔴 Your Jobs with Errors\n\n"
            else:
                title = "# 📋 Your Quantum Jobs\n\n"
            
            result_text = title
            result_text += f"**Total found:** {len(filtered_jobs)}\n\n"
            result_text += "| Job ID | Backend | Status | Created |\n"
            result_text += "|--------|---------|--------|----------|\n"
            
            status_emoji = {
                'QUEUED': '⏳',
                'RUNNING': '🔄',
                'COMPLETED': '✅',
                'DONE': '✅',
                'CANCELLED': '❌',
                'ERROR': '🔴'
            }
            
            for job in filtered_jobs[:10]:  # Show maximum 10
                job_id = job.job_id()[:20] + "..."  # Truncate for table
                backend = job.backend().name if hasattr(job, 'backend') else "N/A"
                status = job.status()
                status_name = str(status) if not hasattr(status, 'name') else status.name
                emoji = status_emoji.get(status_name, '❓')
                created = str(job.creation_date)[:16] if hasattr(job, 'creation_date') else "N/A"
                
                result_text += f"| `{job_id}` | {backend} | {emoji} {status_name} | {created} |\n"
            
            if len(filtered_jobs) > 10:
                result_text += f"\n*Showing 10 of {len(filtered_jobs)} jobs*\n"
            
            result_text += "\n"
            result_text += "💡 **To see details of a specific job**, provide the complete Job ID.\n"
            
            # Add suggestions based on filter
            if filter_status == "running" or filter_status == "queued":
                result_text += "⏱️ **Tip:** These jobs are still processing. Check later to see results.\n"
            elif filter_status == "done":
                result_text += "✅ **Tip:** Use the Job ID to see detailed results of each job.\n"
            
            return StringToolOutput(result=result_text)
            
        except Exception as e:
            return StringToolOutput(
                result=f"❌ Error listing jobs: {str(e)}"
            )
