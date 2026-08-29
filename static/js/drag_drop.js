/**
 * drag_drop.js
 * Mobile-Optimized Drag-and-Drop & Tap-to-Fill Logic with Staggered Animations.
 * Depends on ui-feedback.js (window.ArenaFeedback) and drafts.js (window.ArenaDraft).
 */

document.addEventListener('DOMContentLoaded', () => {
  const blankSlots = document.querySelectorAll('.blank-slot');
  const optionChips = document.querySelectorAll('.option-chip');
  const btnReset = document.getElementById('btn-reset-blanks');
  const submitForm = document.getElementById('challenge-form');
  const feedbackBox = document.getElementById('feedback-box');
  const btnSubmit = document.getElementById('btn-submit');

  const SUCCESS_REDIRECT_DELAY_MS = 1200;
  const SUBMIT_LABEL_DEFAULT = 'Submit Code Answer ➔';
  const SUBMIT_LABEL_EVALUATING = 'Evaluating...';
  const EMPTY_SLOT_TEXT = '___';

  // --- HTML5 Desktop Drag and Drop ---
  optionChips.forEach(chip => {
    chip.addEventListener('dragstart', (e) => {
      if (chip.classList.contains('used')) return;
      chip.classList.add('dragging');
      e.dataTransfer.setData('text/plain', chip.dataset.value);
    });

    chip.addEventListener('dragend', () => {
      chip.classList.remove('dragging');
    });

    // Tap / click to fill support (desktop & mobile)
    chip.addEventListener('click', () => {
      if (chip.classList.contains('used')) return;
      const firstEmpty = Array.from(blankSlots).find(slot => !slot.dataset.value);
      if (firstEmpty) {
        fillSlot(firstEmpty, chip.dataset.value, chip);
      }
    });
  });

  // --- Mobile Finger Touch Drag & Drop Handler ---
  let activeTouchChip = null;
  let touchGhost = null;

  optionChips.forEach(chip => {
    chip.addEventListener('touchstart', (e) => {
      if (chip.classList.contains('used')) return;
      activeTouchChip = chip;
      chip.classList.add('is-dragging-touch');

      const rect = chip.getBoundingClientRect();
      touchGhost = chip.cloneNode(true);
      touchGhost.style.position = 'fixed';
      touchGhost.style.left = `${rect.left}px`;
      touchGhost.style.top = `${rect.top}px`;
      touchGhost.style.width = `${rect.width}px`;
      touchGhost.style.height = `${rect.height}px`;
      touchGhost.style.pointerEvents = 'none';
      touchGhost.style.opacity = '0.92';
      touchGhost.style.zIndex = '9999';
      touchGhost.style.boxShadow = '0 0 24px rgba(0, 217, 255, 0.8)';
      document.body.appendChild(touchGhost);
    }, { passive: true });

    chip.addEventListener('touchmove', (e) => {
      if (!activeTouchChip || !touchGhost) return;
      const touch = e.touches[0];
      touchGhost.style.left = `${touch.clientX - touchGhost.offsetWidth / 2}px`;
      touchGhost.style.top = `${touch.clientY - touchGhost.offsetHeight / 2}px`;

      const elemBelow = document.elementFromPoint(touch.clientX, touch.clientY);
      blankSlots.forEach(slot => {
        if (slot.contains(elemBelow) || slot === elemBelow) {
          slot.classList.add('drag-over');
        } else {
          slot.classList.remove('drag-over');
        }
      });
    }, { passive: true });

    chip.addEventListener('touchend', (e) => {
      if (!activeTouchChip) return;
      if (touchGhost) {
        touchGhost.remove();
        touchGhost = null;
      }

      const touch = e.changedTouches[0];
      const elemBelow = document.elementFromPoint(touch.clientX, touch.clientY);
      let targetSlot = null;
      blankSlots.forEach(slot => {
        if (slot.contains(elemBelow) || slot === elemBelow) {
          targetSlot = slot;
        }
        slot.classList.remove('drag-over');
      });

      if (targetSlot) {
        fillSlot(targetSlot, activeTouchChip.dataset.value, activeTouchChip);
      }
      activeTouchChip.classList.remove('is-dragging-touch');
      activeTouchChip = null;
    }, { passive: true });
  });

  blankSlots.forEach(slot => {
    slot.addEventListener('dragover', (e) => {
      e.preventDefault();
      slot.classList.add('drag-over');
    });

    slot.addEventListener('dragleave', () => {
      slot.classList.remove('drag-over');
    });

    slot.addEventListener('drop', (e) => {
      e.preventDefault();
      slot.classList.remove('drag-over');
      const val = e.dataTransfer.getData('text/plain');
      if (!val) return;
      const matchingChip = Array.from(optionChips).find(c => c.dataset.value === val && !c.classList.contains('used'));
      fillSlot(slot, val, matchingChip);
    });

    // Clicking a filled blank clears it
    slot.addEventListener('click', () => {
      if (slot.dataset.value) clearSlot(slot);
    });
  });

  function fillSlot(slot, value, chipElement) {
    if (slot.dataset.value) clearSlot(slot);

    slot.dataset.value = value;
    slot.textContent = value;
    slot.classList.add('filled');

    const chip = chipElement || Array.from(optionChips).find(c => c.dataset.value === value && !c.classList.contains('used'));
    if (chip) chip.classList.add('used');

    persistDraft();
  }

  function clearSlot(slot) {
    const prevVal = slot.dataset.value;
    if (!prevVal) return;

    slot.dataset.value = '';
    slot.textContent = EMPTY_SLOT_TEXT;
    slot.classList.remove('filled');

    const usedChip = Array.from(optionChips).find(c => c.dataset.value === prevVal && c.classList.contains('used'));
    if (usedChip) usedChip.classList.remove('used');

    persistDraft();
  }

  function persistDraft() {
    if (!window.ArenaDraft || !submitForm) return;
    const values = Array.from(blankSlots).map(s => s.dataset.value || '');
    window.ArenaDraft.save(parseInt(submitForm.dataset.challengeId, 10), values);
  }

  // Restore saved draft
  if (Array.isArray(window.savedDraft)) {
    window.savedDraft.forEach((value, index) => {
      if (!value) return;
      const slot = blankSlots[index];
      const chip = Array.from(optionChips).find(c => c.dataset.value === value && !c.classList.contains('used'));
      if (slot) fillSlot(slot, value, chip);
    });
  }

  if (btnReset) {
    btnReset.addEventListener('click', () => {
      blankSlots.forEach(slot => clearSlot(slot));
      ArenaFeedback.hide(feedbackBox);
    });
  }

  // --- Submit Challenge ---
  if (submitForm) {
    submitForm.addEventListener('submit', async (e) => {
      e.preventDefault();

      const submittedAnswers = Array.from(blankSlots).map(s => s.dataset.value || '');

      if (submittedAnswers.some(ans => ans === '')) {
        ArenaFeedback.shake(submitForm);
        ArenaFeedback.show(feedbackBox, 'Please fill in all blank spaces before submitting.', 'warning');
        return;
      }

      if (window.contestantRoundStatus && window.contestantRoundStatus !== 'ACTIVE') {
        if (window.checkBroadcast) window.checkBroadcast();
        return;
      }

      const challengeId = parseInt(submitForm.dataset.challengeId, 10);
      btnSubmit.disabled = true;
      btnSubmit.innerHTML = SUBMIT_LABEL_EVALUATING;

      try {
        const response = await fetch('/api/submit-challenge', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            challenge_id: challengeId,
            answer: submittedAnswers
          })
        });

        const resData = await response.json();

        if (resData.success) {
          ArenaFeedback.popScore(50);
          ArenaFeedback.show(feedbackBox, '<span class="correct-toast-inline">✓ CORRECT! +50</span>', 'success');
          
          if (window.triggerSlideNav) {
            window.triggerSlideNav(resData.redirect_url, false);
          } else {
            setTimeout(() => {
              window.location.href = resData.redirect_url;
            }, SUCCESS_REDIRECT_DELAY_MS);
          }
          return;
        }

        if (resData.stopped || resData.message === 'GAME_STOPPED') {
          if (window.checkBroadcast) window.checkBroadcast();
        } else {
          ArenaFeedback.shake(submitForm);
          ArenaFeedback.show(feedbackBox, resData.message || '❌ Incorrect solution. Try again!', 'danger');
        }
        btnSubmit.disabled = false;
        btnSubmit.innerHTML = SUBMIT_LABEL_DEFAULT;
      } catch (err) {
        ArenaFeedback.shake(submitForm);
        if (window.checkBroadcast) window.checkBroadcast();
        btnSubmit.disabled = false;
        btnSubmit.innerHTML = SUBMIT_LABEL_DEFAULT;
      }
    });
  }
});
