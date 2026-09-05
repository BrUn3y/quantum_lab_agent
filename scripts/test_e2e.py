#!/usr/bin/env python3
"""Run live end-to-end tests against the four-agent Quantum Lab system."""

from __future__ import annotations

import argparse
import json
import os
import re
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AGENT_CONFIGS = (
    ("developer", "Quantum Developer Agent", "beeai_agents.quantum_developer_agent", "DEVELOPER_PORT", 8001),
    ("status", "Quantum Status Agent", "beeai_agents.quantum_status_agent", "STATUS_PORT", 8002),
    ("computing", "Quantum Computing Agent", "beeai_agents.quantum_computing_agent", "COMPUTING_PORT", 8003),
    ("lab", "Quantum Lab Agent", "beeai_agents.quantum_lab_agent", "LAB_PORT", 8000),
)
COUNT_ROW = re.compile(r"\|\s*`([01]+)`\s*\|\s*(\d+)\s*\|")


@dataclass(frozen=True)
class CircuitCase:
    name: str
    prompt: str
    allowed_states: frozenset[str]
    tag: str


CASES = (
    CircuitCase("Bell state", "Create a Bell state circuit", frozenset({"00", "11"}), "bell-state"),
    CircuitCase("CX gate", "Create a circuit demonstrating the CX gate", frozenset({"11"}), "cx-gate"),
    CircuitCase(
        "Grover search",
        "Create Grover's algorithm for 2 qubits",
        frozenset({"11"}),
        "grover-search",
    ),
    CircuitCase(
        "Deutsch-Jozsa",
        "Create a Deutsch-Jozsa circuit",
        frozenset({"11"}),
        "deutsch-jozsa",
    ),
)


def request_json(url: str, *, payload: dict | None = None, timeout: float = 5) -> dict:
    body = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"} if body else {},
        method="POST" if body else "GET",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode())


def card_url(host: str, port: int) -> str:
    return f"http://{host}:{port}/.well-known/agent-card.json"


def live_agents(host: str, agents: tuple[tuple[str, str, str, str, int], ...]) -> dict[str, bool]:
    result = {}
    for key, expected_name, _, _, port in agents:
        try:
            card = request_json(card_url(host, port), timeout=2)
            result[key] = card.get("name") == expected_name
        except (OSError, ValueError, urllib.error.URLError):
            result[key] = False
    return result


def wait_until_ready(host: str, agents: tuple[tuple[str, str, str, str, int], ...], timeout: float) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        states = live_agents(host, agents)
        if all(states.values()):
            return
        time.sleep(1)
    unavailable = ", ".join(name for name, ready in live_agents(host, agents).items() if not ready)
    raise RuntimeError(f"Agents did not become ready within {timeout:.0f}s: {unavailable}")


def start_agents(
    host: str,
    agents: tuple[tuple[str, str, str, str, int], ...],
    timeout: float,
) -> list[subprocess.Popen]:
    if host not in {"127.0.0.1", "localhost"}:
        raise RuntimeError("Automatic startup is only supported for localhost")

    log_dir = ROOT / ".logs" / "e2e"
    log_dir.mkdir(parents=True, exist_ok=True)
    environment = os.environ.copy()
    environment.setdefault("DEVELOPER_MODEL", "ollama:granite4.2:8b")
    environment.setdefault("STATUS_MODEL", "ollama:granite4.2:8b")
    environment.setdefault("COMPUTING_MODEL", "ollama:granite4.2:8b")
    environment.setdefault("LAB_MODEL", "ollama:granite4.2:8b")
    for prefix in ("DEVELOPER", "STATUS", "COMPUTING", "LAB"):
        environment[f"{prefix}_HOST"] = host
    for _, _, _, port_variable, port in agents:
        environment[port_variable] = str(port)
    processes: list[subprocess.Popen] = []

    for key, _, module, _, _ in agents:
        log = (log_dir / f"{key}.log").open("w")
        process = subprocess.Popen(
            [sys.executable, "-m", module],
            cwd=ROOT,
            env=environment,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        log.close()
        processes.append(process)

    try:
        wait_until_ready(host, agents, timeout)
    except Exception:
        stop_agents(processes)
        raise
    return processes


def stop_agents(processes: list[subprocess.Popen]) -> None:
    for process in processes:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGTERM)
    deadline = time.monotonic() + 10
    for process in processes:
        remaining = max(0, deadline - time.monotonic())
        try:
            process.wait(timeout=remaining)
        except subprocess.TimeoutExpired:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGKILL)


