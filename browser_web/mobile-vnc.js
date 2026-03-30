const root = document.documentElement;
root.classList.add("sl-mobile-vnc");

function clickById(id) {
  const node = document.getElementById(id);
  if (node instanceof HTMLElement) {
    node.click();
    return true;
  }
  return false;
}

function toggleControlBar() {
  const handle = document.getElementById("noVNC_control_bar_handle");
  if (handle instanceof HTMLElement) {
    handle.click();
    return;
  }
  const controlBar = document.getElementById("noVNC_control_bar");
  controlBar?.classList.toggle("noVNC_open");
}

function requestFullscreenFallback() {
  if (document.fullscreenElement) {
    void document.exitFullscreen?.();
    return;
  }
  void document.documentElement.requestFullscreen?.();
}

function buildQuickbar() {
  const shell = document.createElement("div");
  shell.id = "sl-mobile-vnc-quickbar";
  shell.innerHTML = `
    <div class="sl-mobile-vnc-quickbar__inner">
      <div class="sl-mobile-vnc-quickbar__status">
        <span id="sl-mobile-vnc-status">Opening browser surface...</span>
        <span class="sl-mobile-vnc-quickbar__hint">Manual login</span>
      </div>
      <div class="sl-mobile-vnc-quickbar__actions">
        <button class="sl-mobile-vnc-quickbar__button" id="sl-mobile-vnc-menu" type="button">Menu</button>
        <button class="sl-mobile-vnc-quickbar__button" id="sl-mobile-vnc-keyboard" type="button">Keyboard</button>
        <button class="sl-mobile-vnc-quickbar__button" id="sl-mobile-vnc-fullscreen" type="button">Full</button>
        <button class="sl-mobile-vnc-quickbar__button" id="sl-mobile-vnc-reload" type="button">Reload</button>
      </div>
    </div>
  `;
  document.body.appendChild(shell);

  document.getElementById("sl-mobile-vnc-menu")?.addEventListener("click", () => {
    toggleControlBar();
  });

  document.getElementById("sl-mobile-vnc-keyboard")?.addEventListener("click", () => {
    const opened = clickById("noVNC_keyboard_button");
    if (!opened) {
      toggleControlBar();
      window.setTimeout(() => {
        clickById("noVNC_keyboard_button");
      }, 120);
    }
  });

  document.getElementById("sl-mobile-vnc-fullscreen")?.addEventListener("click", () => {
    if (!clickById("noVNC_fullscreen_button")) {
      requestFullscreenFallback();
    }
  });

  document.getElementById("sl-mobile-vnc-reload")?.addEventListener("click", () => {
    window.location.reload();
  });
}

function bindStatusMirror() {
  const statusTarget = document.getElementById("sl-mobile-vnc-status");
  const nativeStatus = document.getElementById("noVNC_status");
  const nativeTransition = document.getElementById("noVNC_transition_text");

  if (!(statusTarget instanceof HTMLElement)) {
    return;
  }

  const update = () => {
    const message =
      nativeTransition?.textContent?.trim() ||
      nativeStatus?.textContent?.trim() ||
      "Remote browser ready";
    statusTarget.textContent = message;
  };

  update();
  const observer = new MutationObserver(update);
  if (nativeStatus) {
    observer.observe(nativeStatus, { childList: true, subtree: true, characterData: true });
  }
  if (nativeTransition) {
    observer.observe(nativeTransition, { childList: true, subtree: true, characterData: true });
  }
}

function boot() {
  document.title = "Social Listening Browser";
  buildQuickbar();
  bindStatusMirror();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", boot, { once: true });
} else {
  boot();
}
