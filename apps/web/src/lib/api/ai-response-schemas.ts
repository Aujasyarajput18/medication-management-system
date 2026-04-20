/**
 * Aujasya — AI Response Zod Validation Schemas
 * BFF-layer validation for all AI service responses.
 * Malformed responses from LLaVA, Bhashini, RxNorm etc. are caught here
 * before reaching frontend hooks.
 */

import { z } from 'zod';

// ── OCR ─────────────────────────────────────────────────────────────────────

export const OcrEntitiesSchema = z.object({
  drug_name: z.string().nullable().optional(),
  dosage: z.string().nullable().optional(),
  frequency: z.string().nullable().optional(),
  duration: z.string().nullable().optional(),
  prescribed_by: z.string().nullable().optional(),
  instructions: z.string().nullable().optional(),
  matched_medicine_id: z.string().nullable().optional(),
  match_confidence: z.number().nullable().optional(),
});

export const OcrResponseSchema = z.object({
  raw_text: z.string(),
  confidence: z.number().min(0).max(1),
  source: z.enum(['tesseract', 'llava']),
  entities: OcrEntitiesSchema.optional().default({}),
  confidence_flag: z.enum(['low']).optional(),
  user_warning: z.string().optional(),
});

// ── Pill ID ─────────────────────────────────────────────────────────────────

export const PillCandidateSchema = z.object({
  drug_name: z.string(),
  confidence: z.number().min(0).max(1),
  color: z.string().nullable().optional(),
  shape: z.string().nullable().optional(),
  imprint: z.string().nullable().optional(),
  matched_medicine_id: z.string().nullable().optional(),
});

export const PillIdResponseSchema = z.object({
  candidates: z.array(PillCandidateSchema),
  model_version: z.string().optional(),
  source: z.string().optional(),
});

// ── Drug Interactions ───────────────────────────────────────────────────────

export const InteractionDrugSchema = z.object({
  rxcui: z.string(),
  name: z.string(),
});

export const InteractionResultSchema = z.object({
  drug_a: InteractionDrugSchema,
  drug_b: InteractionDrugSchema,
  severity: z.enum(['contraindicated', 'major', 'moderate', 'minor']),
  description: z.string(),
});

export const InteractionCheckResponseSchema = z.object({
  interactions: z.array(InteractionResultSchema),
  critical_count: z.number().int().min(0),
  major_count: z.number().int().min(0),
});

export const RxcuiLookupSchema = z.object({
  rxcui: z.string().optional(),
  name: z.string().optional(),
  found: z.boolean(),
});

// ── Voice/STT ───────────────────────────────────────────────────────────────

export const VoiceIntentSchema = z.object({
  type: z.string(),
  slots: z.record(z.string(), z.string()).default({}),
  confidence: z.number().min(0).max(1),
});

export const SttResponseSchema = z.object({
  transcript: z.string(),
  intent: VoiceIntentSchema,
  language: z.string(),
});

// ── Fasting ─────────────────────────────────────────────────────────────────

export const PrayerTimesSchema = z.object({
  suhoor: z.string(),
  iftar: z.string(),
  sunrise: z.string(),
  sunset: z.string(),
  source: z.enum(['aladhan', 'sunrise_sunset', 'static_fallback']),
});

export const ScheduleAdjustmentSchema = z.object({
  schedule_id: z.string(),
  medicine_name: z.string(),
  original_meal_anchor: z.string(),
  adjusted_meal_anchor: z.string(),
  reason: z.string(),
  severity_level: z.enum(['info', 'warning', 'critical']),
  blocked: z.boolean(),
});

export const FastingActivateResponseSchema = z.object({
  fasting_profile_id: z.string(),
  fasting_type: z.string(),
  adjustments: z.array(ScheduleAdjustmentSchema),
  blocked_medications: z.array(ScheduleAdjustmentSchema),
  pharmacist_reviewed: z.boolean(),
});

// ── Generics ────────────────────────────────────────────────────────────────

export const GenericAlternativeSchema = z.object({
  name: z.string(),
  manufacturer: z.string(),
  mrp_per_unit: z.number(),
  savings_percent: z.number(),
  jan_aushadhi: z.boolean(),
  who_gmp: z.boolean(),
  nabl_certified: z.boolean(),
  ranking_score: z.number().optional(),
});

export const GenericSearchResponseSchema = z.object({
  brand: z.object({
    name: z.string(),
    active_ingredient: z.string().optional().default(''),
    mrp_per_unit: z.number().optional().default(0),
  }),
  alternatives: z.array(GenericAlternativeSchema),
});

// ── Journal ─────────────────────────────────────────────────────────────────

export const JournalEntryResponseSchema = z.object({
  id: z.string(),
  medicine_id: z.string().nullable().optional(),
  symptom_text: z.string(),
  symptom_normalized: z.array(z.string()).default([]),
  severity: z.string(),
  onset_date: z.string(),
  resolved_date: z.string().nullable().optional(),
  input_method: z.string(),
  is_flagged: z.boolean().default(false),
  flag_reason: z.string().nullable().optional(),
  created_at: z.string(),
});

export const JournalPatternsResponseSchema = z.object({
  patterns: z.array(
    z.object({
      symptom: z.string(),
      count: z.number().int(),
      first_occurrence: z.string(),
      last_occurrence: z.string(),
    })
  ),
  period_days: z.number().int(),
});

// ── Refills ─────────────────────────────────────────────────────────────────

export const RefillStatusSchema = z.object({
  medicine_id: z.string(),
  brand_name: z.string(),
  remaining_quantity: z.number().nullable(),
  daily_dose_count: z.number(),
  days_remaining: z.number().nullable(),
  projected_runout_date: z.string().nullable(),
  alert_required: z.boolean(),
  nearest_kendras: z.array(z.any()).default([]),
});

/**
 * Validate an AI service response and return typed data or null.
 * Usage in BFF proxy:
 *   const parsed = validateAiResponse(OcrResponseSchema, backendData);
 *   if (!parsed) return NextResponse.json({ error: 'Invalid AI response' }, { status: 502 });
 */
export function validateAiResponse<T>(
  schema: z.ZodType<T>,
  data: unknown
): T | null {
  const result = schema.safeParse(data);
  if (result.success) return result.data;
  console.error('[AI Validation] Schema mismatch:', result.error.issues);
  return null;
}
