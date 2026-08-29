/**
 * line_selector.js
 * Line Selector Logic for Find-the-Error Challenges with Staggered Animations.
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
      selectedLineNumber = parseInt(line.dataset.lineNumber, 10);
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
        if (window.ArenaFeedback) {
          window.ArenaFeedback.shake(submitForm);
          window.ArenaFeedback.show(feedbackBox, 'Please tap or click a line number containing the error.', 'warning');
        }
        return;
      }

      if (window.contestantRoundStatus && window.contestantRoundStatus !== 'ACTIVE') {
        if (window.checkBroadcast) window.checkBroadcast();
        return;
      }

      const challengeId = parseInt(submitForm.dataset.challengeId, 10);
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

        if (resData.success) {
          if (window.ArenaFeedback) {
            window.ArenaFeedback.popScore(50);
            window.ArenaFeedback.show(feedbackBox, '<span class="correct-toast-inline">✓ CORRECT! +50</span>', 'success');
          }

          const mainCard = document.querySelector('.glass-card');
          if (mainCard) mainCard.classList.add('challenge-slide-out');

          setTimeout(() => {
            window.location.href = resData.redirect_url;
          }, 1200);
          return;
        }

        if (resData.stopped || resData.message === 'GAME_STOPPED') {
          if (window.checkBroadcast) window.checkBroadcast();
        } else {
          if (window.ArenaFeedback) {
            window.ArenaFeedback.shake(submitForm);
            window.ArenaFeedback.show(feedbackBox, resData.message || '❌ Incorrect line selected. Try again!', 'danger');
          }
        }
        btnSubmit.disabled = false;
        btnSubmit.innerHTML = 'Submit Selected Error Line ➔';
      } catch (err) {
        if (window.ArenaFeedback) window.ArenaFeedback.shake(submitForm);
        if (window.checkBroadcast) window.checkBroadcast();
        btnSubmit.disabled = false;
        btnSubmit.innerHTML = 'Submit Selected Error Line ➔';
      }
    });
  }
});
