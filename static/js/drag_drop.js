/**
 * drag_drop.js
 * Mobile-Optimized Drag-and-Drop & Any-Order Tap-to-Fill Logic.
 * Enables contestants to select ANY blank slot directly and fill keywords out-of-order.
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

  let activeTargetSlot = null;

  function setActiveTarget(slot) {
    blankSlots.forEach(s => s.classList.remove('active-target-slot'));
    if (slot) {
      activeTargetSlot = slot;
      slot.classList.add('active-target-slot');
    } else {
      activeTargetSlot = null;
    }
  }

  // --- Blank Slot Click Handler: Select slot or clear slot ---
  blankSlots.forEach(slot => {
    slot.addEventListener('click', () => {
      if (slot.dataset.value) {
        clearSlot(slot);
      }
      setActiveTarget(slot);
    });

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
      setActiveTarget(null);
    });
  });

  // --- Option Chips Click & Drag Handlers ---
  optionChips.forEach(chip => {
    chip.addEventListener('dragstart', (e) => {
      if (chip.classList.contains('used')) return;
      chip.classList.add('dragging');
      e.dataTransfer.setData('text/plain', chip.dataset.value);
    });

    chip.addEventListener('dragend', () => {
      chip.classList.remove('dragging');
    });

    // Tap / click to fill any selected slot or first available slot
    chip.addEventListener('click', () => {
      if (chip.classList.contains('used')) return;

      let target = activeTargetSlot;
      // If no active target slot or active target slot is already filled, pick first empty slot
      if (!target || target.dataset.value) {
        target = Array.from(blankSlots).find(slot => !slot.dataset.value);
      }

      if (target) {
        fillSlot(target, chip.dataset.value, chip);
        // Automatically select the next empty slot if available
        const nextEmpty = Array.from(blankSlots).find(slot => !slot.dataset.value);
        setActiveTarget(nextEmpty || null);
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
        setActiveTarget(null);
      }
      activeTouchChip.classList.remove('is-dragging-touch');
      activeTouchChip = null;
    }, { passive: true });
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
      setActiveTarget(null);
      if (window.ArenaFeedback) window.ArenaFeedback.hide(feedbackBox);
    });
  }

  // --- Submit Challenge ---
  if (submitForm) {
    submitForm.addEventListener('submit', async (e) => {
      e.preventDefault();

      const submittedAnswers = Array.from(blankSlots).map(s => s.dataset.value || '');

      if (submittedAnswers.some(ans => ans === '')) {
        if (window.ArenaFeedback) {
          window.ArenaFeedback.shake(submitForm);
          window.ArenaFeedback.show(feedbackBox, 'Please fill in all blank spaces before submitting.', 'warning');
        }
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
          if (window.ArenaFeedback) {
            window.ArenaFeedback.popScore(50);
            window.ArenaFeedback.show(feedbackBox, '<span class="correct-toast-inline">✓ CORRECT! +50</span>', 'success');
          }
          
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
          if (window.ArenaFeedback) {
            window.ArenaFeedback.shake(submitForm);
            window.ArenaFeedback.show(feedbackBox, resData.message || '❌ Incorrect solution. Try again!', 'danger');
          }
        }
        btnSubmit.disabled = false;
        btnSubmit.innerHTML = SUBMIT_LABEL_DEFAULT;
      } catch (err) {
        if (window.ArenaFeedback) window.ArenaFeedback.shake(submitForm);
        if (window.checkBroadcast) window.checkBroadcast();
        btnSubmit.disabled = false;
        btnSubmit.innerHTML = SUBMIT_LABEL_DEFAULT;
      }
    });
  }
});
