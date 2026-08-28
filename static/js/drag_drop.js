/**
 * drag_drop.js
 * Drag-and-Drop / Tap-to-Fill Logic for Challenges 1 & 2.
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
  const SUBMIT_LABEL_DEFAULT = 'Submit Code Answer';
  const SUBMIT_LABEL_EVALUATING = 'Evaluating...';
  const EMPTY_SLOT_TEXT = '___';

  // --- Drag and drop ---
  optionChips.forEach(chip => {
    chip.addEventListener('dragstart', (e) => {
      if (chip.classList.contains('used')) return;
      chip.classList.add('dragging');
      e.dataTransfer.setData('text/plain', chip.dataset.value);
    });

    chip.addEventListener('dragend', () => {
      chip.classList.remove('dragging');
    });

    // Tap / click to fill support (desktop & mobile).
    chip.addEventListener('click', () => {
      if (chip.classList.contains('used')) return;
      const firstEmpty = Array.from(blankSlots).find(slot => !slot.dataset.value);
      if (firstEmpty) {
        fillSlot(firstEmpty, chip.dataset.value, chip);
      }
    });
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

    // Clicking a filled blank clears it.
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

  // Restore any previously saved draft (e.g. after a pause/resume).
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

  // --- Submit challenge ---
  if (submitForm) {
    submitForm.addEventListener('submit', async (e) => {
      e.preventDefault();

      const submittedAnswers = Array.from(blankSlots).map(s => s.dataset.value || '');

      if (submittedAnswers.some(ans => ans === '')) {
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

        if (resData.is_correct) {
          ArenaFeedback.show(feedbackBox, 'Correct! Advancing to next challenge...', 'success');
          setTimeout(() => {
            window.location.href = resData.redirect_url;
          }, SUCCESS_REDIRECT_DELAY_MS);
          return;
        }

        if (resData.stopped || resData.message === 'GAME_STOPPED') {
          if (window.checkBroadcast) window.checkBroadcast();
        } else {
          ArenaFeedback.show(feedbackBox, resData.message || 'Incorrect answer. Review your choices and try again!', 'danger');
        }
        btnSubmit.disabled = false;
        btnSubmit.innerHTML = SUBMIT_LABEL_DEFAULT;
      } catch (err) {
        console.error('Failed to submit challenge:', err);
        if (window.checkBroadcast) window.checkBroadcast();
        btnSubmit.disabled = false;
        btnSubmit.innerHTML = SUBMIT_LABEL_DEFAULT;
      }
    });
  }
});
