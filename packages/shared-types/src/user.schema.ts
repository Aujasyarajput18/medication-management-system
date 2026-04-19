import { z } from 'zod';

/**
 * Supported languages — ISO 639-1 codes.
 * Default is 'hi' (Hindi) — primary target demographic.
 */
export const LanguageCodeSchema = z.enum(['en', 'hi', 'ta', 'te', 'bn', 'mr']);
export type LanguageCode = z.infer<typeof LanguageCodeSchema>;

/**
 * User roles.
 */
export const UserRoleSchema = z.enum(['patient', 'caregiver']);
export type UserRole = z.infer<typeof UserRoleSchema>;

/**
 * Meal names for user_meal_times configuration.
 */
export const MealNameSchema = z.enum([
  'waking',
  'breakfast',
  'lunch',
  'dinner',
  'bedtime',
]);
export type MealName = z.infer<typeof MealNameSchema>;

/**
 * Indian phone number validation — E.164 format with +91 prefix.
 */
export const IndianPhoneSchema = z
  .string()
  .regex(/^\+91[6-9]\d{9}$/, 'Must be a valid Indian mobile number (+91XXXXXXXXXX)');
export type IndianPhone = z.infer<typeof IndianPhoneSchema>;

/**
 * OTP send request.
 */
export const SendOtpSchema = z.object({
  phone: IndianPhoneSchema,
  purpose: z.enum(['login', 'caregiver_link']),
});
export type SendOtp = z.infer<typeof SendOtpSchema>;

/**
 * OTP verify request.
 */
export const VerifyOtpSchema = z.object({
  session_id: z.string().uuid(),
  otp: z.string().length(6).regex(/^\d{6}$/),
  device_info: z
    .object({
      user_agent: z.string().optional(),
      platform: z.string().optional(),
    })
    .optional(),
});
export type VerifyOtp = z.infer<typeof VerifyOtpSchema>;

/**
 * User profile update.
 */
export const UserProfileUpdateSchema = z.object({
  full_name: z.string().min(1).max(200).trim().optional(),
  date_of_birth: z
    .string()
    .regex(/^\d{4}-\d{2}-\d{2}$/)
    .optional(),
  preferred_language: LanguageCodeSchema.optional(),
});
export type UserProfileUpdate = z.infer<typeof UserProfileUpdateSchema>;

/**
 * Meal time configuration — user's typical daily meal schedule.
 */
export const MealTimeSchema = z.object({
  meal_name: MealNameSchema,
  typical_time: z.string().regex(/^\d{2}:\d{2}$/, 'Format must be HH:MM'),
});
export type MealTime = z.infer<typeof MealTimeSchema>;

/**
 * DPDPA consent purpose codes.
 */
export const ConsentPurposeSchema = z.enum([
  'medication_tracking',
  'caregiver_sharing',
  'whatsapp_alerts',
  'sms_alerts',
  'analytics',
  'ivr_calls',
  'data_export',
]);
export type ConsentPurpose = z.infer<typeof ConsentPurposeSchema>;
