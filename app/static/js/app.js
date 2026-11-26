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

function getChartTheme() {
  const styles = getComputedStyle(document.documentElement);
  return {
    accent: styles.getPropertyValue("--accent").trim(),
    ink: styles.getPropertyValue("--ink").trim(),
    muted: styles.getPropertyValue("--muted").trim(),
    border: styles.getPropertyValue("--border").trim(),
  };
}

function applyChartTheme(chart) {
  const theme = getChartTheme();
  chart.data.datasets.forEach((dataset) => {
    dataset.backgroundColor = theme.accent;
  });
  chart.options.color = theme.ink;
  chart.options.plugins.legend.labels.color = theme.ink;
  chart.options.scales.x.ticks.color = theme.muted;
  chart.options.scales.x.grid.color = theme.border;
  chart.options.scales.y.ticks.color = theme.muted;
  chart.options.scales.y.grid.color = theme.border;
  chart.options.scales.y.title.color = theme.ink;
  chart.update("none");
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

  const chartTheme = getChartTheme();
  const chart = new Chart(canvas, {
    type: "bar",
    data: {
      labels: data.labels,
      datasets: [
        {
          label: canvas.dataset.label || "Weekly volume (kg)",
          data: data.volume,
          backgroundColor: chartTheme.accent,
        },
      ],
    },
    options: {
      responsive: true,
      color: chartTheme.ink,
      plugins: { legend: { display: true, labels: { color: chartTheme.ink } } },
      scales: {
        x: {
          ticks: { color: chartTheme.muted },
          grid: { color: chartTheme.border },
        },
        y: {
          beginAtZero: true,
          ticks: { color: chartTheme.muted },
          grid: { color: chartTheme.border },
          title: {
            display: true,
            text: canvas.dataset.yTitle || "Volume (kg)",
            color: chartTheme.ink,
          },
        },
      },
    },
  });
  document.addEventListener("fitness-theme-change", () => applyChartTheme(chart));
});



/* Dark Mode Toggle */

(() => {
    const themeButton = document.getElementById("theme-toggle");
    const root = document.documentElement;

    if (!themeButton) return;

    const savedTheme = localStorage.getItem("fitness-theme");

    function applyTheme(theme) {
        const isDark = theme === "dark";

        if (isDark) {
            root.setAttribute("data-theme", "dark");
        } else {
            root.removeAttribute("data-theme");
        }

        themeButton.textContent = isDark ? "☀️" : "🌙";

        themeButton.setAttribute(
            "aria-label",
            isDark ? "Switch to light mode" : "Switch to dark mode"
        );

        themeButton.setAttribute("aria-pressed", String(isDark));
        document.dispatchEvent(new Event("fitness-theme-change"));
    }

    applyTheme(savedTheme === "dark" ? "dark" : "light");

    themeButton.addEventListener("click", () => {
        const currentTheme = root.getAttribute("data-theme");
        const newTheme = currentTheme === "dark" ? "light" : "dark";

        applyTheme(newTheme);
        localStorage.setItem("fitness-theme", newTheme);
    });
})();
