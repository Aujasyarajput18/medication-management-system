/**
 * Aujasya — BFF Auth Refresh Route
 */
import { NextRequest } from 'next/server';
import { refreshTokens } from '@/lib/bff-auth';

export async function POST(req: NextRequest) {
  return refreshTokens(req);
}
