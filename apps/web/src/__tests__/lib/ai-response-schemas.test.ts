/**
 * Aujasya — AI Response Schema Validation Tests
 */
import { describe, it, expect } from 'vitest';
import {
  OcrResponseSchema,
  PillIdResponseSchema,
  InteractionCheckResponseSchema,
  SttResponseSchema,
  FastingActivateResponseSchema,
  GenericSearchResponseSchema,
  JournalEntryResponseSchema,
  RefillStatusSchema,
  validateAiResponse,
} from '@/lib/api/ai-response-schemas';

describe('OcrResponseSchema', () => {
  it('validates correct OCR response', () => {
    const data = {
      raw_text: 'Paracetamol 500mg',
      confidence: 0.85,
      source: 'tesseract',
    };
    const result = OcrResponseSchema.safeParse(data);
    expect(result.success).toBe(true);
  });

  it('rejects invalid source', () => {
    const data = {
      raw_text: 'Test',
      confidence: 0.5,
      source: 'invalid_source',
    };
    const result = OcrResponseSchema.safeParse(data);
    expect(result.success).toBe(false);
  });

  it('rejects confidence > 1', () => {
    const data = {
      raw_text: 'Test',
      confidence: 1.5,
      source: 'tesseract',
    };
    const result = OcrResponseSchema.safeParse(data);
    expect(result.success).toBe(false);
  });
});

describe('InteractionCheckResponseSchema', () => {
  it('validates correct interaction response', () => {
    const data = {
      interactions: [
        {
          drug_a: { rxcui: '123', name: 'Drug A' },
          drug_b: { rxcui: '456', name: 'Drug B' },
          severity: 'major',
          description: 'Increased risk of bleeding',
        },
      ],
      critical_count: 0,
      major_count: 1,
    };
    const result = InteractionCheckResponseSchema.safeParse(data);
    expect(result.success).toBe(true);
  });

  it('rejects invalid severity', () => {
    const data = {
      interactions: [
        {
          drug_a: { rxcui: '123', name: 'A' },
          drug_b: { rxcui: '456', name: 'B' },
          severity: 'extreme',
          description: 'Bad',
        },
      ],
      critical_count: 0,
      major_count: 0,
    };
    const result = InteractionCheckResponseSchema.safeParse(data);
    expect(result.success).toBe(false);
  });
});

describe('validateAiResponse helper', () => {
  it('returns data on valid input', () => {
    const data = {
      raw_text: 'Test',
      confidence: 0.9,
      source: 'tesseract',
    };
    const result = validateAiResponse(OcrResponseSchema, data);
    expect(result).not.toBeNull();
    expect(result?.raw_text).toBe('Test');
  });

  it('returns null on invalid input', () => {
    const result = validateAiResponse(OcrResponseSchema, { bad: 'data' });
    expect(result).toBeNull();
  });
});

describe('RefillStatusSchema', () => {
  it('validates correct refill status', () => {
    const data = {
      medicine_id: 'uuid-123',
      brand_name: 'Crocin',
      remaining_quantity: 10,
      daily_dose_count: 2,
      days_remaining: 5,
      projected_runout_date: '2026-04-25',
      alert_required: true,
      nearest_kendras: [],
    };
    const result = RefillStatusSchema.safeParse(data);
    expect(result.success).toBe(true);
  });
});
