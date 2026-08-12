/*
 * ValueVista Mini UI contract (no dependencies):
 *
 * Comparison controls:
 *   [data-compare-toggle][data-compare-id]   add/remove a product. Optional
 *       data-compare-name, data-compare-selected-label, and
 *       data-compare-unselected-label customize its feedback.
 *   [data-compare-remove="PRODUCT_ID"]       removes one product.
 *   [data-compare-clear]                     clears the current selection.
 *   [data-compare-count]                     receives the selected total.
 *   [data-compare-status]                    receives data-count/data-state;
 *       use data-compare-status-message on a child when it needs visible text.
 *   [data-compare-link]                      becomes /compare?ids=ID1,ID2.
 *       Optional data-compare-url provides a different base compare URL.
 *   [data-compare-selection], [data-compare-empty], and [data-compare-ready]
 *       are optional status helpers.
 *
 * Other optional controls:
 *   [data-nav-toggle] / [data-menu-toggle] with [data-primary-nav] /
 *       [data-mobile-nav] for a mobile navigation drawer.
 *   [data-filter-toggle] with .filters-panel for mobile filters.
 *   [data-toast] (and an optional [data-toast-message], [data-toast-close])
 *       for dismissible feedback. A toast is made automatically when absent.
 */

(function () {
  "use strict";

  var STORAGE_KEY = "valuevista.compareIds";
  var MAX_COMPARE_ITEMS = 3;
  var memoryIds = [];
  var toastTimer = null;

  function normaliseIds(value) {
    var raw = Array.isArray(value) ? value : [];
    var result = [];

    raw.forEach(function (item) {
      var id = String(item == null ? "" : item).trim();
      if (id && id.length <= 120 && result.indexOf(id) === -1 && result.length < MAX_COMPARE_ITEMS) {
        result.push(id);
      }
    });

    return result;
  }

  function sameIds(first, second) {
    return first.length === second.length && first.every(function (id, index) {
      return id === second[index];
    });
  }

  function getIds() {
    try {
      var stored = window.localStorage.getItem(STORAGE_KEY);
      if (stored === null) {
        return memoryIds.slice();
      }
      var parsed = JSON.parse(stored);
      var ids = normaliseIds(parsed);
      memoryIds = ids.slice();
      return ids;
    } catch (error) {
      return memoryIds.slice();
    }
  }

  function saveIds(ids) {
    var cleanIds = normaliseIds(ids);
    memoryIds = cleanIds.slice();

    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(cleanIds));
    } catch (error) {
      // Some private-browser configurations block storage. The current page
      // remains fully usable with the in-memory fallback.
    }

    document.dispatchEvent(new CustomEvent("valuevista:comparechange", {
      detail: { ids: cleanIds.slice(), maximum: MAX_COMPARE_ITEMS }
    }));

    return cleanIds;
  }

  function readIdsFromLocation() {
    var params = new URLSearchParams(window.location.search);
    var value = params.get("ids");
    return value ? normaliseIds(value.split(",")) : [];
  }

  function compareBaseUrl(element) {
    if (element && element.dataset && element.dataset.compareUrl) {
      return element.dataset.compareUrl;
    }
    if (document.body.dataset.compareUrl) {
      return document.body.dataset.compareUrl;
    }
    if (element && element.tagName === "A") {
      var href = element.getAttribute("href");
      if (href && href !== "#") {
        return href;
      }
    }
    return "/compare";
  }

  function buildCompareUrl(base, ids) {
    var url;
    try {
      url = new URL(base || "/compare", window.location.href);
    } catch (error) {
      url = new URL("/compare", window.location.href);
    }

    url.searchParams.delete("ids");
    if (ids.length) {
      url.searchParams.set("ids", ids.join(","));
    }

    if (url.origin === window.location.origin) {
      return url.pathname + url.search + url.hash;
    }
    return url.toString();
  }

  function selectionState(ids) {
    if (!ids.length) {
      return "empty";
    }
    if (ids.length >= MAX_COMPARE_ITEMS) {
      return "full";
    }
    if (ids.length === 1) {
      return "single";
    }
    return "ready";
  }

  function selectionMessage(ids) {
    if (!ids.length) {
      return "No products selected for comparison.";
    }
    if (ids.length === 1) {
      return "1 product selected. Add one more to compare.";
    }
    return ids.length + " products ready to compare.";
  }

  function controls() {
    return Array.prototype.slice.call(document.querySelectorAll(
      "[data-compare-toggle][data-compare-id], [data-compare-id][data-compare-action='toggle']"
    ));
  }

  function setToggleLabel(control, selected) {
    if (control.matches("input[type='checkbox'], input[type='radio']")) {
      control.checked = selected;
      return;
    }

    if (!control.dataset.compareOriginalLabel) {
      control.dataset.compareOriginalLabel = control.textContent.trim();
    }

    var selectedLabel = control.dataset.compareSelectedLabel || "Added";
    var originalLabel = control.dataset.compareUnselectedLabel || control.dataset.compareOriginalLabel;
    control.textContent = selected ? selectedLabel : originalLabel;
  }

  function syncCompareControls(ids) {
    controls().forEach(function (control) {
      var id = String(control.dataset.compareId || "").trim();
      var selected = ids.indexOf(id) !== -1;
      var atLimit = !selected && ids.length >= MAX_COMPARE_ITEMS;

      control.classList.toggle("is-selected", selected);
      control.classList.toggle("is-at-limit", atLimit);
      control.setAttribute("aria-pressed", selected ? "true" : "false");
      control.setAttribute("aria-label", selected
        ? "Remove " + (control.dataset.compareName || "product") + " from comparison"
        : "Add " + (control.dataset.compareName || "product") + " to comparison");
      control.setAttribute("data-compare-selected", selected ? "true" : "false");
      setToggleLabel(control, selected);
    });
  }

  function syncCompareLinks(ids) {
    document.querySelectorAll("[data-compare-link]").forEach(function (link) {
      var url = buildCompareUrl(compareBaseUrl(link), ids);
      if (link.tagName === "A") {
        link.href = url;
      } else {
        link.dataset.compareHref = url;
      }
      link.setAttribute("aria-label", ids.length
        ? "Compare " + ids.length + " selected product" + (ids.length === 1 ? "" : "s")
        : "Open product comparison");
    });
  }

  function syncStatus(ids) {
    var state = selectionState(ids);
    var message = selectionMessage(ids);

    document.querySelectorAll("[data-compare-count]").forEach(function (count) {
      count.textContent = String(ids.length);
      count.setAttribute("aria-label", ids.length + " products selected for comparison");
    });

    document.querySelectorAll("[data-compare-status]").forEach(function (status) {
      status.dataset.count = String(ids.length);
      status.dataset.state = state;
      status.setAttribute("aria-label", message);

      var messageTarget = status.querySelector("[data-compare-status-message]");
      if (messageTarget) {
        messageTarget.textContent = message;
      } else if (!status.children.length || status.dataset.compareStatusText === "true") {
        status.textContent = message;
      }
    });

    document.querySelectorAll("[data-compare-selection]").forEach(function (selection) {
      selection.textContent = ids.join(", ");
    });

    document.querySelectorAll("[data-compare-empty]").forEach(function (element) {
      element.hidden = ids.length !== 0;
    });

    document.querySelectorAll("[data-compare-ready]").forEach(function (element) {
      element.hidden = ids.length < 2;
    });
  }

  function syncAll(ids) {
    var cleanIds = normaliseIds(ids || getIds());
    syncCompareControls(cleanIds);
    syncCompareLinks(cleanIds);
    syncStatus(cleanIds);
    return cleanIds;
  }

  function getToast() {
    var toast = document.querySelector("[data-toast]");
    if (!toast) {
      toast = document.createElement("div");
      toast.className = "toast";
      toast.dataset.toast = "";
      toast.setAttribute("role", "status");
      toast.setAttribute("aria-live", "polite");
      document.body.appendChild(toast);
    }

    var message = toast.querySelector("[data-toast-message]");
    if (!message) {
      message = document.createElement("span");
      message.dataset.toastMessage = "";
      message.className = "toast__message";
      toast.appendChild(message);
    }

    var close = toast.querySelector("[data-toast-close]");
    if (!close) {
      close = document.createElement("button");
      close.type = "button";
      close.className = "toast__close";
      close.dataset.toastClose = "";
      close.setAttribute("aria-label", "Dismiss message");
      close.textContent = "×";
      toast.appendChild(close);
    }

    return { element: toast, message: message };
  }

  function hideToast() {
    var toast = document.querySelector("[data-toast]");
    if (!toast) {
      return;
    }
    toast.classList.remove("is-visible");
    toast.setAttribute("aria-hidden", "true");
    window.setTimeout(function () {
      if (!toast.classList.contains("is-visible")) {
        toast.hidden = true;
      }
    }, 190);
  }

  function showToast(message, tone) {
    var toastParts = getToast();
    var toast = toastParts.element;
    window.clearTimeout(toastTimer);
    toast.hidden = false;
    toast.dataset.tone = tone || "success";
    toastParts.message.textContent = message;
    toast.setAttribute("aria-hidden", "false");

    // A frame gives the browser a chance to apply its hidden/display state
    // before the transition class appears.
    window.requestAnimationFrame(function () {
      toast.classList.add("is-visible");
    });

    toastTimer = window.setTimeout(hideToast, 4200);
  }

  function productLabel(control) {
    return String(control.dataset.compareName || "This product").trim() || "This product";
  }

  function toggleProduct(control) {
    var id = String(control.dataset.compareId || "").trim();
    if (!id) {
      return;
    }

    var ids = getIds();
    var selectedIndex = ids.indexOf(id);
    if (selectedIndex !== -1) {
      ids.splice(selectedIndex, 1);
      ids = saveIds(ids);
      syncAll(ids);
      showToast(productLabel(control) + " removed from comparison.", "success");
      return;
    }

    if (ids.length >= MAX_COMPARE_ITEMS) {
      showToast("You can compare up to " + MAX_COMPARE_ITEMS + " products. Remove one to add another.", "error");
      return;
    }

    ids.push(id);
    ids = saveIds(ids);
    syncAll(ids);
    showToast(productLabel(control) + " added to comparison (" + ids.length + " of " + MAX_COMPARE_ITEMS + ").", "success");
  }

  function navigateComparePage(ids) {
    if (!document.body.hasAttribute("data-compare-page")) {
      return;
    }

    var destination = buildCompareUrl(window.location.pathname, ids);
    if (destination !== window.location.pathname + window.location.search + window.location.hash) {
      window.location.assign(destination);
    }
  }

  function removeProduct(id) {
    var ids = getIds().filter(function (selectedId) {
      return selectedId !== id;
    });
    var changed = !sameIds(ids, getIds());
    ids = saveIds(ids);
    syncAll(ids);

    if (changed) {
      showToast("Product removed from comparison.", "success");
    }
    navigateComparePage(ids);
  }

  function clearProducts() {
    var hadItems = getIds().length > 0;
    var ids = saveIds([]);
    syncAll(ids);
    if (hadItems) {
      showToast("Your comparison has been cleared.", "success");
    }
    navigateComparePage(ids);
  }

  function initialiseMenu() {
    var toggles = document.querySelectorAll("[data-nav-toggle], [data-menu-toggle]");
    var menus = document.querySelectorAll("[data-primary-nav], [data-mobile-nav]");

    if (!toggles.length || !menus.length) {
      return;
    }

    function setOpen(open) {
      menus.forEach(function (menu) {
        menu.classList.toggle("is-open", open);
      });
      toggles.forEach(function (toggle) {
        toggle.classList.toggle("is-open", open);
        toggle.setAttribute("aria-expanded", open ? "true" : "false");
        toggle.setAttribute("aria-label", open ? "Close navigation" : "Open navigation");
      });
      document.body.classList.toggle("menu-open", open);
    }

    toggles.forEach(function (toggle) {
      toggle.addEventListener("click", function () {
        setOpen(toggle.getAttribute("aria-expanded") !== "true");
      });
    });

    menus.forEach(function (menu) {
      menu.addEventListener("click", function (event) {
        if (event.target.closest("a")) {
          setOpen(false);
        }
      });
    });

    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape") {
        setOpen(false);
      }
    });

    var breakpoint = window.matchMedia("(min-width: 821px)");
    function closeAtDesktop(event) {
      if (event.matches) {
        setOpen(false);
      }
    }
    if (breakpoint.addEventListener) {
      breakpoint.addEventListener("change", closeAtDesktop);
    } else {
      breakpoint.addListener(closeAtDesktop);
    }
  }

  function initialiseFilters() {
    var toggles = document.querySelectorAll("[data-filter-toggle]");
    if (!toggles.length) {
      return;
    }

    toggles.forEach(function (toggle) {
      var layout = toggle.closest(".catalogue-layout, .listing-layout");
      var panel = layout && layout.querySelector(".filters-panel, .filter-panel, .filters");
      if (!panel) {
        return;
      }
      toggle.setAttribute("aria-expanded", "false");
      toggle.addEventListener("click", function () {
        var open = !panel.classList.contains("is-open");
        panel.classList.toggle("is-open", open);
        toggle.classList.toggle("is-active", open);
        toggle.setAttribute("aria-expanded", open ? "true" : "false");
      });
    });
  }

  function initialiseComparePage() {
    if (!document.body.hasAttribute("data-compare-page")) {
      return;
    }

    var idsInUrl = readIdsFromLocation();
    if (idsInUrl.length) {
      saveIds(idsInUrl);
      return;
    }

    var savedIds = getIds();
    if (savedIds.length) {
      window.location.replace(buildCompareUrl(window.location.pathname, savedIds));
    }
  }

  function initialiseEvents() {
    document.addEventListener("click", function (event) {
      var target = event.target;
      if (!target || !target.closest) {
        return;
      }

      var toggle = target.closest("[data-compare-toggle][data-compare-id], [data-compare-id][data-compare-action='toggle']");
      if (toggle) {
        event.preventDefault();
        toggleProduct(toggle);
        return;
      }

      var remove = target.closest("[data-compare-remove]");
      if (remove) {
        event.preventDefault();
        var id = String(remove.dataset.compareRemove || remove.dataset.compareId || remove.value || "").trim();
        if (id) {
          removeProduct(id);
        }
        return;
      }

      if (target.closest("[data-compare-clear]")) {
        event.preventDefault();
        clearProducts();
        return;
      }

      if (target.closest("[data-toast-close]")) {
        event.preventDefault();
        window.clearTimeout(toastTimer);
        hideToast();
        return;
      }

      var compareButton = target.closest("[data-compare-link]:not(a)");
      if (compareButton && compareButton.dataset.compareHref) {
        window.location.assign(compareButton.dataset.compareHref);
      }
    });

    window.addEventListener("storage", function (event) {
      if (event.key === STORAGE_KEY) {
        syncAll(getIds());
      }
    });
  }

  function initialise() {
    initialiseComparePage();
    syncAll(getIds());
    initialiseMenu();
    initialiseFilters();
    initialiseEvents();

    // A tiny public surface is useful for server-rendered pages that may add
    // products dynamically, while keeping all storage rules in one place.
    window.ValueVistaCompare = {
      getIds: function () { return getIds().slice(); },
      setIds: function (ids) { return syncAll(saveIds(ids)); },
      clear: clearProducts,
      maximum: MAX_COMPARE_ITEMS,
      buildUrl: function () { return buildCompareUrl("/compare", getIds()); }
    };
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initialise, { once: true });
  } else {
    initialise();
  }
}());