def final_agent_text(response: dict) -> str:
    if "error" in response:
        raise AssertionError(f"JSON-RPC error: {response['error']}")
    result = response.get("result", {})
    state = result.get("status", {}).get("state")
    if state != "completed":
        raise AssertionError(f"Task did not complete successfully (state={state!r})")

    for message in reversed(result.get("history", [])):
        if message.get("role") != "agent":
            continue
        texts = [part.get("text", "") for part in message.get("parts", []) if part.get("kind") == "text"]
        if any(texts):
            return "\n".join(texts)
    raise AssertionError("Response did not contain a final agent message")


def execute_case(base_url: str, case: CircuitCase, shots: int, timeout: float) -> None:
    prompt = f"{case.prompt} and execute it on the local simulator with {shots} shots. Return the measurement counts."
    request_id = str(uuid.uuid4())
    payload = {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": "message/send",
        "params": {
            "message": {
                "kind": "message",
                "messageId": str(uuid.uuid4()),
                "role": "user",
                "parts": [{"kind": "text", "text": prompt}],
            }
        },
    }
    response = request_json(f"{base_url}/jsonrpc/", payload=payload, timeout=timeout)
    if response.get("id") != request_id:
        raise AssertionError("JSON-RPC response ID does not match the request")

    text = final_agent_text(response)
    required_fragments = (
        "OPENQASM 2.0;",
        "local_statevector_simulator",
        "Local simulation completed",
        "**Job ID:**",
        f"`{case.tag}`",
        f"**Total measurements:** {shots}",
    )
    missing = [fragment for fragment in required_fragments if fragment not in text]
    if missing:
        raise AssertionError(f"Missing expected output: {', '.join(missing)}")

    counts = {state: int(count) for state, count in COUNT_ROW.findall(text)}
    if not counts:
        raise AssertionError("No measurement counts were found")
    unexpected = set(counts) - case.allowed_states
    if unexpected:
        raise AssertionError(f"Unexpected measured states: {sorted(unexpected)}")
    if sum(counts.values()) != shots:
        raise AssertionError(f"Expected {shots} measurements, got {sum(counts.values())}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default=os.getenv("LAB_HOST", "127.0.0.1"))
    parser.add_argument("--lab-port", type=int, default=int(os.getenv("LAB_PORT", "8000")))
    parser.add_argument("--developer-port", type=int, default=int(os.getenv("DEVELOPER_PORT", "8001")))
    parser.add_argument("--status-port", type=int, default=int(os.getenv("STATUS_PORT", "8002")))
    parser.add_argument("--computing-port", type=int, default=int(os.getenv("COMPUTING_PORT", "8003")))
    parser.add_argument("--shots", type=int, default=128)
    parser.add_argument("--timeout", type=float, default=180)
    parser.add_argument("--startup-timeout", type=float, default=90)
    parser.add_argument(
        "--no-start",
        action="store_true",
        help="Fail instead of starting the agents when none are running",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.shots < 1:
        raise SystemExit("--shots must be greater than zero")

    selected_ports = {
        "developer": args.developer_port,
        "status": args.status_port,
        "computing": args.computing_port,
        "lab": args.lab_port,
    }
    agents = tuple(
        (key, name, module, port_variable, selected_ports[key])
        for key, name, module, port_variable, _ in AGENT_CONFIGS
    )
    states = live_agents(args.host, agents)
    ready_count = sum(states.values())
    processes: list[subprocess.Popen] = []
    if ready_count == 0:
        if args.no_start:
            raise SystemExit("No agents are running and --no-start was supplied")
        print("Starting all four agents with Granite 4.2 8B...")
        processes = start_agents(args.host, agents, args.startup_timeout)
    elif ready_count != len(agents):
        unavailable = ", ".join(name for name, ready in states.items() if not ready)
        raise SystemExit(f"Only part of the system is running; unavailable: {unavailable}")
    else:
        print("Reusing the four running agents.")

    base_url = f"http://{args.host}:{args.lab_port}"
    failures = 0
    try:
        for case in CASES:
            started = time.monotonic()
            try:
                execute_case(base_url, case, args.shots, args.timeout)
                print(f"PASS  {case.name:<16} {time.monotonic() - started:5.2f}s")
            except Exception as error:
                failures += 1
                print(f"FAIL  {case.name:<16} {error}", file=sys.stderr)
    finally:
        stop_agents(processes)

    if failures:
        print(f"\n{failures} end-to-end test(s) failed.", file=sys.stderr)
        return 1
    print(f"\nAll {len(CASES)} end-to-end tests passed through Lab → Developer → Computing.")
    print("Status Agent availability was also verified through its live agent card.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
