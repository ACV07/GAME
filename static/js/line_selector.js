/**
 * line_selector.js
 * Multi-line Selector Logic for Find-the-Error Challenges with Staggered Animations.
 */

document.addEventListener('DOMContentLoaded', () => {
  const codeLines = document.querySelectorAll('.code-line-item');
  const submitForm = document.getElementById('line-challenge-form');
  const feedbackBox = document.getElementById('feedback-box');
  const btnSubmit = document.getElementById('btn-submit-line');

  let selectedLineNumbers = [];

  function persistDraft() {
    const form = document.getElementById('line-challenge-form');
    if (!window.ArenaDraft || !form) return;
    window.ArenaDraft.save(parseInt(form.dataset.challengeId, 10), selectedLineNumbers);
  }

  codeLines.forEach(line => {
    line.addEventListener('click', () => {
      const lineNum = parseInt(line.dataset.lineNumber, 10);
      if (line.classList.contains('selected-error-line')) {
        line.classList.remove('selected-error-line');
        selectedLineNumbers = selectedLineNumbers.filter(num => num !== lineNum);
      } else {
        line.classList.add('selected-error-line');
        if (!selectedLineNumbers.includes(lineNum)) {
          selectedLineNumbers.push(lineNum);
        }
      }
      persistDraft();
    });
  });

  if (window.savedDraft) {
    let saved = window.savedDraft;
    if (typeof saved === 'number') {
      saved = [saved];
    } else if (typeof saved === 'string') {
      try {
        saved = JSON.parse(saved);
      } catch(e) {
        saved = [parseInt(saved, 10)];
      }
    }
    if (Array.isArray(saved)) {
      selectedLineNumbers = saved.map(x => parseInt(x, 10)).filter(x => !isNaN(x));
      codeLines.forEach(line => {
        const lineNum = parseInt(line.dataset.lineNumber, 10);
        if (selectedLineNumbers.includes(lineNum)) {
          line.classList.add('selected-error-line');
        }
      });
    }
  }

  if (submitForm) {
    submitForm.addEventListener('submit', async (e) => {
      e.preventDefault();

      if (selectedLineNumbers.length === 0) {
        if (window.ArenaFeedback) {
          window.ArenaFeedback.shake(submitForm);
          window.ArenaFeedback.show(feedbackBox, 'Please tap or click line number(s) containing errors.', 'warning');
        }
        return;
      }

      if (window.contestantRoundStatus && window.contestantRoundStatus !== 'ACTIVE') {
        if (window.checkBroadcast) window.checkBroadcast();
        return;
      }

      const challengeId = parseInt(submitForm.dataset.challengeId, 10);
      btnSubmit.disabled = true;
      btnSubmit.innerHTML = 'Evaluating Line(s)...';

      try {
        const response = await fetch('/api/submit-challenge', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            challenge_id: challengeId,
            answer: selectedLineNumbers.length === 1 ? selectedLineNumbers[0] : selectedLineNumbers
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
            }, 1200);
          }
          return;
        }

        if (resData.stopped || resData.message === 'GAME_STOPPED') {
          if (window.checkBroadcast) window.checkBroadcast();
        } else {
          if (window.ArenaFeedback) {
            window.ArenaFeedback.shake(submitForm);
            window.ArenaFeedback.show(feedbackBox, resData.message || '❌ Incorrect line(s) selected. Try again!', 'danger');
          }
        }
        btnSubmit.disabled = false;
        btnSubmit.innerHTML = 'Submit Selected Error Line(s) ➔';
      } catch (err) {
        if (window.ArenaFeedback) window.ArenaFeedback.shake(submitForm);
        if (window.checkBroadcast) window.checkBroadcast();
        btnSubmit.disabled = false;
        btnSubmit.innerHTML = 'Submit Selected Error Line(s) ➔';
      }
    });
  }
});
