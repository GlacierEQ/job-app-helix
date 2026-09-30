(() => {
  document.documentElement.classList.add("js");

  const tabs = Array.from(document.querySelectorAll("[data-audience]"));
  const panels = Array.from(document.querySelectorAll("[data-panel]"));

  if (!tabs.length || !panels.length) return;

  const activate = (name, focus = false) => {
    tabs.forEach((tab) => {
      const active = tab.dataset.audience === name;
      tab.setAttribute("aria-selected", String(active));
      tab.tabIndex = active ? 0 : -1;
      if (active && focus) tab.focus();
    });

    panels.forEach((panel) => {
      panel.hidden = panel.dataset.panel !== name;
    });
  };

  tabs.forEach((tab, index) => {
    tab.addEventListener("click", () => activate(tab.dataset.audience));
    tab.addEventListener("keydown", (event) => {
      if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
      event.preventDefault();
      let next = index;
      if (event.key === 'ArrowRight') next = (index + 1) % tabs.length;
      if (event.key === 'ArrowLeft') next = (index - 1 + tabs.length) % tabs.length;
      if (event.key === 'Home') next = 0;
      if (event.key === 'End') next = tabs.length - 1;
      activate(tabs[next].dataset.audience, true);
    });
  });

  activate("recruiter");
})();
