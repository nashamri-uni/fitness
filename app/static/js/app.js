// Applies the chosen language as soon as the dropdown changes (issue #1),
// so no extra "Switch" click is needed. The button stays as a no-JS fallback.
function setupLanguageSwitcher() {
  document.querySelectorAll("form[data-auto-submit]").forEach((form) => {
    const select = form.querySelector("select");
    if (!select) return;

    form.classList.add("js-auto-submit");
    select.addEventListener("change", () => {
      if (typeof form.requestSubmit === "function") {
        form.requestSubmit();
      } else {
        form.submit();
      }
    });
  });
}

// Progress charts for the analytics dashboard (FREQ-12).
document.addEventListener("DOMContentLoaded", () => {
  setupLanguageSwitcher();

  const canvas = document.getElementById("volume-chart");
  if (!canvas) return;

  let data = {};
  try {
    data = JSON.parse(canvas.dataset.data || "{}");
  } catch (error) {
    console.error("Could not read chart data", error);
    return;
  }

  if (!data.labels || data.labels.length === 0) {
    canvas.replaceWith(Object.assign(document.createElement("p"), {
      className: "empty",
      textContent: canvas.dataset.empty || "Log at least one completed set to see your progress chart.",
    }));
    return;
  }

  if (typeof Chart === "undefined") {
    canvas.replaceWith(Object.assign(document.createElement("p"), {
      className: "empty",
      textContent: canvas.dataset.noChart || "Chart library is unavailable, but the numbers are shown in the table.",
    }));
    return;
  }

  new Chart(canvas, {
    type: "bar",
    data: {
      labels: data.labels,
      datasets: [
        { label: canvas.dataset.label || "Weekly volume (kg)", data: data.volume, backgroundColor: "#2563eb" },
      ],
    },
    options: {
      responsive: true,
      plugins: { legend: { display: true } },
      scales: {
        y: {
          beginAtZero: true,
          title: { display: true, text: canvas.dataset.yTitle || "Volume (kg)" },
        },
      },
    },
  });
});
