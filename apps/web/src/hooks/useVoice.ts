/**
 * Aujasya — useVoice Hook
 * Manages voice recording, STT, TTS, and intent classification.
 * Audio is NEVER persisted — processed in memory only.
 */

'use client';

import { useState, useCallback, useRef, useEffect } from 'react';
import type { VoiceStatus, SttResult, SupportedLanguage } from '@/types/voice.types';

export function useVoice() {
  const [status, setStatus] = useState<VoiceStatus>('idle');
  const [result, setResult] = useState<SttResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [language, setLanguage] = useState<SupportedLanguage>('hi');
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  useEffect(() => {
    return () => {
      // Cleanup: stop recording if component unmounts
      if (mediaRecorderRef.current?.state === 'recording') {
        mediaRecorderRef.current.stop();
      }
    };
  }, []);

  const startRecording = useCallback(async () => {
    try {
      setStatus('listening');
      setError(null);
      chunksRef.current = [];

      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { sampleRate: 16000, channelCount: 1, echoCancellation: true },
      });

      const recorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      recorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' });
        await processAudio(blob);
      };

      // Haptic feedback for recording start (elderly UX improvement)
      if (navigator.vibrate) navigator.vibrate(100);

      recorder.start();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Microphone access denied');
      setStatus('error');
    }
  }, []);

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current?.state === 'recording') {
      // Haptic feedback for recording stop
      if (navigator.vibrate) navigator.vibrate([50, 50, 50]);
      mediaRecorderRef.current.stop();
    }
  }, []);

  const processAudio = async (blob: Blob) => {
    try {
      setStatus('processing');

      const formData = new FormData();
      formData.append('audio', blob, 'recording.webm');
      formData.append('language', language);

      const resp = await fetch('/api/bff/voice/stt', { method: 'POST', body: formData });
      if (!resp.ok) throw new Error('STT failed');

      const data: SttResult = await resp.json();
      setResult(data);
      setStatus('done');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Processing failed');
      setStatus('error');
    }
  };

  const reset = useCallback(() => {
    setStatus('idle');
    setResult(null);
    setError(null);
  }, []);

  return { status, result, error, language, setLanguage, startRecording, stopRecording, reset };
}
