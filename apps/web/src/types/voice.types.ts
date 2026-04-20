/** Aujasya — Voice Type Definitions */

export interface VoiceIntent {
  type: 'log_dose_taken' | 'log_dose_skipped' | 'query_next_dose' | 'query_streak' | 'add_medicine' | 'unknown';
  slots: Record<string, string>;
  confidence: number;
}

export interface SttResult {
  transcript: string;
  intent: VoiceIntent;
  language: string;
}

export type VoiceStatus = 'idle' | 'listening' | 'processing' | 'speaking' | 'done' | 'error';

export type SupportedLanguage = 'hi' | 'en' | 'bn' | 'ta' | 'te' | 'mr';
