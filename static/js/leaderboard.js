/**
 * Leaderboard Live Auto-Refresh Script
 */

document.addEventListener('DOMContentLoaded', () => {
  const leaderboardBody = document.getElementById('leaderboard-tbody');
  const POLL_INTERVAL_MS = 5000;

  async function updateLeaderboard() {
    if (!leaderboardBody) return;

    try {
      const res = await fetch('/api/leaderboard');
      const data = await res.json();
      
      if (data && data.rankings) {
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
      
      let rankDisplay = `#${row.rank}`;
      let rankClass = '';
      if (row.rank === 1) { rankDisplay = '🏆 1'; rankClass = 'rank-podium-1'; }
      else if (row.rank === 2) { rankDisplay = '🥈 2'; rankClass = 'rank-podium-2'; }
      else if (row.rank === 3) { rankDisplay = '🥉 3'; rankClass = 'rank-podium-3'; }

      let statusBadge = `<span class="badge-status status-waiting">Waiting</span>`;
      if (row.status === 'ACTIVE') {
        statusBadge = `<span class="badge-status status-active">Active</span>`;
      } else if (row.status === 'COMPLETED') {
        statusBadge = `<span class="badge-status status-completed">Completed</span>`;
      }

      tr.innerHTML = `
        <td class="${rankClass}">${rankDisplay}</td>
        <td><strong>${escapeHtml(row.team_name)}</strong> <small style="color: var(--text-dim);">(${row.team_code})</small></td>
        <td>${row.current_challenge > 5 ? '5/5 (Finish)' : `${row.current_challenge - 1}/5`}</td>
        <td style="font-family: var(--font-code);">${row.formatted_time}</td>
        <td>${statusBadge}</td>
      `;
      leaderboardBody.appendChild(tr);
    });
  }

  function escapeHtml(str) {
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  // Poll every 5 seconds
  setInterval(updateLeaderboard, POLL_INTERVAL_MS);
});
