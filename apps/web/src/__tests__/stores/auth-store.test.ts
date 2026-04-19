/**
 * Aujasya — Auth Store Tests
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { useAuthStore } from '@/stores/auth-store';

// Mock the API client
vi.mock('@/lib/api-client', () => ({
  default: {
    post: vi.fn(),
    get: vi.fn(),
    patch: vi.fn(),
  },
  setAccessToken: vi.fn(),
  getAccessToken: vi.fn(() => null),
}));

describe('Auth Store', () => {
  beforeEach(() => {
    // Reset store state
    useAuthStore.setState({
      user: null,
      isAuthenticated: false,
      isLoading: true,
      isNewUser: false,
    });
  });

  it('should have initial state', () => {
    const state = useAuthStore.getState();
    expect(state.user).toBeNull();
    expect(state.isAuthenticated).toBe(false);
    expect(state.isLoading).toBe(true);
  });

  it('should set user on setUser', () => {
    const mockUser = {
      id: '123',
      phoneNumber: '+919876543210',
      phoneVerified: true,
      fullName: 'Test User',
      dateOfBirth: null,
      preferredLanguage: 'hi',
      role: 'patient' as const,
      timezone: 'Asia/Kolkata',
      isActive: true,
    };

    useAuthStore.getState().setUser(mockUser);

    const state = useAuthStore.getState();
    expect(state.user).toEqual(mockUser);
    expect(state.isAuthenticated).toBe(true);
  });

  it('should clear state on logout', async () => {
    const { setAccessToken } = await import('@/lib/api-client');

    // Set initial authenticated state
    useAuthStore.setState({
      user: { id: '123' } as any,
      isAuthenticated: true,
      isLoading: false,
    });

    await useAuthStore.getState().logout();

    const state = useAuthStore.getState();
    expect(state.user).toBeNull();
    expect(state.isAuthenticated).toBe(false);
    expect(setAccessToken).toHaveBeenCalledWith(null);
  });

  it('should handle logout error gracefully', async () => {
    const api = (await import('@/lib/api-client')).default;
    (api.post as any).mockRejectedValueOnce(new Error('Network error'));

    useAuthStore.setState({
      user: { id: '123' } as any,
      isAuthenticated: true,
    });

    // Should not throw
    await useAuthStore.getState().logout();

    expect(useAuthStore.getState().isAuthenticated).toBe(false);
  });
});
