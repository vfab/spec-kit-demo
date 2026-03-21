// Main JavaScript functionality for ShopHub - Enhanced UI

document.addEventListener("DOMContentLoaded", function () {
  // Initialize enhanced UI components
  initializeEnhancedUI();

  // Initialize tooltips
  const tooltipTriggerList = [].slice.call(
    document.querySelectorAll('[data-bs-toggle="tooltip"]'),
  );
  tooltipTriggerList.map(function (tooltipTriggerEl) {
    return new bootstrap.Tooltip(tooltipTriggerEl);
  });

  // Initialize popovers
  const popoverTriggerList = [].slice.call(
    document.querySelectorAll('[data-bs-toggle="popover"]'),
  );
  popoverTriggerList.map(function (popoverTriggerEl) {
    return new bootstrap.Popover(popoverTriggerEl);
  });

  // Smooth scrolling for anchor links with enhanced animation
  document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
    anchor.addEventListener("click", function (e) {
      e.preventDefault();
      const target = document.querySelector(this.getAttribute("href"));
      if (target) {
        // Add loading state
        showLoadingOverlay(500);
        target.scrollIntoView({
          behavior: "smooth",
          block: "start",
        });
      }
    });
  });

  // Enhanced auto-hide alerts with fade animation
  setTimeout(function () {
    const alerts = document.querySelectorAll(".alert:not(.alert-permanent)");
    alerts.forEach(function (alert) {
      alert.style.opacity = "0";
      alert.style.transform = "translateY(-20px)";
      setTimeout(() => {
        const bootstrapAlert = new bootstrap.Alert(alert);
        bootstrapAlert.close();
      }, 300);
    });
  }, 5000);

  // Enhanced search form with real-time feedback
  const searchForm = document.querySelector('form[action*="search"]');
  if (searchForm) {
    const searchInput = searchForm.querySelector('input[name="q"]');
    if (searchInput) {
      // Add visual feedback and loading states
      searchInput.addEventListener("input", function () {
        if (this.value.length > 2) {
          this.classList.add("border-success");
          this.classList.remove("border-danger");
        } else if (this.value.length > 0) {
          this.classList.add("border-warning");
          this.classList.remove("border-success", "border-danger");
        } else {
          this.classList.remove(
            "border-success",
            "border-warning",
            "border-danger",
          );
        }
      });
    }
  }

  // Product card hover effects
  const productCards = document.querySelectorAll(".product-card");
  productCards.forEach((card) => {
    card.addEventListener("mouseenter", function () {
      this.style.transform = "translateY(-5px)";
    });

    card.addEventListener("mouseleave", function () {
      this.style.transform = "translateY(0)";
    });
  });

  // Lazy loading for images
  const images = document.querySelectorAll("img[data-src]");
  const imageObserver = new IntersectionObserver((entries, observer) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        const img = entry.target;
        img.src = img.dataset.src;
        img.classList.remove("lazy");
        imageObserver.unobserve(img);
      }
    });
  });

  images.forEach((img) => imageObserver.observe(img));

  // Form validation enhancements
  const forms = document.querySelectorAll(".needs-validation");
  forms.forEach((form) => {
    form.addEventListener("submit", function (event) {
      if (!form.checkValidity()) {
        event.preventDefault();
        event.stopPropagation();
      }
      form.classList.add("was-validated");
    });
  });

  // Price formatting
  const priceElements = document.querySelectorAll("[data-price]");
  priceElements.forEach((element) => {
    const price = parseFloat(element.dataset.price);
    element.textContent = new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
    }).format(price);
  });

  // Quantity input validation
  const quantityInputs = document.querySelectorAll(
    'input[type="number"][name*="quantity"]',
  );
  quantityInputs.forEach((input) => {
    input.addEventListener("change", function () {
      const min = parseInt(this.min) || 1;
      const max = parseInt(this.max) || 999;
      const value = parseInt(this.value);

      if (value < min) this.value = min;
      if (value > max) this.value = max;
    });
  });

  // Shopping cart count update
  updateCartCount();
});

// Utility functions
function showNotification(message, type = "info") {
  const alertDiv = document.createElement("div");
  alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
  alertDiv.style.cssText =
    "top: 100px; right: 20px; z-index: 9999; min-width: 300px;";
  alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

  document.body.appendChild(alertDiv);

  // Auto remove after 4 seconds
  setTimeout(() => {
    if (alertDiv.parentNode) {
      alertDiv.remove();
    }
  }, 4000);
}

