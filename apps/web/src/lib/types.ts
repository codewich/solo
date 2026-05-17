export type TravelWindow = {
  id: string;
  start_date: string;
  end_date: string;
  label?: string | null;
  status?: "candidate" | "planned" | "archived";
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
  score_breakdown?: {
    climateScore: number;
    attractionScore: number;
    popularityScore: number;
    affordabilityScore: number;
    airQualityScore?: number;
  } | null;
  attraction_count?: number;
  attractionCount?: number;
  best_months_to_visit?: string[];
  top_attractions?: string[];
  summary?: string | null;
  image_url?: string | null;
  imageUrl?: string | null;
  air_quality?: {
    pm25?: number | null;
    pm10?: number | null;
    no2?: number | null;
    summary: string;
    source: string;
    status: "available" | "unavailable";
  } | null;
  airQuality?: {
    pm25?: number | null;
    pm10?: number | null;
    no2?: number | null;
    summary: string;
    source: string;
    status: "available" | "unavailable";
  } | null;
  warning?: string | null;
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
};

export type HomeLocation = Coordinates & {
  city: string;
  country: string;
  admin1?: string | null;
};

export type DestinationIntelligenceRequest = {
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
  hotels: {
    average_nightly_price: number | null;
    median_nightly_price: number | null;
    currency: string | null;
    sample_size: number;
    source: string;
    status: "available" | "unavailable";
  };
  cost_of_living: {
    currency: string;
    meal_inexpensive?: number | null;
    coffee?: number | null;
    local_transport_ticket?: number | null;
    summary: string;
    source: string;
  };
  warnings?: Array<{
    step: string;
    service: string;
    message: string;
  }>;
};
