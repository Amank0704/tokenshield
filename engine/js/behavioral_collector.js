/**
 * TokenShield Behavioral Biometrics Collector
 * Lightweight, non-blocking, privacy-preserving.
 *
 * Captures:
 *   - Typing rhythm
 *   - Mouse movement/velocity
 *   - Click rate and click latency
 *   - Scroll activity
 *   - Idle time
 *   - Stable browser/device fingerprint
 *
 * NO keystroke text or input values are ever recorded.
 */
(function (window, document) {
  'use strict';

  if (window.__TokenShieldCollector) return;

  var MAX_SAMPLES = 50;

  var buffer = {
    keyHolds: [],
    keyFlights: [],
    mouseSpeeds: [],
    clickLatencies: [],
    scrollIntervals: [],

    lastKeyDown: 0,
    lastKeyUp: 0,

    lastMouseMove: 0,
    lastMousePos: null,

    lastClickTime: 0,
    lastScrollTime: 0,

    totalClicks: 0,
    totalScrolls: 0,

    totalIdleMs: 0,
    lastActivityTime: Date.now(),
    startTime: Date.now()
  };

  /*
   * ------------------------------------------------------------
   * Utility helpers
   * ------------------------------------------------------------
   */

  function pushSample(array, value) {
    if (!isFinite(value)) return;

    array.push(value);

    if (array.length > MAX_SAMPLES) {
      array.shift();
    }
  }

  function registerActivity() {
    var now = Date.now();
    var gap = now - buffer.lastActivityTime;

    /*
     * Consider a gap greater than 2 seconds as idle time.
     */
    if (gap > 2000) {
      buffer.totalIdleMs += gap;
    }

    buffer.lastActivityTime = now;
  }

  /*
   * ------------------------------------------------------------
   * Keystroke dynamics
   * ------------------------------------------------------------
   *
   * We only record timing information.
   * No key names, characters, passwords, or input values.
   */

  document.addEventListener('keydown', function (e) {
    registerActivity();

    if (!e.isTrusted) return;

    var now = performance.now();

    /*
     * Flight time = time between previous key release
     * and current key press.
     */
    if (buffer.lastKeyUp > 0) {
      var flight = now - buffer.lastKeyUp;

      if (flight >= 0 && flight < 2000) {
        pushSample(buffer.keyFlights, flight);
      }
    }

    buffer.lastKeyDown = now;
  }, true);

  document.addEventListener('keyup', function (e) {
    registerActivity();

    if (!e.isTrusted) return;

    var now = performance.now();

    /*
     * Hold time = duration a key was held down.
     */
    if (buffer.lastKeyDown > 0) {
      var hold = now - buffer.lastKeyDown;

      if (hold >= 0 && hold < 2000) {
        pushSample(buffer.keyHolds, hold);
      }
    }

    buffer.lastKeyUp = now;
  }, true);

  /*
   * ------------------------------------------------------------
   * Mouse dynamics
   * ------------------------------------------------------------
   */

  document.addEventListener('mousemove', function (e) {
    registerActivity();

    if (!e.isTrusted) return;

    var now = performance.now();

    if (buffer.lastMousePos && buffer.lastMouseMove > 0) {
      var dt = now - buffer.lastMouseMove;

      if (dt > 10 && dt < 1000) {
        var dx = e.clientX - buffer.lastMousePos.x;
        var dy = e.clientY - buffer.lastMousePos.y;

        var distance = Math.sqrt(
          (dx * dx) + (dy * dy)
        );

        /*
         * Pixels per second.
         */
        var speed = (distance / dt) * 1000;

        pushSample(buffer.mouseSpeeds, speed);
      }
    }

    buffer.lastMousePos = {
      x: e.clientX,
      y: e.clientY
    };

    buffer.lastMouseMove = now;
  }, {
    passive: true
  });

  /*
   * ------------------------------------------------------------
   * Click dynamics
   * ------------------------------------------------------------
   */

  document.addEventListener('click', function (e) {
    registerActivity();

    if (!e.isTrusted) return;

    var now = performance.now();

    buffer.totalClicks += 1;

    if (buffer.lastClickTime > 0) {
      var latency = now - buffer.lastClickTime;

      if (latency >= 0 && latency < 10000) {
        pushSample(buffer.clickLatencies, latency);
      }
    }

    buffer.lastClickTime = now;
  }, true);

  /*
   * ------------------------------------------------------------
   * Scroll dynamics
   * ------------------------------------------------------------
   */

  window.addEventListener('scroll', function () {
    registerActivity();

    var now = performance.now();

    buffer.totalScrolls += 1;

    if (buffer.lastScrollTime > 0) {
      var interval = now - buffer.lastScrollTime;

      if (interval >= 0 && interval < 10000) {
        pushSample(buffer.scrollIntervals, interval);
      }
    }

    buffer.lastScrollTime = now;
  }, {
    passive: true
  });

  /*
   * ------------------------------------------------------------
   * Statistics
   * ------------------------------------------------------------
   */

  function calcStats(arr) {
    if (!arr || arr.length === 0) {
      return {
        mean: 0,
        std: 0,
        cv: 0
      };
    }

    var sum = 0;

    for (var i = 0; i < arr.length; i++) {
      sum += arr[i];
    }

    var mean = sum / arr.length;

    var sqDiff = 0;

    for (var j = 0; j < arr.length; j++) {
      sqDiff += Math.pow(arr[j] - mean, 2);
    }

    var std = Math.sqrt(
      sqDiff / arr.length
    );

    var cv = mean > 0
      ? std / mean
      : 0;

    return {
      mean: mean,
      std: std,
      cv: cv
    };
  }

  /*
   * ------------------------------------------------------------
   * Stable browser/device fingerprint
   * ------------------------------------------------------------
   *
   * This is a browser identity signal, not a hardware serial
   * number. It is used only to detect a change of browser/device
   * context during the controlled TokenShield demo.
   */

  function simpleHash(value) {
    var hash = 2166136261;

    for (var i = 0; i < value.length; i++) {
      hash ^= value.charCodeAt(i);
      hash +=
        (hash << 1) +
        (hash << 4) +
        (hash << 7) +
        (hash << 8) +
        (hash << 24);
    }

    return ('00000000' + (hash >>> 0).toString(16)).slice(-8);
  }

  function getCanvasFingerprint() {
    try {
      var canvas = document.createElement('canvas');
      canvas.width = 240;
      canvas.height = 60;

      var ctx = canvas.getContext('2d');

      if (!ctx) return '';

      ctx.textBaseline = 'top';
      ctx.font = '16px Arial';

      ctx.fillStyle = '#f60';
      ctx.fillRect(10, 10, 100, 20);

      ctx.fillStyle = '#069';
      ctx.fillText(
        'TokenShield',
        15,
        15
      );

      return canvas.toDataURL();
    } catch (e) {
      return '';
    }
  }

  function getWebGLFingerprint() {
    try {
      var canvas = document.createElement('canvas');

      var gl =
        canvas.getContext('webgl') ||
        canvas.getContext('experimental-webgl');

      if (!gl) return '';

      var debugInfo =
        gl.getExtension(
          'WEBGL_debug_renderer_info'
        );

      if (!debugInfo) return '';

      var vendor = gl.getParameter(
        debugInfo.UNMASKED_VENDOR_WEBGL
      );

      var renderer = gl.getParameter(
        debugInfo.UNMASKED_RENDERER_WEBGL
      );

      return String(vendor) + '|' + String(renderer);
    } catch (e) {
      return '';
    }
  }

  function createDeviceFingerprint() {
    var components = [];

    components.push(
      'ua=' + String(navigator.userAgent || '')
    );

    components.push(
      'platform=' + String(navigator.platform || '')
    );

    components.push(
      'language=' + String(navigator.language || '')
    );

    components.push(
      'languages=' +
      String(
        (navigator.languages || []).join(',')
      )
    );

    components.push(
      'timezone=' +
      String(
        Intl.DateTimeFormat().resolvedOptions().timeZone || ''
      )
    );

    components.push(
      'screen=' +
      String(window.screen.width || 0) +
      'x' +
      String(window.screen.height || 0)
    );

    components.push(
      'pixel_ratio=' +
      String(window.devicePixelRatio || 1)
    );

    components.push(
      'color_depth=' +
      String(window.screen.colorDepth || 0)
    );

    components.push(
      'touch=' +
      String(navigator.maxTouchPoints || 0)
    );

    components.push(
      'canvas=' +
      simpleHash(getCanvasFingerprint())
    );

    components.push(
      'webgl=' +
      simpleHash(getWebGLFingerprint())
    );

    return 'tsfp-' + simpleHash(
      components.join('||')
    );
  }

  var deviceFingerprint =
    createDeviceFingerprint();

  /*
   * ------------------------------------------------------------
   * Behavioral metrics
   * ------------------------------------------------------------
   */

  function getMetrics() {
    var now = Date.now();

    var sessionDuration =
      Math.max(
        now - buffer.startTime,
        1000
      );

    var holdStats =
      calcStats(buffer.keyHolds);

    var flightStats =
      calcStats(buffer.keyFlights);

    var mouseStats =
      calcStats(buffer.mouseSpeeds);

    var clickStats =
      calcStats(buffer.clickLatencies);

    var scrollStats =
      calcStats(buffer.scrollIntervals);

    /*
     * Approximate typing speed.
     *
     * This is intentionally based only on timing.
     * No actual text is recorded.
     */
    var averageKeyInterval =
      holdStats.mean +
      (flightStats.mean || 100);

    var cpm =
      averageKeyInterval > 0
        ? 60000 / averageKeyInterval
        : 0;

    var wpm =
      Math.min(
        Math.max(cpm / 5, 0),
        200
      );

    /*
     * Idle ratio.
     */
    var idleRatio =
      Math.min(
        Math.max(
          buffer.totalIdleMs /
          sessionDuration,
          0
        ),
        1
      );

    /*
     * Click rate per minute.
     */
    var minutes =
      Math.max(
        sessionDuration / 60000,
        1 / 60
      );

    var clickRate =
      buffer.totalClicks / minutes;

    return {
      /*
       * Typing signals
       */
      typing_wpm:
        Math.round(wpm * 100) / 100,

      typing_rhythm_cv:
        Math.round(
          holdStats.cv * 1000
        ) / 1000,

      key_hold_mean:
        Math.round(
          holdStats.mean * 100
        ) / 100,

      key_flight_mean:
        Math.round(
          flightStats.mean * 100
        ) / 100,

      /*
       * Mouse signals
       */
      mouse_velocity_mean:
        Math.round(
          mouseStats.mean * 10
        ) / 10,

      mouse_velocity_cv:
        Math.round(
          mouseStats.cv * 1000
        ) / 1000,

      /*
       * Click signals
       */
      click_rate:
        Math.round(
          clickRate * 100
        ) / 100,

      click_latency_mean:
        Math.round(
          clickStats.mean * 10
        ) / 10,

      /*
       * Scroll signals
       */
      scroll_interval_mean:
        Math.round(
          scrollStats.mean * 10
        ) / 10,

      scroll_count:
        buffer.totalScrolls,

      /*
       * Idle signal
       */
      idle_time_ratio:
        Math.round(
          idleRatio * 1000
        ) / 1000,

      /*
       * Sample count
       */
      samples_count:
        buffer.keyHolds.length +
        buffer.keyFlights.length +
        buffer.mouseSpeeds.length +
        buffer.clickLatencies.length,

      /*
       * Session timing
       */
      session_duration_ms:
        sessionDuration
    };
  }

  /*
   * ------------------------------------------------------------
   * Expose collector
   * ------------------------------------------------------------
   */

  window.__TokenShieldFingerprint =
    deviceFingerprint;

  window.__TokenShieldCollector = {
    getMetrics: getMetrics,

    getFingerprint: function () {
      return deviceFingerprint;
    }
  };

  /*
   * ------------------------------------------------------------
   * Automatically attach telemetry to fetch()
   * ------------------------------------------------------------
   */

  var originalFetch = null;

  if (window.fetch) {
    originalFetch = window.fetch;

    window.fetch = function (
      resource,
      init
    ) {
      init = init || {};

      try {
        init.headers =
          new Headers(
            init.headers || {}
          );

        /*
         * Attach device fingerprint.
         */
        init.headers.set(
          'X-Device-Fingerprint',
          deviceFingerprint
        );

        /*
         * Attach behavioral telemetry.
         */
        var metrics =
          getMetrics();

        if (
          metrics.samples_count > 0
        ) {
          init.headers.set(
            'X-TS-Biometrics',
            JSON.stringify(metrics)
          );
        }
      } catch (err) {
        /*
         * Never allow telemetry
         * collection to break the application.
         */
      }

      return originalFetch.call(
        this,
        resource,
        init
      );
    };
  }

  /*
   * ------------------------------------------------------------
   * Automatically attach telemetry to XMLHttpRequest
   * ------------------------------------------------------------
   */

  if (window.XMLHttpRequest) {
    var OriginalXHR =
      window.XMLHttpRequest;

    function TokenShieldXHR() {
      var xhr =
        new OriginalXHR();

      var originalOpen =
        xhr.open;

      var originalSend =
        xhr.send;

      xhr.open =
        function () {
          return originalOpen.apply(
            xhr,
            arguments
          );
        };

      xhr.send =
        function (body) {
          try {
            xhr.setRequestHeader(
              'X-Device-Fingerprint',
              deviceFingerprint
            );

            var metrics =
              getMetrics();

            if (
              metrics.samples_count > 0
            ) {
              xhr.setRequestHeader(
                'X-TS-Biometrics',
                JSON.stringify(metrics)
              );
            }
          } catch (err) {}

          return originalSend.call(
            xhr,
            body
          );
        };

      return xhr;
    }

    /*
     * Preserve prototype/static behavior
     * as much as possible while allowing
     * telemetry headers to be added.
     */
    TokenShieldXHR.prototype =
      OriginalXHR.prototype;

    try {
      window.XMLHttpRequest =
        TokenShieldXHR;
    } catch (e) {}
  }

  /*
   * ------------------------------------------------------------
   * Periodic telemetry flush
   * ------------------------------------------------------------
   *
   * Sends a lightweight behavioral baseline
   * update every 15 seconds.
   */

  setInterval(function () {
    try {
      var metrics =
        getMetrics();

      if (
        metrics.samples_count < 3
      ) {
        return;
      }

      var token =
        localStorage.getItem('token') ||
        sessionStorage.getItem('token');

      var userId =
        localStorage.getItem('user_id') ||
        sessionStorage.getItem('user_id');

      var headers = {
        'Content-Type':
          'application/json',

        'X-Device-Fingerprint':
          deviceFingerprint
      };

      if (token) {
        headers.Authorization =
          'Bearer ' + token;
      }

      /*
       * Use the original fetch so that
       * this telemetry request does not
       * recursively trigger the collector.
       */
      if (originalFetch) {
        originalFetch(
          '/api/biometrics/update',
          {
            method: 'POST',

            headers: headers,

            body: JSON.stringify({
              user_id: userId,
              device_fingerprint:
                deviceFingerprint,
              metrics: metrics
            })
          }
        ).catch(
          function () {}
        );
      }
    } catch (e) {}
  }, 15000);

})(window, document);