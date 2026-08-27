/**
 * Line Selector Logic for Find-the-Error Challenges (Challenges 3 & 4)
 */

document.addEventListener('DOMContentLoaded', () => {
  const codeLines = document.querySelectorAll('.code-line-item');
  const submitForm = document.getElementById('line-challenge-form');
  const feedbackBox = document.getElementById('feedback-box');
  const btnSubmit = document.getElementById('btn-submit-line');

  let selectedLineNumber = null;

  function persistDraft() {
    const form = document.getElementById('line-challenge-form');
    if (!window.ArenaDraft || !form || !selectedLineNumber) return;
    window.ArenaDraft.save(parseInt(form.dataset.challengeId), selectedLineNumber);
  }

  codeLines.forEach(line => {
    line.addEventListener('click', () => {
      codeLines.forEach(l => l.classList.remove('selected-error-line'));
      line.classList.add('selected-error-line');
      selectedLineNumber = parseInt(line.dataset.lineNumber);
      persistDraft();
    });
  });

  if (window.savedDraft) {
    selectedLineNumber = parseInt(window.savedDraft, 10);
    codeLines.forEach(line => {
      if (parseInt(line.dataset.lineNumber, 10) === selectedLineNumber) {
        line.classList.add('selected-error-line');
      }
    });
  }

  if (submitForm) {
    submitForm.addEventListener('submit', async (e) => {
      e.preventDefault();

      if (!selectedLineNumber) {
        showFeedback('Please select a line number containing the error before submitting.', 'warning');
        return;
      }

      if (window.contestantRoundStatus && window.contestantRoundStatus !== 'ACTIVE') {
        if (window.checkBroadcast) window.checkBroadcast();
        return;
      }

      const challengeId = parseInt(submitForm.dataset.challengeId);
      btnSubmit.disabled = true;
      btnSubmit.innerHTML = 'Evaluating Line...';

      try {
        const response = await fetch('/api/submit-challenge', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            challenge_id: challengeId,
            answer: selectedLineNumber
          })
        });

        const resData = await response.json();

        if (resData.is_correct) {
          showFeedback(`Correct! Found error on line ${selectedLineNumber}. Advancing to next challenge...`, 'success');
          setTimeout(() => {
            window.location.href = resData.redirect_url;
          }, 1200);
        } else {
          if (resData.stopped || resData.message === 'GAME_STOPPED') {
            if (window.checkBroadcast) window.checkBroadcast();
          } else {
            showFeedback(resData.message || 'Incorrect line selected. Inspect the syntax and logic carefully.', 'danger');
          }
          btnSubmit.disabled = false;
          btnSubmit.innerHTML = 'Submit Error Line';
        }
      } catch (err) {
        if (window.checkBroadcast) window.checkBroadcast();
        btnSubmit.disabled = false;
        btnSubmit.innerHTML = 'Submit Error Line';
      }
    });
  }

  function showFeedback(msg, type) {
    if (!feedbackBox) return;
    feedbackBox.className = `alert-banner alert-${type}`;
    feedbackBox.innerHTML = msg;
    feedbackBox.style.display = 'flex';
  }
});
