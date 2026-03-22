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

    searchInputs.forEach(function (input) {
      let dropdown = null;
      let activeIndex = -1;
      let abortController = null;

      function createDropdown() {
        if (dropdown) return;
        dropdown = document.createElement("ul");
        dropdown.className = "list-group position-absolute shadow w-100";
        dropdown.style.zIndex = "9999";
        dropdown.style.maxHeight = "300px";
        dropdown.style.overflowY = "auto";
        input.parentElement.style.position = "relative";
        input.parentElement.appendChild(dropdown);
      }

      function clearDropdown() {
        if (dropdown) {
          dropdown.innerHTML = "";
          activeIndex = -1;
        }
      }

      function hideDropdown() {
        if (dropdown) {
          dropdown.remove();
          dropdown = null;
          activeIndex = -1;
        }
      }

      input.addEventListener("input", function () {
        const q = this.value.trim();
        if (q.length < MIN_CHARS) {
          hideDropdown();
          return;
        }
        if (abortController) abortController.abort();
        abortController = new AbortController();

        fetch(`${AUTOCOMPLETE_URL}?q=${encodeURIComponent(q)}`, {
          signal: abortController.signal,
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
              li.className = "list-group-item list-group-item-action cursor-pointer";
              li.textContent = item.name;
              li.dataset.url = item.url;
              li.dataset.idx = idx;
              li.addEventListener("mousedown", function (e) {
                e.preventDefault();
                window.location.href = item.url;
              });
              dropdown.appendChild(li);
            });
          })
          .catch(function () {});
      });

      input.addEventListener("keydown", function (e) {
        if (!dropdown) return;
        const items = dropdown.querySelectorAll("li");
        if (e.key === "ArrowDown") {
          e.preventDefault();
          activeIndex = Math.min(activeIndex + 1, items.length - 1);
        } else if (e.key === "ArrowUp") {
          e.preventDefault();
          activeIndex = Math.max(activeIndex - 1, -1);
        } else if (e.key === "Enter" && activeIndex >= 0) {
          e.preventDefault();
          window.location.href = items[activeIndex].dataset.url;
          return;
        } else if (e.key === "Escape") {
          hideDropdown();
          return;
        }
        items.forEach(function (li, i) {
          li.classList.toggle("active", i === activeIndex);
        });
      });

      document.addEventListener("click", function (e) {
        if (!input.contains(e.target) && (!dropdown || !dropdown.contains(e.target))) {
          hideDropdown();
        }
      });
    });
  });
})();
