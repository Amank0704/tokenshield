/**
 * TokenShield Behavioral Biometrics Collector
 * Lightweight (~4KB), non-blocking, privacy-preserving.
 * Captures typing rhythm, mouse trajectories, scroll patterns, and idle time.
 * NO keystroke text or input values are ever recorded.
 */
(function (window, document) {
  'use strict';

  if (window.__TokenShieldCollector) return;

  var buffer = {
    keyHolds: [],
    keyFlights: [],
    mouseSpeeds: [],
    clickLatencies: [],
    scrollDeltas: [],
    lastKeyDown: 0,
    lastKeyUp: 0,
    lastMouseMove: 0,
    lastMousePos: null,
    totalIdleMs: 0,
    lastActivityTime: Date.now(),
    startTime: Date.now()
  };

  var MAX_SAMPLES = 50;

  function registerActivity() {
    var now = Date.now();
    var gap = now - buffer.lastActivityTime;
    if (gap > 2000) {
      buffer.totalIdleMs += gap;
    }
    buffer.lastActivityTime = now;
  }

  // Keystroke dynamics
  document.addEventListener('keydown', function (e) {
    registerActivity();
    if (!e.isTrusted) return;
    var now = performance.now();
    buffer.lastKeyDown = now;
    if (buffer.lastKeyUp > 0) {
      var flight = now - buffer.lastKeyUp;
      if (flight >= 0 && flight < 2000) {
        buffer.keyFlights.push(flight);
        if (buffer.keyFlights.length > MAX_SAMPLES) buffer.keyFlights.shift();
      }
    }
  }, true);

  document.addEventListener('keyup', function (e) {
    registerActivity();
    if (!e.isTrusted) return;
    var now = performance.now();
    buffer.lastKeyUp = now;
    if (buffer.lastKeyDown > 0) {
      var hold = now - buffer.lastKeyDown;
      if (hold >= 0 && hold < 2000) {
        buffer.keyHolds.push(hold);
        if (buffer.keyHolds.length > MAX_SAMPLES) buffer.keyHolds.shift();
      }
    }
  }, true);

  // Mouse dynamics
  document.addEventListener('mousemove', function (e) {
    registerActivity();
    if (!e.isTrusted) return;
    var now = performance.now();
    if (buffer.lastMousePos && buffer.lastMouseMove > 0) {
      var dt = now - buffer.lastMouseMove;
      if (dt > 10 && dt < 1000) {
        var dx = e.clientX - buffer.lastMousePos.x;
        var dy = e.clientY - buffer.lastMousePos.y;
        var dist = Math.sqrt(dx * dx + dy * dy);
        var speed = (dist / dt) * 1000; // px/sec
        buffer.mouseSpeeds.push(speed);
        if (buffer.mouseSpeeds.length > MAX_SAMPLES) buffer.mouseSpeeds.shift();
      }
    }
    buffer.lastMousePos = { x: e.clientX, y: e.clientY };
    buffer.lastMouseMove = now;
  }, { passive: true });

  // Scroll dynamics
  window.addEventListener('scroll', function () {
    registerActivity();
    var now = performance.now();
    buffer.scrollDeltas.push(now);
    if (buffer.scrollDeltas.length > MAX_SAMPLES) buffer.scrollDeltas.shift();
  }, { passive: true });

  function calcStats(arr) {
    if (!arr || arr.length === 0) return { mean: 0, std: 0, cv: 0 };
    var sum = 0;
    for (var i = 0; i < arr.length; i++) sum += arr[i];
    var mean = sum / arr.length;
    var sqDiff = 0;
    for (var j = 0; j < arr.length; j++) sqDiff += Math.pow(arr[j] - mean, 2);
    var std = Math.sqrt(sqDiff / arr.length);
    var cv = mean > 0 ? std / mean : 0;
    return { mean: mean, std: std, cv: cv };
  }

  function getMetrics() {
    var now = Date.now();
    var sessionDuration = Math.max(now - buffer.startTime, 1000);
    var holdStats = calcStats(buffer.keyHolds);
    var flightStats = calcStats(buffer.keyFlights);
    var mouseStats = calcStats(buffer.mouseSpeeds);

    // Approximate typing WPM
    var cpm = holdStats.mean > 0 ? (60000 / (holdStats.mean + (flightStats.mean || 100))) : 0;
    var wpm = Math.min(Math.max(cpm / 5, 0), 200);

    var idleRatio = Math.min(Math.max(buffer.totalIdleMs / sessionDuration, 0), 1);

    return {
      typing_wpm: Math.round(wpm * 100) / 100,
      typing_rhythm_cv: Math.round(holdStats.cv * 1000) / 1000,
      mouse_velocity_mean: Math.round(mouseStats.mean * 10) / 10,
      mouse_velocity_cv: Math.round(mouseStats.cv * 1000) / 1000,
      click_rate: buffer.keyHolds.length,
      idle_time_ratio: Math.round(idleRatio * 1000) / 1000,
      samples_count: buffer.keyHolds.length + buffer.mouseSpeeds.length
    };
  }

  // Expose to window and auto-attach to fetch/XHR
  window.__TokenShieldCollector = {
    getMetrics: getMetrics
  };

  // Intercept fetch to automatically add header
  if (window.fetch) {
    var originalFetch = window.fetch;
    window.fetch = function (resource, init) {
      init = init || {};
      init.headers = new Headers(init.headers || {});
      try {
        var metrics = getMetrics();
        if (metrics.samples_count > 0) {
          init.headers.set('X-TS-Biometrics', JSON.stringify(metrics));
        }
      } catch (err) {}
      return originalFetch.call(this, resource, init);
    };
  }

  // Periodic background telemetry flush (every 15s) for baseline building
  setInterval(function () {
    try {
      var metrics = getMetrics();
      if (metrics.samples_count >= 3) {
        var token = localStorage.getItem('token') || sessionStorage.getItem('token');
        var userId = localStorage.getItem('user_id') || sessionStorage.getItem('user_id');
        var headers = { 'Content-Type': 'application/json' };
        if (token) headers['Authorization'] = 'Bearer ' + token;
        
        // Push telemetry to banking server or engine
        originalFetch ? originalFetch('/api/biometrics/update', {
          method: 'POST',
          headers: headers,
          body: JSON.stringify({ user_id: userId, metrics: metrics })
        }).catch(function () {}) : null;
      }
    } catch (e) {}
  }, 15000);
})(window, document);

