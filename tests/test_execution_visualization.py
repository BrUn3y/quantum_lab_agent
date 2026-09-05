import os
import unittest

from qiskit import QuantumCircuit

from beeai_agents.execution_visualization import render_execution_dashboard
from beeai_agents.quantum_lab_agent import _execution_canvas_from_computing


class ExecutionVisualizationTests(unittest.TestCase):
    def test_dashboard_contains_a_high_resolution_png(self):
        circuit = QuantumCircuit(2, 2)
        circuit.h(0)
        circuit.cx(0, 1)
        circuit.measure([0, 1], [0, 1])
        path = render_execution_dashboard(circuit, {"00": 518, "11": 506}, backend_name="local_statevector_simulator", job_id="test-job", shots=1024)
        try:
            with open(path, "rb") as image:
                content = image.read()
            self.assertTrue(content.startswith(b"\x89PNG\r\n\x1a\n"))
            self.assertGreater(len(content), 30_000)
        finally:
            os.unlink(path)

    def test_lab_forwards_results_without_duplicate_heading(self):
        artifact = _execution_canvas_from_computing(
            "**Backend:** local_statevector_simulator\n![Quantum execution results](agentstack://12345678-1234-1234-1234-123456789abc)",
            "OPENQASM 2.0;",
        )
        self.assertIsNotNone(artifact)
        self.assertFalse(artifact.parts[0].root.text.startswith("#"))


if __name__ == "__main__":
    unittest.main()
