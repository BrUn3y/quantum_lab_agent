import asyncio
import os
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace

from qiskit.transpiler import CouplingMap

from beeai_agents.backend_visualization import (
    BACKEND_CANVAS_MARKER,
    canvas_marker,
    render_backend_dashboard,
)
from beeai_agents.quantum_lab_agent import _backend_canvas_from_status
from beeai_agents.quantum_status_agent import _create_backend_canvas


class FakeBackend:
    name = "ibm_test"
    num_qubits = 5
    coupling_map = CouplingMap([(0, 1), (1, 2), (2, 3), (3, 4)])

    def status(self):
        return SimpleNamespace(operational=True, pending_jobs=2)

    def properties(self):
        qubits = [
            [
                SimpleNamespace(name="T1", value=100 + index),
                SimpleNamespace(name="T2", value=80 + index),
                SimpleNamespace(name="readout_error", value=0.01 + index / 1000),
            ]
            for index in range(5)
        ]
        gates = [
            SimpleNamespace(
                qubits=[0, 1],
                parameters=[SimpleNamespace(name="gate_error", value=0.002)],
            )
        ]
        return SimpleNamespace(
            qubits=qubits,
            gates=gates,
            last_update_date=datetime.now(timezone.utc),
        )


class BackendVisualizationTests(unittest.TestCase):
    def test_dashboard_is_a_nonempty_png(self):
        path = render_backend_dashboard(FakeBackend())
        try:
            with open(path, "rb") as image:
                content = image.read()
            self.assertTrue(content.startswith(b"\x89PNG\r\n\x1a\n"))
            self.assertGreater(len(content), 20_000)
        finally:
            os.unlink(path)

    def test_canvas_is_not_created_without_internal_marker(self):
        text, artifact = asyncio.run(_create_backend_canvas("ordinary status response", "ibm_test"))
        self.assertEqual(text, "ordinary status response")
        self.assertIsNone(artifact)

    def test_lab_only_forwards_a_topology_image(self):
        self.assertIsNone(_backend_canvas_from_status("ordinary status response", "ibm_test"))
        artifact = _backend_canvas_from_status(
            "![ibm_test topology](agentstack://12345678-1234-1234-1234-123456789abc)",
            "ibm_test",
        )
        self.assertIsNotNone(artifact)
        self.assertFalse(artifact.parts[0].root.text.startswith("#"))

    def test_marker_round_trip(self):
        marker = canvas_marker("/tmp/quantum_lab_pngs/example.png")
        self.assertEqual(BACKEND_CANVAS_MARKER.search(marker).group(1), "/tmp/quantum_lab_pngs/example.png")


if __name__ == "__main__":
    unittest.main()
