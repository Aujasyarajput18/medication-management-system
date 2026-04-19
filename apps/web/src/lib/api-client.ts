/**
 * Aujasya — API Client (Frontend → BFF)
 * Axios instance with interceptors for JWT refresh hop.
 * [FIX-1] BFF pattern: browser never touches FastAPI directly.
 * [FIX-4] Token refresh interceptor handles 401 and retries.
 */

import axios, { type AxiosError, type InternalAxiosRequestConfig } from 'axios';

const api = axios.create({
  baseURL: '/api/bff',
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true, // Send httpOnly cookies
});

// ── Request Interceptor ────────────────────────────────────────────────────
// Attach access token from memory (not localStorage — XSS safe)
let accessToken: string | null = null;

export function setAccessToken(token: string | null): void {
  accessToken = token;
}

export function getAccessToken(): string | null {
  return accessToken;
}

api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`;
  }
  return config;
});

// ── Response Interceptor — Token Refresh Hop ───────────────────────────────
// [FIX-4] When a 401 is received:
// 1. Call /api/bff/auth/refresh (sends httpOnly cookie automatically)
// 2. BFF Route Handler reads cookie, calls FastAPI /auth/refresh
// 3. BFF returns new access_token in JSON, sets new refresh_token cookie
// 4. Retry the original request with the new access_token

let isRefreshing = false;
let failedQueue: Array<{
  resolve: (token: string) => void;
  reject: (error: unknown) => void;
}> = [];

function processQueue(error: unknown, token: string | null = null): void {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else if (token) {
      prom.resolve(token);
    }
  });
  failedQueue = [];
}

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & {
      _retry?: boolean;
    };

    // Only attempt refresh on 401, and only once per request
    if (error.response?.status !== 401 || originalRequest._retry) {
      return Promise.reject(error);
    }

    // Don't retry refresh or login endpoints
    if (
      originalRequest.url?.includes('/auth/refresh') ||
      originalRequest.url?.includes('/auth/send-otp') ||
      originalRequest.url?.includes('/auth/verify-otp')
    ) {
      return Promise.reject(error);
    }

    if (isRefreshing) {
      // Queue this request — it will be retried when refresh completes
      return new Promise<string>((resolve, reject) => {
        failedQueue.push({ resolve, reject });
      }).then((token) => {
        originalRequest.headers.Authorization = `Bearer ${token}`;
        return api(originalRequest);
      });
    }

    originalRequest._retry = true;
    isRefreshing = true;

    try {
      // [FIX-4] BFF refresh hop — cookie is sent automatically
      const { data } = await axios.post('/api/bff/auth/refresh');
      const newToken = data.access_token;

      setAccessToken(newToken);
      processQueue(null, newToken);

      originalRequest.headers.Authorization = `Bearer ${newToken}`;
      return api(originalRequest);
    } catch (refreshError) {
      processQueue(refreshError, null);
      setAccessToken(null);

      // Redirect to login
      if (typeof window !== 'undefined') {
        window.location.href = '/login';
      }

      return Promise.reject(refreshError);
    } finally {
      isRefreshing = false;
    }
  }
);

export default api;