function formatCurrency(amount) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(amount);
}

function updateCartCount() {
  // This would typically fetch cart count from server
  // For now, we'll update based on existing cart items
  const cartItems = document.querySelectorAll(".cart-item");
  const cartBadge = document.querySelector(".navbar .badge");

  if (cartBadge && cartItems.length > 0) {
    let totalItems = 0;
    cartItems.forEach((item) => {
      const quantityInput = item.querySelector('input[type="number"]');
      if (quantityInput) {
        totalItems += parseInt(quantityInput.value) || 0;
      }
    });

    if (totalItems > 0) {
      cartBadge.textContent = totalItems;
      cartBadge.style.display = "inline-block";
    } else {
      cartBadge.style.display = "none";
    }
  }
}

// AJAX helper function
function makeAjaxRequest(url, method, data, successCallback, errorCallback) {
  const xhr = new XMLHttpRequest();
  xhr.open(method, url, true);
  xhr.setRequestHeader("Content-Type", "application/x-www-form-urlencoded");
  xhr.setRequestHeader("X-Requested-With", "XMLHttpRequest");

  // Add CSRF token for POST requests
  if (method === "POST") {
    const csrfToken = document.querySelector("[name=csrfmiddlewaretoken]");
    if (csrfToken) {
      xhr.setRequestHeader("X-CSRFToken", csrfToken.value);
    }
  }

  xhr.onreadystatechange = function () {
    if (xhr.readyState === 4) {
      if (xhr.status === 200) {
        try {
          const response = JSON.parse(xhr.responseText);
          if (successCallback) successCallback(response);
        } catch (e) {
          if (successCallback) successCallback(xhr.responseText);
        }
      } else {
        if (errorCallback) errorCallback(xhr);
        else showNotification("An error occurred. Please try again.", "danger");
      }
    }
  };

  xhr.send(data);
}

// Loading state management
function setLoadingState(element, loading = true) {
  if (loading) {
    element.classList.add("loading");
    element.disabled = true;
    const originalText = element.textContent;
    element.dataset.originalText = originalText;
    element.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Loading...';
  } else {
    element.classList.remove("loading");
    element.disabled = false;
    if (element.dataset.originalText) {
      element.textContent = element.dataset.originalText;
      delete element.dataset.originalText;
    }
  }
}

// Debounce function for search and other inputs
function debounce(func, wait, immediate) {
  let timeout;
  return function executedFunction() {
    const context = this;
    const args = arguments;
    const later = function () {
      timeout = null;
      if (!immediate) func.apply(context, args);
    };
    const callNow = immediate && !timeout;
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
    if (callNow) func.apply(context, args);
  };
}

// Enhanced UI Functions
function initializeEnhancedUI() {
  // Initialize dark mode
  initializeDarkMode();

  // Add entrance animations to page elements
  const animatedElements = document.querySelectorAll(
    ".card, .product-card, .category-tile",
  );

  const observerOptions = {
    threshold: 0.1,
    rootMargin: "0px 0px -50px 0px",
  };

  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add("animate-slide-up");
        observer.unobserve(entry.target);
      }
    });
  }, observerOptions);

  animatedElements.forEach((el) => {
    observer.observe(el);
  });

  // Enhanced button interactions
  enhanceButtons();

  // Add loading states to forms
  enhanceFormSubmissions();

  // Initialize smooth page transitions
  initializePageTransitions();
}

function initializeDarkMode() {
  // Check for saved theme preference or default to light mode
  const currentTheme = localStorage.getItem("theme") || "light";
  document.documentElement.setAttribute("data-theme", currentTheme);

  // Update icon based on current theme
  updateDarkModeIcon(currentTheme);

  // Add dark mode toggle listener
  const darkModeToggle = document.getElementById("darkModeToggle");
  if (darkModeToggle) {
    darkModeToggle.addEventListener("click", toggleDarkMode);
  }
}

function toggleDarkMode() {
  const currentTheme = document.documentElement.getAttribute("data-theme");
  const newTheme = currentTheme === "dark" ? "light" : "dark";

  document.documentElement.setAttribute("data-theme", newTheme);
  localStorage.setItem("theme", newTheme);
  updateDarkModeIcon(newTheme);

  // Show toast notification
  showToast(`Switched to ${newTheme} mode`, "success", 2000);
}

