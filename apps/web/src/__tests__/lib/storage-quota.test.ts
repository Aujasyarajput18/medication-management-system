/**
 * Aujasya — Storage Quota Monitor Tests
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock navigator.storage
const mockEstimate = vi.fn();

beforeEach(() => {
  vi.stubGlobal('navigator', {
    storage: { estimate: mockEstimate },
  });
  vi.stubGlobal('caches', {
    delete: vi.fn().mockResolvedValue(true),
  });
});

describe('checkStorageQuota', () => {
  it('returns ok when plenty of storage', async () => {
    mockEstimate.mockResolvedValue({
      usage: 10 * 1024 * 1024,    // 10MB used
      quota: 100 * 1024 * 1024,   // 100MB quota
    });

    const { checkStorageQuota } = await import('@/lib/storage-quota');
    const status = await checkStorageQuota();
    expect(status.status).toBe('ok');
    expect(status.action).toBe('none');
  });

  it('returns low when < 20MB remaining', async () => {
    mockEstimate.mockResolvedValue({
      usage: 85 * 1024 * 1024,    // 85MB used
      quota: 100 * 1024 * 1024,   // 100MB quota → 15MB remaining
    });

    const { checkStorageQuota } = await import('@/lib/storage-quota');
    const status = await checkStorageQuota();
    expect(status.status).toBe('low');
    expect(status.action).toBe('disable_model_cache');
  });

  it('returns critical when < 10MB remaining', async () => {
    mockEstimate.mockResolvedValue({
      usage: 95 * 1024 * 1024,    // 95MB used
      quota: 100 * 1024 * 1024,   // 100MB quota → 5MB remaining
    });

    const { checkStorageQuota } = await import('@/lib/storage-quota');
    const status = await checkStorageQuota();
    expect(status.status).toBe('critical');
    expect(status.action).toBe('purge_all_caches');
  });

  it('returns unknown when API unavailable', async () => {
    vi.stubGlobal('navigator', { storage: {} });

    const { checkStorageQuota } = await import('@/lib/storage-quota');
    const status = await checkStorageQuota();
    expect(status.status).toBe('unknown');
  });
});
