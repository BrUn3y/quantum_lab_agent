"use strict";

const agentInfo = {
  lab: {
    kind: "THE ORCHESTRATOR",
    port: "8000",
    title: "One conversation. Everything connected.",
    description:
      "Understands your request and coordinates specialized agents through A2A. Code, backend details, and results come back to you in a single response.",
    repo: "quantum_lab_agent",
    symbol: "Q",
  },
  developer: {
    kind: "THE CIRCUIT BUILDER",
    port: "8001",
    title: "Your ideas, in quantum language.",
    description:
      "Turns instructions into Qiskit and OpenQASM code. Generates circuits and algorithms such as Bell, Grover, and Deutsch–Jozsa, ready for the next step.",
    repo: "quantum-developer-agent",
    symbol: "H",
  },
  status: {
    kind: "THE HARDWARE OBSERVER",
    port: "8002",
    title: "See the status of every possibility.",
    description:
      "Checks IBM Quantum backend availability, queues, and topologies. Retrieves your job status and results with live information from the service.",
    repo: "quantum-status-agent",
    symbol: "S",
  },
  computing: {
    kind: "THE QUANTUM EXECUTOR",
    port: "8003",
    title: "From circuit to real results.",
    description:
      "Runs circuits on local simulators or IBM Quantum QPUs available to your account. Get the backend, job ID, and measurements for each run.",
    repo: "quantum-computing-agent",
    symbol: "X",
  },
  experiment: {
    kind: "THE EXPLORER / IN DEVELOPMENT",
    port: "8004",
    title: "Explore the hybrid frontier.",
    description:
      "Experiments with QAOA Max-Cut and hybrid optimization workflows. Combines classical validation, Canvas analysis, and optional QPU evaluation. Agent in development.",
    repo: "quantum-experiment-agent",
    symbol: "E",
  },
};

const demos = {
  grover: {
    image: "images/quantum-lab-demo.gif",
    title: "quantum_lab / grover_workflow",
    alt: "Demo of Grover circuit generation and execution, with results and visualization in Agent Stack.",
    caption:
      "From a prompt to a Grover circuit: generation, coordinated execution, and results visualization.",
  },
  qaoa: {
    image: "images/quantum-experiment-real-hardware.gif",
    title: "quantum_lab / qaoa_real_hardware",
    alt: "QAOA Max-Cut demo: local optimization, classical validation, and real hardware execution on ibm_marrakesh with 1,024 shots.",
    caption:
      "QAOA Max-Cut on a 5-node graph: local optimization, classical validation, and execution on ibm_marrakesh with 1,024 shots. Feature in development.",
  },
};

function setupTabs(selector, onSelect) {
  const tabs = [...document.querySelectorAll(selector)];
  const activate = (tab) => {
    tabs.forEach((item) => {
      const selected = item === tab;
      item.setAttribute("aria-selected", String(selected));
      item.tabIndex = selected ? 0 : -1;
    });
    onSelect(tab);
  };
  tabs.forEach((tab, index) => {
    tab.addEventListener("click", () => activate(tab));
    tab.addEventListener("keydown", (event) => {
      let next;
      if (event.key === "ArrowDown" || event.key === "ArrowRight")
        next = (index + 1) % tabs.length;
      if (event.key === "ArrowUp" || event.key === "ArrowLeft")
        next = (index - 1 + tabs.length) % tabs.length;
      if (event.key === "Home") next = 0;
      if (event.key === "End") next = tabs.length - 1;
      if (next !== undefined) {
        event.preventDefault();
        activate(tabs[next]);
        tabs[next].focus();
      }
    });
  });
}

setupTabs(".agent-tab", (tab) => {
  const agent = agentInfo[tab.dataset.agent];
  document.querySelector("#agent-kind").textContent = agent.kind;
  document.querySelector("#agent-port").textContent = `PORT :${agent.port}`;
  document.querySelector("#agent-title").textContent = agent.title;
  document.querySelector("#agent-description").textContent = agent.description;
  document.querySelector("#agent-repo").href =
    `https://github.com/BrUn3y/${agent.repo}`;
  document.querySelector(".orbital-core").textContent = agent.symbol;
  document
    .querySelector("#agent-detail")
    .setAttribute("aria-labelledby", tab.id);
});

setupTabs("[data-demo]", (tab) => {
  const demo = demos[tab.dataset.demo];
  const image = document.querySelector("#demo-image");
  image.src = demo.image;
  image.alt = demo.alt;
  document.querySelector("#demo-window-title").textContent = demo.title;
  document.querySelector("#demo-caption").textContent = demo.caption;
  document.querySelector("#demo-panel").setAttribute("aria-labelledby", tab.id);
});

const menuToggle = document.querySelector(".menu-toggle");
const navigation = document.querySelector("#navigation");
function closeMenu() {
  menuToggle.setAttribute("aria-expanded", "false");
  navigation.classList.remove("open");
}
menuToggle.addEventListener("click", () => {
  const expanded = menuToggle.getAttribute("aria-expanded") !== "true";
  menuToggle.setAttribute("aria-expanded", String(expanded));
  navigation.classList.toggle("open", expanded);
});
navigation
  .querySelectorAll("a")
  .forEach((link) => link.addEventListener("click", closeMenu));
document.addEventListener("keydown", (event) => {
  if (
    event.key === "Escape" &&
    menuToggle.getAttribute("aria-expanded") === "true"
  ) {
    closeMenu();
    menuToggle.focus();
  }
});

const installCommands = `git clone https://github.com/BrUn3y/quantum_lab_agent.git
cd quantum_lab_agent
uv sync
ollama pull granite4.2:8b
cp .env.example .env
# Set QISKIT_IBM_TOKEN in .env before starting the agents.
./start_all.sh`;

let toastTimer;
function showToast(message) {
  const toast = document.querySelector(".toast");
  clearTimeout(toastTimer);
  toast.textContent = message;
  toast.classList.add("visible");
  toastTimer = setTimeout(() => toast.classList.remove("visible"), 3500);
}

async function copyText(text) {
  if (navigator.clipboard && window.isSecureContext) {
    await navigator.clipboard.writeText(text);
    return;
  }
  const field = document.createElement("textarea");
  field.value = text;
  field.style.position = "fixed";
  field.style.opacity = "0";
  field.setAttribute("readonly", "");
  document.body.append(field);
  const previousFocus = document.activeElement;
  field.select();
  const copied = document.execCommand("copy");
  field.remove();
  previousFocus?.focus();
  if (!copied) throw new Error("Clipboard unavailable");
}

document.querySelectorAll("[data-copy]").forEach((button) => {
  button.addEventListener("click", async () => {
    const text =
      button.dataset.copy === "install"
        ? installCommands
        : document.querySelector("#sample-prompt").textContent;
    try {
      await copyText(text);
      showToast(
        button.dataset.copy === "install"
          ? "Commands copied. Your lab awaits."
          : "Prompt copied. Try it in your Lab Agent.",
      );
    } catch {
      showToast("Select the text to copy it manually.");
    }
  });
});
