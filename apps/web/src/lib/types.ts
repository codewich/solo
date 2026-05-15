export type Pace = "rushed" | "balanced" | "wandering";

export type TravelWindow = {
  id: string;
  start_date: string;
  end_date: string;
  label?: string | null;
  linked_holiday?: string | null;
  status?: "candidate" | "planned" | "archived";
  notes?: string | null;
};

export type PreferenceProfile = {
  pace: Pace;
  climate?: "cool" | "mild" | "warm" | "any";
  budget_sensitivity?: number;
  popularity?: "popular" | "underrated" | "mix";
  interests?: Record<string, number>;
};

export type RecommendationRequest = {
  home_city: string;
  travel_windows: TravelWindow[];
  preferences: PreferenceProfile;
  excluded_destination_ids: string[];
};

export type Destination = {
  id: string;
  city: string;
  country: string;
  tags: string[];
  climate_notes: string;
  caveats: string[];
};

export type Recommendation = {
  travel_window_id: string;
  destination: Destination;
  score: number;
  reasons: string[];
  caveats: string[];
};

export type RecommendationGroup = {
  travel_window: TravelWindow;
  recommendations: Recommendation[];
};
