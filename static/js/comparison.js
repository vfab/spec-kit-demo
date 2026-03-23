/**
 * Comparison — T035
 * Intercepts "Add to Compare" button clicks, POSTs to compare/add/ via fetch(),
 * updates the widget count badge, and shows error toasts on
 * category mismatch or limit exceeded.
 */
(function () {
  "use strict";

  const ADD_URL = "/products/compare/add/";

  /**
   * Escape user-supplied text before injecting into innerHTML.
   * Prevents XSS when product names contain HTML special characters.
   */
  function escapeHtml(str) {
    const d = document.createElement("div");
    d.appendChild(document.createTextNode(str));
    return d.innerHTML;
  }

  function getCSRFToken() {
    const cookie = document.cookie
      .split(";")
      .map(function (c) { return c.trim(); })
      .find(function (c) { return c.startsWith("csrftoken="); });
    return cookie ? cookie.split("=")[1] : "";
  }

  function showToast(message, type) {
    type = type || "info";
    const container = document.getElementById("toast-container") || createToastContainer();
    const toast = document.createElement("div");
    toast.className = `alert alert-${type} alert-dismissible fade show py-2 px-3`;
    toast.style.cssText = "min-width:250px;";
    toast.innerHTML = `${message}<button type="button" class="btn-close" data-bs-dismiss="alert"></button>`;
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
    // Re-fetch the compare widget via a lightweight endpoint.
    // Simplest approach: reload the widget element if it exists.
    const widget = document.getElementById("compare-widget");
    if (widget) {
      // Force a reload of the page partial — simplest implementation
      // is to update the badge from a counter in localStorage.
    }
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
            '<i class="fas fa-exclamation-circle me-1"></i> Products must be from the same category to compare.',
            "warning"
          );
        } else if (finalUrl && finalUrl.includes("compare_error=limit")) {
          showToast(
            '<i class="fas fa-exclamation-circle me-1"></i> You can compare up to 3 products at a time.',
            "warning"
          );
        } else if (finalUrl && finalUrl.includes("compare_error=invalid")) {
          showToast('<i class="fas fa-times me-1"></i> Invalid product.', "danger");
        } else {
          showToast(
            `<i class="fas fa-check me-1"></i> &ldquo;${escapeHtml(productName)}&rdquo; added to comparison.`,
            "success"
          );
          // Update the compare widget by reloading the page silently
          // (full solution would use a dedicated API endpoint)
          setTimeout(function () { window.location.reload(); }, 800);
        }
      })
      .catch(function () {
        showToast('<i class="fas fa-times me-1"></i> Could not add product. Please try again.', "danger");
      });
  });
})();
