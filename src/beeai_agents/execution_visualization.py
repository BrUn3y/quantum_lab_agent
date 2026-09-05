"""Canvas-ready visualization for completed quantum circuit executions."""

from __future__ import annotations

import re
import tempfile
import uuid
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyBboxPatch


RESULT_CANVAS_MARKER = re.compile(r"__QUANTUM_RESULT_CANVAS__:(.+)")


def result_canvas_marker(path: str | Path) -> str:
    return f"__QUANTUM_RESULT_CANVAS__:{Path(path)}"


def _draw_circuit(ax, circuit) -> None:
    qubit_count = circuit.num_qubits
    shown_ops = list(circuit.data)[:24]
    width = max(len(shown_ops) + 1, 6)
    ax.set_xlim(-0.8, width)
    ax.set_ylim(-0.8, max(qubit_count - 0.2, 0.8))
    ax.axis("off")

    for index in range(qubit_count):
        y = qubit_count - index - 1
        ax.plot([0, width - 0.2], [y, y], color="#697077", linewidth=1.2, zorder=0)
        ax.text(-0.25, y, f"q{index}", color="#c6c6c6", ha="right", va="center", fontsize=9)

    for column, instruction in enumerate(shown_ops, start=1):
        operation = instruction.operation.name.lower()
        qubits = [circuit.find_bit(bit).index for bit in instruction.qubits]
        ys = [qubit_count - index - 1 for index in qubits]
        x = column
        if len(ys) > 1:
            ax.plot([x, x], [min(ys), max(ys)], color="#f1c21b", linewidth=1.4, zorder=1)
        if operation in {"cx", "cz"} and len(ys) == 2:
            ax.add_patch(Circle((x, ys[0]), 0.075, color="#f1c21b", zorder=3))
            ax.add_patch(Circle((x, ys[1]), 0.18, edgecolor="#f1c21b", facecolor="#161616", linewidth=1.5))
            if operation == "cx":
                ax.plot([x - 0.11, x + 0.11], [ys[1], ys[1]], color="#f1c21b", linewidth=1.4)
                ax.plot([x, x], [ys[1] - 0.11, ys[1] + 0.11], color="#f1c21b", linewidth=1.4)
            else:
                ax.text(x, ys[1], "Z", color="#f1c21b", ha="center", va="center", fontsize=8)
            continue
        for y in ys:
            color = "#42be65" if operation == "measure" else "#78a9ff"
            label = "M" if operation == "measure" else operation.upper()
            box = FancyBboxPatch(
                (x - 0.28, y - 0.2), 0.56, 0.4,
                boxstyle="round,pad=0.03,rounding_size=0.04",
                facecolor=color, edgecolor="none", zorder=2,
            )
            ax.add_patch(box)
            ax.text(x, y, label[:5], color="#161616", ha="center", va="center", fontsize=7, weight="bold")

    if len(circuit.data) > len(shown_ops):
        ax.text(width - 0.2, -0.55, f"+{len(circuit.data) - len(shown_ops)} operations", color="#8d8d8d", ha="right", fontsize=8)


def render_execution_dashboard(
    circuit,
    counts: dict[str, int],
    *,
    backend_name: str,
    job_id: str,
    shots: int,
) -> Path:
    """Render an IBM-inspired execution summary with histogram and circuit."""
    states_and_counts = sorted(counts.items(), key=lambda item: item[1], reverse=True)
    states = [item[0] for item in states_and_counts]
    values = [item[1] for item in states_and_counts]
    total = sum(values) or shots

    figure = plt.figure(figsize=(16, 9), facecolor="#161616")
    grid = figure.add_gridspec(12, 12, left=0.045, right=0.975, top=0.94, bottom=0.07, hspace=1.2)
    histogram = figure.add_subplot(grid[2:7, :])
    circuit_ax = figure.add_subplot(grid[9:12, :])

    figure.text(0.047, 0.925, "EXECUTION RESULTS", color="#78a9ff", fontsize=10, weight="bold")
    figure.text(0.047, 0.875, backend_name, color="#f4f4f4", fontsize=25, weight="bold")
    figure.text(0.047, 0.825, f"Job {job_id}", color="#a8a8a8", fontsize=10)

    cards = (("SHOTS", f"{total:,}"), ("OUTCOMES", str(len(counts))), ("QUBITS", str(circuit.num_qubits)), ("GATES", str(len(circuit.data))))
    for index, (label, value) in enumerate(cards):
        x = 0.44 + index * 0.135
        figure.text(x, 0.905, label, color="#8d8d8d", fontsize=8, weight="bold")
        figure.text(x, 0.855, value, color="#f4f4f4", fontsize=19)

    histogram.set_facecolor("#161616")
    bars = histogram.bar(states, values, color="#33b1ff", width=0.55)
    histogram.set_title("Measurement outcomes", color="#f4f4f4", fontsize=14, loc="left", pad=14)
    histogram.set_ylabel("Frequency", color="#c6c6c6")
    histogram.tick_params(colors="#c6c6c6", labelsize=9)
    histogram.grid(axis="y", color="#393939", linewidth=0.8)
    histogram.set_axisbelow(True)
    for spine in histogram.spines.values():
        spine.set_color("#525252")
    for bar, value in zip(bars, values):
        histogram.text(bar.get_x() + bar.get_width() / 2, value, f"{value:,}\n{value / total:.1%}", color="#f4f4f4", ha="center", va="bottom", fontsize=8)

    figure.text(0.047, 0.285, "CIRCUIT", color="#8d8d8d", fontsize=9, weight="bold")
    figure.text(0.047, 0.255, "Diagram", color="#f4f4f4", fontsize=10, weight="bold")
    figure.add_artist(plt.Line2D([0.047, 0.103], [0.245, 0.245], color="#33b1ff", linewidth=2))
    _draw_circuit(circuit_ax, circuit)

    output_directory = Path(tempfile.gettempdir()) / "quantum_lab_pngs"
    output_directory.mkdir(parents=True, exist_ok=True)
    safe_job_id = re.sub(r"[^a-zA-Z0-9_-]", "-", job_id)[:48] or "local-job"
    output_path = output_directory / f"{safe_job_id}_results_{uuid.uuid4().hex[:8]}.png"
    figure.savefig(output_path, dpi=150, facecolor=figure.get_facecolor())
    plt.close(figure)
    return output_path
