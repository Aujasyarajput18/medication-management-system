import { z } from 'zod';

/**
 * Allowed dosage units for medications.
 */
export const DosageUnitSchema = z.enum(['mg', 'ml', 'mcg', 'units']);
export type DosageUnit = z.infer<typeof DosageUnitSchema>;

/**
 * Allowed medication forms.
 */
export const MedicineFormSchema = z.enum([
  'tablet',
  'capsule',
  'syrup',
  'injection',
  'drops',
]);
export type MedicineForm = z.infer<typeof MedicineFormSchema>;

/**
 * Meal anchors define when a dose is taken relative to meals.
 * This is the core of Aujasya's meal-anchored scheduling system.
 */
export const MealAnchorSchema = z.enum([
  'before_breakfast',
  'with_breakfast',
  'after_breakfast',
  'before_lunch',
  'with_lunch',
  'after_lunch',
  'before_dinner',
  'with_dinner',
  'after_dinner',
  'at_bedtime',
  'on_waking',
  'any_time',
]);
export type MealAnchor = z.infer<typeof MealAnchorSchema>;

/**
 * Days of week: 0=Sunday, 1=Monday, ..., 6=Saturday
 * Matches JavaScript Date.getDay() and date-fns getDay()
 * [FIX-14] — DO NOT use ISO week numbering (Monday=1)
 */
export const DayOfWeekSchema = z
  .number()
  .int()
  .min(0)
  .max(6);
export type DayOfWeek = z.infer<typeof DayOfWeekSchema>;

/**
 * Schedule creation schema — defines when a medication should be taken.
 */
export const ScheduleCreateSchema = z.object({
  meal_anchor: MealAnchorSchema,
  offset_minutes: z.number().int().min(-120).max(120).default(0),
  dose_quantity: z.number().positive().max(100).default(1),
  days_of_week: z
    .array(DayOfWeekSchema)
    .min(1)
    .max(7)
    .default([0, 1, 2, 3, 4, 5, 6]),
  reminder_level: z.number().int().min(1).max(4).default(4),
});
export type ScheduleCreate = z.infer<typeof ScheduleCreateSchema>;

/**
 * Medicine creation schema — full validation for adding a new medicine.
 */
export const MedicineCreateSchema = z.object({
  brand_name: z.string().min(1).max(200).trim(),
  generic_name: z.string().max(200).trim().optional(),
  dosage_value: z.number().positive().max(99999),
  dosage_unit: DosageUnitSchema,
  form: MedicineFormSchema,
  start_date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
  end_date: z
    .string()
    .regex(/^\d{4}-\d{2}-\d{2}$/)
    .nullable()
    .optional(),
  prescribed_by: z.string().max(200).trim().optional(),
  instructions: z.string().max(1000).trim().optional(),
  total_quantity: z.number().int().positive().optional(),
  schedules: z.array(ScheduleCreateSchema).min(1).max(10),
});
export type MedicineCreate = z.infer<typeof MedicineCreateSchema>;

/**
 * Medicine update schema — only allowed fields can be modified.
 * Brand name and dosage cannot be changed (create a new medicine instead).
 */
export const MedicineUpdateSchema = z.object({
  instructions: z.string().max(1000).trim().optional(),
  end_date: z
    .string()
    .regex(/^\d{4}-\d{2}-\d{2}$/)
    .nullable()
    .optional(),
  prescribed_by: z.string().max(200).trim().optional(),
  total_quantity: z.number().int().positive().optional(),
});
export type MedicineUpdate = z.infer<typeof MedicineUpdateSchema>;
