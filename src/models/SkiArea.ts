/**
 * Ski Area data models and predefined ski areas
 * Requirements: 7.1 - Five ski area options with metadata
 */

export interface GeographicBounds {
  northEast: { lat: number; lng: number };
  southWest: { lat: number; lng: number };
}

export interface AgentEndpoints {
  hillMetrics: string;
  weather: string;
  equipment: string;
}

export interface SkiArea {
  id: string;
  name: string;
  location: string;
  country: string;
  bounds: GeographicBounds;
  elevation: { min: number; max: number };
  previewImage: string;
  agentEndpoints: AgentEndpoints;
  fisCompatible: boolean; // For future World Cup simulation
}

/**
 * Predefined ski areas as specified in requirements 7.1
 * Five world-renowned ski areas: Chamonix, Whistler, Saint Anton am Arlberg, Zermatt, Copper Mountain
 */
export const PREDEFINED_SKI_AREAS: SkiArea[] = [
  {
    id: 'chamonix',
    name: 'Chamonix',
    location: 'Chamonix-Mont-Blanc',
    country: 'France',
    bounds: {
      northEast: { lat: 45.9237, lng: 6.8694 },
      southWest: { lat: 45.9037, lng: 6.8494 }
    },
    elevation: { min: 1035, max: 3842 },
    previewImage: 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48ZGVmcz48bGluZWFyR3JhZGllbnQgaWQ9ImNoYW1vbml4IiB4MT0iMCUiIHkxPSIwJSIgeDI9IjEwMCUiIHkyPSIxMDAlIj48c3RvcCBvZmZzZXQ9IjAlIiBzdHlsZT0ic3RvcC1jb2xvcjojNGY0NmU1O3N0b3Atb3BhY2l0eToxIiAvPjxzdG9wIG9mZnNldD0iMTAwJSIgc3R5bGU9InN0b3AtY29sb3I6IzdjM2FlZDtzdG9wLW9wYWNpdHk6MSIgLz48L2xpbmVhckdyYWRpZW50PjwvZGVmcz48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSJ1cmwoI2NoYW1vbml4KSIvPjx0ZXh0IHg9IjUwJSIgeT0iNTAlIiBmb250LWZhbWlseT0iQXJpYWwsIHNhbnMtc2VyaWYiIGZvbnQtc2l6ZT0iMjQiIGZpbGw9IndoaXRlIiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBkeT0iLjNlbSI+Q2hhbW9uaXg8L3RleHQ+PC9zdmc+',
    agentEndpoints: {
      hillMetrics: 'http://localhost:8001/hill-metrics',
      weather: 'http://localhost:8002/weather',
      equipment: 'http://localhost:8003/equipment'
    },
    fisCompatible: true
  },
  {
    id: 'whistler',
    name: 'Whistler',
    location: 'Whistler',
    country: 'Canada',
    bounds: {
      northEast: { lat: 50.1163, lng: -122.9574 },
      southWest: { lat: 50.0963, lng: -122.9774 }
    },
    elevation: { min: 652, max: 2284 },
    previewImage: 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48ZGVmcz48bGluZWFyR3JhZGllbnQgaWQ9IndoaXN0bGVyIiB4MT0iMCUiIHkxPSIwJSIgeDI9IjEwMCUiIHkyPSIxMDAlIj48c3RvcCBvZmZzZXQ9IjAlIiBzdHlsZT0ic3RvcC1jb2xvcjojMjJjNTVlO3N0b3Atb3BhY2l0eToxIiAvPjxzdG9wIG9mZnNldD0iMTAwJSIgc3R5bGU9InN0b3AtY29sb3I6IzE2YTM0YTtzdG9wLW9wYWNpdHk6MSIgLz48L2xpbmVhckdyYWRpZW50PjwvZGVmcz48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSJ1cmwoI3doaXN0bGVyKSIvPjx0ZXh0IHg9IjUwJSIgeT0iNTAlIiBmb250LWZhbWlseT0iQXJpYWwsIHNhbnMtc2VyaWYiIGZvbnQtc2l6ZT0iMjQiIGZpbGw9IndoaXRlIiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBkeT0iLjNlbSI+V2hpc3RsZXI8L3RleHQ+PC9zdmc+',
    agentEndpoints: {
      hillMetrics: 'http://localhost:8001/hill-metrics',
      weather: 'http://localhost:8002/weather',
      equipment: 'http://localhost:8003/equipment'
    },
    fisCompatible: true
  },
  {
    id: 'st-anton',
    name: 'Saint Anton am Arlberg',
    location: 'Sankt Anton am Arlberg',
    country: 'Austria',
    bounds: {
      northEast: { lat: 47.1313, lng: 10.2604 },
      southWest: { lat: 47.1113, lng: 10.2404 }
    },
    elevation: { min: 1304, max: 2811 },
    previewImage: 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48ZGVmcz48bGluZWFyR3JhZGllbnQgaWQ9InN0YW50b24iIHgxPSIwJSIgeTE9IjAlIiB4Mj0iMTAwJSIgeTI9IjEwMCUiPjxzdG9wIG9mZnNldD0iMCUiIHN0eWxlPSJzdG9wLWNvbG9yOiNlZjQ0NDQ7c3RvcC1vcGFjaXR5OjEiIC8+PHN0b3Agb2Zmc2V0PSIxMDAlIiBzdHlsZT0ic3RvcC1jb2xvcjojZGMyNjI2O3N0b3Atb3BhY2l0eToxIiAvPjwvbGluZWFyR3JhZGllbnQ+PC9kZWZzPjxyZWN0IHdpZHRoPSIxMDAlIiBoZWlnaHQ9IjEwMCUiIGZpbGw9InVybCgjc3RhbnRvbikiLz48dGV4dCB4PSI1MCUiIHk9IjUwJSIgZm9udC1mYW1pbHk9IkFyaWFsLCBzYW5zLXNlcmlmIiBmb250LXNpemU9IjIwIiBmaWxsPSJ3aGl0ZSIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZHk9Ii4zZW0iPlN0LiBBbnRvbjwvdGV4dD48L3N2Zz4=',
    agentEndpoints: {
      hillMetrics: 'http://localhost:8001/hill-metrics',
      weather: 'http://localhost:8002/weather',
      equipment: 'http://localhost:8003/equipment'
    },
    fisCompatible: true
  },
  {
    id: 'zermatt',
    name: 'Zermatt',
    location: 'Zermatt',
    country: 'Switzerland',
    bounds: {
      northEast: { lat: 45.9770, lng: 7.7492 },
      southWest: { lat: 45.9570, lng: 7.7292 }
    },
    elevation: { min: 1620, max: 3883 },
    previewImage: 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48ZGVmcz48bGluZWFyR3JhZGllbnQgaWQ9Inplcm1hdHQiIHgxPSIwJSIgeTE9IjAlIiB4Mj0iMTAwJSIgeTI9IjEwMCUiPjxzdG9wIG9mZnNldD0iMCUiIHN0eWxlPSJzdG9wLWNvbG9yOiNmOTczMTY7c3RvcC1vcGFjaXR5OjEiIC8+PHN0b3Agb2Zmc2V0PSIxMDAlIiBzdHlsZT0ic3RvcC1jb2xvcjojZWE1ODA2O3N0b3Atb3BhY2l0eToxIiAvPjwvbGluZWFyR3JhZGllbnQ+PC9kZWZzPjxyZWN0IHdpZHRoPSIxMDAlIiBoZWlnaHQ9IjEwMCUiIGZpbGw9InVybCgjemVybWF0dCkiLz48dGV4dCB4PSI1MCUiIHk9IjUwJSIgZm9udC1mYW1pbHk9IkFyaWFsLCBzYW5zLXNlcmlmIiBmb250LXNpemU9IjI0IiBmaWxsPSJ3aGl0ZSIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZHk9Ii4zZW0iPnplcm1hdHQ8L3RleHQ+PC9zdmc+',
    agentEndpoints: {
      hillMetrics: 'http://localhost:8001/hill-metrics',
      weather: 'http://localhost:8002/weather',
      equipment: 'http://localhost:8003/equipment'
    },
    fisCompatible: true
  },
  {
    id: 'copper-mountain',
    name: 'Copper Mountain',
    location: 'Copper Mountain',
    country: 'United States',
    bounds: {
      northEast: { lat: 39.5022, lng: -106.1506 },
      southWest: { lat: 39.4822, lng: -106.1706 }
    },
    elevation: { min: 2926, max: 3962 },
    previewImage: 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48ZGVmcz48bGluZWFyR3JhZGllbnQgaWQ9ImNvcHBlciIgeDE9IjAlIiB5MT0iMCUiIHgyPSIxMDAlIiB5Mj0iMTAwJSI+PHN0b3Agb2Zmc2V0PSIwJSIgc3R5bGU9InN0b3AtY29sb3I6IzU5MTMwYztzdG9wLW9wYWNpdHk6MSIgLz48c3RvcCBvZmZzZXQ9IjEwMCUiIHN0eWxlPSJzdG9wLWNvbG9yOiM5MjQwMGQ7c3RvcC1vcGFjaXR5OjEiIC8+PC9saW5lYXJHcmFkaWVudD48L2RlZnM+PHJlY3Qgd2lkdGg9IjEwMCUiIGhlaWdodD0iMTAwJSIgZmlsbD0idXJsKCNjb3BwZXIpIi8+PHRleHQgeD0iNTAlIiB5PSI1MCUiIGZvbnQtZmFtaWx5PSJBcmlhbCwgc2Fucy1zZXJpZiIgZm9udC1zaXplPSIxOCIgZmlsbD0id2hpdGUiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGR5PSIuM2VtIj5Db3BwZXIgTXRuPC90ZXh0Pjwvc3ZnPg==',
    agentEndpoints: {
      hillMetrics: 'http://localhost:8001/hill-metrics',
      weather: 'http://localhost:8002/weather',
      equipment: 'http://localhost:8003/equipment'
    },
    fisCompatible: true
  }
];

/**
 * Helper function to get ski area by ID
 */
export function getSkiAreaById(id: string): SkiArea | undefined {
  for (const area of PREDEFINED_SKI_AREAS) {
    if (area.id === id) {
      return area;
    }
  }
  return undefined;
}

/**
 * Helper function to get all available ski areas
 */
export function getAvailableSkiAreas(): SkiArea[] {
  return PREDEFINED_SKI_AREAS.slice();
}