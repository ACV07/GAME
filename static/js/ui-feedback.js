/**
 * ui-feedback.js
 * Mobile-first interaction and feedback module.
 */

window.ArenaFeedback = (function () {
  function show(el, message, type) {
    if (!el) return;
    el.className = `alert-banner alert-${type}`;
    el.innerHTML = message;
    el.style.display = 'flex';
  }

  function hide(el) {
    if (!el) return;
    el.style.display = 'none';
  }

  /**
   * Trigger a quick horizontal shake animation on an element (e.g. form, card, or option)
   * @param {HTMLElement|null} el 
   */
  function shake(el) {
    if (!el) return;
    el.classList.remove('shake-element');
    void el.offsetWidth; // Force reflow
    el.classList.add('shake-element');
    setTimeout(() => {
      el.classList.remove('shake-element');
    }, 400);
  }

  /**
   * Trigger floating score upward animation (+50 / +100)
   * @param {number} pts 
   */
  function popScore(pts = 50) {
    if (window.triggerFloatingScore) {
      window.triggerFloatingScore(pts);
    }
  }

  return { show, hide, shake, popScore };
})();

// Mobile Immediate Touch Feedback Listener
document.addEventListener('DOMContentLoaded', () => {
  const touchableSelector = '.btn-cyber, .btn-secondary, .option-chip, .blank-slot, .code-line-item, .glass-card';

  document.addEventListener('touchstart', (e) => {
    const target = e.target.closest(touchableSelector);
    if (target) {
      target.classList.add('is-tapped');
    }
  }, { passive: true });

  document.addEventListener('touchend', (e) => {
    const target = e.target.closest(touchableSelector);
    if (target) {
      setTimeout(() => target.classList.remove('is-tapped'), 150);
    }
  }, { passive: true });

  document.addEventListener('touchcancel', (e) => {
    const target = e.target.closest(touchableSelector);
    if (target) {
      target.classList.remove('is-tapped');
    }
  }, { passive: true });
});
