/**
 * Aujasya — BFF Auth Send OTP Route
 */
import { NextRequest } from 'next/server';
import { sendOtp } from '@/lib/bff-auth';

export async function POST(req: NextRequest) {
  return sendOtp(req);
}
