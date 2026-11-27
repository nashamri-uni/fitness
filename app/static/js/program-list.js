(() => {
  const dialog = document.getElementById("program-day-delete-dialog");
  const page = document.querySelector(".programs-page");
  if (!page) return;
  const menus = page.querySelectorAll(".program-day-menu");
  const closeMenu = (menu, focus = false) => {
    menu.open = false;
    if (focus) menu.querySelector("summary").focus();
  };
  document.addEventListener("click", (event) => {
    menus.forEach((menu) => {
      if (menu.open && !menu.contains(event.target)) closeMenu(menu);
    });
  });
  page.addEventListener("keydown", (event) => {
    if (event.key !== "Escape") return;
    const menu = event.target.closest(".program-day-menu[open]");
    if (menu) {
      event.preventDefault();
      closeMenu(menu, true);
    }
  });
  if (!dialog || typeof dialog.showModal !== "function") return;

  const form = dialog.querySelector("form");
  const message = document.getElementById("program-day-delete-message");
  let menuTrigger;
  page.addEventListener("click", (event) => {
    const link = event.target.closest("[data-confirm-delete]");
    if (!link || event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;

    event.preventDefault();
    form.action = link.href;
    message.textContent = link.dataset.confirmDelete;
    const menu = link.closest(".program-day-menu");
    menuTrigger = menu?.querySelector("summary");
    if (menu) closeMenu(menu);
    dialog.showModal();
  });

  dialog.querySelector("[data-cancel-delete]").addEventListener("click", () => dialog.close());
  dialog.addEventListener("close", () => menuTrigger?.focus());
})();
