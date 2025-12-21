// Dutch cities data for onboarding home city selection
// Extracted from Infra/config/cities.yml
// Format: { key: string, name: string, region: string }

export interface DutchCity {
  key: string;
  name: string;
  region: string;
  center_lat?: number;
  center_lng?: number;
}

export const DUTCH_CITIES: DutchCity[] = [
  { key: "bergen_op_zoom", name: "Bergen op Zoom", region: "Noord-Brabant", center_lat: 51.4944756, center_lng: 4.2871541 },
  { key: "breda", name: "Breda", region: "Noord-Brabant", center_lat: 51.593834, center_lng: 4.77983 },
  { key: "den_haag", name: "Den Haag", region: "Zuid-Holland", center_lat: 52.0705, center_lng: 4.3007 },
  { key: "dordrecht", name: "Dordrecht", region: "Zuid-Holland", center_lat: 51.813366281298144, center_lng: 4.668750627398341 },
  { key: "etten_leur", name: "Etten-Leur", region: "Noord-Brabant", center_lat: 51.5692065, center_lng: 4.6360813 },
  { key: "hellevoetsluis", name: "Hellevoetsluis", region: "Zuid-Holland", center_lat: 51.833921, center_lng: 4.1436739 },
  { key: "leiden", name: "Leiden", region: "Zuid-Holland", center_lat: 52.157284, center_lng: 4.493417 },
  { key: "leidschendam_voorburg", name: "Leidschendam-Voorburg", region: "Zuid-Holland", center_lat: 52.080887, center_lng: 4.390966 },
  { key: "roosendaal", name: "Roosendaal", region: "Noord-Brabant", center_lat: 51.533148, center_lng: 4.456128 },
  { key: "rotterdam", name: "Rotterdam", region: "Zuid-Holland" },
  { key: "schiedam", name: "Schiedam", region: "Zuid-Holland", center_lat: 51.918, center_lng: 4.395 },
  { key: "vlaardingen", name: "Vlaardingen", region: "Zuid-Holland", center_lat: 51.912, center_lng: 4.341 },
  { key: "zoetermeer", name: "Zoetermeer", region: "Zuid-Holland", center_lat: 52.0603304035099, center_lng: 4.4925787701747675 },
];

// Helper function to get city by key
export function getCityByKey(key: string): DutchCity | undefined {
  return DUTCH_CITIES.find((c) => c.key === key);
}

// Helper function to get city by name (case-insensitive)
export function getCityByName(name: string): DutchCity | undefined {
  return DUTCH_CITIES.find(
    (c) => c.name.toLowerCase() === name.toLowerCase()
  );
}

// Helper function to get cities by region
export function getCitiesByRegion(region: string): DutchCity[] {
  return DUTCH_CITIES.filter((c) => c.region === region);
}

// Get unique regions
export function getRegions(): string[] {
  return Array.from(new Set(DUTCH_CITIES.map((c) => c.region))).sort();
}




