/**
 * ui-feedback.js
 * Shared helper for showing/hiding the challenge feedback banner.
 * Used by line_selector.js and drag_drop.js so the banner markup
 * and behavior stay in one place instead of being duplicated per-challenge-type.
 */

window.ArenaFeedback = (function () {
  /**
   * Show a message in the given feedback element.
   * @param {HTMLElement|null} el - the feedback banner element
   * @param {string} message - message to display (may contain trusted markup)
   * @param {'success'|'warning'|'danger'} type - banner style variant
   */
  function show(el, message, type) {
    if (!el) return;
    el.className = `alert-banner alert-${type}`;
    el.innerHTML = message;
    el.style.display = 'flex';
  }

  /**
   * Hide the feedback banner.
   * @param {HTMLElement|null} el - the feedback banner element
   */
  function hide(el) {
    if (!el) return;
    el.style.display = 'none';
  }

  return { show, hide };
})();
