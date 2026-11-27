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

function setupActivityChart() {
  const canvas = document.getElementById("activity-chart");
  if (!canvas) return;

  const dataElement = document.getElementById("activity-chart-data");
  const select = document.getElementById("activity-week");
  const picker = document.querySelector(".activity-week-picker");
  const emptyMessage = document.getElementById("activity-empty-message");
  const modeButtons = document.querySelectorAll("[data-activity-mode]");
  let activity;

  try {
    activity = JSON.parse(dataElement.textContent);
  } catch (error) {
    console.error("Could not read activity chart data", error);
    return;
  }

  if (typeof Chart === "undefined") {
    canvas.replaceWith(Object.assign(document.createElement("p"), {
      className: "empty",
      textContent: canvas.dataset.noChart || "Chart library is unavailable.",
    }));
    return;
  }

  const locale = document.documentElement.lang || "en";
  const dateAtNoon = (value) => new Date(`${value}T12:00:00`);
  const formatDate = (value, options) => new Intl.DateTimeFormat(locale, options).format(dateAtNoon(value));
  const formatWeek = (week) => (
    `${formatDate(week.start, { month: "short", day: "numeric", year: "numeric" })} – ` +
    formatDate(week.end, { month: "short", day: "numeric", year: "numeric" })
  );
  const formatWeekOption = (week) => (
    `${formatDate(week.start, { month: "short", day: "numeric" })} – ` +
    formatDate(week.end, { month: "short", day: "numeric" })
  );
  const formatWeekTick = (week) => formatDate(week.start, { month: "short", day: "numeric" });
  const weekByStart = new Map(activity.weeks.map((week) => [week.start, week]));

  activity.weeks.forEach((week) => {
    const option = document.createElement("option");
    option.value = week.start;
    option.textContent = formatWeekOption(week);
    select.appendChild(option);
  });
  select.value = activity.current_week;

  const styles = getComputedStyle(document.documentElement);
  let mode = "weekly";
  const chart = new Chart(canvas, {
    type: "bar",
    data: {
      labels: [],
      datasets: [{
        label: canvas.dataset.weekLabel,
        data: [],
        backgroundColor: styles.getPropertyValue("--accent").trim(),
        barPercentage: 0.65,
        categoryPercentage: 0.7,
        maxBarThickness: 46,
        borderRadius: 4,
        borderSkipped: false,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      locale,
      plugins: {
        legend: {
          display: true,
          rtl: document.documentElement.dir === "rtl",
          textDirection: document.documentElement.dir,
          labels: { color: styles.getPropertyValue("--ink").trim() },
        },
        tooltip: {
          callbacks: {
            title: (items) => {
              if (!items.length) return "";
              const index = items[0].dataIndex;
              if (mode === "daily") {
                const day = weekByStart.get(select.value).days[index];
                return formatDate(day, {
                  weekday: "long",
                  day: "numeric",
                  month: "long",
                  year: "numeric",
                });
              }
              return formatWeek(activity.weeks[index]);
            },
          },
        },
      },
      scales: {
        x: {
          grid: { color: styles.getPropertyValue("--border").trim() },
          ticks: {
            color: styles.getPropertyValue("--muted").trim(),
            maxRotation: 0,
            minRotation: 0,
            maxTicksLimit: 6,
          },
        },
        y: {
          beginAtZero: true,
          max: 7,
          grid: { color: styles.getPropertyValue("--border").trim() },
          ticks: { stepSize: 1, color: styles.getPropertyValue("--muted").trim() },
          title: {
            display: true,
            text: canvas.dataset.weekYTitle,
            color: styles.getPropertyValue("--ink").trim(),
          },
        },
      },
    },
  });

  const updateEmptyMessage = () => {
    const selectedWeek = weekByStart.get(select.value);
    const showEmpty = mode === "daily"
      ? selectedWeek.count === 0
      : !activity.has_activity;
    emptyMessage.hidden = !showEmpty;
  };

  const updateChart = () => {
    const selectedWeek = weekByStart.get(select.value);
    const isDaily = mode === "daily";
    chart.data.labels = isDaily
      ? selectedWeek.days.map((day) => formatDate(day, { weekday: "short" }))
      : activity.weeks.map((week) => formatWeekTick(week));
    chart.options.scales.x.ticks.autoSkip = !isDaily;
    chart.options.scales.x.ticks.maxTicksLimit = isDaily ? 7 : 6;
    chart.data.datasets[0].label = isDaily ? canvas.dataset.dailyLabel : canvas.dataset.weekLabel;
    chart.data.datasets[0].data = isDaily
      ? selectedWeek.daily
      : activity.weeks.map((week) => week.count);
    chart.options.scales.y.max = isDaily ? Math.max(1, ...selectedWeek.daily) : 7;
    chart.options.scales.y.title.text = isDaily
      ? canvas.dataset.dailyYTitle
      : canvas.dataset.weekYTitle;
    chart.options.onClick = isDaily ? undefined : (_event, elements) => {
      if (elements.length) {
        select.value = activity.weeks[elements[0].index].start;
        mode = "daily";
        picker.hidden = false;
        modeButtons.forEach((button) => {
          button.setAttribute("aria-pressed", String(button.dataset.activityMode === mode));
        });
        updateChart();
      }
    };
    updateEmptyMessage();
    chart.update();
  };

  modeButtons.forEach((button) => {
    button.addEventListener("click", () => {
      mode = button.dataset.activityMode;
      picker.hidden = mode !== "daily";
      modeButtons.forEach((modeButton) => {
        modeButton.setAttribute("aria-pressed", String(modeButton === button));
      });
      updateChart();
    });
  });
  select.addEventListener("change", updateChart);

  const themeButton = document.getElementById("theme-toggle");
  if (themeButton) {
    themeButton.addEventListener("click", () => {
      const currentStyles = getComputedStyle(document.documentElement);
      chart.data.datasets[0].backgroundColor = currentStyles.getPropertyValue("--accent").trim();
      chart.options.scales.x.grid.color = currentStyles.getPropertyValue("--border").trim();
      chart.options.scales.y.grid.color = currentStyles.getPropertyValue("--border").trim();
      chart.options.scales.x.ticks.color = currentStyles.getPropertyValue("--muted").trim();
      chart.options.scales.y.ticks.color = currentStyles.getPropertyValue("--muted").trim();
      chart.options.plugins.legend.labels.color = currentStyles.getPropertyValue("--ink").trim();
      chart.options.scales.y.title.color = currentStyles.getPropertyValue("--ink").trim();
      chart.update();
    });
  }

  updateChart();
}

// Progress charts for the analytics dashboard (FREQ-12).
document.addEventListener("DOMContentLoaded", () => {
  setupLanguageSwitcher();
  setupActivityChart();

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
    }

    applyTheme(savedTheme === "dark" ? "dark" : "light");

    themeButton.addEventListener("click", () => {
        const currentTheme = root.getAttribute("data-theme");
        const newTheme = currentTheme === "dark" ? "light" : "dark";

        applyTheme(newTheme);
        localStorage.setItem("fitness-theme", newTheme);
    });
})();
