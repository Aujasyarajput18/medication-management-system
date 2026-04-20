/** Aujasya — Fasting Mode Type Definitions */

export interface PrayerTimes {
  suhoor: string;
  iftar: string;
  sunrise: string;
  sunset: string;
  source: 'aladhan' | 'sunrise_sunset' | 'static_fallback';
}

export interface ScheduleAdjustment {
  scheduleId: string;
  medicineName: string;
  originalMealAnchor: string;
  adjustedMealAnchor: string;
  reason: string;
  severityLevel: 'info' | 'warning' | 'critical';
  physicianNoteRequired: boolean;
  blocked: boolean;
}

export interface FastingActivationResult {
  fastingProfileId: string;
  fastingType: string;
  adjustments: ScheduleAdjustment[];
  blockedMedications: ScheduleAdjustment[];
  pharmacistReviewed: boolean;
  disclaimer: string;
}

export type FastingType = 'ramadan' | 'karva_chauth' | 'navratri' | 'ekadashi' | 'jain_paryushana' | 'custom';
