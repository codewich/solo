export type SearchMode = "radius" | "rectangle";

export type SearchBounds = {
  west: number;
  south: number;
  east: number;
  north: number;
};

export type TravelWindow = {
  id: string;
  start_date: string;
  end_date: string;
  label?: string | null;
  status?: "candidate" | "planned" | "archived";
  latest_search?: {
    id: string;
    home_city_id: string;
    home_city?: Destination | null;
    radius_km: number;
    search_mode?: SearchMode;
    search_bounds?: SearchBounds | null;
    min_population: number;
    candidate_limit: number;
    result_count: number;
  } | null;
};

export type RecommendationRequest = {
  home_city: string;
  center_latitude?: number;
  center_longitude?: number;
  radius_km?: number;
  min_population?: number;
  candidate_limit?: number;
  region?: string | null;
  q?: string | null;
  travel_windows: TravelWindow[];
  excluded_destination_ids?: string[];
};

export type Destination = {
  id: string;
  city: string;
  country: string;
  timezone?: string | null;
  latitude?: number;
  longitude?: number;
  population?: number | null;
  region?: string | null;
  country_code?: string | null;
};

export type Recommendation = {
  travel_window_id: string;
  destination: Destination;
  score: number;
  reasons: string[];
  caveats: string[];
  status?: "ready" | "error";
  warning?: string | null;
  score_breakdown?: {
    climateScore: number;
    attractionScore: number;
    popularityScore: number;
    airQualityScore?: number;
  } | null;
  attraction_count?: number;
  attractionCount?: number;
  best_months_to_visit?: string[];
  top_attractions?: string[];
  summary?: string | null;
  image_url?: string | null;
  imageUrl?: string | null;
  climate?: {
    average_temperature_c: number | null;
    average_temperature_min_c?: number | null;
    average_temperature_max_c?: number | null;
    precipitation_mm: number | null;
    sunshine_hours: number | null;
    summary: string;
    source: string;
  } | null;
  air_quality?: {
    european_aqi?: number | null;
    us_aqi?: number | null;
    pm25?: number | null;
    pm10?: number | null;
    no2?: number | null;
    summary: string;
    source: string;
    status: "available" | "unavailable";
  } | null;
  airQuality?: {
    european_aqi?: number | null;
    us_aqi?: number | null;
    pm25?: number | null;
    pm10?: number | null;
    no2?: number | null;
    summary: string;
    source: string;
    status: "available" | "unavailable";
  } | null;
};

export type RecommendationGroup = {
  travel_window: TravelWindow;
  recommendations: Recommendation[];
};

export type Coordinates = {
  latitude: number;
  longitude: number;
};

export type CitySuggestion = Coordinates & {
  id: string;
  name: string;
  country: string;
  admin1?: string | null;
  timezone?: string | null;
  country_code?: string | null;
};

export type HomeLocation = Coordinates & {
  city: string;
  country: string;
  admin1?: string | null;
  country_code?: string | null;
};

export type HolidayRegion = {
  country_code: string;
  region_code: string;
  name: string;
};

export type PublicHoliday = {
  date: string;
  name: string;
  country_code: string;
  region_code?: string | null;
  type?: string | null;
};

export type DestinationIntelligenceRequest = {
  city_id?: string;
  destination_city: string;
  country: string;
  latitude: number;
  longitude: number;
  start_date: string;
  end_date: string;
};

export type DestinationIntelligence = {
  destination_city: string;
  country: string;
  climate: {
    average_temperature_c: number | null;
    average_temperature_min_c?: number | null;
    average_temperature_max_c?: number | null;
    precipitation_mm: number | null;
    sunshine_hours: number | null;
    summary: string;
    source: string;
  };
  attractions: Array<{
    name: string;
    category: string;
    latitude?: number | null;
    longitude?: number | null;
    description?: string | null;
    source: string;
  }>;
  warnings?: Array<{
    step: string;
    service: string;
    message: string;
  }>;
};

export type RecommendationSearchCreateRequest = {
  travel_window: TravelWindow;
  home_city_id: string;
  radius_km: number;
  search_mode?: SearchMode;
  search_bounds?: SearchBounds | null;
  min_population: number;
  candidate_limit: number;
  excluded_city_ids?: string[];
  user_email?: string | null;
  user_name?: string | null;
  provider_subject?: string | null;
};

export type TravelWindowDeleteRequest = {
  user_email: string;
  provider_subject?: string | null;
};

export type RecommendationSearchCreateResponse = {
  id: string;
  travel_window_id: string;
  status: "created";
};

export type RecommendationSearchCity = {
  search_id: string;
  destination: Destination;
};

export type NearestCityRequest = Coordinates;
