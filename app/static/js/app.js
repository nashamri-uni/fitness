// The language menu submits the existing Django language-switch form.
function setupLanguageSwitcher() {
  document.querySelectorAll("form[data-auto-submit]").forEach((form) => {
    const dropdown = form.querySelector("[data-language-dropdown]");
    const trigger = form.querySelector("[data-language-trigger]");
    const menu = form.querySelector(".language-menu");
    const languageInput = form.querySelector("[data-language-value]");
    const options = menu ? Array.from(menu.querySelectorAll("[data-language-option]")) : [];
    if (!dropdown || !trigger || !menu || !languageInput || !options.length) {
      console.error("Could not initialize the language dropdown.");
      return;
    }

    form.classList.add("js-auto-submit");
    languageInput.disabled = false;
    options.forEach((option) => {
      option.tabIndex = -1;
    });

    function setOpen(open, focusIndex = null, restoreFocus = false) {
      menu.hidden = !open;
      trigger.setAttribute("aria-expanded", String(open));
      if (focusIndex !== null) options[focusIndex].focus();
      if (restoreFocus) trigger.focus();
    }

    function focusOption(index) {
      const wrappedIndex = (index + options.length) % options.length;
      options[wrappedIndex].focus();
    }

    trigger.addEventListener("click", () => {
      const opening = trigger.getAttribute("aria-expanded") !== "true";
      const selectedIndex = options.findIndex((option) => option.getAttribute("aria-checked") === "true");
      setOpen(opening, opening ? Math.max(selectedIndex, 0) : null);
    });

    dropdown.addEventListener("keydown", (event) => {
      const currentIndex = options.indexOf(document.activeElement);
      if (event.key === "Escape") {
        if (trigger.getAttribute("aria-expanded") === "true") {
          event.preventDefault();
          setOpen(false, null, true);
        }
      } else if (document.activeElement === trigger && event.key === "ArrowDown") {
        event.preventDefault();
        setOpen(true, 0);
      } else if (document.activeElement === trigger && event.key === "ArrowUp") {
        event.preventDefault();
        setOpen(true, options.length - 1);
      } else if (currentIndex !== -1 && (event.key === "ArrowDown" || event.key === "ArrowUp")) {
        event.preventDefault();
        focusOption(currentIndex + (event.key === "ArrowDown" ? 1 : -1));
      } else if (currentIndex !== -1 && event.key === "Home") {
        event.preventDefault();
        focusOption(0);
      } else if (currentIndex !== -1 && event.key === "End") {
        event.preventDefault();
        focusOption(options.length - 1);
      }
    });

    options.forEach((option) => {
      option.addEventListener("click", () => {
        const language = option.dataset.language;
        if (!language) {
          console.error("A language option is missing its language code.");
          return;
        }
        languageInput.value = language;

        if (typeof form.requestSubmit === "function") {
          form.requestSubmit();
        } else {
          form.submit();
        }
      });
    });

    document.addEventListener("click", (event) => {
      if (!dropdown.contains(event.target)) setOpen(false);
    });
    document.addEventListener("focusin", (event) => {
      if (!dropdown.contains(event.target)) setOpen(false);
    });
  });
}

function setupAccountDropdown() {
  const dropdown = document.querySelector("[data-account-dropdown]");
  if (!dropdown) return;

  const trigger = dropdown.querySelector("[data-account-dropdown-trigger]");
  const menu = dropdown.querySelector(".account-dropdown-menu");
  if (!trigger || !menu) {
    console.error("Could not initialize the account dropdown.");
    return;
  }

  const items = Array.from(menu.querySelectorAll('a[href], button:not([disabled])'));

  function setOpen(open, restoreFocus = false) {
    menu.hidden = !open;
    trigger.setAttribute("aria-expanded", String(open));
    if (restoreFocus) trigger.focus();
  }

  function focusItem(index) {
    if (!items.length) return;
    const wrappedIndex = (index + items.length) % items.length;
    items[wrappedIndex].focus();
  }

  trigger.addEventListener("click", () => {
    setOpen(trigger.getAttribute("aria-expanded") !== "true");
  });
  dropdown.addEventListener("keydown", (event) => {
    const currentIndex = items.indexOf(document.activeElement);

    if (event.key === "Escape") {
      if (trigger.getAttribute("aria-expanded") === "true") {
        event.preventDefault();
        setOpen(false, true);
      }
      return;
    }

    if (document.activeElement === trigger && event.key === "ArrowDown") {
      event.preventDefault();
      setOpen(true);
      focusItem(0);
    } else if (document.activeElement === trigger && event.key === "ArrowUp") {
      event.preventDefault();
      setOpen(true);
      focusItem(items.length - 1);
    } else if (currentIndex !== -1 && (event.key === "ArrowDown" || event.key === "ArrowUp")) {
      event.preventDefault();
      focusItem(currentIndex + (event.key === "ArrowDown" ? 1 : -1));
    } else if (currentIndex !== -1 && event.key === "Home") {
      event.preventDefault();
      focusItem(0);
    } else if (currentIndex !== -1 && event.key === "End") {
      event.preventDefault();
      focusItem(items.length - 1);
    }
  });

  document.addEventListener("click", (event) => {
    if (!dropdown.contains(event.target)) setOpen(false);
  });
  document.addEventListener("focusin", (event) => {
    if (!dropdown.contains(event.target)) setOpen(false);
  });
}

document.addEventListener("DOMContentLoaded", () => {
  setupLanguageSwitcher();
  setupAccountDropdown();
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

        themeButton.setAttribute(
            "aria-label",
            isDark ? themeButton.dataset.labelDark : themeButton.dataset.labelLight
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
