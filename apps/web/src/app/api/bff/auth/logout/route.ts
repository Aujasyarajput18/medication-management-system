/**
 * Aujasya — BFF Auth Logout Route
 */
import { NextRequest } from 'next/server';
import { logoutUser } from '@/lib/bff-auth';

export async function POST(req: NextRequest) {
  return logoutUser(req);
}
