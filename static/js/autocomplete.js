/**
 * Autocomplete — T013
 * Listens to the search input, fetches suggestions from /products/autocomplete/,
 * renders a dropdown, and supports keyboard navigation + selection.
 */
(function () {
  "use strict";

  const MIN_CHARS = 2;
  const AUTOCOMPLETE_URL = "/products/autocomplete/";

  document.addEventListener("DOMContentLoaded", function () {
    const searchInputs = document.querySelectorAll(
      "input[name='q'], input[name='search'], #searchInput"
    );

    // Per-input state objects, kept for the single document click handler.
    const inputStates = [];

    searchInputs.forEach(function (input, inputIdx) {
      // Unique IDs scoped to this input instance so multiple search boxes
      // on the same page each get their own listbox.
      const listboxId = `autocomplete-listbox-${inputIdx}`;

      // ARIA combobox pattern: annotate the input before any interaction.
      input.setAttribute("role", "combobox");
      input.setAttribute("aria-haspopup", "listbox");
      input.setAttribute("aria-expanded", "false");
      input.setAttribute("aria-autocomplete", "list");
      input.setAttribute("aria-controls", listboxId);

      const state = {
        input: input,
        dropdown: null,
        activeIndex: -1,
        abortController: null,
      };
      inputStates.push(state);

      function createDropdown() {
        if (state.dropdown) return;
        state.dropdown = document.createElement("ul");
        state.dropdown.id = listboxId;
        state.dropdown.setAttribute("role", "listbox");
        state.dropdown.className = "list-group position-absolute shadow w-100";
        state.dropdown.style.zIndex = "9999";
        state.dropdown.style.maxHeight = "300px";
        state.dropdown.style.overflowY = "auto";
        input.parentElement.style.position = "relative";
        input.parentElement.appendChild(state.dropdown);
        input.setAttribute("aria-expanded", "true");
      }

      function clearDropdown() {
        if (state.dropdown) {
          state.dropdown.innerHTML = "";
          state.activeIndex = -1;
          input.removeAttribute("aria-activedescendant");
        }
      }

      function hideDropdown() {
        if (state.dropdown) {
          state.dropdown.remove();
          state.dropdown = null;
          state.activeIndex = -1;
          input.setAttribute("aria-expanded", "false");
          input.removeAttribute("aria-activedescendant");
        }
      }

      input.addEventListener("input", function () {
        const q = this.value.trim();
        if (q.length < MIN_CHARS) {
          hideDropdown();
          return;
        }
        if (state.abortController) state.abortController.abort();
        state.abortController = new AbortController();

        fetch(`${AUTOCOMPLETE_URL}?q=${encodeURIComponent(q)}`, {
          signal: state.abortController.signal,
        })
          .then((r) => r.json())
          .then(function (data) {
            if (!data.results || data.results.length === 0) {
              hideDropdown();
              return;
            }
            createDropdown();
            clearDropdown();
            data.results.forEach(function (item, idx) {
              const li = document.createElement("li");
              const optionId = `${listboxId}-option-${idx}`;
              li.id = optionId;
              li.setAttribute("role", "option");
              li.setAttribute("aria-selected", "false");
              li.className = "list-group-item list-group-item-action cursor-pointer";
              li.textContent = item.name;
              li.dataset.url = item.url;
              li.dataset.idx = idx;
              li.addEventListener("mousedown", function (e) {
                e.preventDefault();
                window.location.href = item.url;
              });
              state.dropdown.appendChild(li);
            });
          })
          .catch(function () {});
      });

      input.addEventListener("keydown", function (e) {
        if (!state.dropdown) return;
        const items = state.dropdown.querySelectorAll("li");
        if (e.key === "ArrowDown") {
          e.preventDefault();
          state.activeIndex = Math.min(state.activeIndex + 1, items.length - 1);
        } else if (e.key === "ArrowUp") {
          e.preventDefault();
          state.activeIndex = Math.max(state.activeIndex - 1, -1);
        } else if (e.key === "Enter" && state.activeIndex >= 0) {
          e.preventDefault();
          window.location.href = items[state.activeIndex].dataset.url;
          return;
        } else if (e.key === "Escape") {
          hideDropdown();
          return;
        }
        items.forEach(function (li, i) {
          const isActive = i === state.activeIndex;
          li.classList.toggle("active", isActive);
          li.setAttribute("aria-selected", isActive ? "true" : "false");
        });
        if (state.activeIndex >= 0) {
          input.setAttribute("aria-activedescendant", items[state.activeIndex].id);
        } else {
          input.removeAttribute("aria-activedescendant");
        }
      });
    });

    // Single document-level click handler for all inputs — avoids duplicate
    // listeners when multiple search inputs exist on the same page.
    document.addEventListener("click", function (e) {
      inputStates.forEach(function (state) {
        if (!state.dropdown) return;
        if (
          !state.input.contains(e.target) &&
          !state.dropdown.contains(e.target)
        ) {
          state.dropdown.remove();
          state.dropdown = null;
          state.activeIndex = -1;
        }
      });
    });
  });
})();
