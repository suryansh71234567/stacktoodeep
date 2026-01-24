// src/utils/distance.ts

export interface LocationData {
  display_name: string;
  lat: string;
  lon: string;
}

// 1. Search Function (Calls OpenStreetMap Free API)
export async function searchLocations(query: string): Promise<LocationData[]> {
  if (!query || query.length < 3) return []; // Don't search for 1-2 chars
  
  try {
    // We restrict results to India using 'countrycodes=in'
    const url = `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query)}&countrycodes=in&limit=5`;
    const response = await fetch(url);
    const data = await response.json();
    return data;
  } catch (error) {
    console.error("Error searching location:", error);
    return [];
  }
}

// 2. Standard Haversine Formula (Calculates distance between two coordinates)
export function calculateHaversineDistance(
  lat1: number, lon1: number, 
  lat2: number, lon2: number
): number {
  const R = 6371; // Earth Radius in km
  const dLat = (lat2 - lat1) * (Math.PI / 180);
  const dLon = (lon2 - lon1) * (Math.PI / 180);
  
  const a = 
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(lat1 * (Math.PI / 180)) * Math.cos(lat2 * (Math.PI / 180)) * Math.sin(dLon / 2) * Math.sin(dLon / 2);
    
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return Math.round(R * c); 
}