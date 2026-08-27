/**
 * Drag and Drop / Tap-to-Fill Logic for Challenges 1 & 2
 */

document.addEventListener('DOMContentLoaded', () => {
  const blankSlots = document.querySelectorAll('.blank-slot');
  const optionChips = document.querySelectorAll('.option-chip');
  const btnReset = document.getElementById('btn-reset-blanks');
  const submitForm = document.getElementById('challenge-form');
  const feedbackBox = document.getElementById('feedback-box');
  const btnSubmit = document.getElementById('btn-submit');

  let draggedChip = null;

  // 1. Drag and Drop event listeners
  optionChips.forEach(chip => {
    chip.addEventListener('dragstart', (e) => {
      if (chip.classList.contains('used')) return;
      draggedChip = chip;
      chip.classList.add('dragging');
      e.dataTransfer.setData('text/plain', chip.dataset.value);
    });

    chip.addEventListener('dragend', () => {
      chip.classList.remove('dragging');
      draggedChip = null;
    });

    // Tap / Click to fill support (Desktop & Mobile)
    chip.addEventListener('click', () => {
      if (chip.classList.contains('used')) return;
      // Find first empty blank slot
      const firstEmpty = Array.from(blankSlots).find(slot => !slot.dataset.value);
      if (firstEmpty) {
        fillSlot(firstEmpty, chip.dataset.value, chip);
      }
    });
  });

  blankSlots.forEach((slot, index) => {
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
      if (val) {
        const matchingChip = Array.from(optionChips).find(c => c.dataset.value === val && !c.classList.contains('used'));
        fillSlot(slot, val, matchingChip);
      }
    });

    // Clicking a filled blank clears it
    slot.addEventListener('click', () => {
      if (slot.dataset.value) {
        clearSlot(slot);
      }
    });
  });

  function fillSlot(slot, value, chipElement) {
    // If slot already had a value, free previous chip
    if (slot.dataset.value) {
      clearSlot(slot);
    }

    slot.dataset.value = value;
    slot.textContent = value;
    slot.classList.add('filled');

    if (chipElement) {
      chipElement.classList.add('used');
    } else {
      const chip = Array.from(optionChips).find(c => c.dataset.value === value && !c.classList.contains('used'));
      if (chip) chip.classList.add('used');
    }
    persistDraft();
  }

  function persistDraft() {
    const submitForm = document.getElementById('challenge-form');
    if (!window.ArenaDraft || !submitForm) return;
    const values = Array.from(blankSlots).map(s => s.dataset.value || '');
    window.ArenaDraft.save(parseInt(submitForm.dataset.challengeId), values);
  }

  function clearSlot(slot) {
    const prevVal = slot.dataset.value;
    if (!prevVal) return;

    slot.dataset.value = '';
    slot.textContent = '___';
    slot.classList.remove('filled');

    // Restore corresponding chip in bank
    const usedChip = Array.from(optionChips).find(c => c.dataset.value === prevVal && c.classList.contains('used'));
    if (usedChip) {
      usedChip.classList.remove('used');
    }
    persistDraft();
  }

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
      hideFeedback();
    });
  }

  // 2. Submit Challenge
  if (submitForm) {
    submitForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      
      // Collect values from all blank slots
      const submittedAnswers = Array.from(blankSlots).map(s => s.dataset.value || '');
      
      if (submittedAnswers.some(ans => ans === '')) {
        showFeedback('Please fill in all blank spaces before submitting.', 'warning');
        return;
      }

      if (window.contestantRoundStatus && window.contestantRoundStatus !== 'ACTIVE') {
        if (window.checkBroadcast) window.checkBroadcast();
        return;
      }

      const challengeId = parseInt(submitForm.dataset.challengeId);
      
      btnSubmit.disabled = true;
      btnSubmit.innerHTML = 'Evaluating...';

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
          showFeedback('Correct! Advancing to next challenge...', 'success');
          setTimeout(() => {
            window.location.href = resData.redirect_url;
          }, 1200);
        } else {
          if (resData.stopped || resData.message === 'GAME_STOPPED') {
            if (window.checkBroadcast) window.checkBroadcast();
          } else {
            showFeedback(resData.message || 'Incorrect answer. Review your choices and try again!', 'danger');
          }
          btnSubmit.disabled = false;
          btnSubmit.innerHTML = 'Submit Code Answer';
        }
      } catch (err) {
        if (window.checkBroadcast) window.checkBroadcast();
        btnSubmit.disabled = false;
        btnSubmit.innerHTML = 'Submit Code Answer';
      }
    });
  }

  function showFeedback(msg, type) {
    if (!feedbackBox) return;
    feedbackBox.className = `alert-banner alert-${type}`;
    feedbackBox.innerHTML = msg;
    feedbackBox.style.display = 'flex';
  }

  function hideFeedback() {
    if (!feedbackBox) return;
    feedbackBox.style.display = 'none';
  }
});
