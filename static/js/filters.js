/**
 * AJAX Filters — T018
 * Intercepts filter/sort form submission on the product listing page,
 * fires a fetch() with format=partial, swaps the #product-grid div,
 * and updates the browser URL via history.pushState.
 */
(function () {
  "use strict";

  document.addEventListener("DOMContentLoaded", function () {
    const filterForm = document.getElementById("filterForm");
    const productGrid = document.getElementById("product-grid");

    if (!filterForm || !productGrid) return;

    function loadPartial(url) {
      const partialUrl = url.includes("?")
        ? url + "&format=partial"
        : url + "?format=partial";

      fetch(partialUrl, {
        headers: { "X-Requested-With": "XMLHttpRequest" },
      })
        .then(function (response) {
          if (!response.ok) throw new Error("Network response was not ok");
          return response.text();
        })
        .then(function (html) {
          productGrid.innerHTML = html;
          // Re-attach pagination link interceptors after swap
          attachPaginationLinks();
        })
        .catch(function () {
          // Fallback: full page navigation on error
          window.location.href = url;
        });
    }

    function attachPaginationLinks() {
      productGrid.querySelectorAll("a.page-link").forEach(function (link) {
        link.addEventListener("click", function (e) {
          e.preventDefault();
          const href = this.getAttribute("href");
          history.pushState(null, "", href);
          loadPartial(href);
        });
      });
    }

    filterForm.addEventListener("submit", function (e) {
      e.preventDefault();
      const url = filterForm.action + "?" + new URLSearchParams(new FormData(filterForm)).toString();
      history.pushState(null, "", url);
      loadPartial(url);
    });

    // Also intercept sort select change if it's outside the form
    const sortSelect = document.getElementById("sortSelect");
    if (sortSelect && !filterForm.contains(sortSelect)) {
      sortSelect.addEventListener("change", function () {
        const urlParams = new URLSearchParams(window.location.search);
        urlParams.set("sort", this.value);
        const url = "?" + urlParams.toString();
        history.pushState(null, "", url);
        loadPartial(window.location.pathname + url);
      });
    }

    attachPaginationLinks();

    // Handle browser back/forward
    window.addEventListener("popstate", function () {
      loadPartial(window.location.pathname + window.location.search);
    });
  });
})();
