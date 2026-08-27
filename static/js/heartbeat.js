/**
 * Heartbeat Keeper
 * Sends a background heartbeat to the server every 10 seconds to maintain single-device session locking.
 */

(function () {
  const HEARTBEAT_INTERVAL_MS = 10000;

  function sendHeartbeat() {
    fetch('/api/heartbeat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      }
    })
      .then(response => response.json())
      .then(data => {
        if (!data.active) {
          console.warn('Session expired or logged in on another device:', data.message);
          window.location.href = '/?session_expired=1';
        }
      })
      .catch(err => {
        console.error('Heartbeat error:', err);
      });
  }

  // Send initial heartbeat and start interval
  sendHeartbeat();
  setInterval(sendHeartbeat, HEARTBEAT_INTERVAL_MS);
})();
