(() => {
  const root = document.getElementById("workout-builder");
  if (!root) return;

  const source = JSON.parse(document.getElementById("builder-data").textContent);
  const labelsElement = document.getElementById("builder-labels");
  const labels = Object.fromEntries(
    Array.from(labelsElement.attributes)
      .filter((attribute) => attribute.name.startsWith("data-"))
      .map((attribute) => [attribute.name.slice(5).replace(/-([a-z])/g, (_, letter) => letter.toUpperCase()), attribute.value]),
  );
  const controls = {
    programName: document.getElementById("builder-program-name"),
    programTitle: document.getElementById("builder-program-title"),
    programSettings: document.getElementById("builder-program-settings"),
    days: document.getElementById("builder-days"),
    addDay: document.getElementById("builder-add-day"),
    reorderDays: document.getElementById("builder-reorder-days"),
    daySettings: document.getElementById("builder-day-settings"),
    dayName: document.getElementById("builder-day-name"),
    dayDuration: document.getElementById("builder-day-duration"),
    dayDescription: document.getElementById("builder-day-description"),
    removeDay: document.getElementById("builder-remove-day"),
    editDay: document.getElementById("builder-edit-day"),
    selectedExercises: document.getElementById("builder-selected-exercises"),
    exerciseTitle: document.getElementById("builder-exercises-title"),
    exerciseCount: document.getElementById("builder-exercise-count"),
    reorderExercises: document.getElementById("builder-reorder-exercises"),
    emptyDay: document.getElementById("builder-empty-day"),
    library: document.getElementById("builder-library"),
    libraryList: document.getElementById("builder-library-list"),
    libraryCount: document.getElementById("builder-library-result-count"),
    search: document.getElementById("builder-search"),
    clearSearch: document.getElementById("builder-clear-search"),
    category: document.getElementById("builder-category"),
    selectionCount: document.getElementById("builder-selection-count"),
    addSelected: document.getElementById("builder-add-selected"),
    addSelectedInline: document.getElementById("builder-add-selected-inline"),
    openLibrary: document.getElementById("builder-open-library"),
    closeLibrary: document.getElementById("builder-close-library"),
    save: document.getElementById("builder-save"),
    status: document.getElementById("builder-save-status"),
    statusText: document.getElementById("builder-save-status-text"),
    preview: document.getElementById("exercise-preview-dialog"),
    previewTitle: document.getElementById("exercise-preview-title"),
    previewImage: document.getElementById("exercise-preview-image"),
    previewNoImage: document.getElementById("exercise-preview-no-image"),
    previewDescription: document.getElementById("exercise-preview-description"),
    previewMuscles: document.getElementById("exercise-preview-muscles"),
    previewEquipment: document.getElementById("exercise-preview-equipment"),
    previewInstructions: document.getElementById("exercise-preview-instructions"),
    previewAdd: document.getElementById("exercise-preview-add"),
  };
  const exerciseById = new Map(
    [...source.exercises, ...source.retired_exercises].map((exercise) => [exercise.id, exercise]),
  );
  const programGoal = document.getElementById("builder-program-goal");
  const goalLabel = document.getElementById("builder-program-goal-label");
  const cardioIds = new Set(source.cardio_ids);
  const catalogIds = source.exercises.map((exercise) => exercise.id);
  const allowedIds = (goal) => goal === "cardio" ? source.cardio_ids : catalogIds;
  let editor = null;
  const advancedOpen = new WeakSet();
  const removedExercises = new WeakMap();
  const state = {
    programName: source.program.name,
    goal: source.program.goal,
    revision: source.revision,
    days: source.days.map((day) => ({
      ...day,
      client_key: `day-${day.id}`,
      exercises: day.exercises.map((exercise) => ({
        ...exercise,
        name: exerciseById.get(exercise.exercise_id).name,
        rest_seconds: Number(exercise.rest_seconds),
        notes: exercise.notes || "",
        removed_set_ids: [],
        sets: exercise.sets.map((set) => ({ ...set })),
      })),
    })),
    activeKey: null,
    selectedExercises: new Set(),
    collapsedExercises: new Set(),
    reorderingDays: false,
    reorderingExercises: false,
    dirty: false,
    saving: false,
    previewExerciseId: null,
    lastPreviewTrigger: null,
    lastLibraryOpener: null,
  };
  const selectedDayId = root.dataset.selectedPlanId;
  const activeDay = () => state.days.find((day) => day.client_key === state.activeKey) || null;
  const dayUrl = (day) => day?.id
    ? root.dataset.dayUrlTemplate.replace(/0\/?$/, `${day.id}/`)
    : root.dataset.programUrl;

  function syncDayUrl() {
    const url = dayUrl(activeDay());
    window.history.replaceState(null, "", url);
    const languageRedirect = document.querySelector('.language-switcher input[name="next"]');
    if (languageRedirect) languageRedirect.value = url;
  }

  const makeDay = () => {
    const names = new Set(state.days.map((day) => day.name.toLocaleLowerCase()));
    let number = state.days.length + 1;
    let name = `${labels.dayPrefix || "Day"} ${number}`;
    while (names.has(name.toLocaleLowerCase())) {
      number += 1;
      name = `${labels.dayPrefix || "Day"} ${number}`;
    }
    return {
      id: null,
      client_key: `draft-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      name,
      description: "",
      estimated_duration_minutes: 45,
      goal: state.goal || source.default_day_goal,
      allowed_exercise_ids: allowedIds(state.goal || source.default_day_goal),
      exercises: [],
    };
  };
  const setStatus = (text, error = false) => {
    controls.statusText.textContent = text;
    controls.status.classList.toggle("is-error", error);
    controls.status.classList.toggle("is-unsaved", text === labels.unsaved);
    controls.status.classList.toggle("is-saving", text === labels.saving);
    controls.status.classList.toggle("is-success", text === labels.saveSuccess);
  };
  const markDirty = () => {
    state.dirty = true;
    setStatus(labels.unsaved);
  };
  const createElement = (tag, className, text) => {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (text !== undefined) element.textContent = text;
    return element;
  };
  const makeButton = (text, className, ariaLabel, action) => {
    const button = createElement("button", className, text);
    button.type = "button";
    if (ariaLabel) button.setAttribute("aria-label", ariaLabel);
    if (action) button.dataset.action = action;
    return button;
  };
  const isMixed = (sets, field) => sets.some((set) => set[field] !== sets[0]?.[field]);
  const commonValue = (sets, field) => sets.length && !isMixed(sets, field) ? sets[0][field] : null;

  if (root.dataset.startNewDay === "true" || !state.days.length) {
    const firstDay = makeDay();
    state.days.push(firstDay);
    state.activeKey = firstDay.client_key;
    state.dirty = true;
    setStatus(labels.unsaved);
  } else {
    const selected = state.days.find((day) => String(day.id) === selectedDayId);
    state.activeKey = (selected || state.days[0]).client_key;
  }
  controls.programName.value = state.programName;
  controls.programTitle.textContent = state.programName;

  function moveItem(items, from, to) {
    if (from < 0 || from >= items.length || to < 0 || to >= items.length || from === to) return false;
    const [item] = items.splice(from, 1);
    items.splice(to, 0, item);
    return true;
  }

  function moveDay(key, offset) {
    const index = state.days.findIndex((day) => day.client_key === key);
    if (moveItem(state.days, index, index + offset)) {
      markDirty();
      renderDays();
    }
  }

  function renderDays() {
    controls.days.replaceChildren();
    state.days.forEach((day, index) => {
      const wrapper = createElement("div", "builder-day-tab");
      wrapper.dataset.dayKey = day.client_key;
      wrapper.draggable = state.reorderingDays;
      if (day.client_key === state.activeKey) wrapper.classList.add("is-active");
      const select = makeButton(day.name || `${labels.dayPrefix || "Day"} ${index + 1}`, "builder-day-select", "", "select-day");
      select.setAttribute("aria-current", String(day.client_key === state.activeKey));
      select.dataset.dayKey = day.client_key;
      wrapper.append(select);
      if (state.reorderingDays) {
        const moveUp = makeButton("↑", "builder-reorder-step", `${labels.moveUp}: ${day.name}`, "move-day-up");
        const moveDown = makeButton("↓", "builder-reorder-step", `${labels.moveDown}: ${day.name}`, "move-day-down");
        moveUp.dataset.dayKey = day.client_key;
        moveDown.dataset.dayKey = day.client_key;
        moveUp.disabled = index === 0;
        moveDown.disabled = index === state.days.length - 1;
        wrapper.append(moveUp, moveDown);
      }
      controls.days.append(wrapper);
    });
    controls.addDay.disabled = state.days.length >= 50;
    controls.reorderDays.disabled = state.days.length < 2;
    controls.reorderDays.setAttribute("aria-pressed", String(state.reorderingDays));
    controls.reorderDays.setAttribute("aria-label", labels.reorderDays);
    controls.reorderDays.querySelector("span:last-child").textContent =
      state.reorderingDays ? labels.reorderDone : labels.reorderDays;
    controls.reorderDays.classList.toggle("is-active", state.reorderingDays);
  }

  function numberText(value) {
    return value.trim()
      .replace(/[٠-٩]/g, (digit) => String(digit.charCodeAt(0) - 0x660))
      .replace(/[۰-۹]/g, (digit) => String(digit.charCodeAt(0) - 0x6f0))
      .replace(/[٫,]/g, ".");
  }

  function parseNumber(value) {
    return /^\d+(?:\.\d+)?$/.test(value) ? Number(value) : NaN;
  }

  function makeInputField(labelText, value, options = {}) {
    const wrapper = createElement("label", "builder-basic-field");
    const label = createElement("span", "", labelText);
    const input = document.createElement("input");
    input.type = "text";
    input.inputMode = options.step === "any" ? "decimal" : "numeric";
    input.dir = "ltr";
    if (value !== null && value !== undefined && value !== "") input.value = value;
    if (value === null) input.placeholder = labels.mixed;
    input.dataset.exerciseField = options.field;
    input.dataset.exerciseIndex = options.exerciseIndex;
    if (options.field === "set_count") {
      input.setAttribute("aria-label", `${labelText}, ${options.exerciseName}`);
    }
    wrapper.append(label, input);
    return wrapper;
  }

  function setSummary(exercise, kind) {
    const setCount = exercise.sets.length;
    const setLabel = setCount === 1 ? labels.set.toLocaleLowerCase() : labels.setsLower;
    const parts = [`${setCount} ${setLabel}`];
    if (!exercise.sets.length) return parts.join(" · ");
    const reps = commonValue(exercise.sets, "reps");
    const duration = commonValue(exercise.sets, "duration_seconds");
    const weight = commonValue(exercise.sets, "weight_kg");
    if (kind === "resistance" || kind === "bodyweight") {
      parts.push(reps === null ? labels.mixed : `${reps} ${labels.repetitions.toLocaleLowerCase()}`);
    }
    if (kind === "timed" || kind === "cardio") {
      const durationSummary = duration === null
        ? labels.mixed
        : kind === "cardio" && duration % 60 === 0
          ? `${duration / 60} ${labels.minutes}` : `${duration} ${labels.seconds}`;
      parts.push(durationSummary);
    }
    if (kind === "resistance" && weight !== null && Number(weight) > 0) {
      parts.push(`${weight} ${labels.kilograms}`);
    } else if (kind === "resistance" && weight === null) {
      parts.push(labels.mixed);
    }
    if (kind !== "cardio" || exercise.sets.length > 1) {
      parts.push(`${exercise.rest_seconds} ${labels.restShort}`);
    }
    return parts.join(" · ");
  }

  function makeCommonField(exercise, index, label, setField, options = {}) {
    const value = commonValue(exercise.sets, setField);
    const fieldValue = options.toInput && value !== null ? options.toInput(value) : value;
    const wrapper = makeInputField(label, fieldValue, {
      field: options.field,
      exerciseIndex: index,
      exerciseName: exercise.name,
      min: "0",
      step: options.step || "1",
      max: options.max,
    });
    if (value === null && exercise.sets.length > 1) wrapper.classList.add("is-mixed");
    return wrapper;
  }

  function makeAdvancedField(labelText, value, field, exerciseIndex, setIndex, options = {}) {
    const label = createElement("label", "builder-table-field");
    label.append(createElement("span", "sr-only", `${labelText}, ${labels.set} ${setIndex + 1}`));
    const input = document.createElement("input");
    input.type = "text";
    input.inputMode = field === "weight_kg" || options.minutes ? "decimal" : "numeric";
    input.dir = "ltr";
    input.value = field === "weight_kg" && Number(value) === 0 ? "" : value;
    input.dataset.setField = field;
    input.dataset.exerciseIndex = exerciseIndex;
    input.dataset.setIndex = setIndex;
    if (options.minutes) input.value = Number(value) / 60;
    label.append(input);
    const cell = document.createElement("td");
    cell.append(label);
    return cell;
  }

  function renderAdvancedSettings(exercise, index, kind) {
    const details = document.createElement("details");
    details.className = "builder-advanced";
    details.open = advancedOpen.has(exercise);
    details.addEventListener("toggle", () => {
      if (details.open) advancedOpen.add(exercise);
      else advancedOpen.delete(exercise);
    });
    const summary = createElement("summary", "", labels.advanced);
    details.append(summary);
    const tableWrap = createElement("div", "builder-set-table-wrap");
    const table = document.createElement("table");
    table.className = "builder-set-table";
    const header = document.createElement("thead");
    const headerRow = document.createElement("tr");
    const columns = [labels.set];
    if (kind === "resistance" || kind === "bodyweight") columns.push(labels.repetitions);
    if (kind === "resistance") columns.push(labels.weight);
    if (kind === "cardio") columns.push(labels.durationMinutes);
    else if (kind === "timed") columns.push(labels.duration);
    columns.push(labels.setType, labels.remove);
    columns.forEach((text) => headerRow.append(createElement("th", "", text)));
    header.append(headerRow);
    table.append(header);
    const body = document.createElement("tbody");
    exercise.sets.forEach((set, setIndex) => {
      const row = document.createElement("tr");
      row.append(createElement("th", "builder-set-number", `${labels.set} ${setIndex + 1}`));
      if (kind === "resistance" || kind === "bodyweight") {
        row.append(makeAdvancedField(labels.repetitions, set.reps, "reps", index, setIndex));
      }
      if (kind === "resistance") {
        row.append(makeAdvancedField(labels.weight, set.weight_kg, "weight_kg", index, setIndex));
      }
      if (kind === "timed" || kind === "cardio") {
        const durationField = kind === "cardio" ? "duration_minutes" : "duration_seconds";
        const durationLabel = kind === "cardio" ? labels.durationMinutes : labels.duration;
        row.append(makeAdvancedField(durationLabel, set.duration_seconds, durationField, index, setIndex, { minutes: kind === "cardio" }));
      }
      const typeCell = document.createElement("td");
      const typeSelect = document.createElement("select");
      typeSelect.setAttribute("aria-label", `${labels.setType}, ${labels.set} ${setIndex + 1}`);
      typeSelect.dataset.setField = "set_type";
      typeSelect.dataset.exerciseIndex = index;
      typeSelect.dataset.setIndex = setIndex;
      [
        ["normal", labels.normal],
        ["warmup", labels.warmup],
        ["drop_set", labels.dropSet],
        ["failure", labels.failure],
      ].forEach(([value, text]) => {
        const option = document.createElement("option");
        option.value = value;
        option.textContent = text;
        typeSelect.append(option);
      });
      typeSelect.value = set.set_type;
      typeCell.append(typeSelect);
      row.append(typeCell);
      const removeCell = document.createElement("td");
      const removeSet = makeButton("×", "builder-remove-set", `${labels.remove}: ${labels.set} ${setIndex + 1}`, "remove-set");
      removeSet.dataset.setIndex = setIndex;
      removeSet.disabled = exercise.sets.length <= 1;
      removeCell.append(removeSet);
      row.append(removeCell);
      body.append(row);
    });
    table.append(body);
    tableWrap.append(table);
    details.append(tableWrap);
    const footer = createElement("div", "builder-advanced-footer");
    const addSet = makeButton(`+ ${kind === "cardio" ? labels.addInterval : labels.addSet}`, "builder-add-set", "", "add-set");
    addSet.disabled = exercise.sets.length >= 50;
    footer.append(addSet);
    details.append(footer);
    const notes = document.createElement("label");
    notes.className = "builder-notes-field";
    notes.append(createElement("span", "", labels.notes));
    const textarea = document.createElement("textarea");
    textarea.rows = 2;
    textarea.maxLength = 255;
    textarea.value = exercise.notes;
    textarea.dataset.exerciseField = "notes";
    textarea.dataset.exerciseIndex = index;
    notes.append(textarea);
    details.append(notes);
    return details;
  }

  function renderExerciseCard(exercise, index) {
    const libraryExercise = exerciseById.get(exercise.exercise_id);
    if (!libraryExercise) return null;
    const collapsed = state.collapsedExercises.has(exercise.exercise_id);
    const card = createElement("article", "builder-exercise-card");
    card.dataset.exerciseIndex = index;
    card.dataset.exerciseId = exercise.exercise_id;
    card.draggable = state.reorderingExercises;
    if (state.reorderingExercises) card.classList.add("is-reordering");

    const header = createElement("div", "builder-exercise-heading");
    const preview = makeButton("", "builder-exercise-preview", `${labels.preview}: ${exercise.name}`, "preview-exercise");
    preview.dataset.exerciseId = exercise.exercise_id;
    if (libraryExercise.thumbnail) {
      const image = document.createElement("img");
      image.className = "exercise-thumbnail exercise-thumbnail--selected";
      image.src = libraryExercise.thumbnail;
      image.alt = "";
      image.width = 64;
      image.height = 64;
      image.loading = "lazy";
      image.decoding = "async";
      preview.append(image);
    }
    const title = createElement("span", "builder-exercise-title");
    title.append(createElement("strong", "", libraryExercise.name));
    title.append(createElement("small", "muted", setSummary(exercise, libraryExercise.kind)));
    preview.append(title);
    preview.append(createElement("span", "builder-preview-indicator", "↗"));
    header.append(preview);

    const actions = createElement("div", "builder-exercise-actions");
    if (state.reorderingExercises) {
      const moveUp = makeButton("↑", "builder-reorder-step", `${labels.moveUp}: ${exercise.name}`, "move-exercise-up");
      const moveDown = makeButton("↓", "builder-reorder-step", `${labels.moveDown}: ${exercise.name}`, "move-exercise-down");
      moveUp.disabled = index === 0;
      moveDown.disabled = index === activeDay().exercises.length - 1;
      actions.append(moveUp, moveDown);
    }
    const collapse = makeButton(collapsed ? "+" : "−", "builder-collapse-button", collapsed ? labels.expand : labels.collapse, "toggle-exercise");
    collapse.setAttribute("aria-expanded", String(!collapsed));
    actions.append(collapse);
    const menu = document.createElement("details");
    menu.className = "builder-popover builder-exercise-menu";
    const menuSummary = createElement("summary", "", "···");
    menuSummary.setAttribute("aria-label", labels.moreActions);
    menu.append(menuSummary);
    const menuContent = createElement("div", "builder-popover-content");
    menuContent.append(makeButton(labels.removeExercise, "builder-menu-action is-danger", "", "remove-exercise"));
    menu.append(menuContent);
    actions.append(menu);
    header.append(actions);
    card.append(header);

    if (collapsed) {
      const summary = createElement("p", "builder-collapsed-summary", setSummary(exercise, libraryExercise.kind));
      card.append(summary);
    } else {
      const fields = createElement("div", "builder-basic-fields");
      const countLabel = libraryExercise.kind === "cardio" ? labels.intervalCount : labels.setCount;
      fields.append(makeInputField(countLabel, exercise.sets.length, {
        field: "set_count",
        exerciseIndex: index,
        exerciseName: exercise.name,
        max: "50",
      }));
      const hasMixed = (
        ((libraryExercise.kind === "resistance" || libraryExercise.kind === "bodyweight") && isMixed(exercise.sets, "reps"))
        || (libraryExercise.kind === "resistance" && isMixed(exercise.sets, "weight_kg"))
        || ((libraryExercise.kind === "timed" || libraryExercise.kind === "cardio") && isMixed(exercise.sets, "duration_seconds"))
      );
      if (libraryExercise.kind === "resistance" || libraryExercise.kind === "bodyweight") {
        fields.append(makeCommonField(exercise, index, labels.repetitions, "reps", { field: "basic_reps" }));
      }
      if (libraryExercise.kind === "resistance") {
        fields.append(makeCommonField(exercise, index, labels.weight, "weight_kg", {
          field: "basic_weight",
          step: "any",
        }));
      }
      if (libraryExercise.kind === "timed" || libraryExercise.kind === "cardio") {
        const isCardio = libraryExercise.kind === "cardio";
        fields.append(makeCommonField(
          exercise,
          index,
          isCardio ? labels.durationMinutes : labels.duration,
          "duration_seconds",
          {
            field: isCardio ? "basic_duration_minutes" : "basic_duration_seconds",
            toInput: isCardio ? (value) => Number(value) / 60 : null,
            step: isCardio ? "any" : "1",
          },
        ));
      }
      if (libraryExercise.kind !== "cardio" || exercise.sets.length > 1) {
        fields.append(makeInputField(labels.rest, exercise.rest_seconds, {
          field: "rest_seconds",
          exerciseIndex: index,
          exerciseName: exercise.name,
        }));
      }
      card.append(fields);
      const mixedHint = createElement("p", "builder-mixed-hint", labels.valuesVary);
      mixedHint.hidden = !hasMixed;
      card.append(mixedHint);
      card.append(renderAdvancedSettings(exercise, index, libraryExercise.kind));
    }
    return card;
  }

  function renderSelected() {
    const day = activeDay();
    controls.selectedExercises.replaceChildren();
    if (!day) {
      controls.exerciseTitle.textContent = labels.dayPrefix;
      controls.exerciseCount.textContent = "";
      controls.emptyDay.hidden = false;
      controls.removeDay.disabled = true;
      controls.editDay.disabled = true;
      controls.reorderExercises.disabled = true;
      controls.openLibrary.disabled = true;
      controls.addSelectedInline.disabled = true;
      controls.emptyDay.querySelector("button").disabled = true;
      return;
    }
    controls.removeDay.disabled = false;
    controls.editDay.disabled = false;
    controls.reorderExercises.disabled = day.exercises.length < 2;
    controls.openLibrary.disabled = false;
    controls.addSelectedInline.disabled = false;
    controls.emptyDay.querySelector("button").disabled = false;
    controls.exerciseTitle.textContent = day.name;
    controls.exerciseCount.textContent = `${labels.exerciseCount} · ${day.exercises.length}`;
    controls.emptyDay.hidden = day.exercises.length > 0;
    day.exercises.forEach((exercise, index) => {
      const card = renderExerciseCard(exercise, index);
      if (card) controls.selectedExercises.append(card);
    });
  }

  function renderCategoryOptions() {
    const day = activeDay();
    if ((state.goal || day?.goal) === "cardio") {
      const option = document.createElement("option");
      option.value = "";
      option.textContent = labels.cardioOnly;
      controls.category.replaceChildren(option);
      return;
    }
    const available = source.exercises.filter((exercise) => (
      !day || !Array.isArray(day.allowed_exercise_ids) || day.allowed_exercise_ids.includes(exercise.id)
    ));
    const currentValue = controls.category.value;
    const options = new Map();
    available.forEach((exercise) => options.set(exercise.category_key, exercise.category));
    controls.category.replaceChildren();
    const allOption = document.createElement("option");
    allOption.value = "";
    allOption.textContent = controls.category.dataset.allLabel || labels.allCategories || "";
    controls.category.append(allOption);
    options.forEach((name, key) => {
      const option = document.createElement("option");
      option.value = key;
      option.textContent = name;
      controls.category.append(option);
    });
    controls.category.value = options.has(currentValue) ? currentValue : "";
  }

  function renderLibrary() {
    const day = activeDay();
    const term = controls.search.value.trim().toLocaleLowerCase();
    const cardioOnly = (state.goal || day?.goal) === "cardio";
    const categoryKey = controls.category.value;
    const added = new Set(day ? day.exercises.map((exercise) => exercise.exercise_id) : []);
    const filtered = source.exercises.filter((exercise) => {
      const allowed = !day || !Array.isArray(day.allowed_exercise_ids)
        || day.allowed_exercise_ids.includes(exercise.id);
      const searchText = [
        exercise.name,
        exercise.english_name,
        exercise.arabic_name,
        exercise.category,
        exercise.group,
        cardioOnly && exercise.conditioning ? labels.conditioning : "",
        ...(exercise.muscles || []).map((muscle) => muscle.name),
        ...(exercise.equipment || []),
      ].join(" ").toLocaleLowerCase();
      return allowed && (!term || searchText.includes(term))
        && (!categoryKey || exercise.category_key === categoryKey);
    });
    controls.libraryList.replaceChildren();
    const grouped = new Map();
    filtered.forEach((exercise) => {
      const groupKey = cardioOnly ? (exercise.conditioning ? "conditioning" : "cardio") :
        `${exercise.category_key}:${exercise.group || ""}`;
      const title = cardioOnly ? (exercise.conditioning ? labels.conditioning : source.goals.cardio) :
        exercise.group || exercise.category;
      if (!grouped.has(groupKey)) grouped.set(groupKey, { title, items: [] });
      grouped.get(groupKey).items.push(exercise);
    });
    grouped.forEach((group) => {
      const section = createElement("section", "builder-library-group");
      section.append(createElement("h3", "builder-library-group-title", group.title));
      const list = createElement("div", "builder-library-items");
      group.items.forEach((exercise) => {
        const alreadyAdded = added.has(exercise.id);
        const item = createElement("article", "builder-library-item");
        if (state.selectedExercises.has(exercise.id)) item.classList.add("is-selected");
        if (alreadyAdded) item.classList.add("is-added");

        const checkbox = document.createElement("input");
        checkbox.type = "checkbox";
        checkbox.id = `library-exercise-${exercise.id}`;
        checkbox.value = exercise.id;
        checkbox.checked = state.selectedExercises.has(exercise.id);
        checkbox.disabled = alreadyAdded;
        checkbox.setAttribute("aria-label", `${labels.addExercise}: ${exercise.name}`);
        checkbox.addEventListener("change", () => {
          if (checkbox.checked) state.selectedExercises.add(exercise.id);
          else state.selectedExercises.delete(exercise.id);
          item.classList.toggle("is-selected", checkbox.checked);
          updateSelectionCount();
        });

        const preview = makeButton("", "builder-library-preview", `${labels.preview}: ${exercise.name}`, "preview-exercise");
        preview.dataset.exerciseId = exercise.id;
        if (exercise.thumbnail) {
          const image = document.createElement("img");
          image.className = "exercise-thumbnail exercise-thumbnail--picker";
          image.src = exercise.thumbnail;
          image.alt = "";
          image.width = 60;
          image.height = 60;
          image.loading = "lazy";
          image.decoding = "async";
          preview.append(image);
        }
        const copy = createElement("span", "builder-library-copy");
        copy.append(createElement("strong", "", exercise.name));
        if (exercise.group) copy.append(createElement("small", "muted", exercise.group));
        preview.append(copy);

        const actions = createElement("div", "builder-library-item-actions");
        if (alreadyAdded) {
          actions.append(createElement("span", "builder-library-added", `✓ ${labels.added}`));
        } else {
          const add = makeButton("+", "builder-library-add-one", `${labels.addExercise}: ${exercise.name}`, "add-one");
          add.dataset.exerciseId = exercise.id;
          actions.append(add);
        }
        item.append(checkbox, preview, actions);
        list.append(item);
      });
      section.append(list);
      controls.libraryList.append(section);
    });
    if (!filtered.length) controls.libraryList.append(createElement("p", "builder-library-empty", labels.noResults));
    const count = filtered.length;
    const form = new Intl.PluralRules(document.documentElement.lang).select(count);
    const key = `available${form[0].toUpperCase()}${form.slice(1)}`;
    controls.libraryCount.textContent = labels[key].replace(/[0-9]+/, String(count));
    controls.clearSearch.hidden = !controls.search.value;
    updateSelectionCount();
  }

  function updateSelectionCount() {
    const count = state.selectedExercises.size;
    controls.selectionCount.textContent = count
      ? `${labels.selected} · ${count}`
      : labels.selectExercises;
    controls.addSelected.disabled = count === 0 || !activeDay();
  }

  function render() {
    renderDays();
    renderSelected();
    renderCategoryOptions();
    renderLibrary();
  }

  function defaultSet(kind) {
    return {
      id: null,
      reps: kind === "resistance" || kind === "bodyweight" ? 10 : 0,
      duration_seconds: kind === "timed" ? 30 : kind === "cardio" ? 1200 : 0,
      weight_kg: 0,
      set_type: "normal",
    };
  }

  function appendSet(exercise) {
    const set = defaultSet(exerciseById.get(exercise.exercise_id).kind);
    for (const field of ["reps", "duration_seconds", "weight_kg"]) {
      set[field] = commonValue(exercise.sets, field) ?? set[field];
    }
    exercise.sets.push(set);
  }

  const basicSetFields = {
    basic_reps: "reps",
    basic_weight: "weight_kg",
    basic_duration_minutes: "duration_seconds",
    basic_duration_seconds: "duration_seconds",
  };

  function syncSetFields(card, exercise) {
    let mixed = false;
    for (const input of card.querySelectorAll("[data-exercise-field]")) {
      const field = basicSetFields[input.dataset.exerciseField];
      if (!field) continue;
      const varies = isMixed(exercise.sets, field);
      const value = commonValue(exercise.sets, field);
      input.value = value === null ? "" : input.dataset.exerciseField === "basic_duration_minutes" ? value / 60 : value;
      input.placeholder = varies ? labels.mixed : "";
      input.closest("label").classList.toggle("is-mixed", varies);
      mixed ||= varies;
    }
    for (const input of card.querySelectorAll("input[data-set-field]")) {
      const set = exercise.sets[Number(input.dataset.setIndex)];
      const field = input.dataset.setField;
      input.value = field === "duration_minutes" ? set.duration_seconds / 60
        : field === "weight_kg" && set.weight_kg === 0 ? "" : set[field];
    }
    card.querySelector(".builder-mixed-hint").hidden = !mixed;
    card.querySelector(".builder-exercise-title small").textContent =
      setSummary(exercise, exerciseById.get(exercise.exercise_id).kind);
  }

  function addExercises(ids, clearSelection = false) {
    const day = activeDay();
    if (!day) return;
    const existing = new Set(day.exercises.map((exercise) => exercise.exercise_id));
    let added = false;
    for (const id of ids) {
      const exercise = exerciseById.get(id);
      if (day.exercises.length >= 100) break;
      if (!exercise || existing.has(id) || !canAddExercise(id, day)) continue;
      const count = exercise.kind === "cardio" ? 1 : 3;
      const removed = removedExercises.get(day);
      day.exercises.push(removed?.get(id) || {
        exercise_id: id,
        name: exercise.name,
        rest_seconds: exercise.kind === "cardio" ? 0 : 90,
        notes: "",
        removed_set_ids: [],
        sets: Array.from({ length: count }, () => defaultSet(exercise.kind)),
      });
      removed?.delete(id);
      existing.add(id);
      state.selectedExercises.delete(id);
      added = true;
    }
    if (clearSelection) state.selectedExercises.clear();
    if (added) markDirty();
    render();
  }

  function canAddExercise(id, day) {
    return Boolean(day && day.exercises.length < 100
      && source.exercises.some((exercise) => exercise.id === id)
      && (!day.allowed_exercise_ids || day.allowed_exercise_ids.includes(id)));
  }

  function openLibrary(trigger) {
    if (!window.matchMedia("(max-width: 900px)").matches) {
      controls.search.focus();
      controls.library.scrollIntoView({ behavior: "smooth", block: "nearest" });
      return;
    }
    state.lastLibraryOpener = trigger;
    controls.library.classList.add("is-open");
    trigger?.setAttribute("aria-expanded", "true");
    document.body.classList.add("builder-library-open");
    controls.library.setAttribute("role", "dialog");
    controls.library.setAttribute("aria-modal", "true");
    controls.search.focus();
  }

  function closeLibrary() {
    controls.library.classList.remove("is-open");
    controls.library.removeAttribute("role");
    controls.library.removeAttribute("aria-modal");
    document.body.classList.remove("builder-library-open");
    if (state.lastLibraryOpener?.isConnected) {
      state.lastLibraryOpener.setAttribute("aria-expanded", "false");
      const opener = state.lastLibraryOpener.getClientRects().length
        ? state.lastLibraryOpener : controls.openLibrary;
      opener.focus();
    }
    state.lastLibraryOpener = null;
  }

  function fillTags(container, values, emptyLabel, role = null) {
    container.replaceChildren();
    if (!values.length) {
      container.append(createElement("span", "muted", emptyLabel));
      return;
    }
    values.forEach((value) => {
      const tag = createElement("span", "exercise-preview-tag", value.name || value);
      if (role && value.role) {
        tag.classList.add(`is-${value.role}`);
        tag.append(createElement("small", "", value.role === "primary" ? labels.primary : labels.secondary));
      }
      container.append(tag);
    });
  }

  function openPreview(id, trigger) {
    const exercise = exerciseById.get(Number(id));
    if (!exercise) return;
    state.previewExerciseId = exercise.id;
    state.lastPreviewTrigger = trigger;
    controls.previewTitle.textContent = exercise.name;
    controls.previewDescription.textContent = exercise.description || "";
    controls.previewDescription.hidden = !exercise.description;
    controls.previewInstructions.textContent = exercise.instructions || labels.noInstructions;
    fillTags(controls.previewMuscles, exercise.muscles || [], labels.noMuscles, true);
    fillTags(controls.previewEquipment, exercise.equipment || [], labels.noEquipment);
    const imageUrl = exercise.animation || exercise.thumbnail;
    controls.previewImage.hidden = !imageUrl;
    controls.previewNoImage.hidden = Boolean(imageUrl);
    controls.previewNoImage.textContent = labels.noImage;
    if (imageUrl) {
      controls.previewImage.src = imageUrl;
      controls.previewImage.alt = exercise.name;
    } else {
      controls.previewImage.removeAttribute("src");
      controls.previewImage.alt = "";
    }
    const alreadyAdded = Boolean(activeDay()?.exercises.some((entry) => entry.exercise_id === exercise.id));
    controls.previewAdd.disabled = alreadyAdded;
    if (!alreadyAdded) controls.previewAdd.disabled = !canAddExercise(exercise.id, activeDay());
    controls.previewAdd.replaceChildren();
    controls.previewAdd.append(
      createElement("span", "", alreadyAdded ? "✓" : "+"),
      document.createTextNode(alreadyAdded ? labels.added : labels.addExercise),
    );
    controls.preview.showModal();
  }

  function closePreview() {
    if (controls.preview.open) controls.preview.close();
  }
  controls.previewImage.addEventListener("error", () => {
    const fallback = exerciseById.get(state.previewExerciseId)?.thumbnail;
    if (fallback && controls.previewImage.getAttribute("src") !== fallback) {
      controls.previewImage.src = fallback;
    } else {
      controls.previewImage.hidden = true;
      controls.previewNoImage.hidden = false;
    }
  });

  function renderReorderControls() {
    controls.reorderExercises.setAttribute("aria-pressed", String(state.reorderingExercises));
    controls.reorderExercises.setAttribute("aria-label", labels.reorderExercises);
    controls.reorderExercises.classList.toggle("is-active", state.reorderingExercises);
    controls.reorderExercises.querySelector("span:last-child").textContent =
      state.reorderingExercises ? labels.reorderDone : labels.reorderExercises;
    renderSelected();
  }

  function editorError(message, focus) {
    const error = editor.panel.querySelector(".builder-editor-error");
    error.textContent = message;
    error.hidden = !message;
    focus?.focus();
  }

  function editorValues() {
    return editor.day
      ? [controls.dayName.value, controls.dayDuration.value, controls.dayDescription.value]
      : [controls.programName.value, programGoal.value];
  }

  function editorChanged() {
    return editor && editorValues().some((value, index) => value !== editor.original[index]);
  }

  function closeEditor(restoreFocus = true) {
    if (!editor) return;
    const { panel, trigger } = editor;
    editor = null;
    panel.open = false;
    if (restoreFocus) trigger.focus();
  }

  function openEditor(panel, trigger) {
    if (editor?.panel === panel) {
      if (editorChanged()) editorError(labels.editorPending);
      else closeEditor();
      return;
    }
    if (editorChanged()) {
      editorError(labels.editorPending, editor.input);
      return;
    }
    closeEditor(false);
    const day = panel === controls.daySettings ? activeDay() : null;
    if (panel === controls.daySettings && !day) return;
    const input = day ? controls.dayName : controls.programName;
    input.value = day ? day.name : state.programName;
    if (day) {
      controls.dayDuration.value = day.estimated_duration_minutes;
      controls.dayDescription.value = day.description;
    } else {
      programGoal.value = state.goal || "";
    }
    editor = { panel, trigger, input, day };
    editor.original = editorValues();
    root.querySelectorAll(".builder-exercise-menu[open]").forEach((menu) => { menu.open = false; });
    panel.open = true;
    editorError("");
    input.focus();
    input.select();
  }

  function applyEditor(restoreFocus = true) {
    if (!editor) return true;
    const { day, input } = editor;
    const name = input.value.trim();
    if (!name || Array.from(name).length > 120) {
      editorError(labels.invalidName, input);
      return false;
    }
    if (day) {
      const rawDuration = numberText(controls.dayDuration.value);
      const duration = Number(rawDuration);
      if (!/^\d+$/.test(rawDuration) || !Number.isInteger(duration) || duration < 1 || duration > 2147483647) {
        editorError(labels.invalidDuration, controls.dayDuration);
        return false;
      }
      day.name = name;
      day.estimated_duration_minutes = duration;
      day.description = controls.dayDescription.value;
    } else {
      const goal = programGoal.value || null;
      if (goal === "cardio" && state.goal !== goal) {
        const conflicts = state.days.flatMap((day) => day.exercises
          .filter((item) => !cardioIds.has(item.exercise_id))
          .map((item) => `${day.name} · ${item.name}`));
        if (conflicts.length) {
          editorError(`${labels.cardioConflicts} ${conflicts.join(" · ")}`, programGoal);
          return false;
        }
      }
      state.programName = name;
      if (goal !== state.goal) {
        state.goal = goal;
        if (goal && programGoal.options[0]?.value === "") programGoal.options[0].disabled = true;
        state.selectedExercises.clear();
        state.days.forEach((day) => {
          day.goal = goal || day.goal;
          day.allowed_exercise_ids = allowedIds(day.goal);
        });
      }
      controls.programTitle.textContent = name;
      goalLabel.textContent = source.goals[state.goal] || labels.mixedGoals;
    }
    closeEditor(restoreFocus);
    markDirty();
    render();
    return true;
  }

  for (const panel of [controls.programSettings, controls.daySettings]) {
    const summary = panel.querySelector("summary");
    summary.addEventListener("click", (event) => {
      event.preventDefault();
      openEditor(panel, summary);
    });
    const form = panel.querySelector("form");
    form.addEventListener("keydown", (event) => {
      if (event.key === "Enter" && !event.isComposing && event.target.matches("input")) {
        event.preventDefault();
        form.requestSubmit();
      }
    });
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      applyEditor();
    });
    panel.querySelector("[data-editor-cancel]").addEventListener("click", () => closeEditor());
    panel.addEventListener("input", () => { if (editor?.panel === panel) editorError(""); });
  }

  document.addEventListener("click", (event) => {
    const target = event.target;
    if (editor && !editor.panel.contains(target) && !target.closest("#builder-save, #builder-edit-program-title, #builder-edit-day")) {
      if (editorChanged()) {
        event.preventDefault();
        event.stopPropagation();
        editorError(labels.editorPending, editor.input);
        return;
      }
      closeEditor(false);
    }
    root.querySelectorAll(".builder-exercise-menu[open]").forEach((menu) => {
      if (!menu.contains(target)) menu.open = false;
    });
  }, true);

  controls.search.addEventListener("input", renderLibrary);
  controls.clearSearch.addEventListener("click", () => {
    controls.search.value = "";
    renderLibrary();
    controls.search.focus();
  });
  controls.category.addEventListener("change", renderLibrary);
  controls.category.dataset.allLabel = controls.category.options[0].textContent;

  controls.addDay.addEventListener("click", () => {
    if (state.days.length >= 50) return;
    const day = makeDay();
    state.days.push(day);
    state.activeKey = day.client_key;
    state.selectedExercises.clear();
    controls.daySettings.open = false;
    markDirty();
    render();
  });
  controls.reorderDays.addEventListener("click", () => {
    state.reorderingDays = !state.reorderingDays;
    renderDays();
  });
  controls.reorderExercises.addEventListener("click", () => {
    state.reorderingExercises = !state.reorderingExercises;
    renderReorderControls();
  });
  document.getElementById("builder-edit-program-title").addEventListener("click", (event) => {
    openEditor(controls.programSettings, event.currentTarget);
  });
  controls.editDay.addEventListener("click", (event) => openEditor(controls.daySettings, event.currentTarget));
  controls.openLibrary.addEventListener("click", () => openLibrary(controls.openLibrary));
  document.querySelector("[data-open-library]").addEventListener("click", (event) => {
    openLibrary(event.currentTarget);
  });
  controls.addSelectedInline.addEventListener("click", () => openLibrary(controls.addSelectedInline));
  controls.closeLibrary.addEventListener("click", closeLibrary);
  controls.addSelected.addEventListener("click", () => {
    if (!state.selectedExercises.size) return;
    addExercises(Array.from(state.selectedExercises), true);
    closeLibrary();
  });
  document.getElementById("exercise-preview-close").addEventListener("click", closePreview);
  controls.preview.addEventListener("close", () => {
    controls.previewImage.removeAttribute("src");
    if (state.lastPreviewTrigger?.isConnected) state.lastPreviewTrigger.focus();
  });
  controls.preview.addEventListener("click", (event) => {
    if (event.target === controls.preview) closePreview();
  });
  controls.previewAdd.addEventListener("click", () => {
    if (state.previewExerciseId === null || controls.previewAdd.disabled) return;
    addExercises([state.previewExerciseId]);
    controls.preview.close();
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && editor) {
      event.preventDefault();
      closeEditor();
      return;
    }
    const openMenu = root.querySelector(".builder-exercise-menu[open]");
    if (event.key === "Escape" && openMenu) {
      openMenu.open = false;
      openMenu.querySelector("summary").focus();
      return;
    }
    if (event.key === "Escape" && controls.preview.open) {
      event.preventDefault();
      closePreview();
      return;
    }
    if (event.key === "Escape" && controls.library.classList.contains("is-open") && !controls.preview.open) {
      closeLibrary();
      return;
    }
    if (
      event.key === "Tab"
      && controls.library.classList.contains("is-open")
      && window.matchMedia("(max-width: 900px)").matches
      && !controls.preview.open
    ) {
      const focusable = Array.from(controls.library.querySelectorAll(
        'a[href], button:not(:disabled), input:not(:disabled), select:not(:disabled), textarea:not(:disabled), summary, [tabindex]:not([tabindex="-1"])',
      )).filter((element) => element.getClientRects().length);
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (!first || !last) return;
      if (!controls.library.contains(document.activeElement)) {
        event.preventDefault();
        first.focus();
      } else if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }
  });

  controls.days.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-action]");
    if (!button) return;
    if (button.dataset.action === "select-day") {
      state.activeKey = button.dataset.dayKey;
      state.selectedExercises.clear();
      controls.daySettings.open = false;
      render();
      syncDayUrl();
      controls.days.querySelector('[aria-current="true"]')?.focus();
      return;
    }
    if (button.dataset.action === "move-day-up") moveDay(button.dataset.dayKey, -1);
    if (button.dataset.action === "move-day-down") moveDay(button.dataset.dayKey, 1);
  });
  controls.days.addEventListener("dragstart", (event) => {
    const tab = event.target.closest(".builder-day-tab");
    if (tab && state.reorderingDays) event.dataTransfer.setData("text/plain", tab.dataset.dayKey);
    else event.preventDefault();
  });
  controls.days.addEventListener("dragover", (event) => {
    if (state.reorderingDays && event.target.closest(".builder-day-tab")) event.preventDefault();
  });
  controls.days.addEventListener("drop", (event) => {
    const tab = event.target.closest(".builder-day-tab");
    if (!tab || !state.reorderingDays) return;
    event.preventDefault();
    const from = state.days.findIndex((day) => day.client_key === event.dataTransfer.getData("text/plain"));
    const to = state.days.findIndex((day) => day.client_key === tab.dataset.dayKey);
    if (moveItem(state.days, from, to)) {
      markDirty();
      renderDays();
    }
  });

  controls.removeDay.addEventListener("click", () => {
    const day = activeDay();
    if (!day) return;
    if (!window.confirm(labels.confirmRemoveDay)) return;
    closeEditor(false);
    state.days = state.days.filter((item) => item.client_key !== day.client_key);
    state.activeKey = state.days.length ? state.days[0].client_key : null;
    state.selectedExercises.clear();
    controls.daySettings.open = false;
    markDirty();
    render();
  });

  controls.selectedExercises.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-action]");
    if (!button) return;
    const day = activeDay();
    if (!day) return;
    const card = button.closest(".builder-exercise-card");
    const index = Number(card?.dataset.exerciseIndex);
    const exercise = day.exercises[index];
    if (button.dataset.action === "preview-exercise") {
      openPreview(button.dataset.exerciseId, button);
      return;
    }
    if (!exercise) return;
    switch (button.dataset.action) {
      case "toggle-exercise":
        if (state.collapsedExercises.has(exercise.exercise_id)) state.collapsedExercises.delete(exercise.exercise_id);
        else state.collapsedExercises.add(exercise.exercise_id);
        renderSelected();
        return;
      case "remove-exercise":
        if (!removedExercises.has(day)) removedExercises.set(day, new Map());
        removedExercises.get(day).set(exercise.exercise_id, exercise);
        day.exercises.splice(index, 1);
        state.collapsedExercises.delete(exercise.exercise_id);
        break;
      case "move-exercise-up":
        moveItem(day.exercises, index, index - 1);
        break;
      case "move-exercise-down":
        moveItem(day.exercises, index, index + 1);
        break;
      case "add-set": {
        if (exercise.sets.length < 50) appendSet(exercise);
        break;
      }
      case "remove-set": {
        const [removedSet] = exercise.sets.splice(Number(button.dataset.setIndex), 1);
        if (removedSet?.id) exercise.removed_set_ids.push(removedSet.id);
        break;
      }
      default:
        return;
    }
    markDirty();
    renderSelected();
    renderLibrary();
  });

  controls.libraryList.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-action]");
    if (!button) return;
    const exerciseId = Number(button.dataset.exerciseId);
    if (button.dataset.action === "preview-exercise") openPreview(exerciseId, button);
    if (button.dataset.action === "add-one") addExercises([exerciseId]);
  });

  controls.selectedExercises.addEventListener("input", (event) => {
    const target = event.target;
    const day = activeDay();
    if (!day) return;
    if (target.dataset.setField && target.dataset.setField !== "set_type") {
      const set = day.exercises[Number(target.dataset.exerciseIndex)]?.sets[Number(target.dataset.setIndex)];
      if (!set) return;
      const value = numberText(target.value);
      if (target.dataset.setField === "weight_kg") set.weight_kg = value === "" ? 0 : parseNumber(value);
      else if (target.dataset.setField === "duration_minutes") set.duration_seconds = value === "" ? 0 : Math.round(parseNumber(value) * 60);
      else set[target.dataset.setField] = value === "" ? "" : parseNumber(value);
      markDirty();
      return;
    }
    if (!target.dataset.exerciseField || target.dataset.exerciseField === "set_count") return;
    const exercise = day.exercises[Number(target.dataset.exerciseIndex)];
    if (!exercise) return;
    const value = target.dataset.exerciseField === "notes" ? target.value : numberText(target.value);
    switch (target.dataset.exerciseField) {
      case "rest_seconds":
        exercise.rest_seconds = value === "" ? "" : parseNumber(value);
        break;
      case "notes":
        exercise.notes = value;
        break;
      case "basic_reps":
        exercise.sets.forEach((set) => { set.reps = value === "" ? "" : parseNumber(value); });
        break;
      case "basic_weight":
        exercise.sets.forEach((set) => { set.weight_kg = value === "" ? 0 : parseNumber(value); });
        break;
      case "basic_duration_minutes":
        exercise.sets.forEach((set) => { set.duration_seconds = value === "" ? 0 : Math.round(parseNumber(value) * 60); });
        break;
      case "basic_duration_seconds":
        exercise.sets.forEach((set) => { set.duration_seconds = value === "" ? 0 : parseNumber(value); });
        break;
      default:
        return;
    }
    markDirty();
  });

  controls.selectedExercises.addEventListener("change", (event) => {
    const target = event.target;
    const day = activeDay();
    if (!day) return;
    const exercise = day.exercises[Number(target.dataset.exerciseIndex)];
    if (!exercise) return;
    if (target.dataset.exerciseField === "set_count") {
      const requestedCount = parseNumber(numberText(target.value));
      if (!target.value || !Number.isInteger(requestedCount) || requestedCount < 1 || requestedCount > 50) {
        target.value = exercise.sets.length;
        setStatus(labels.invalidValues, true);
        return;
      }
      if (requestedCount < exercise.sets.length) {
        if (!window.confirm(labels.confirmRemoveSets)) {
          target.value = exercise.sets.length;
          return;
        }
        const removed = exercise.sets.splice(requestedCount);
        removed.forEach((set) => {
          if (set.id) exercise.removed_set_ids.push(set.id);
        });
      } else {
        while (exercise.sets.length < requestedCount) appendSet(exercise);
      }
      markDirty();
      renderSelected();
      return;
    }
    if (target.dataset.setField === "set_type") {
      exercise.sets[Number(target.dataset.setIndex)].set_type = target.value;
      markDirty();
    } else if (target.dataset.setField || target.dataset.exerciseField) {
      if (target.matches("input") && target.value.trim() && !Number.isFinite(parseNumber(numberText(target.value)))) {
        setStatus(labels.invalidValues, true);
        return;
      }
      syncSetFields(target.closest(".builder-exercise-card"), exercise);
    }
  });

  controls.selectedExercises.addEventListener("dragstart", (event) => {
    const card = event.target.closest(".builder-exercise-card");
    if (card && state.reorderingExercises) event.dataTransfer.setData("text/plain", card.dataset.exerciseIndex);
    else event.preventDefault();
  });
  controls.selectedExercises.addEventListener("dragover", (event) => {
    if (state.reorderingExercises && event.target.closest(".builder-exercise-card")) event.preventDefault();
  });
  controls.selectedExercises.addEventListener("drop", (event) => {
    const card = event.target.closest(".builder-exercise-card");
    const day = activeDay();
    if (!card || !day || !state.reorderingExercises) return;
    event.preventDefault();
    const from = Number(event.dataTransfer.getData("text/plain"));
    const to = Number(card.dataset.exerciseIndex);
    if (moveItem(day.exercises, from, to)) {
      markDirty();
      renderSelected();
    }
  });

  async function saveProgram() {
    if (state.saving) return;
    if (editorChanged() && !applyEditor(false)) return;
    closeEditor(false);
    const invalid = (value, max, integer = true) => value === "" || value == null ||
      !Number.isFinite(Number(value)) || Number(value) < 0 || Number(value) > max ||
      (integer && !Number.isInteger(Number(value)));
    if (state.days.some((day) => day.exercises.some((exercise) =>
      invalid(exercise.rest_seconds, 2147483647) || exercise.sets.some((set) =>
        invalid(set.reps, 2147483647) || invalid(set.duration_seconds, 2147483647) ||
        invalid(set.weight_kg, 10000, false)
      )
    ))) {
      setStatus(labels.invalidValues, true);
      return;
    }
    if (
      !state.programName.trim()
      || state.days.some((day) => !day.name.trim()
        || !Number.isInteger(Number(day.estimated_duration_minutes))
        || Number(day.estimated_duration_minutes) < 1)
    ) {
      setStatus(labels.saveError, true);
      return;
    }
    const payload = {
      name: state.programName,
      goal: state.goal,
      revision: state.revision,
      days: state.days.map((day) => ({
        id: day.id,
        client_key: day.client_key,
        name: day.name,
        description: day.description,
        estimated_duration_minutes: Number(day.estimated_duration_minutes),
        exercises: day.exercises.map((exercise) => ({
          exercise_id: exercise.exercise_id,
          rest_seconds: Number(exercise.rest_seconds),
          notes: exercise.notes,
          removed_set_ids: exercise.removed_set_ids,
          sets: exercise.sets.map((set) => ({
            id: set.id,
            reps: Number(set.reps),
            duration_seconds: Number(set.duration_seconds),
            weight_kg: Number(set.weight_kg),
            set_type: set.set_type,
          })),
        })),
      })),
    };
    state.saving = true;
    const editingRegions = root.querySelectorAll(".builder-program-heading, .builder-daybar, .builder-layout");
    editingRegions.forEach((region) => { region.inert = true; });
    controls.save.disabled = true;
    setStatus(labels.saving);
    try {
      const response = await fetch(root.dataset.saveUrl, {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": document.getElementById("builder-csrf").value,
        },
        body: JSON.stringify(payload),
      });
      const result = await response.json().catch(() => null);
      if (!result) throw new Error(labels.saveError);
      if (!response.ok) throw new Error(result.error || labels.saveError);
      state.revision = result.revision;
      state.programName = result.program_name;
      controls.programName.value = result.program_name;
      controls.programTitle.textContent = result.program_name;
      state.days.forEach((day) => {
        const savedDay = result.records[day.client_key];
        if (!savedDay) return;
        day.id = savedDay.id;
        day.name = savedDay.name;
        removedExercises.delete(day);
        day.exercises.forEach((exercise) => {
          const savedExercise = savedDay.exercises[String(exercise.exercise_id)];
          if (!savedExercise) return;
          exercise.id = savedExercise.id;
          exercise.sets.forEach((set, index) => {
            set.id = savedExercise.sets[index];
          });
          exercise.removed_set_ids = [];
        });
      });
      state.dirty = false;
      setStatus(labels.saveSuccess);
      render();
      syncDayUrl();
    } catch (error) {
      setStatus(error instanceof TypeError ? labels.saveError : error.message || labels.saveError, true);
    } finally {
      state.saving = false;
      editingRegions.forEach((region) => { region.inert = false; });
      controls.save.disabled = false;
    }
  }
  controls.save.addEventListener("click", saveProgram);
  window.addEventListener("beforeunload", (event) => {
    if (!state.dirty && !editorChanged()) return;
    event.preventDefault();
    event.returnValue = labels.confirmLeave;
  });

  render();
})();
