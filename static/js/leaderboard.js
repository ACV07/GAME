/**
 * leaderboard.js
 * Polls the live leaderboard endpoint and re-renders the standings table.
 */

document.addEventListener('DOMContentLoaded', () => {
  const leaderboardBody = document.getElementById('leaderboard-tbody');
  const POLL_INTERVAL_MS = 5000;

  const RANK_DISPLAY = {
    1: { label: '🏆 1', className: 'rank-podium-1' },
    2: { label: '🥈 2', className: 'rank-podium-2' },
    3: { label: '🥉 3', className: 'rank-podium-3' }
  };

  const STATUS_BADGES = {
    ACTIVE: '<span class="badge-status status-active">Active</span>',
    COMPLETED: '<span class="badge-status status-completed">Completed</span>'
  };
  const DEFAULT_STATUS_BADGE = '<span class="badge-status status-waiting">Waiting</span>';

  async function updateLeaderboard() {
    if (!leaderboardBody) return;

    try {
      const res = await fetch('/api/leaderboard');
      const data = await res.json();

      if (data && Array.isArray(data.rankings)) {
        renderRankings(data.rankings);
      }
    } catch (err) {
      console.error('Failed to poll leaderboard updates:', err);
    }
  }

  function renderRankings(rankings) {
    leaderboardBody.innerHTML = '';

    rankings.forEach(row => {
      const tr = document.createElement('tr');
      const { label: rankDisplay, className: rankClass } =
        RANK_DISPLAY[row.rank] || { label: `#${row.rank}`, className: '' };
      const statusBadge = STATUS_BADGES[row.status] || DEFAULT_STATUS_BADGE;
      const progress = row.current_challenge > 5
        ? '5/5 (Finish)'
        : `${row.current_challenge - 1}/5`;

      tr.innerHTML = `
        <td class="${rankClass}">${rankDisplay}</td>
        <td><strong>${escapeHtml(row.team_name)}</strong> <small style="color: var(--text-dim);">(${escapeHtml(row.team_code)})</small></td>
        <td>${progress}</td>
        <td style="font-family: var(--font-code);">${escapeHtml(row.formatted_time)}</td>
        <td>${statusBadge}</td>
      `;
      leaderboardBody.appendChild(tr);
    });
  }

  /**
   * Escape a value for safe insertion into innerHTML.
   * Handles all HTML-significant characters, not just angle brackets,
   * so values used inside attributes stay safe too.
   * @param {*} value
   * @returns {string}
   */
  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  updateLeaderboard();
  setInterval(updateLeaderboard, POLL_INTERVAL_MS);
});
