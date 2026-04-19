/**
 * Aujasya — Swipe Action Hook
 * Enables swipe-to-take / swipe-to-skip on dose cards.
 */

import { useRef, useState, useCallback, type TouchEvent } from 'react';

interface SwipeActionOptions {
  threshold?: number;
  onSwipeLeft?: () => void;
  onSwipeRight?: () => void;
}

export function useSwipeAction(options: SwipeActionOptions = {}) {
  const { threshold = 80, onSwipeLeft, onSwipeRight } = options;
  const startX = useRef(0);
  const [offsetX, setOffsetX] = useState(0);
  const [isSwiping, setIsSwiping] = useState(false);

  const onTouchStart = useCallback((e: TouchEvent) => {
    startX.current = e.touches[0].clientX;
    setIsSwiping(true);
  }, []);

  const onTouchMove = useCallback((e: TouchEvent) => {
    if (!isSwiping) return;
    const diff = e.touches[0].clientX - startX.current;
    setOffsetX(diff);
  }, [isSwiping]);

  const onTouchEnd = useCallback(() => {
    if (offsetX > threshold && onSwipeRight) {
      onSwipeRight();
    } else if (offsetX < -threshold && onSwipeLeft) {
      onSwipeLeft();
    }
    setOffsetX(0);
    setIsSwiping(false);
  }, [offsetX, threshold, onSwipeLeft, onSwipeRight]);

  return {
    swipeHandlers: { onTouchStart, onTouchMove, onTouchEnd },
    offsetX,
    isSwiping,
    swipeDirection: offsetX > 20 ? 'right' : offsetX < -20 ? 'left' : null,
  };
}
