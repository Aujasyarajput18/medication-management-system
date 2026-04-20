/** Aujasya — Generic Drug Type Definitions */

export interface JanAushadhiKendra {
  name: string;
  address: string;
  distanceKm: number;
  lat: number;
  lng: number;
}

export interface GenericAlternative {
  name: string;
  manufacturer: string;
  mrpPerUnit: number;
  savingsPercent: number;
  janAushadhi: boolean;
  whoGmp: boolean;
  nablCertified: boolean;
  pmbjpCode: string | null;
  bioequivalenceMin: number;
  bioequivalenceMax: number;
  rankingScore: number;
  nearestKendras: JanAushadhiKendra[];
}

export interface BrandInfo {
  name: string;
  mrpPerUnit: number;
  activeIngredient: string;
}

export interface GenericSearchResult {
  brand: BrandInfo;
  alternatives: GenericAlternative[];
}

export type GenericSearchStatus = 'idle' | 'searching' | 'done' | 'error';
