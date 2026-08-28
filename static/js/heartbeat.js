/**
 * heartbeat.js
 * Sends a background heartbeat to the server at a fixed interval to
 * enforce single-device session locking. If the server reports the
 * session is no longer active (expired, or superseded by a login on
 * another device), the contestant is redirected out.
 */

(function () {
  const HEARTBEAT_INTERVAL_MS = 10000;
  const SESSION_EXPIRED_REDIRECT = '/?session_expired=1';

  async function sendHeartbeat() {
    try {
      const response = await fetch('/api/heartbeat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });

      const data = await response.json();

      if (!data.active) {
        console.warn('Session expired or logged in on another device:', data.message);
        window.location.href = SESSION_EXPIRED_REDIRECT;
      }
    } catch (err) {
      console.error('Heartbeat error:', err);
    }
  }

  sendHeartbeat();
  setInterval(sendHeartbeat, HEARTBEAT_INTERVAL_MS);
})();
