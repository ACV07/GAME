/**
 * Persist in-progress challenge answers so pause/stop can restore the same board.
 */
window.ArenaDraft = {
  save(challengeId, draft) {
    fetch('/api/save-draft', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ challenge_id: challengeId, draft })
    }).catch(() => {});
  }
};
