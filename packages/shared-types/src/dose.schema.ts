import { z } from 'zod';
import { MealAnchorSchema } from './medicine.schema';

/**
 * Dose status values.
 * - 'taken': patient confirmed intake
 * - 'missed': window closed without confirmation
 * - 'skipped': patient deliberately skipped with reason
 * - 'pending': future or within current window
 */
export const DoseStatusSchema = z.enum(['taken', 'missed', 'skipped', 'pending']);
export type DoseStatus = z.infer<typeof DoseStatusSchema>;

/**
 * Mark dose as taken — sent from frontend when user taps "Take".
 */
export const DoseTakenSchema = z.object({
  notes: z.string().max(500).trim().optional(),
  offline_sync: z.boolean().default(false),
  device_timestamp: z.string().datetime().optional(),
});
export type DoseTaken = z.infer<typeof DoseTakenSchema>;

/**
 * Mark dose as skipped — requires a reason (min 5 chars).
 */
export const DoseSkippedSchema = z.object({
  skip_reason: z.string().min(5).max(500).trim(),
  notes: z.string().max(500).trim().optional(),
});
export type DoseSkipped = z.infer<typeof DoseSkippedSchema>;

/**
 * Offline sync mutation — a single dose action taken while offline.
 */
export const OfflineSyncMutationSchema = z.object({
  dose_id: z.string().uuid(),
  action: z.enum(['taken', 'skipped']),
  device_timestamp: z.string().datetime(),
  notes: z.string().max(500).trim().optional(),
  skip_reason: z.string().max(500).trim().optional(),
});
export type OfflineSyncMutation = z.infer<typeof OfflineSyncMutationSchema>;

/**
 * Batch offline sync request.
 */
export const OfflineSyncRequestSchema = z.object({
  mutations: z.array(OfflineSyncMutationSchema).min(1).max(100),
});
export type OfflineSyncRequest = z.infer<typeof OfflineSyncRequestSchema>;

/**
 * Calendar query — [FIX-15] uses month=YYYY-MM only, no separate year param.
 */
export const CalendarQuerySchema = z.object({
  month: z.string().regex(/^\d{4}-\d{2}$/, 'Format must be YYYY-MM'),
  patient_id: z.string().uuid().optional(),
});
export type CalendarQuery = z.infer<typeof CalendarQuerySchema>;
