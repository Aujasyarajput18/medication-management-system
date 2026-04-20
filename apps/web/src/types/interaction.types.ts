/** Aujasya — Drug Interaction Type Definitions */

export interface DrugInfo {
  rxcui: string;
  name: string;
}

export interface InteractionResult {
  drugA: DrugInfo;
  drugB: DrugInfo;
  severity: 'contraindicated' | 'major' | 'moderate' | 'minor';
  description: string;
  recommendation: string;
}

export interface InteractionCheckResult {
  interactions: InteractionResult[];
  criticalCount: number;
  majorCount: number;
}

export type InteractionStatus = 'idle' | 'checking' | 'done' | 'error';
