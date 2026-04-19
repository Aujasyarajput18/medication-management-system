/**
 * Aujasya — BFF Proxy Route (allowlisted, NOT catch-all)
 *
 * [FIX-4, Issue #4] This proxy ONLY forwards requests to a strict allowlist
 * of FastAPI routes. A catch-all proxy would:
 *   - Expose internal/debug FastAPI endpoints to the public internet
 *   - Let clients bypass BFF auth handlers that manage httpOnly cookies
 *   - Make FastAPI rate limiting fire on the Next.js server IP, not the real client
 *
 * HOW THIS WORKS:
 * 1. Request arrives at /api/bff/medicines, /api/bff/doses/today, etc.
 * 2. We check the resolved path against ALLOWED_ROUTES.
 * 3. If not allowed → 403. If allowed → proxy with X-Forwarded-For.
 * 4. Auth routes are handled by dedicated BFF handlers in /api/bff/auth/,
 *    NOT by this proxy — those manage httpOnly cookies directly.
 */

import { NextRequest, NextResponse } from 'next/server';

const API_BASE = process.env.API_URL || 'http://localhost:8000';

/**
 * Strict allowlist of route prefixes that may be proxied.
 * Auth routes are NOT listed — they have dedicated BFF handlers.
 * Internal/admin/debug routes are NOT listed — they stay internal.
 */
const ALLOWED_ROUTE_PREFIXES = [
  'medicines',
  'doses',
  'caregivers',
  'notifications',
  'health',
];

function isAllowedRoute(pathSegments: string[]): boolean {
  if (pathSegments.length === 0) return false;
  const firstSegment = pathSegments[0];
  return ALLOWED_ROUTE_PREFIXES.includes(firstSegment);
}

export async function GET(req: NextRequest, { params }: { params: { path: string[] } }) {
  return proxyRequest(req, params.path, 'GET');
}

export async function POST(req: NextRequest, { params }: { params: { path: string[] } }) {
  return proxyRequest(req, params.path, 'POST');
}

export async function PATCH(req: NextRequest, { params }: { params: { path: string[] } }) {
  return proxyRequest(req, params.path, 'PATCH');
}

export async function PUT(req: NextRequest, { params }: { params: { path: string[] } }) {
  return proxyRequest(req, params.path, 'PUT');
}

export async function DELETE(req: NextRequest, { params }: { params: { path: string[] } }) {
  return proxyRequest(req, params.path, 'DELETE');
}

async function proxyRequest(
  req: NextRequest,
  pathSegments: string[],
  method: string
): Promise<NextResponse> {
  // ── Route Allowlist Check ──────────────────────────────────────────────
  if (!isAllowedRoute(pathSegments)) {
    return NextResponse.json(
      { message: 'Route not allowed through BFF proxy' },
      { status: 403 }
    );
  }

  const path = pathSegments.join('/');
  const url = `${API_BASE}/api/v1/${path}`;

  // ── Headers ────────────────────────────────────────────────────────────
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };

  // Forward auth header (access token from client)
  const authHeader = req.headers.get('authorization');
  if (authHeader) {
    headers['Authorization'] = authHeader;
  }

  // Forward accept-language for i18n
  const lang = req.headers.get('accept-language');
  if (lang) {
    headers['Accept-Language'] = lang;
  }

  // [Issue #4] Forward real client IP so FastAPI rate limiting works per-user,
  // not per-Next.js-server-IP. In production behind NGINX, this chain is:
  //   Client → NGINX (sets X-Real-IP) → Next.js (appends X-Forwarded-For) → FastAPI
  const clientIp =
    req.headers.get('x-real-ip') ||
    req.headers.get('x-forwarded-for')?.split(',')[0]?.trim() ||
    req.ip ||
    'unknown';
  headers['X-Forwarded-For'] = clientIp;

  const fetchOptions: RequestInit = {
    method,
    headers,
  };

  // Include body for non-GET/DELETE requests
  if (method !== 'GET' && method !== 'DELETE') {
    try {
      const body = await req.json();
      fetchOptions.body = JSON.stringify(body);
    } catch {
      // No body — that's fine for some POST endpoints
    }
  }

  // Forward query params
  const searchParams = req.nextUrl.searchParams.toString();
  const fullUrl = searchParams ? `${url}?${searchParams}` : url;

  try {
    const backendRes = await fetch(fullUrl, fetchOptions);
    const data = await backendRes.json().catch(() => null);

    return NextResponse.json(data, { status: backendRes.status });
  } catch (error) {
    return NextResponse.json(
      { message: 'Backend unavailable' },
      { status: 502 }
    );
  }
}
