/**
 * Aujasya — BFF Auth Verify OTP Route
 */
import { NextRequest } from 'next/server';
import { verifyOtp } from '@/lib/bff-auth';

export async function POST(req: NextRequest) {
  return verifyOtp(req);
}
