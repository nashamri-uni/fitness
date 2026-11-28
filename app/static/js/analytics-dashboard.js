(() => {
  const dashboard = document.querySelector("[data-analytics]");
  if (!dashboard) return;

  const root = document.documentElement;
  const locale = root.lang?.startsWith("ar")
    ? new Intl.Locale(root.lang, { numberingSystem: "arab" }).toString() : root.lang || "en";
  const rtl = root.dir === "rtl";
  const number = new Intl.NumberFormat(locale, { maximumFractionDigits: 2 });
  const signed = new Intl.NumberFormat(locale, { maximumFractionDigits: 2, signDisplay: "exceptZero" });
  const percent = new Intl.NumberFormat(locale, { style: "percent", maximumFractionDigits: 1 });
  const signedPercent = new Intl.NumberFormat(locale, {
    style: "percent", maximumFractionDigits: 1, signDisplay: "exceptZero",
  });
  const dateFormat = (options, timeZone = "UTC") => new Intl.DateTimeFormat(
    locale, { calendar: "gregory", timeZone, ...options },
  );
  const localDate = dateFormat({ dateStyle: "medium" });
  const weekday = dateFormat({ weekday: "short" });
  const dateValue = (date) => Date.parse(`${date}T00:00:00Z`);
  for (const element of dashboard.querySelectorAll("[data-number]")) {
    const formatter = element.hasAttribute("data-signed") ? signed : number;
    element.textContent = formatter.format(Number(element.dataset.number));
  }
  for (const element of dashboard.querySelectorAll("[data-percent]")) {
    const value = Number(element.dataset.percent) / 100;
    element.textContent = element.hasAttribute("data-signed")
      ? `(${signedPercent.format(value)})` : percent.format(value);
  }
  const digits = new Intl.NumberFormat(locale, { useGrouping: false });
  for (const element of dashboard.querySelectorAll("[data-localize-digits]")) {
    element.textContent = element.textContent.replace(/\d+/g, (value) => digits.format(Number(value)));
  }
  for (const element of dashboard.querySelectorAll("time[data-date]")) {
    const formatter = element.dataset.date === "weekday" ? weekday : localDate;
    element.textContent = formatter.format(dateValue(element.dateTime));
  }
  const dateRange = (start, end) => {
    const first = dateValue(start);
    const last = dateValue(end);
    return localDate.formatRange?.(first, last) || `${localDate.format(first)} – ${localDate.format(last)}`;
  };
  for (const option of dashboard.querySelectorAll("option[data-date-end]")) {
    option.textContent = dateRange(option.value, option.dataset.dateEnd);
  }
  const activityPeriod = dashboard.querySelector("[data-activity-period]");
  if (activityPeriod) {
    activityPeriod.querySelector("select").addEventListener("change", () => activityPeriod.requestSubmit());
    activityPeriod.hidden = false;
  }

  const picker = dashboard.querySelector("[data-exercise-picker]");
  if (picker) {
    const summary = picker.querySelector("summary");
    const search = picker.querySelector("[data-exercise-search]");
    const input = search.querySelector("input");
    const empty = picker.querySelector("[data-exercise-empty]");
    const options = [...picker.querySelectorAll("[data-exercise-option]")];
    // Accept Arabic names with or without diacritics and common alef variants.
    const normalize = (text) => text.toLocaleLowerCase(locale).normalize("NFD")
      .replace(/\p{Mark}|ـ/gu, "").replace(/\s+/g, " ").trim();
    const names = options.map((option) => normalize(option.dataset.search));
    search.hidden = false;
    input.addEventListener("input", () => {
      const terms = normalize(input.value).split(" ");
      options.forEach((option, index) => {
        option.hidden = !terms.every((term) => names[index].includes(term));
      });
      empty.hidden = options.some((option) => !option.hidden);
    });
    picker.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && picker.open) {
        event.preventDefault();
        picker.open = false;
        summary.focus();
      }
    });
    document.addEventListener("pointerdown", (event) => {
      if (picker.open && !picker.contains(event.target)) picker.open = false;
    });
    document.addEventListener("focusin", (event) => {
      if (picker.open && !picker.contains(event.target)) picker.open = false;
    });
  }

  const activityCanvas = dashboard.querySelector("[data-activity-chart]");
  const performanceCanvas = dashboard.querySelector("[data-performance-chart]");
  const canvas = activityCanvas || performanceCanvas;
  if (!canvas || typeof Chart === "undefined") return;
  const plot = canvas.parentElement;
  const fallback = plot.closest(".analytics-panel").querySelector("[data-chart-table]");
  const style = (token) => getComputedStyle(dashboard).getPropertyValue(token).trim();
  let colors;
  const chartColors = () => ({
    primary: style("--analytics-blue"),
    secondary: style("--ok"),
    surface: style("--card"),
    fill: `color-mix(in srgb, ${style("--analytics-blue")} 12%, transparent)`,
  });
  const shortDate = dateFormat({ month: "short", day: "numeric" });
  const activityDate = (row) => row.end
    ? dateRange(row.date, row.end) : localDate.format(dateValue(row.date));

  function activityConfig() {
    const rows = JSON.parse(document.getElementById("analytics-activity-data").textContent);
    const weekly = Boolean(rows[0].end);
    const labels = rows.map((row) => (weekly ? shortDate : weekday).format(dateValue(row.date)));
    const datasets = [{
      label: canvas.dataset.sessions,
      data: rows.map((row) => row.sessions),
      borderColor: () => colors.primary,
      backgroundColor: () => colors.fill,
      pointBackgroundColor: () => colors.primary,
      borderWidth: 2.5,
      fill: "origin",
    }];
    if (weekly) datasets.push({
      label: canvas.dataset.days,
      data: rows.map((row) => row.days),
      borderColor: () => colors.secondary,
      backgroundColor: () => colors.secondary,
      pointBackgroundColor: () => colors.secondary,
      borderWidth: 1.7,
      borderDash: [5, 4],
    });
    return {
      type: "line",
      data: { labels, datasets },
      options: {
        interaction: { mode: "index", intersect: false },
        elements: {
          line: { cubicInterpolationMode: "monotone" },
          point: { radius: 2.5, hoverRadius: 4.5, borderColor: () => colors.surface, borderWidth: 1 },
        },
        scales: {
          x: { reverse: rtl, offset: true, grid: { display: false }, ticks: { maxRotation: 0, maxTicksLimit: rows.length } },
          y: { beginAtZero: true, suggestedMax: 1, ticks: { maxTicksLimit: 4, precision: 0 } },
        },
        plugins: {
          legend: { display: weekly },
          tooltip: {
            callbacks: {
              title: ([item]) => activityDate(rows[item.dataIndex]),
              label: (item) => `${item.dataset.label}: ${number.format(item.parsed.y)}`,
              labelColor: ({ datasetIndex }) => {
                const color = datasetIndex === 0 ? colors.primary : colors.secondary;
                return { borderColor: color, backgroundColor: color };
              },
            },
          },
        },
      },
    };
  }

  function performanceConfig() {
    const rows = JSON.parse(document.getElementById("analytics-performance-data").textContent);
    const timeZone = canvas.dataset.timezone;
    const axisDate = dateFormat({ month: "short", day: "numeric", year: "2-digit" }, timeZone);
    const tooltipDate = dateFormat({ dateStyle: "medium", timeStyle: "short" }, timeZone);
    const first = rows[0].timestamp;
    const last = rows.at(-1).timestamp;
    const day = 86400000;
    const padding = first === last ? day / 2 : Math.max(day / 24, (last - first) * .025);
    return {
      type: "line",
      data: {
        datasets: [{
          data: rows.map((row) => ({ x: row.timestamp, y: row.value })),
          parsing: false,
          fill: "start",
          spanGaps: false,
          tension: 0,
          borderWidth: 2,
          borderColor: () => colors.primary,
          backgroundColor: () => colors.fill,
          pointBackgroundColor: () => colors.primary,
          pointBorderColor: () => colors.surface,
          pointRadius: rows.length > 60 ? 2 : 3.2,
          pointHitRadius: 15,
          pointHoverRadius: 5,
        }],
      },
      options: {
        interaction: { mode: "nearest", axis: "xy", intersect: false },
        scales: {
          x: {
            type: "linear",
            reverse: rtl,
            min: first - padding,
            max: last + padding,
            grid: { display: false },
            afterBuildTicks(axis) {
              const capacity = Math.max(2, Math.min(6, Math.floor(plot.clientWidth / 85)));
              const intervals = Math.min(capacity - 1, Math.floor((last - first) / day));
              const ticks = intervals
                ? Array.from({ length: intervals + 1 }, (_, index) => first + (last - first) * index / intervals)
                : [first];
              const labels = new Set();
              const axisTicks = ticks.filter((timestamp) => {
                const label = axisDate.format(timestamp);
                if (labels.has(label)) return false;
                labels.add(label);
                return true;
              }).map((value) => ({ value }));
              axis.ticks = rtl ? axisTicks.reverse() : axisTicks;
            },
            ticks: { callback: (value) => axisDate.format(value), maxRotation: 0 },
          },
          y: {
            grace: "12%",
            min: rows.some(({ value }) => value === 0) ? 0 : undefined,
            ticks: { maxTicksLimit: 5, callback: (value) => number.format(value) },
            title: { display: true, text: canvas.dataset.unit },
          },
        },
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              title: ([item]) => tooltipDate.format(item.parsed.x),
              label: (item) => `${canvas.dataset.metric}: ${number.format(item.parsed.y)} ${canvas.dataset.unit}`,
            },
          },
        },
      },
    };
  }

  let chart;
  function applyTheme() {
    if (!chart) return;
    colors = chartColors();
    const muted = style("--muted");
    const border = style("--border");
    const { plugins, scales } = chart.options;
    for (const axis of [scales.x, scales.y]) {
      axis.ticks.color = muted;
      axis.border.display = false;
      axis.grid.color = border;
    }
    scales.y.title.color = muted;
    plugins.legend.labels.color = style("--ink");
    plugins.tooltip.backgroundColor = style("--ink");
    plugins.tooltip.titleColor = style("--card");
    plugins.tooltip.bodyColor = style("--card");
    chart.update("none");
  }

  function mountChart() {
    plot.hidden = false;
    try {
      colors = chartColors();
      const config = activityCanvas ? activityConfig() : performanceConfig();
      const { options } = config;
      Object.assign(options, {
        responsive: true, maintainAspectRatio: false, animation: false, locale,
        font: { family: getComputedStyle(dashboard).fontFamily, size: 11 },
        layout: { padding: { left: 3, right: 5, top: 6 } },
      });
      options.plugins.colors = false;
      Object.assign(options.plugins.legend, {
        position: "bottom", rtl, labels: { usePointStyle: true, boxWidth: 8, padding: 10 },
      });
      if (activityCanvas) {
        options.plugins.legend.labels.usePointStyle = false;
        options.plugins.legend.labels.boxWidth = 17;
        options.plugins.legend.labels.boxHeight = 0;
      }
      Object.assign(options.plugins.tooltip, { rtl, padding: 10, displayColors: Boolean(activityCanvas) });
      chart = new Chart(canvas, config);
      applyTheme();
      fallback.open = false;
    } catch (error) {
      Chart.getChart(canvas)?.destroy();
      chart = undefined;
      plot.hidden = true;
      fallback.open = true;
      console.error("Unable to render dashboard chart", error);
    }
  }

  mountChart();
  const theme = new MutationObserver(applyTheme);
  theme.observe(root, { attributes: true, attributeFilter: ["data-theme"] });
  document.fonts?.ready.then(applyTheme);
  window.addEventListener("pagehide", () => {
    chart?.destroy();
    chart = undefined;
  });
  window.addEventListener("pageshow", (event) => {
    if (event.persisted && !chart) mountChart();
  });
})();
