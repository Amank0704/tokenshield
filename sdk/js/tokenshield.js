/**
 * TokenShield Node.js / Express Middleware & Client SDK
 * ======================================================
 * Drop-in zero-trust real-time threat defense for Express, Fastify, Next.js, or Koa.
 *
 * Usage:
 *   const { tokenshieldMiddleware, TokenShieldClient } = require('./tokenshield');
 *
 *   app.use(tokenshieldMiddleware({
 *     engineUrl: 'http://localhost:7777',
 *     failOpen: true,
 *     onBlock: (req, res, decision) => {
 *       res.status(403).json({ error: 'Access Denied', reasons: decision.reasons });
 *     }
 *   }));
 */

const http = require('http');
const https = require('https');
const { URL } = require('url');

class TokenShieldClient {
  constructor(options = {}) {
    this.engineUrl = (options.engineUrl || 'http://localhost:7777').replace(/\/+$/, '');
    this.apiKey = options.apiKey || null;
    this.timeoutMs = options.timeoutMs || 250;
    this.failOpen = options.failOpen !== false;
  }

  /**
   * Evaluates request context with TokenShield AI Engine.
   */
  async inspectRequest(context) {
    const payload = JSON.stringify({
      session_id: context.sessionId || 'anonymous',
      user_id: context.userId || null,
      ip: context.ip || '127.0.0.1',
      user_agent: context.userAgent || '',
      path: context.path || '/',
      method: (context.method || 'GET').toUpperCase(),
      payload: context.payload || null,
      biometrics: context.biometrics || null,
      status_code: context.statusCode || 200
    });

    const parsedUrl = new URL(`${this.engineUrl}/api/v1/analyze`);
    const transport = parsedUrl.protocol === 'https:' ? https : http;

    return new Promise((resolve) => {
      const startTime = Date.now();
      const headers = {
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(payload)
      };
      if (this.apiKey) headers['Authorization'] = `Bearer ${this.apiKey}`;

      const req = transport.request(parsedUrl, {
        method: 'POST',
        headers,
        timeout: this.timeoutMs
      }, (res) => {
        let body = '';
        res.on('data', chunk => body += chunk);
        res.on('end', () => {
          try {
            const data = JSON.parse(body);
            resolve({
              threatScore: data.threat_score,
              threatLevel: data.threat_level,
              action: data.action,
              shouldBlock: data.action === 'block',
              reasons: data.reasons || [],
              signals: data.signals || {},
              explanation: data.explanation || {},
              latencyMs: Date.now() - startTime
            });
          } catch (e) {
            resolve(this._getFallback(Date.now() - startTime, 'invalid_json'));
          }
        });
      });

      req.on('error', () => {
        resolve(this._getFallback(Date.now() - startTime, 'connection_error'));
      });

      req.on('timeout', () => {
        req.destroy();
        resolve(this._getFallback(Date.now() - startTime, 'timeout'));
      });

      req.write(payload);
      req.end();
    });
  }

  _getFallback(elapsed, reason) {
    if (this.failOpen) {
      return {
        threatScore: 0.0,
        threatLevel: 'safe',
        action: 'allow',
        shouldBlock: false,
        reasons: [`engine_unreachable_${reason}`],
        signals: {},
        explanation: { narrative: 'TokenShield engine unreachable. Allowed under fail-open.' },
        latencyMs: elapsed
      };
    }
    return {
      threatScore: 1.0,
      threatLevel: 'critical',
      action: 'block',
      shouldBlock: true,
      reasons: [`engine_unreachable_${reason}`],
      signals: {},
      explanation: { narrative: 'TokenShield engine unreachable. Blocked under fail-closed.' },
      latencyMs: elapsed
    };
  }
}

function tokenshieldMiddleware(options = {}) {
  const client = new TokenShieldClient(options);

  return async function (req, res, next) {
    try {
      let biometrics = null;
      if (req.headers['x-ts-biometrics']) {
        try { biometrics = JSON.parse(req.headers['x-ts-biometrics']); } catch (e) {}
      }

      const clientIp = req.headers['x-forwarded-for']
        ? req.headers['x-forwarded-for'].split(',')[0].trim()
        : (req.socket.remoteAddress || '127.0.0.1');

      const sessionId = req.headers['authorization'] || req.cookies?.session || 'anonymous';
      const userId = req.user?.id || req.session?.userId || null;

      const decision = await client.inspectRequest({
        sessionId,
        userId,
        ip: clientIp,
        userAgent: req.headers['user-agent'],
        path: req.originalUrl || req.url,
        method: req.method,
        payload: typeof req.body === 'object' ? JSON.stringify(req.body) : req.body,
        biometrics
      });

      req.tokenshield = decision;

      if (decision.shouldBlock) {
        if (typeof options.onBlock === 'function') {
          return options.onBlock(req, res, decision);
        }
        return res.status(403).json({
          error: 'Access Denied by TokenShield Security Engine',
          threatLevel: decision.threatLevel,
          reasons: decision.reasons
        });
      }

      next();
    } catch (err) {
      next();
    }
  };
}

module.exports = {
  TokenShieldClient,
  tokenshieldMiddleware
};
