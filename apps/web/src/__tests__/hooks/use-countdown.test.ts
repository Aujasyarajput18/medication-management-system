/**
 * Aujasya — Hook Tests
 */

import { describe, it, expect, vi } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useCountdown } from '@/hooks/use-countdown';

describe('useCountdown', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('should initialize with given seconds', () => {
    const { result } = renderHook(() => useCountdown(60));
    expect(result.current.seconds).toBe(60);
    expect(result.current.isActive).toBe(false);
  });

  it('should start countdown', () => {
    const { result } = renderHook(() => useCountdown(5));

    act(() => {
      result.current.start();
    });

    expect(result.current.isActive).toBe(true);
    expect(result.current.seconds).toBe(5);

    act(() => {
      vi.advanceTimersByTime(1000);
    });

    expect(result.current.seconds).toBe(4);
  });

  it('should stop at zero', () => {
    const { result } = renderHook(() => useCountdown(2));

    act(() => {
      result.current.start();
    });

    act(() => {
      vi.advanceTimersByTime(3000);
    });

    expect(result.current.seconds).toBe(0);
    expect(result.current.isActive).toBe(false);
    expect(result.current.isComplete).toBe(true);
  });

  it('should reset', () => {
    const { result } = renderHook(() => useCountdown(60));

    act(() => {
      result.current.start();
    });

    act(() => {
      vi.advanceTimersByTime(5000);
    });

    act(() => {
      result.current.reset();
    });

    expect(result.current.seconds).toBe(60);
    expect(result.current.isActive).toBe(false);
  });
});
