/**
 * Aujasya — Next.js Middleware
 * [FIX-2] Located at src/middleware.ts (root of src/), NOT inside app/.
 * Handles locale routing and auth guards.
 */

import createMiddleware from 'next-intl/middleware';
import { NextRequest, NextResponse } from 'next/server';
import { locales, defaultLocale } from './i18n/config';

const intlMiddleware = createMiddleware({
  locales,
  defaultLocale,
  localePrefix: 'always',
});

// Pages that don't require authentication
const PUBLIC_PAGES = ['/login', '/verify', '/offline'];

// Pages that should redirect authenticated users away
const AUTH_PAGES = ['/login', '/verify'];

export default function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Skip middleware for API routes and static files
  if (
    pathname.startsWith('/api/') ||
    pathname.startsWith('/_next/') ||
    pathname.startsWith('/icons/') ||
    pathname.includes('.') // Static files
  ) {
    return NextResponse.next();
  }

  // Apply i18n middleware
  const response = intlMiddleware(request);

  // Check auth state via cookie presence
  const hasRefreshToken = request.cookies.has('refresh_token');

  // Extract the page path without locale prefix
  const pathnameWithoutLocale = pathname.replace(
    new RegExp(`^/(${locales.join('|')})`),
    ''
  ) || '/';

  // Redirect unauthenticated users to login
  if (!hasRefreshToken && !PUBLIC_PAGES.some(p => pathnameWithoutLocale.startsWith(p))) {
    const loginUrl = new URL(`/${defaultLocale}/login`, request.url);
    loginUrl.searchParams.set('redirect', pathname);
    return NextResponse.redirect(loginUrl);
  }

  // Redirect authenticated users away from auth pages
  if (hasRefreshToken && AUTH_PAGES.some(p => pathnameWithoutLocale.startsWith(p))) {
    return NextResponse.redirect(new URL(`/${defaultLocale}/today`, request.url));
  }

  // Redirect root to /today for authenticated users
  if (hasRefreshToken && (pathnameWithoutLocale === '/' || pathnameWithoutLocale === '')) {
    return NextResponse.redirect(new URL(`/${defaultLocale}/today`, request.url));
  }

  return response;
}

export const config = {
  matcher: ['/((?!api|_next|icons|.*\\..*).*)'],
};
