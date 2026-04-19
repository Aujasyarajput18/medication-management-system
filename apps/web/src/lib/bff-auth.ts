/**
 * Aujasya — BFF Auth Route Handlers
 * [FIX-1] Browser NEVER calls FastAPI directly.
 * [FIX-3] Refresh token stored in httpOnly cookie.
 */

import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';

const API_BASE = process.env.API_URL || 'http://localhost:8000';
const API_PREFIX = '/api/v1';

/** Forward request to FastAPI backend */
async function proxyToBackend(
  endpoint: string,
  options: RequestInit
): Promise<Response> {
  return fetch(`${API_BASE}${API_PREFIX}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });
}

// ── POST /api/bff/auth/send-otp ─────────────────────────────────────────────
export async function sendOtp(req: NextRequest): Promise<NextResponse> {
  const body = await req.json();
  const backendRes = await proxyToBackend('/auth/send-otp', {
    method: 'POST',
    body: JSON.stringify(body),
  });

  const data = await backendRes.json();
  return NextResponse.json(data, { status: backendRes.status });
}

// ── POST /api/bff/auth/verify-otp ───────────────────────────────────────────
export async function verifyOtp(req: NextRequest): Promise<NextResponse> {
  const body = await req.json();
  const backendRes = await proxyToBackend('/auth/verify-otp', {
    method: 'POST',
    body: JSON.stringify(body),
  });

  if (!backendRes.ok) {
    const errorData = await backendRes.json();
    return NextResponse.json(errorData, { status: backendRes.status });
  }

  const data = await backendRes.json();

  // [FIX-3] Set refresh token in httpOnly cookie
  const response = NextResponse.json({
    access_token: data.access_token,
    user: data.user,
    is_new_user: data.is_new_user,
  });

  response.cookies.set('refresh_token', data.refresh_token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'lax',
    path: '/',
    maxAge: 30 * 24 * 60 * 60, // 30 days
  });

  return response;
}

// ── POST /api/bff/auth/refresh ──────────────────────────────────────────────
export async function refreshTokens(req: NextRequest): Promise<NextResponse> {
  const cookieStore = await cookies();
  const refreshToken = cookieStore.get('refresh_token')?.value;

  if (!refreshToken) {
    return NextResponse.json(
      { message: 'No refresh token' },
      { status: 401 }
    );
  }

  // [FIX-3] BFF reads cookie, sends to FastAPI as JSON body
  const backendRes = await proxyToBackend('/auth/refresh', {
    method: 'POST',
    body: JSON.stringify({ refresh_token: refreshToken }),
  });

  if (!backendRes.ok) {
    // Invalid refresh token — clear cookie
    const response = NextResponse.json(
      { message: 'Session expired' },
      { status: 401 }
    );
    response.cookies.delete('refresh_token');
    return response;
  }

  const data = await backendRes.json();

  // Set new refresh token cookie (rotation)
  const response = NextResponse.json({
    access_token: data.access_token,
  });

  response.cookies.set('refresh_token', data.refresh_token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'lax',
    path: '/',
    maxAge: 30 * 24 * 60 * 60,
  });

  return response;
}

// ── POST /api/bff/auth/logout ───────────────────────────────────────────────
export async function logoutUser(req: NextRequest): Promise<NextResponse> {
  const cookieStore = await cookies();
  const refreshToken = cookieStore.get('refresh_token')?.value;
  const authHeader = req.headers.get('authorization') || '';

  if (refreshToken) {
    const body = await req.json().catch(() => ({}));
    await proxyToBackend('/auth/logout', {
      method: 'POST',
      headers: { Authorization: authHeader },
      body: JSON.stringify({
        refresh_token: refreshToken,
        logout_all: body.logout_all || false,
      }),
    });
  }

  const response = NextResponse.json({ success: true });
  response.cookies.delete('refresh_token');
  return response;
}