function updateDarkModeIcon(theme) {
  const icon = document.getElementById("darkModeIcon");
  if (icon) {
    icon.className = theme === "dark" ? "fas fa-sun" : "fas fa-moon";
  }
}

function enhanceButtons() {
  const buttons = document.querySelectorAll(".btn");

  buttons.forEach((button) => {
    button.addEventListener("click", function (e) {
      if (!this.disabled) {
        // Create ripple effect
        const ripple = document.createElement("span");
        const rect = this.getBoundingClientRect();
        const size = Math.max(rect.width, rect.height);
        const x = e.clientX - rect.left - size / 2;
        const y = e.clientY - rect.top - size / 2;

        ripple.style.cssText = `
          position: absolute;
          border-radius: 50%;
          background: rgba(255, 255, 255, 0.6);
          width: ${size}px;
          height: ${size}px;
          left: ${x}px;
          top: ${y}px;
          pointer-events: none;
          transform: scale(0);
          animation: ripple 0.6s linear;
        `;

        this.style.position = "relative";
        this.style.overflow = "hidden";
        this.appendChild(ripple);

        setTimeout(() => ripple.remove(), 600);
      }
    });
  });
}

function enhanceFormSubmissions() {
  const forms = document.querySelectorAll("form");

  forms.forEach((form) => {
    form.addEventListener("submit", function (e) {
      const submitButton = this.querySelector(
        'button[type="submit"], input[type="submit"]',
      );
      if (submitButton && !submitButton.disabled) {
        setLoadingState(submitButton, true);

        // Re-enable button after 5 seconds as fallback
        setTimeout(() => {
          setLoadingState(submitButton, false);
        }, 5000);
      }
    });
  });
}

function initializePageTransitions() {
  // Add smooth page transitions for internal links
  const internalLinks = document.querySelectorAll(
    'a[href^="/"], a[href^="' + window.location.origin + '"]',
  );

  internalLinks.forEach((link) => {
    link.addEventListener("click", function (e) {
      if (!e.ctrlKey && !e.metaKey && !e.shiftKey) {
        showLoadingOverlay(200);
      }
    });
  });

  // Hide loading overlay when page loads
  window.addEventListener("load", () => {
    hideLoadingOverlay();
  });
}

function showLoadingOverlay(delay = 0) {
  setTimeout(() => {
    let overlay = document.getElementById("loadingOverlay");
    if (!overlay) {
      overlay = document.createElement("div");
      overlay.id = "loadingOverlay";
      overlay.className = "loading-overlay";
      overlay.innerHTML = '<div class="spinner"></div>';
      document.body.appendChild(overlay);
    }
    overlay.style.display = "flex";
    overlay.style.opacity = "0";
    setTimeout(() => (overlay.style.opacity = "1"), 10);
  }, delay);
}

function hideLoadingOverlay() {
  const overlay = document.getElementById("loadingOverlay");
  if (overlay) {
    overlay.style.opacity = "0";
    setTimeout(() => {
      overlay.style.display = "none";
    }, 300);
  }
}

function showToast(message, type = "success", duration = 3000) {
  // Create toast container if it doesn't exist
  let container = document.querySelector(".toast-container");
  if (!container) {
    container = document.createElement("div");
    container.className = "toast-container";
    document.body.appendChild(container);
  }

  // Create toast element
  const toast = document.createElement("div");
  toast.className = `toast toast-${type} show`;
  toast.setAttribute("role", "alert");

  toast.innerHTML = `
    <div class="toast-body d-flex align-items-center">
      <i class="fas fa-${type === "success" ? "check-circle" : "exclamation-circle"} me-2"></i>
      ${message}
      <button type="button" class="btn-close btn-close-white ms-auto" data-bs-dismiss="toast"></button>
    </div>
  `;

  container.appendChild(toast);

  // Auto-remove after duration
  setTimeout(() => {
    toast.classList.remove("show");
    setTimeout(() => toast.remove(), 300);
  }, duration);
}

// Add CSS for ripple effect animation
const style = document.createElement("style");
style.textContent = `
  @keyframes ripple {
    to {
      transform: scale(4);
      opacity: 0;
    }
  }
`;
document.head.appendChild(style);

// Export functions for use in other scripts
window.ShopHub = {
  showNotification,
  formatCurrency,
  updateCartCount,
  makeAjaxRequest,
  setLoadingState,
  debounce,
  showLoadingOverlay,
  hideLoadingOverlay,
  showToast,
  initializeEnhancedUI,
  toggleDarkMode,
  initializeDarkMode,
};
