"use strict";

const agentInfo = {
  lab: {
    kind: "THE ORCHESTRATOR",
    port: "8000",
    title: "Una conversación. Todo conectado.",
    description:
      "Entiende tu solicitud y coordina a los agentes especializados mediante A2A. Código, backend y resultados vuelven a ti en una sola respuesta.",
    repo: "quantum_lab_agent",
    symbol: "Q",
  },
  developer: {
    kind: "THE CIRCUIT BUILDER",
    port: "8001",
    title: "Tus ideas, en lenguaje cuántico.",
    description:
      "Transforma instrucciones en código Qiskit y OpenQASM. Genera circuitos y algoritmos como Bell, Grover y Deutsch–Jozsa, listos para el siguiente paso.",
    repo: "quantum-developer-agent",
    symbol: "H",
  },
  status: {
    kind: "THE HARDWARE OBSERVER",
    port: "8002",
    title: "Conoce el estado de cada posibilidad.",
    description:
      "Consulta disponibilidad, colas y topologías de los backends IBM Quantum. Recupera el estado de tus jobs y sus resultados con información del servicio en vivo.",
    repo: "quantum-status-agent",
    symbol: "S",
  },
  computing: {
    kind: "THE QUANTUM EXECUTOR",
    port: "8003",
    title: "Del circuito al resultado real.",
    description:
      "Ejecuta circuitos en simuladores locales o en las QPU IBM Quantum accesibles para tu cuenta. Obtén el backend, el Job ID y las mediciones de cada ejecución.",
    repo: "quantum-computing-agent",
    symbol: "X",
  },
  experiment: {
    kind: "THE EXPLORER / IN DEVELOPMENT",
    port: "8004",
    title: "Explora la frontera híbrida.",
    description:
      "Experimenta con QAOA Max-Cut y flujos de optimización híbrida. Combina validación clásica, análisis en Canvas y evaluación opcional en una QPU. Agente en desarrollo.",
    repo: "quantum-experiment-agent",
    symbol: "E",
  },
};

const demos = {
  grover: {
    image: "images/quantum-lab-demo.gif",
    title: "quantum_lab / grover_workflow",
    alt: "Demo de generación y ejecución de un circuito de Grover, con resultados y visualización en Agent Stack.",
    caption:
      "De un prompt a un circuito de Grover: generación, ejecución coordinada y visualización de resultados.",
  },
  qaoa: {
    image: "images/quantum-experiment-real-hardware.gif",
    title: "quantum_lab / qaoa_real_hardware",
    alt: "Demo de QAOA Max-Cut: optimización local, validación clásica y ejecución real en ibm_marrakesh con 1024 shots.",
    caption:
      "QAOA Max-Cut en un grafo de 5 nodos: optimización local, validación clásica y ejecución en ibm_marrakesh con 1,024 shots. Función en desarrollo.",
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
# Edita QISKIT_IBM_TOKEN en .env antes de iniciar los agentes.
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
          ? "Comandos copiados. Tu laboratorio te espera."
          : "Prompt copiado. Pruébalo en tu Lab Agent.",
      );
    } catch {
      showToast("Selecciona el texto para copiarlo manualmente.");
    }
  });
});
