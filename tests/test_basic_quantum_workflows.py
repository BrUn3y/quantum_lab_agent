import asyncio
import re
import unittest

from qiskit import QuantumCircuit
from qiskit.primitives import StatevectorSampler

from beeai_agents.quantum_computing_agent import _execution_parameters
from beeai_agents.quantum_developer_agent import _basic_algorithm_qasm, _superposition_qasm
from beeai_agents.quantum_lab_agent import (
    LAB_AGENT_SKILLS,
    _is_create_and_execute_request,
    _is_explanation_query,
    _is_status_query,
)
from beeai_agents.tools.quantum_tool import IBMQuantumTool


def _qasm_from_response(response: str) -> str:
    match = re.search(r"```qasm\n(.*?)```", response, re.DOTALL)
    if not match:
        raise AssertionError("Response did not contain a QASM block")
    return match.group(1)


def _sample(prompt: str, shots: int = 4096) -> dict[str, int]:
    generated = _basic_algorithm_qasm(prompt)
    if not generated:
        raise AssertionError(f"No deterministic circuit generated for {prompt!r}")
    circuit = QuantumCircuit.from_qasm_str(_qasm_from_response(generated[1]))
    return StatevectorSampler(seed=42).run([circuit], shots=shots).result()[0].data.c.get_counts()


class BasicAlgorithmTests(unittest.TestCase):
    def test_bell_state(self):
        counts = _sample("Create a Bell state circuit")
        self.assertLessEqual(set(counts), {"00", "11"})

    def test_cx_gate(self):
        self.assertEqual(_sample("Create a circuit demonstrating the CX gate"), {"11": 4096})

    def test_two_qubit_grover(self):
        self.assertEqual(_sample("Implement Grover's algorithm for 2 qubits"), {"11": 4096})

    def test_three_qubit_grover(self):
        counts = _sample("Implement Grover's algorithm for 3 qubits")
        self.assertEqual(max(counts, key=counts.get), "111")
        self.assertGreater(counts["111"] / 4096, 0.70)

    def test_deutsch_jozsa(self):
        self.assertEqual(_sample("Create a Deutsch-Jozsa circuit"), {"11": 4096})

    def test_hyphenated_qubit_count(self):
        response = _superposition_qasm("Create a 2-qubit superposition circuit")
        self.assertIn("qreg q[2];", response)


class SuggestedPromptTests(unittest.TestCase):
    def test_prompts_cover_every_agent_capability(self):
        examples = LAB_AGENT_SKILLS[0].examples
        self.assertTrue(all(_is_create_and_execute_request(prompt) for prompt in examples[:3]))
        self.assertTrue(all(_is_status_query(prompt) for prompt in examples[3:5]))
        self.assertTrue(_is_explanation_query(examples[5]))
        self.assertTrue(_is_create_and_execute_request(examples[6]))

    def test_spanish_grover_example_routes_to_create_and_execute(self):
        prompt = "dame un ejemplo del algoritmo de grover y ejecutado en una computadora cuantica"
        self.assertTrue(_is_create_and_execute_request(prompt))
        self.assertFalse(_is_status_query(prompt))

    def test_run_algorithm_without_create_verb_routes_to_execution(self):
        prompt = "Run Grover's algorithm on a quantum computer"
        self.assertTrue(_is_create_and_execute_request(prompt))
        self.assertFalse(_is_status_query(prompt))


class ExecutionTests(unittest.IsolatedAsyncioTestCase):
    def test_internal_policy_does_not_force_hardware(self):
        request = (
            "Create a Bell state on the simulator\n\n"
            "Execute exactly once. If the user requested real hardware, select a real backend."
        )
        parameters = _execution_parameters(request)
        self.assertFalse(parameters["use_real_device"])
        self.assertEqual(parameters["job_tags"], ["quantum-lab", "bell-state"])

    def test_named_ibm_backend_is_real_hardware(self):
        parameters = _execution_parameters("Run a CX circuit on ibm_fez with 256 shots")
        self.assertTrue(parameters["use_real_device"])
        self.assertEqual(parameters["backend_name"], "ibm_fez")
        self.assertEqual(parameters["shots"], 256)
        self.assertEqual(parameters["job_tags"], ["quantum-lab", "cx-gate"])

    def test_least_busy_real_ibm_quantum_backend_is_hardware(self):
        parameters = _execution_parameters(
            "Create a Bell state and execute it once on the least busy real IBM Quantum backend"
        )
        self.assertTrue(parameters["use_real_device"])
        self.assertEqual(parameters["backend_name"], "")

    def test_quantum_machine_in_spanish_defaults_to_real_hardware(self):
        parameters = _execution_parameters(
            "dame un ejemplo del algoritmo de grover y ejecuto en una maquina cuantica"
        )
        self.assertTrue(parameters["use_real_device"])
        self.assertEqual(parameters["backend_name"], "")
        self.assertEqual(parameters["job_tags"], ["quantum-lab", "grover-search"])

    def test_execution_without_backend_defaults_to_real_hardware(self):
        parameters = _execution_parameters("Execute this Grover circuit")
        self.assertTrue(parameters["use_real_device"])

    def test_explicit_spanish_simulation_uses_local_simulator(self):
        parameters = _execution_parameters("Ejecuta Grover en el simulador local")
        self.assertFalse(parameters["use_real_device"])

    def test_negated_simulator_request_uses_real_hardware(self):
        parameters = _execution_parameters("Run Grover without a simulator")
        self.assertTrue(parameters["use_real_device"])

    async def test_local_simulator_returns_results_and_tags(self):
        generated = _basic_algorithm_qasm("Create a Bell state circuit")
        output = await IBMQuantumTool().run(
            {
                "qasm_code": _qasm_from_response(generated[1]),
                "backend_name": "simulator",
                "shots": 128,
                "job_tags": ["quantum-lab", "bell-state"],
            }
        )
        response = output.get_text_content()
        self.assertIn("local_statevector_simulator", response)
        self.assertIn("Local simulation completed", response)
        self.assertIn("`quantum-lab`, `bell-state`", response)


if __name__ == "__main__":
    unittest.main()
