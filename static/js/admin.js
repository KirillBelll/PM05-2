// Подтверждение опасных действий и закрытие уведомлений
(function () {
  "use strict";

  const dialog = document.getElementById("confirm-dialog");
  let pendingForm = null;

  document.addEventListener("submit", function (event) {
    const form = event.target;
    const text = form.getAttribute("data-confirm");
    if (!text || form.dataset.confirmed === "1") return;
    event.preventDefault();

    if (!dialog || typeof dialog.showModal !== "function") {
      if (window.confirm(text)) { form.dataset.confirmed = "1"; form.submit(); }
      return;
    }
    pendingForm = form;
    dialog.querySelector("[data-confirm-text]").textContent = text;
    dialog.showModal();
  });

  if (dialog) {
    dialog.addEventListener("close", function () {
      if (dialog.returnValue === "ok" && pendingForm) {
        pendingForm.dataset.confirmed = "1";
        pendingForm.requestSubmit ? pendingForm.requestSubmit() : pendingForm.submit();
      }
      pendingForm = null;
    });
  }

  document.addEventListener("click", function (event) {
    const btn = event.target.closest(".flash-close");
    if (btn) btn.parentElement.remove();
  });

  // Автоприменение фильтров при смене значения в выпадающем списке
  document.querySelectorAll("form[data-autosubmit] select").forEach(function (el) {
    el.addEventListener("change", function () { el.form.submit(); });
  });
})();
