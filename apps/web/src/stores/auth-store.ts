/**
 * Aujasya — Auth Store (Zustand)
 * Manages authentication state with initializeAuth pattern.
 * [FIX-4] Access token stored in memory only — never localStorage.
 */

import { create } from 'zustand';
import api, { setAccessToken, getAccessToken } from '@/lib/api-client';

interface User {
  id: string;
  phoneNumber: string;
  phoneVerified: boolean;
  fullName: string | null;
  dateOfBirth: string | null;
  preferredLanguage: string;
  role: 'patient' | 'caregiver';
  timezone: string;
  isActive: boolean;
}

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  isNewUser: boolean;

  // Actions
  sendOtp: (phone: string) => Promise<{ sessionId: string }>;
  verifyOtp: (sessionId: string, otp: string) => Promise<void>;
  logout: (logoutAll?: boolean) => Promise<void>;
  initializeAuth: () => Promise<void>;
  updateProfile: (data: Partial<User>) => Promise<void>;
  setUser: (user: User | null) => void;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  isAuthenticated: false,
  isLoading: true,
  isNewUser: false,

  sendOtp: async (phone: string) => {
    const { data } = await api.post('/auth/send-otp', {
      phone,
      purpose: 'login',
    });
    return { sessionId: data.session_id };
  },

  verifyOtp: async (sessionId: string, otp: string) => {
    const { data } = await api.post('/auth/verify-otp', {
      session_id: sessionId,
      otp,
    });

    // [FIX-4] Store access token in memory only
    setAccessToken(data.access_token);

    // Transform API response to frontend User shape
    const user: User = {
      id: data.user.id,
      phoneNumber: data.user.phone_number,
      phoneVerified: data.user.phone_verified,
      fullName: data.user.full_name,
      dateOfBirth: data.user.date_of_birth,
      preferredLanguage: data.user.preferred_language,
      role: data.user.role,
      timezone: data.user.timezone,
      isActive: data.user.is_active,
    };

    set({
      user,
      isAuthenticated: true,
      isLoading: false,
      isNewUser: data.is_new_user,
    });
  },

  logout: async (logoutAll = false) => {
    try {
      await api.post('/auth/logout', { logout_all: logoutAll });
    } catch {
      // Best effort — clear local state regardless
    }
    setAccessToken(null);
    set({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      isNewUser: false,
    });
  },

  initializeAuth: async () => {
    /**
     * Called once on app mount. Attempts silent token refresh via
     * the httpOnly cookie. If the cookie exists and is valid, the
     * BFF returns a new access_token + user profile.
     */
    set({ isLoading: true });

    try {
      const { data } = await api.post('/auth/refresh');
      setAccessToken(data.access_token);

      // Fetch user profile
      const { data: userData } = await api.get('/auth/me');
      const user: User = {
        id: userData.id,
        phoneNumber: userData.phone_number,
        phoneVerified: userData.phone_verified,
        fullName: userData.full_name,
        dateOfBirth: userData.date_of_birth,
        preferredLanguage: userData.preferred_language,
        role: userData.role,
        timezone: userData.timezone,
        isActive: userData.is_active,
      };

      set({ user, isAuthenticated: true, isLoading: false });
    } catch {
      // No valid session — user needs to log in
      set({ user: null, isAuthenticated: false, isLoading: false });
    }
  },

  updateProfile: async (data: Partial<User>) => {
    const { data: updated } = await api.patch('/auth/me', {
      full_name: data.fullName,
      date_of_birth: data.dateOfBirth,
      preferred_language: data.preferredLanguage,
    });

    const current = get().user;
    if (current) {
      set({
        user: {
          ...current,
          fullName: updated.full_name ?? current.fullName,
          dateOfBirth: updated.date_of_birth ?? current.dateOfBirth,
          preferredLanguage: updated.preferred_language ?? current.preferredLanguage,
        },
      });
    }
  },

  setUser: (user: User | null) => {
    set({ user, isAuthenticated: !!user });
  },
}));
