'use client';

/**
 * Aujasya — Client Auth Initializer
 * Runs initializeAuth() once on app mount.
 */

import { useEffect } from 'react';
import { useAuthStore } from '@/stores/auth-store';

export function ClientAuthInit() {
  const initializeAuth = useAuthStore((s) => s.initializeAuth);

  useEffect(() => {
    initializeAuth();
  }, [initializeAuth]);

  return null;
}
