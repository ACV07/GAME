/**
 * ui-feedback.js
 * Mobile-first interaction, feedback module, and Horizontal Slide Transitions (Forward & Reverse).
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

// Horizontal Slide Navigation Handler for Client Contestant Pages
document.addEventListener('DOMContentLoaded', () => {
  const mainCard = document.querySelector('.glass-card');
  if (!mainCard) return;

  // 1. Check Entry Navigation Direction (Forward vs Reverse)
  const navDir = sessionStorage.getItem('arena_nav_direction');
  if (navDir === 'prev') {
    mainCard.classList.remove('challenge-slide-in-next', 'challenge-slide-out-prev', 'challenge-slide-out-next');
    mainCard.classList.add('challenge-slide-in-prev');
    sessionStorage.removeItem('arena_nav_direction');
  } else if (navDir === 'next') {
    mainCard.classList.remove('challenge-slide-in-prev', 'challenge-slide-out-prev', 'challenge-slide-out-next');
    mainCard.classList.add('challenge-slide-in-next');
    sessionStorage.removeItem('arena_nav_direction');
  }

  // 2. Determine Current Challenge ID
  let currentChallengeId = null;
  const challengeForm = document.querySelector('[data-challenge-id]');
  if (challengeForm) {
    currentChallengeId = parseInt(challengeForm.dataset.challengeId, 10);
  }

  // 3. Helper to trigger horizontal slide out before page redirect
  window.triggerSlideNav = function (targetUrl, isReverse = false) {
    sessionStorage.setItem('arena_nav_direction', isReverse ? 'prev' : 'next');
    mainCard.classList.remove('challenge-slide-in-next', 'challenge-slide-in-prev');
    if (isReverse) {
      mainCard.classList.add('challenge-slide-out-prev');
    } else {
      mainCard.classList.add('challenge-slide-out-next');
    }
    setTimeout(() => {
      window.location.href = targetUrl;
    }, 240);
  };

  // 4. Intercept Link Clicks for Challenge Navigation (Previous, Next, Step Nodes)
  document.addEventListener('click', (e) => {
    const link = e.target.closest('a');
    if (!link) return;

    const href = link.getAttribute('href');
    if (!href || !href.includes('/challenge/')) return;

    const match = href.match(/\/challenge\/(\d+)/);
    if (!match) return;

    const targetId = parseInt(match[1], 10);
    if (isNaN(targetId)) return;

    e.preventDefault();

    if (currentChallengeId !== null && targetId < currentChallengeId) {
      // Reverse Slide (Going to Previous Challenge) -> Current card slides RIGHT out
      window.triggerSlideNav(href, true);
    } else {
      // Forward Slide (Going to Next Challenge) -> Current card slides LEFT out
      window.triggerSlideNav(href, false);
    }
  });

  // 5. Intercept Skip Challenge Button
  const btnSkip = document.getElementById('btn-skip-challenge');
  if (btnSkip) {
    btnSkip.addEventListener('click', (e) => {
      e.preventDefault();
      if (currentChallengeId !== null) {
        const nextId = currentChallengeId < 5 ? currentChallengeId + 1 : 5;
        window.triggerSlideNav(`/challenge/${nextId}`, false);
      }
    });
  }

  // 6. Mobile Immediate Touch Feedback
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
