// Runtime configuration — Workforce Twin Frontend
//
// In Docker: docker-entrypoint.sh overwrites this file with env-var values.
// In browser (fallback): auto-detects environment from hostname if globals are not set.
//
// Priority:
//   1. docker-entrypoint.sh sets window.__WORKFORCE_TWIN_API_BASE__ and __ETTER_API_BASE__
//   2. If not set, this script detects env from hostname and sets them automatically

(function () {
  'use strict';

  // ── Environment map ──────────────────────────────────────────────
  // Maps frontend hostname patterns → backend base URLs
  var ENV_MAP = {
    // QA environment
    qa: {
      patterns: ['qa-etter.draup.technology', 'etter-workforcetwin.draup.technology'],
      apiBase: 'https://qa-etter.draup.technology/api/v1/workforce-twin',
      etterBase: 'https://qa-etter.draup.technology/api',
    },
    // Production environment
    prod: {
      patterns: ['etter.draup.com', 'workforcetwin.draup.com'],
      apiBase: 'https://etter.draup.com/api/v1/workforce-twin',
      etterBase: 'https://etter.draup.com/api',
    },
    // Local development — handled by Vite proxy, no base needed
    local: {
      patterns: ['localhost', '127.0.0.1'],
      apiBase: '/api',
      etterBase: '/etter-api',
    },
  };

  // ── Logging helper ───────────────────────────────────────────────
  var PREFIX = '[WorkforceTwin Config]';

  function log(msg) {
    console.log(PREFIX + ' ' + msg);
  }
  function warn(msg) {
    console.warn(PREFIX + ' ' + msg);
  }

  // ── Detect environment from hostname ─────────────────────────────
  function detectEnv(hostname) {
    var envNames = Object.keys(ENV_MAP);
    for (var i = 0; i < envNames.length; i++) {
      var env = ENV_MAP[envNames[i]];
      for (var j = 0; j < env.patterns.length; j++) {
        if (hostname.indexOf(env.patterns[j]) !== -1) {
          return { name: envNames[i], config: env };
        }
      }
    }
    return null;
  }

  // ── Main ─────────────────────────────────────────────────────────
  var hostname = window.location.hostname;
  log('Hostname: ' + hostname);
  log('Full origin: ' + window.location.origin);

  // Check if docker-entrypoint.sh already set the values
  var apiAlreadySet = window.__WORKFORCE_TWIN_API_BASE__ &&
    window.__WORKFORCE_TWIN_API_BASE__ !== '/api';
  var etterAlreadySet = window.__ETTER_API_BASE__ &&
    window.__ETTER_API_BASE__ !== '/etter-api';

  if (apiAlreadySet || etterAlreadySet) {
    log('Config already set by docker-entrypoint:');
    log('  API_BASE  = ' + window.__WORKFORCE_TWIN_API_BASE__);
    log('  ETTER_BASE = ' + window.__ETTER_API_BASE__);
    return;
  }

  // Auto-detect from hostname
  var detected = detectEnv(hostname);

  if (detected) {
    log('Detected environment: ' + detected.name);
    log('  Matched hostname: ' + hostname);
    log('  Setting API_BASE  = ' + detected.config.apiBase);
    log('  Setting ETTER_BASE = ' + detected.config.etterBase);

    window.__WORKFORCE_TWIN_API_BASE__ = detected.config.apiBase;
    window.__ETTER_API_BASE__ = detected.config.etterBase;
  } else {
    warn('Unknown hostname "' + hostname + '" — no environment matched.');
    warn('Known environments:');
    var envNames = Object.keys(ENV_MAP);
    for (var i = 0; i < envNames.length; i++) {
      warn('  ' + envNames[i] + ': ' + ENV_MAP[envNames[i]].patterns.join(', '));
    }
    warn('Falling back to relative paths: /api and /etter-api');
    warn('Set API_BASE_URL and ETTER_API_BASE env vars in Docker to fix this.');

    window.__WORKFORCE_TWIN_API_BASE__ = window.__WORKFORCE_TWIN_API_BASE__ || '/api';
    window.__ETTER_API_BASE__ = window.__ETTER_API_BASE__ || '/etter-api';
  }

  log('Final config:');
  log('  __WORKFORCE_TWIN_API_BASE__ = ' + window.__WORKFORCE_TWIN_API_BASE__);
  log('  __ETTER_API_BASE__          = ' + window.__ETTER_API_BASE__);
})();
