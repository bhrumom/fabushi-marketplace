(() => {
  "use strict";

  const STORAGE_KEY = "fabushi.global-dharma.state.v1";
  const TOOL_NAMES = Object.freeze([
    "offline.capabilities",
    "offline.state.read",
    "offline.practice.record",
    "local.prayer-wheel.start"
  ]);
  const CAPABILITIES = Object.freeze([
    { name: "offline.capabilities", free: true, offline: true, mutation: false, entitlement: false },
    { name: "offline.state.read", free: true, offline: true, mutation: false, entitlement: false },
    { name: "offline.practice.record", free: true, offline: true, mutation: true, entitlement: false },
    { name: "local.prayer-wheel.start", free: false, offline: false, mutation: true, entitlement: true }
  ]);

  let registered = false;

  function initialState() {
    return {
      schemaVersion: 1,
      revision: 0,
      freeActionCount: 0,
      prayerWheelStartCount: 0,
      lastAction: null,
      updatedAt: null
    };
  }

  function normalizeState(raw) {
    const fallback = initialState();
    if (!raw || typeof raw !== "object" || raw.schemaVersion !== 1) return fallback;
    const integer = (value) => Number.isSafeInteger(value) && value >= 0 ? value : 0;
    return {
      schemaVersion: 1,
      revision: integer(raw.revision),
      freeActionCount: integer(raw.freeActionCount),
      prayerWheelStartCount: integer(raw.prayerWheelStartCount),
      lastAction: typeof raw.lastAction === "string" ? raw.lastAction.slice(0, 160) : null,
      updatedAt: typeof raw.updatedAt === "string" ? raw.updatedAt.slice(0, 64) : null
    };
  }

  function readState() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      return raw ? normalizeState(JSON.parse(raw)) : initialState();
    } catch (_) {
      return initialState();
    }
  }

  function persistState(state) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  }

  function currentResult(state = readState()) {
    return {
      appId: "global-dharma",
      schemaVersion: state.schemaVersion,
      revision: state.revision,
      freeActionCount: state.freeActionCount,
      prayerWheelStartCount: state.prayerWheelStartCount,
      lastAction: state.lastAction,
      updatedAt: state.updatedAt
    };
  }

  function mutate(kind, apply) {
    const previous = readState();
    const next = { ...previous };
    apply(next);
    next.revision = previous.revision + 1;
    next.lastAction = kind;
    next.updatedAt = new Date().toISOString();
    persistState(next);
    render(next);
    window.dispatchEvent(new CustomEvent("global-dharma:state", { detail: currentResult(next) }));
    return currentResult(next);
  }

  function recordFreePractice(input = {}) {
    const raw = typeof input.label === "string" ? input.label.trim() : "";
    const label = raw ? raw.slice(0, 80) : "免费本地修持";
    return mutate("offline.practice.record:" + label, (next) => {
      next.freeActionCount += 1;
    });
  }

  function recordPrayerWheelStart() {
    return mutate("local.prayer-wheel.start", (next) => {
      next.prayerWheelStartCount += 1;
    });
  }

  function toolResult(text, structuredContent) {
    return {
      content: [{ type: "text", text }],
      structuredContent
    };
  }

  function registerTools() {
    if (registered) return true;
    const api = window.__fabushiWebMcp;
    if (!api || typeof api.registerLocalTool !== "function") return false;

    api.registerLocalTool({
      name: "offline.capabilities",
      title: "查看离线能力",
      description: "读取全球法布施当前包实际可用的免费离线与受保护能力。",
      inputSchema: { type: "object", properties: {}, additionalProperties: false },
      annotations: { readOnlyHint: true }
    }, async () => toolResult("已读取全球法布施离线能力。", {
      appId: "global-dharma",
      capabilities: CAPABILITIES,
      state: currentResult()
    }));

    api.registerLocalTool({
      name: "offline.state.read",
      title: "读取本地状态",
      description: "读取当前页面的真实持久状态和 revision。",
      inputSchema: { type: "object", properties: {}, additionalProperties: false },
      annotations: { readOnlyHint: true }
    }, async () => toolResult("已读取全球法布施本地状态。", {
      state: currentResult()
    }));

    api.registerLocalTool({
      name: "offline.practice.record",
      title: "记录免费本地修持",
      description: "执行无需联网的免费本地操作，并立即更新页面与持久状态。",
      inputSchema: {
        type: "object",
        properties: { label: { type: "string", maxLength: 80 } },
        additionalProperties: false
      },
      annotations: { readOnlyHint: false }
    }, async (input = {}) => {
      const state = recordFreePractice(input);
      return toolResult("免费本地操作已完成。", { state });
    });

    api.registerLocalTool({
      name: "local.prayer-wheel.start",
      title: "启动本地转经轮",
      description: "受保护操作；只有 Host 完成当前账户 entitlement 核验后才会调用此页面工具。",
      inputSchema: { type: "object", properties: {}, additionalProperties: false },
      annotations: { readOnlyHint: false }
    }, async () => {
      const state = recordPrayerWheelStart();
      return toolResult("本地转经轮已启动。", { state });
    });

    registered = true;
    document.querySelector("#bridge-status").textContent = "WebMCP 本地工具已注册";
    return true;
  }

  function render(state = readState()) {
    document.querySelector("#revision").textContent = "rev " + state.revision;
    document.querySelector("#free-count").textContent = String(state.freeActionCount);
    document.querySelector("#prayer-count").textContent = String(state.prayerWheelStartCount);
    document.querySelector("#last-action").textContent = state.lastAction
      ? "最近操作：" + state.lastAction
      : "尚无操作";

    const list = document.querySelector("#capabilities");
    list.replaceChildren(...CAPABILITIES.map((capability) => {
      const li = document.createElement("li");
      li.textContent = capability.name + " · "
        + (capability.free ? "免费" : "受保护") + " · "
        + (capability.offline ? "离线可用" : "执行时需联网核验");
      return li;
    }));
  }

  async function requestProtectedStart() {
    const result = document.querySelector("#protected-result");
    const api = window.__fabushiWebMcp;
    if (!api || typeof api.call !== "function") {
      result.textContent = "Host WebMCP 尚未就绪，未执行受保护操作。";
      return;
    }
    result.textContent = "正在请求 Host 权限与 entitlement 核验…";
    try {
      const response = await api.call("local.prayer-wheel.start", {});
      const state = response?.structuredContent?.state;
      if (state && Number.isSafeInteger(state.revision)) render(normalizeState(state));
      result.textContent = "Host 已授权并执行本地转经轮。";
    } catch (error) {
      result.textContent = "未执行：" + String(error?.message || error);
    }
  }

  document.querySelector("#free-action").addEventListener("click", () => {
    recordFreePractice({ label: "页面按钮" });
  });
  document.querySelector("#prayer-action").addEventListener("click", () => {
    void requestProtectedStart();
  });

  render();
  registerTools();
  window.addEventListener("fabushi:webmcp-ready", registerTools);
  window.addEventListener("storage", (event) => {
    if (event.key === STORAGE_KEY) render();
  });

  Object.defineProperty(window, "__globalDharmaOffline", {
    configurable: false,
    enumerable: false,
    value: Object.freeze({
      version: 1,
      toolNames: TOOL_NAMES,
      readState: () => currentResult()
    })
  });
})();
