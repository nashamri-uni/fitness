(() => {
  const dialog = document.getElementById("dashboard-details-dialog");
  if (!dialog) return;

  const panel = dialog.querySelector(".dashboard-details-panel");
  const title = document.getElementById("dashboard-details-title");
  const content = document.getElementById("dashboard-details-content");
  const closeButton = document.getElementById("dashboard-details-close");
  const triggers = Array.from(document.querySelectorAll("[data-dashboard-detail]"));
  const templates = new Map(
    Array.from(document.querySelectorAll("[data-dashboard-detail-template]"))
      .map((template) => [template.dataset.dashboardDetailTemplate, template])
  );
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

  let activeTrigger = null;
  let closeTimer = null;
  let isClosing = false;

  function finishClose() {
    window.clearTimeout(closeTimer);
    if (dialog.open) dialog.close();
    document.body.classList.remove("dashboard-details-scroll-lock");
    if (activeTrigger) {
      activeTrigger.setAttribute("aria-expanded", "false");
      activeTrigger.focus();
    }
    activeTrigger = null;
    isClosing = false;
  }

  function closeDetails() {
    if (!dialog.open || isClosing) return;

    isClosing = true;
    dialog.classList.remove("is-open");
    if (reduceMotion.matches) {
      finishClose();
      return;
    }
    closeTimer = window.setTimeout(finishClose, 270);
  }

  function openDetails(trigger) {
    if (dialog.open || isClosing) return;

    const template = templates.get(trigger.dataset.dashboardDetail);
    if (!template) {
      console.error("No detail template found for Dashboard statistic.", trigger.dataset.dashboardDetail);
      return;
    }

    activeTrigger = trigger;
    title.textContent = template.dataset.title;
    content.replaceChildren(template.content.cloneNode(true));
    dialog.showModal();
    document.body.classList.add("dashboard-details-scroll-lock");
    trigger.setAttribute("aria-expanded", "true");
    requestAnimationFrame(() => {
      if (dialog.open) dialog.classList.add("is-open");
    });
    closeButton.focus({ preventScroll: true });
  }

  triggers.forEach((trigger) => {
    trigger.addEventListener("click", () => openDetails(trigger));
    trigger.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        openDetails(trigger);
      }
    });
  });

  closeButton.addEventListener("click", closeDetails);
  dialog.addEventListener("cancel", (event) => {
    event.preventDefault();
    closeDetails();
  });
  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) closeDetails();
  });
  dialog.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      event.preventDefault();
      closeDetails();
      return;
    }
    if (event.key !== "Tab") return;

    const focusable = Array.from(
      dialog.querySelectorAll('a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])')
    ).filter((element) => !element.hidden);
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (!first || !last) {
      event.preventDefault();
      panel.focus();
    } else if (event.shiftKey && (document.activeElement === first || !dialog.contains(document.activeElement))) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && (document.activeElement === last || !dialog.contains(document.activeElement))) {
      event.preventDefault();
      first.focus();
    }
  });
})();
