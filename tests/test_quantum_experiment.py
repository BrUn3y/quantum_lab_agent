import unittest
from types import SimpleNamespace

from a2a.types import Message, Part, Role, TextPart
from PIL import Image

from beeai_agents.experiment_engine import parse_maxcut_graph, run_maxcut_qaoa
from beeai_agents.quantum_experiment_agent import (
    format_experiment_summary,
    is_qaoa_maxcut_request,
    should_submit_hardware,
)
from beeai_agents.quantum_lab_agent import (
    _experiment_canvas_from_response,
    _is_experiment_hardware_followup,
    _is_experiment_query,
    _previous_experiment_request,
)
from beeai_agents.tools.quantum_experiment_client import extract_experiment_response


class ExperimentRoutingTests(unittest.TestCase):
    def test_qaoa_maxcut_routes_to_experiment_agent(self):
        prompt = "Use QAOA to solve Max-Cut on a 5-node graph using the local simulator"
        self.assertTrue(_is_experiment_query(prompt))
        self.assertTrue(is_qaoa_maxcut_request(prompt))
        self.assertFalse(should_submit_hardware(prompt))

    def test_hardware_comparison_requests_qpu_submission(self):
        prompt = "Compare a QAOA Max-Cut baseline with real IBM Quantum hardware"
        self.assertTrue(should_submit_hardware(prompt))

    def test_hardware_followup_recovers_previous_experiment(self):
        original = "Use QAOA to solve Max-Cut on a 5-node graph using the local simulator"
        followup = "now execute the experiment in IBM Quantum"
        history = [
            Message(
                message_id="original-request",
                role=Role.user,
                parts=[Part(root=TextPart(text=original))],
            ),
            Message(
                message_id="followup-request",
                role=Role.user,
                parts=[Part(root=TextPart(text=followup))],
            ),
        ]
        self.assertTrue(_is_experiment_hardware_followup(followup))
        self.assertEqual(_previous_experiment_request(history, followup), original)

    def test_lab_forwards_experiment_canvas(self):
        artifact = _experiment_canvas_from_response(
            "![QAOA experiment dashboard](agentstack://01234567-89ab-cdef-0123-456789abcdef)"
        )
        self.assertIsNotNone(artifact)
        self.assertEqual(artifact.name, "Hybrid quantum experiment")

    def test_client_prefers_final_task_text_over_canvas_artifact(self):
        final_message = Message(
            message_id="final-message",
            role=Role.agent,
            parts=[Part(root=TextPart(text="Full QAOA experiment summary"))],
        )
        response = SimpleNamespace(
            event=(SimpleNamespace(history=[final_message]),),
            last_message=SimpleNamespace(text="![Canvas](agentstack://artifact-id)"),
        )
        self.assertEqual(extract_experiment_response(response), "Full QAOA experiment summary")


class QAOAEngineTests(unittest.TestCase):
    def test_explicit_graph_edges_are_parsed(self):
        nodes, edges = parse_maxcut_graph(
            "QAOA Max-Cut for a 4-node graph with edges (0,1), (1,2), (2,3), (3,0)"
        )
        self.assertEqual(nodes, 4)
        self.assertEqual(edges, ((0, 1), (0, 3), (1, 2), (2, 3)))

    def test_five_node_qaoa_is_validated_against_exact_solution(self):
        result = run_maxcut_qaoa(
            "Use QAOA to solve Max-Cut on a 5-node graph using the local simulator",
            shots=256,
        )
        try:
            self.assertEqual(result.exact_cut, 4)
            self.assertEqual(result.best_cut, result.exact_cut)
            self.assertGreater(result.approximation_ratio, 0.9)
            self.assertEqual(sum(result.counts.values()), 256)
            self.assertIn("OPENQASM 2.0", result.qasm)
            self.assertIn("measure", result.qasm)
            with Image.open(result.dashboard_path) as image:
                self.assertGreaterEqual(image.width, 2000)
                self.assertGreaterEqual(image.height, 1200)
            summary = format_experiment_summary(result)
            self.assertIn("Approximation ratio", summary)
            self.assertIn("Exact optimum", summary)
        finally:
            result.dashboard_path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
