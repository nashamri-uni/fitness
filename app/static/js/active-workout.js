(() => {
  const root = document.getElementById("active-workout");
  if (!root) return;
  const labels = document.getElementById("workout-labels").dataset;
  const storageKey = `fitplanner-workout-${root.dataset.session}`;
  const fields = ["reps_completed", "weight_kg", "duration_seconds"];
  const empty = { reps_completed: 0, weight_kg: 0, duration_seconds: 0 };
  const number = new Intl.NumberFormat(document.documentElement.lang, {
    maximumFractionDigits: 2, numberingSystem: "latn",
  });
  const inputNumber = new Intl.NumberFormat(document.documentElement.lang, {
    useGrouping: false, maximumFractionDigits: 16, numberingSystem: "latn",
  });
  const normalizeDigits = (value) => String(value)
    .replace(/[٠-٩]/g, (digit) => String(digit.charCodeAt(0) - 0x660))
    .replace(/[۰-۹]/g, (digit) => String(digit.charCodeAt(0) - 0x6f0))
    .replace(/[٫,]/g, ".");
  let openMenu;
  function closeMenu(restoreFocus = false) {
    if (!openMenu) return;
    openMenu.list.hidden = true;
    openMenu.control.setAttribute("aria-expanded", "false");
    if (restoreFocus) openMenu.control.focus();
    openMenu = null;
  }

  function actionMenu(control, actions) {
    const menu = el("div", "workout-set-menu");
    const list = el("div", "workout-set-menu-list");
    list.hidden = true;
    control.setAttribute("aria-expanded", "false");
    for (const [label, action] of actions) {
      list.append(button(label, null, () => {
        closeMenu(true);
        action();
      }));
    }
    control.addEventListener("click", () => {
      const reopening = openMenu?.control !== control;
      closeMenu();
      if (reopening) {
        root.querySelectorAll(".workout-exercise-menu[open]").forEach((panel) => { panel.open = false; });
        openMenu = { control, list, menu };
        list.hidden = false;
        control.setAttribute("aria-expanded", "true");
        list.querySelector("button")?.focus();
      }
    });
    menu.append(control, list);
    return menu;
  }
  const byId = (id) => document.getElementById(id);
  const form = byId("workout-complete-form");
  const csrf = form.elements.csrfmiddlewaretoken.value;
  const feedback = byId("workout-feedback");
  const preview = byId("workout-preview");
  const completion = byId("workout-completion");
  const finish = byId("workout-finish");
  let feedbackTimeout;
  let pending = 0;
  let finishing = false;
  let previewTrigger;
  let state;
  try {
    state = JSON.parse(localStorage.getItem(storageKey) || "{}") || {};
  } catch {
    state = {};
  }
  const drafts = state.drafts || {};
  const extras = state.extras || {};
  const timers = state.timers || {};

  function store() {
    try {
      localStorage.setItem(storageKey, JSON.stringify({
        drafts, extras, timers,
      }));
    } catch {
      // Tracking and saving still work when local storage is unavailable.
    }
  }

  const keyFor = (exercise, row) => `${exercise.id}:${row.key}`;
  const trackedValues = (values) => Object.fromEntries(
    fields.map((field) => [field, values?.[field] ?? empty[field]]),
  );
  const valuesFor = (row) => trackedValues(row.logged || row.target || row.defaults);
  const exercises = JSON.parse(byId("active-workout-data").textContent).map((exercise) => {
    exercise.card = root.querySelector(`[data-entry="${exercise.id}"]`);
    for (const item of extras[exercise.id] || []) {
      if (!exercise.rows.some((row) => row.key === item.key)) exercise.rows.push(item);
    }
    for (const row of exercise.rows) {
      const key = keyFor(exercise, row);
      if (drafts[key] && drafts[key].loggedId !== (row.logged?.id ?? null)) delete drafts[key];
      const draft = drafts[key];
      row.inputs = draft ? trackedValues(draft.values) : valuesFor(row);
      if (draft) draft.values = row.inputs;
      row.editing = Boolean(row.logged && draft?.loggedId === row.logged.id);
      if (row.inputs.weight_kg > 0 && exercise.kind === "bodyweight") exercise.weighted = true;
    }
    return exercise;
  });

  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function button(text, label, action, className) {
    const node = el("button", className, text);
    node.type = "button";
    if (label) {
      node.setAttribute("aria-label", label);
      node.title = label;
    }
    if (action) node.addEventListener("click", action);
    return node;
  }

  function inform(message, tone = "") {
    clearTimeout(feedbackTimeout);
    feedback.textContent = message;
    feedback.dataset.tone = tone;
    if (message && tone !== "error") {
      feedbackTimeout = setTimeout(() => { feedback.textContent = ""; }, 3500);
    }
  }

  function clock(seconds) {
    const total = Math.max(0, seconds);
    const pad = (value) => String(value).padStart(2, "0");
    const hours = Math.floor(total / 3600);
    const minutes = pad(Math.floor(total / 60) % 60);
    return `${hours ? `${hours}:` : ""}${minutes}:${pad(total % 60)}`;
  }

  function progress() {
    let completeExercises = 0;
    let completeSets = 0;
    let targetSets = 0;
    let targetDone = 0;
    let activeFound = false;
    for (const exercise of exercises) {
      const targets = exercise.rows.filter((row) => row.target);
      const done = exercise.rows.filter((row) => row.logged).length;
      const plannedDone = targets.filter((row) => row.logged).length;
      const complete = Boolean(done && plannedDone === targets.length);
      const status = complete ? "completed" : activeFound ? "upcoming" : "active";
      if (!complete) activeFound = true;
      if (complete) completeExercises++;
      completeSets += done;
      targetSets += targets.length;
      targetDone += plannedDone;
      exercise.card.dataset.status = status;
      if (status === "active" && exercise.autoCollapsed) {
        setExpanded(exercise, true);
        exercise.autoCollapsed = false;
      }
      exercise.card.querySelector("[data-state]").textContent = labels[status];
      exercise.card.querySelector("[data-exercise-progress]").textContent =
        targets.length ? `${number.format(done)} / ${number.format(targets.length)}` : number.format(done);
    }
    byId("workout-exercise-count").textContent = `${number.format(completeExercises)} / ${number.format(exercises.length)}`;
    byId("workout-set-count").textContent = targetSets
      ? `${number.format(completeSets)} / ${number.format(targetSets)}` : number.format(completeSets);
    const bar = byId("workout-progress");
    bar.max = Math.max(1, targetSets || exercises.length);
    bar.value = targetSets ? targetDone : completeExercises;
    return targetSets - targetDone;
  }

  function columns(exercise) {
    const timed = exercise.kind === "timed" || exercise.kind === "cardio";
    const visible = timed ? [["duration_seconds", labels.duration]] : [["reps_completed", labels.reps]];
    if (exercise.weighted && !timed) visible.unshift(["weight_kg", labels.weight]);
    return visible;
  }

  function previousText(exercise, setNumber) {
    const prior = exercise.previous[setNumber];
    if (!prior) return "—";
    if (exercise.kind === "timed" || exercise.kind === "cardio") return clock(prior.duration_seconds);
    if (exercise.weighted && prior.weight_kg) {
      return `${number.format(prior.weight_kg)} × ${number.format(prior.reps_completed)}`;
    }
    return `${number.format(prior.reps_completed)} ${labels.reps}`;
  }

  function updateDraft(exercise, row) {
    const key = keyFor(exercise, row);
    if (fields.some((field) => String(row.inputs[field] ?? "") !== String(valuesFor(row)[field] ?? ""))) {
      drafts[key] = { loggedId: row.logged?.id ?? null, values: { ...row.inputs } };
    } else {
      delete drafts[key];
    }
    store();
  }

  function renderRow(exercise, row) {
    const tableRow = el("tr", "workout-set-row");
    tableRow.classList.toggle("is-logged", Boolean(row.logged));
    tableRow.classList.toggle("is-editing", Boolean(row.editing));
    tableRow.classList.toggle("has-error", Boolean(row.error));
    tableRow.setAttribute("aria-busy", String(Boolean(row.pending)));
    const setNumber = row.logged?.set_number ?? row.target?.set_number ?? row.defaults.set_number;
    const rowLabel = `${exercise.kind === "cardio" ? labels.interval : labels.set} ${number.format(setNumber)}`;
    const index = el("th", "workout-set-number", number.format(setNumber));
    index.scope = "row";
    index.title = rowLabel;
    if (row.logged?.record) {
      const badge = el("span", "workout-set-pr", "★");
      badge.setAttribute("aria-label", labels.pr);
      badge.title = labels.pr;
      index.append(badge);
    }
    const previous = el("td", "workout-previous", previousText(exercise, setNumber));
    previous.dir = exercise.kind === "bodyweight" && !exercise.weighted ? "auto" : "ltr";
    previous.title = labels.previousTitle;
    tableRow.append(index, previous);

    const inputs = [];
    for (const [field, label] of columns(exercise)) {
      const cell = el("td", "workout-value");
      if (row.logged && !row.editing) {
        cell.textContent = row.logged[field] === null ? "—" : number.format(row.logged[field]);
      } else {
        const input = el("input");
        input.type = "text";
        input.inputMode = field === "weight_kg" ? "decimal" : "numeric";
        input.value = row.inputs[field] === "" ? "" :
          Number.isFinite(Number(row.inputs[field])) ? inputNumber.format(row.inputs[field]) : row.inputs[field];
        input.required = true;
        input.dataset.field = field;
        input.disabled = Boolean(row.pending);
        input.setAttribute("aria-label", `${rowLabel} · ${field === "weight_kg" ? labels.weightLabel : label}`);
        input.addEventListener("input", () => {
          row.inputs[field] = normalizeDigits(input.value);
          input.setCustomValidity("");
          row.error = false;
          tableRow.classList.remove("has-error");
          updateDraft(exercise, row);
        });
        input.addEventListener("blur", () => {
          if (/^\d+(?:\.\d+)?$/.test(row.inputs[field]) && Number.isFinite(Number(row.inputs[field]))) {
            input.value = inputNumber.format(row.inputs[field]);
          }
        });
        inputs.push(input);
        cell.append(input);
        if (field === "duration_seconds" && exercise.kind === "timed" && !row.pending) {
          cell.classList.add("workout-duration");
          const key = keyFor(exercise, row);
          const timer = button(timers[key] ? "■" : "▷", timers[key] ? labels.stopTimer : labels.startTimer, () => {
            if (timers[key]) {
              row.inputs.duration_seconds = Math.max(1, Math.round((Date.now() - timers[key]) / 1000));
              delete timers[key];
              updateDraft(exercise, row);
            } else {
              timers[key] = Date.now();
              store();
            }
            renderRow(exercise, row);
          }, "workout-row-timer");
          timer.dataset.timerKey = key;
          timer.setAttribute("aria-pressed", String(Boolean(timers[key])));
          cell.append(timer);
        }
      }
      tableRow.append(cell);
    }
    const actions = el("td", "workout-row-actions");
    const extra = !row.target;
    const validate = (input) => {
      const field = input.dataset.field;
      const value = row.inputs[field];
      const pattern = field === "weight_kg" ? /^\d+(?:\.\d+)?$/ : /^\d+$/;
      const max = field === "weight_kg" ? 10000 : 2147483647;
      input.setCustomValidity(pattern.test(String(value)) && Number(value) <= max ? "" : labels.invalidNumber);
      return input.reportValidity();
    };
    const completed = row.logged && !row.editing;
    const primary = button(
      row.pending ? "…" : completed || row.editing ? "✓" : "○",
      row.pending ? labels.saving : completed ? labels.setActions : row.editing ? labels.saveSet : labels.completeSet,
      () => {
        if (pending || finishing || completed) return;
        const key = keyFor(exercise, row);
        if (exercise.kind === "timed" && timers[key]) {
          row.inputs.duration_seconds = Math.max(1, Math.round((Date.now() - timers[key]) / 1000));
          inputs[0].value = inputNumber.format(row.inputs.duration_seconds);
          delete timers[key];
          updateDraft(exercise, row);
        }
        if (inputs.every(validate)) saveSet(exercise, row, row.logged ? "edit" : "log", setNumber);
      },
      "workout-check",
    );
    primary.disabled = Boolean(row.pending);
    const discardExtra = () => {
      if (window.confirm(labels.confirmDeleteExtra)) {
        if (row.logged) saveSet(exercise, row, "undo", setNumber, true);
        else removeExtra(exercise, row);
      }
    };
    if (completed && !row.pending) {
      const menuActions = [
        [labels.editSet, () => {
          row.editing = true;
          renderRow(exercise, row);
          row.node.querySelector("input")?.focus();
        }],
        [labels.undoSet, () => saveSet(exercise, row, "undo", setNumber)],
      ];
      if (extra) menuActions.push([labels.deleteExtra, discardExtra]);
      actions.append(actionMenu(primary, menuActions));
    } else {
      actions.append(primary);
      if (!row.pending && (row.editing || extra)) {
        const ancillary = button("···", labels.setActions, null, "workout-row-secondary");
        actions.append(actionMenu(ancillary, [
          row.editing ? [labels.cancel, () => {
            delete drafts[keyFor(exercise, row)];
            row.inputs = valuesFor(row);
            row.editing = false;
            row.error = false;
            store();
            renderRow(exercise, row);
            row.node.querySelector(".workout-check")?.focus();
          }] : [labels.deleteExtra, discardExtra],
        ]));
      }
    }
    for (const input of inputs) {
      input.addEventListener("keydown", (event) => {
        if (event.key === "Enter") {
          event.preventDefault();
          primary.focus();
        }
      });
    }
    tableRow.append(actions);
    if (row.node?.isConnected) row.node.replaceWith(tableRow);
    row.node = tableRow;
    return tableRow;
  }

  function renderExercise(exercise) {
    const head = exercise.card.querySelector("[data-head]");
    const names = [
      exercise.kind === "cardio" ? labels.interval : labels.set, labels.previous,
      ...columns(exercise).map(([, label]) => label), labels.done,
    ];
    head.replaceChildren(...names.map((label, index) => {
      const cell = el("th", "", label);
      cell.scope = "col";
      if (index === 0) {
        const mark = el("span", "", "#");
        mark.setAttribute("aria-hidden", "true");
        cell.replaceChildren(mark, el("span", "sr-only", label));
      }
      if (label === labels.previous) cell.title = labels.previousTitle;
      return cell;
    }));
    const body = exercise.card.querySelector("[data-rows]");
    body.replaceChildren(...exercise.rows.map((row) => renderRow(exercise, row)));
  }

  async function request(url, data) {
    const response = await fetch(url, {
      method: "POST",
      credentials: "same-origin",
      headers: { "X-CSRFToken": csrf, "X-Requested-With": "XMLHttpRequest" },
      body: data,
    });
    if (!response.headers.get("content-type")?.includes("application/json")) throw new Error(labels.error);
    const payload = await response.json();
    if (!response.ok) {
      const error = new Error(payload.error || labels.error);
      error.incomplete = payload.incomplete;
      throw error;
    }
    return payload;
  }

  function removeExtra(exercise, row) {
    const key = keyFor(exercise, row);
    delete drafts[key];
    delete timers[key];
    extras[exercise.id] = (extras[exercise.id] || []).filter((item) => item.key !== row.key);
    exercise.rows = exercise.rows.filter((item) => item !== row);
    row.node.remove();
    exercise.card.querySelector('[data-action="add"]').focus({ preventScroll: true });
    progress();
    store();
  }

  async function saveSet(exercise, row, operation, setNumber, removeSlot = false) {
    if (pending || finishing) return;
    const key = keyFor(exercise, row);
    const data = new FormData();
    data.set("operation", operation);
    data.set("logged_id", row.logged?.id ?? "");
    data.set("set_number", setNumber);
    for (const field of fields) data.set(field, row.inputs[field] ?? empty[field]);
    if (operation === "log") {
      const editingDefaults = {};
      for (const field of fields) editingDefaults[field] = row.inputs[field] ?? empty[field];
      drafts[key] = { loggedId: null, values: editingDefaults };
      store();
    }
    row.pending = true;
    row.error = false;
    pending++;
    finish.disabled = true;
    renderRow(exercise, row);
    inform(labels.saving);
    try {
      const payload = await request(exercise.card.dataset.logUrl, data);
      row.logged = payload.set;
      row.editing = false;
      delete drafts[key];
      delete timers[key];
      if (operation === "undo" && (removeSlot || row.key.startsWith("legacy-"))) {
        removeExtra(exercise, row);
      } else {
        if (!row.target && !row.defaults) {
          row.defaults = { ...empty, set_number: setNumber };
          (extras[exercise.id] ||= []).push({ key: row.key, defaults: row.defaults });
        }
        row.inputs = valuesFor(row);
      }
      progress();
      inform(
        payload.new_record ? `★ ${labels.newRecord}` :
          operation === "undo" ? labels.undone : operation === "edit" ? labels.updated : labels.logged,
        payload.new_record ? "record" : "success",
      );
      store();
    } catch (error) {
      row.error = true;
      inform(error instanceof TypeError ? labels.error : error.message, "error");
    } finally {
      pending--;
      finish.disabled = false;
      row.pending = false;
      if (row.node.isConnected) {
        renderRow(exercise, row);
        if (document.activeElement === document.body) row.node.querySelector(".workout-check")?.focus({ preventScroll: true });
      }
    }
  }

  const started = Date.parse(root.dataset.started);
  function tick() {
    byId("workout-elapsed").textContent = clock(Math.floor((Date.now() - started) / 1000));
    for (const control of root.querySelectorAll("[data-timer-key]")) {
      const time = timers[control.dataset.timerKey];
      if (time) control.textContent = clock(Math.floor((Date.now() - time) / 1000));
    }
  }

  function openPreview(exercise, trigger) {
    if (typeof preview.showModal !== "function") return false;
    previewTrigger = trigger;
    byId("workout-preview-title").textContent = exercise.name;
    byId("workout-preview-muscles").textContent = exercise.all_muscles.join(" · ") || labels.noMuscles;
    byId("workout-preview-equipment").textContent = exercise.equipment.join(" · ") || labels.noEquipment;
    byId("workout-preview-instructions").textContent = exercise.instructions || labels.noInstructions;
    const image = byId("workout-preview-image");
    const fallback = byId("workout-preview-empty");
    image.onerror = () => {
      if (exercise.thumbnail && image.getAttribute("src") !== exercise.thumbnail) image.src = exercise.thumbnail;
      else {
        image.hidden = true;
        fallback.hidden = false;
      }
    };
    const source = exercise.animation || exercise.thumbnail;
    fallback.hidden = Boolean(source);
    image.hidden = !source;
    if (source) image.src = source;
    preview.showModal();
    preview.querySelector("[data-close]").focus();
    return true;
  }

  preview.addEventListener("close", () => {
    const image = byId("workout-preview-image");
    image.onerror = null;
    image.removeAttribute("src");
    previewTrigger?.focus({ preventScroll: true });
  });
  for (const dialog of [preview, completion]) {
    dialog.querySelectorAll("[data-close]").forEach((control) => {
      control.addEventListener("click", () => { if (!finishing) dialog.close(); });
    });
    dialog.addEventListener("click", (event) => {
      if (event.target === dialog && !finishing) dialog.close();
    });
  }

  function setExpanded(exercise, expanded) {
    const control = exercise.card.querySelector('[data-action="collapse"]');
    byId(control.getAttribute("aria-controls")).hidden = !expanded;
    control.setAttribute("aria-expanded", String(expanded));
    control.setAttribute("aria-label", expanded ? labels.collapse : labels.expand);
  }

  for (const exercise of exercises) {
    const card = exercise.card;
    const trigger = card.querySelector("[data-preview]");
    trigger.addEventListener("click", (event) => {
      if (!event.ctrlKey && !event.metaKey && !event.shiftKey && !event.altKey && openPreview(exercise, trigger)) {
        event.preventDefault();
      }
    });
    card.querySelector('[data-action="collapse"]').addEventListener("click", (event) => {
      exercise.autoCollapsed = false;
      setExpanded(exercise, event.currentTarget.getAttribute("aria-expanded") !== "true");
    });
    const weight = card.querySelector('[data-action="weight"]');
    if (weight) {
      weight.setAttribute("aria-pressed", String(exercise.weighted));
      weight.addEventListener("click", () => {
        exercise.weighted = !exercise.weighted;
        weight.setAttribute("aria-pressed", String(exercise.weighted));
        const menu = weight.closest("details");
        menu.open = false;
        menu.querySelector("summary").focus();
        renderExercise(exercise);
      });
    }
    card.querySelector('[data-action="add"]').addEventListener("click", () => {
      if (finishing) return;
      const last = exercise.rows.at(-1);
      const next = Math.max(0, ...exercise.rows.map((row) => Number(row.logged?.set_number ?? row.target?.set_number ?? row.defaults.set_number))) + 1;
      const defaults = { ...valuesFor(last || {}), set_number: next };
      const row = { key: String(next), defaults, logged: null, target: null, inputs: { ...defaults } };
      (extras[exercise.id] ||= []).push({ key: row.key, defaults });
      exercise.rows.push(row);
      store();
      card.querySelector("[data-rows]").append(renderRow(exercise, row));
      row.node.querySelector("input")?.focus();
    });
    renderExercise(exercise);
  }

  function setIncomplete(incomplete) {
    byId("workout-incomplete").hidden = !incomplete;
    form.elements.allow_incomplete.value = incomplete ? "yes" : "no";
    form.querySelector('button[type="submit"]').textContent = incomplete ? labels.finishIncomplete : labels.finish;
  }

  finish.addEventListener("click", () => {
    if (pending || finishing) return;
    byId("workout-completion-error").hidden = true;
    setIncomplete(progress() > 0);
    completion.showModal();
  });
  completion.addEventListener("cancel", (event) => {
    if (finishing) event.preventDefault();
  });
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (pending || finishing) return;
    const submit = form.querySelector('button[type="submit"]');
    const errorBox = byId("workout-completion-error");
    errorBox.hidden = true;
    submit.disabled = true;
    finishing = true;
    try {
      const result = await request(form.action, new FormData(form));
      try { localStorage.removeItem(storageKey); } catch { /* No persisted data to remove. */ }
      window.removeEventListener("beforeunload", guardDrafts);
      window.location.assign(result.url);
    } catch (error) {
      errorBox.textContent = error instanceof TypeError ? labels.error : error.message;
      errorBox.hidden = false;
      if (error.incomplete) setIncomplete(true);
      submit.disabled = false;
      finishing = false;
    }
  });

  function guardDrafts(event) {
    if (!pending && !finishing && !Object.keys(drafts).length && !form.elements.notes.value && !form.elements.rating.value) return;
    event.preventDefault();
    event.returnValue = true;
  }
  window.addEventListener("beforeunload", guardDrafts);
  document.addEventListener("click", (event) => {
    if (openMenu && !openMenu.menu.contains(event.target)) closeMenu();
    root.querySelectorAll(".workout-exercise-menu[open]").forEach((panel) => {
      if (!panel.contains(event.target)) panel.open = false;
    });
  }, true);
  document.addEventListener("keydown", (event) => {
    if (event.key !== "Escape") return;
    if (openMenu) closeMenu(true);
    const details = root.querySelector(".workout-exercise-menu[open]");
    if (details) {
      details.open = false;
      details.querySelector("summary").focus();
    }
  });
  progress();
  for (const exercise of exercises) {
    if (exercise.card.dataset.status === "upcoming"
        && !exercise.rows.some((row) => row.logged || drafts[keyFor(exercise, row)] || timers[keyFor(exercise, row)])) {
      exercise.autoCollapsed = true;
      setExpanded(exercise, false);
    }
  }
  tick();
  store();
  window.setInterval(tick, 250);
})();
