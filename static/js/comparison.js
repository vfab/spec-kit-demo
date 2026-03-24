/**
 * Comparison — T035
 * Intercepts "Add to Compare" button clicks, POSTs to compare/add/ via fetch(),
 * updates the widget count badge, and shows error toasts on
 * category mismatch or limit exceeded.
 */
(function () {
  "use strict";

  const ADD_URL = (function () {
    // Prefer a URL rendered by the template via a data-* attribute on the
    // compare button, e.g. data-compare-add-url="{% url 'products:compare_add' %}"
    var el = document.querySelector("[data-compare-add-url]");
    var url = el && el.getAttribute("data-compare-add-url");
    return url || "/products/compare/add/";
  })();

  function getCSRFToken() {
    // Prefer the meta tag (set on every page via base.html) so compare buttons
    // work for anonymous users on GET pages before any form cookie is written.
    var meta = document.querySelector("meta[name='csrf-token']");
    if (meta) return meta.getAttribute("content") || "";
    var cookie = document.cookie
      .split(";")
      .map(function (c) { return c.trim(); })
      .find(function (c) { return c.startsWith("csrftoken="); });
    return cookie ? cookie.split("=")[1] : "";
  }

  // showToast renders plain text safely via DOM APIs.
  // iconClass is an optional Font Awesome class string (e.g. "fas fa-check").
  function showToast(message, type, iconClass) {
    type = type || "info";
    const container = document.getElementById("toast-container") || createToastContainer();
    const toast = document.createElement("div");
    toast.className = "alert alert-" + type + " alert-dismissible fade show py-2 px-3";
    toast.style.cssText = "min-width:250px;";
    if (iconClass) {
      const icon = document.createElement("i");
      icon.className = iconClass + " me-1";
      toast.appendChild(icon);
    }
    toast.appendChild(document.createTextNode(message));
    const closeBtn = document.createElement("button");
    closeBtn.type = "button";
    closeBtn.className = "btn-close";
    closeBtn.setAttribute("data-bs-dismiss", "alert");
    toast.appendChild(closeBtn);
    container.appendChild(toast);
    setTimeout(function () { toast.remove(); }, 4000);
  }

  function createToastContainer() {
    const div = document.createElement("div");
    div.id = "toast-container";
    div.style.cssText = "position:fixed;top:1rem;right:1rem;z-index:9999;display:flex;flex-direction:column;gap:0.5rem;";
    document.body.appendChild(div);
    return div;
  }

  function refreshWidget() {
    // Reload the page so the compare widget badge and button states reflect
    // the updated session list.  A future enhancement could replace this with
    // a lightweight fetch to a dedicated widget-reload endpoint.
    window.location.reload();
  }

  document.addEventListener("click", function (e) {
    const btn = e.target.closest(".compare-btn");
    if (!btn) return;
    e.preventDefault();

    const productId = btn.dataset.productId;
    const productName = btn.dataset.productName || "Product";

    const formData = new FormData();
    formData.append("product_id", productId);
    formData.append("next", window.location.pathname + window.location.search);

    fetch(ADD_URL, {
      method: "POST",
      headers: { "X-CSRFToken": getCSRFToken() },
      body: formData,
      // Use default redirect:"follow" so response.url is the final settled URL
      // and compare_error parameters are reliably readable.
    })
      .then(function (response) {
        // Django redirects to the 'next' URL, possibly with an error param.
        // With default redirect handling, response.url is the final URL.
        const finalUrl = response.url;
        if (finalUrl && finalUrl.includes("compare_error=category")) {
          showToast(
            "Products must be from the same category to compare.",
            "warning",
            "fas fa-exclamation-circle"
          );
        } else if (finalUrl && finalUrl.includes("compare_error=limit")) {
          showToast(
            "You can compare up to 3 products at a time.",
            "warning",
            "fas fa-exclamation-circle"
          );
        } else if (finalUrl && finalUrl.includes("compare_error=invalid")) {
          showToast("Invalid product.", "danger", "fas fa-times");
        } else {
          showToast(
            "\u201c" + productName + "\u201d added to comparison.",
            "success",
            "fas fa-check"
          );
          setTimeout(refreshWidget, 800);
        }
      })
      .catch(function () {
        showToast("Could not add product. Please try again.", "danger", "fas fa-times");
      });
  });
})();
