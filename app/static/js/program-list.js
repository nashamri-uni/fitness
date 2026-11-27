(() => {
  const dialog = document.getElementById("program-day-delete-dialog");
  if (!dialog || typeof dialog.showModal !== "function") return;

  const form = dialog.querySelector("form");
  const message = document.getElementById("program-day-delete-message");
  dialog.closest(".programs-page").addEventListener("click", (event) => {
    const link = event.target.closest("[data-confirm-delete]");
    if (!link || event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;

    event.preventDefault();
    form.action = link.href;
    message.textContent = link.dataset.confirmDelete;
    dialog.showModal();
  });

  dialog.querySelector("[data-cancel-delete]").addEventListener("click", () => dialog.close());
})();
