"use client";

import dynamic from "next/dynamic";
import { useEffect, useMemo, useState } from "react";
import { ListChecks, LocateFixed, RotateCcw, X } from "lucide-react";
import { getSession } from "next-auth/react";
import type { Session } from "next-auth";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Calendar } from "@/components/ui/calendar";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Slider } from "@/components/ui/slider";
import { Spinner } from "@/components/ui/spinner";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { DestinationMap } from "./destination-map";
import {
  ApiRequestError,
  createRecommendationSearch,
  deleteTravelWindow,
  fetchCitySuggestions,
  fetchHolidayRegions,
  fetchNearestCity,
  fetchPublicHolidays,
  fetchRecommendationSearchCities,
  fetchRecommendationSearchCityIntelligence,
  fetchTravelWindows,
  fetchSavedRecommendationSearchResults,
  scoreRecommendationSearchCity,
} from "@/lib/api";
import { formatWindowLabel } from "@/lib/date-windows";
import { cn } from "@/lib/utils";
import type { DateRange } from "react-day-picker";
import type {
  CitySuggestion,
  Destination,
  DestinationIntelligence,
  HolidayRegion,
  HomeLocation,
  PublicHoliday,
  Recommendation,
  SearchBounds,
  SearchMode,
  TravelWindow,
} from "@/lib/types";

const AuthButton = dynamic(
  () => import("@/components/auth-button").then((module) => module.AuthButton),
  {
    ssr: false,
    loading: () => (
      <Button type="button" variant="outline" disabled>
        Account
      </Button>
    ),
  },
);

type PlanningWindow = TravelWindow & {
  dates: string;
  label: string;
  status: "candidate" | "planned" | "archived";
};

type DraftRange = {
  start_date: string;
  end_date: string;
};

type SelectedCity = HomeLocation & {
  id: string;
};

type CandidateCard = {
  destination: Destination;
  recommendation?: Recommendation;
  intelligence?: DestinationIntelligence;
  scoreError?: string;
  detailsError?: string;
  scoring: boolean;
  detailsLoading: boolean;
  order: number;
};

function formatSearchBounds(bounds: SearchBounds): string {
  return `${bounds.south.toFixed(2)} to ${bounds.north.toFixed(2)} lat, ${bounds.west.toFixed(
    2,
  )} to ${bounds.east.toFixed(2)} lng`;
}

const defaultHomeCity: SelectedCity = {
  id: "2643743",
  city: "London",
  country: "United Kingdom",
  admin1: "England",
  latitude: 51.5072,
  longitude: -0.1276,
  country_code: "GB",
};

const rangePageSize = 6;

function Pill({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <Badge className={cn("app-pill", className)} variant="outline">
      {children}
    </Badge>
  );
}

function cityFromSuggestion(suggestion: CitySuggestion): SelectedCity {
  return {
    id: suggestion.id,
    city: suggestion.name,
    country: suggestion.country,
    admin1: suggestion.admin1,
    latitude: suggestion.latitude,
    longitude: suggestion.longitude,
    country_code: suggestion.country_code,
  };
}

function padDatePart(value: number): string {
  return String(value).padStart(2, "0");
}

function toLocalIsoDate(date: Date): string {
  return `${date.getFullYear()}-${padDatePart(date.getMonth() + 1)}-${padDatePart(
    date.getDate(),
  )}`;
}

function isoDateToLocalDate(isoDate: string): Date {
  const [year, month, day] = isoDate.split("-").map(Number);
  return new Date(year, month - 1, day);
}

function dateRangeFromTravelRange(range: DraftRange | TravelWindow | null): DateRange | undefined {
  if (!range) {
    return undefined;
  }
  return {
    from: isoDateToLocalDate(range.start_date),
    to: isoDateToLocalDate(range.end_date),
  };
}

function preferredHolidayRegion(regions: HolidayRegion[], admin1?: string | null): string | null {
  if (regions.length === 0) {
    return null;
  }
  const normalizedAdmin = (admin1 ?? "").trim().toLowerCase();
  const match = regions.find((region) => region.name.trim().toLowerCase() === normalizedAdmin);
  return match?.region_code ?? regions[0].region_code;
}

function orderedRange(firstDate: string, secondDate: string): DraftRange {
  return firstDate <= secondDate
    ? { start_date: firstDate, end_date: secondDate }
    : { start_date: secondDate, end_date: firstDate };
}

function planningWindowFromDraft(range: DraftRange, existingWindows: PlanningWindow[]): PlanningWindow {
  const dates = formatWindowLabel(range.start_date, range.end_date);
  const baseId = `range-${Date.now()}`;
  const existingIds = new Set(existingWindows.map((window) => window.id));
  let id = baseId;
  let suffix = 2;

  while (existingIds.has(id)) {
    id = `${baseId}-${suffix}`;
    suffix += 1;
  }

  return {
    id,
    label: dates,
    dates,
    start_date: range.start_date,
    end_date: range.end_date,
    status: "candidate",
  };
}

function planningWindowFromSaved(window: TravelWindow): PlanningWindow {
  const dates = formatWindowLabel(window.start_date, window.end_date);
  return {
    ...window,
    label: window.label ?? dates,
    dates,
    status: window.status ?? "candidate",
  };
}

function errorMessage(reason: unknown, fallback: string): string {
  return reason instanceof ApiRequestError || reason instanceof Error ? reason.message : fallback;
}

async function withRetry<T>(operation: () => Promise<T>, retryCount = 2): Promise<T> {
  let lastError: unknown;
  for (let attempt = 0; attempt <= retryCount; attempt += 1) {
    try {
      return await operation();
    } catch (error) {
      lastError = error;
    }
  }
  throw lastError;
}

function ScoreSkeleton() {
  return <Skeleton className="score-skeleton" aria-label="Loading score" />;
}

function ScoringSkeleton() {
  return (
    <div className="candidate-skeleton-section" aria-label="Loading destination score">
      <Skeleton className="h-4 w-3/4" />
      <Skeleton className="h-4 w-2/3" />
    </div>
  );
}

function DetailSkeleton() {
  return (
    <div className="candidate-skeleton-section" aria-label="Loading destination details">
      <div className="skeleton-chip-row">
        <Skeleton className="h-7 w-24" />
        <Skeleton className="h-7 w-20" />
        <Skeleton className="h-7 w-24" />
      </div>
      <Skeleton className="h-4 w-5/6" />
    </div>
  );
}

function IntelligenceSkeleton() {
  return (
    <div className="candidate-skeleton-section intelligence-skeleton" aria-label="Loading destination intelligence">
      <Skeleton className="h-7 w-32" />
      <Skeleton className="h-4 w-2/5" />
    </div>
  );
}

function AirQualityPill({ recommendation }: { recommendation: Recommendation }) {
  const air = recommendation.air_quality ?? recommendation.airQuality;
  if (!air || air.status === "unavailable") {
    return <Pill className="air-unknown">Air N/A</Pill>;
  }
  if (air.european_aqi !== undefined && air.european_aqi !== null) {
    const label =
      air.european_aqi <= 20 ? "Good air" : air.european_aqi <= 60 ? "Moderate air" : "Poor air";
    const className =
      air.european_aqi <= 20 ? "air-good" : air.european_aqi <= 60 ? "air-moderate" : "air-poor";
    return <Pill className={className}>{label}</Pill>;
  }
  if (air.us_aqi !== undefined && air.us_aqi !== null) {
    const label = air.us_aqi <= 50 ? "Good air" : air.us_aqi <= 150 ? "Moderate air" : "Poor air";
    const className = air.us_aqi <= 50 ? "air-good" : air.us_aqi <= 150 ? "air-moderate" : "air-poor";
    return <Pill className={className}>{label}</Pill>;
  }
  const pm25 = air.pm25 ?? 0;
  const label = pm25 <= 10 ? "Good air" : pm25 <= 25 ? "Moderate air" : "Poor air";
  const className = pm25 <= 10 ? "air-good" : pm25 <= 25 ? "air-moderate" : "air-poor";
  return <Pill className={className}>{label}</Pill>;
}

function AutocompleteLoadingRows() {
  return (
    <>
      <li>
        <Skeleton className="h-8 w-full" />
      </li>
      <li>
        <Skeleton className="h-8 w-5/6" />
      </li>
      <li>
        <Skeleton className="h-8 w-2/3" />
      </li>
    </>
  );
}

function DestinationCandidateCard({
  card,
  onRetryScore,
}: {
  card: CandidateCard;
  onRetryScore: (destination: Destination) => void;
}) {
  const recommendation = card.recommendation;
  const city = card.destination.city;
  const country = card.destination.country;
  const imageUrl = recommendation?.image_url ?? recommendation?.imageUrl;
  const climate = recommendation?.climate ?? card.intelligence?.climate;
  const attractionCount = recommendation?.attraction_count ?? recommendation?.attractionCount;
  const savedAttractions =
    recommendation?.top_attractions?.map((name) => ({
      name,
      category: "attraction",
      description: null,
      source: "Saved recommendation",
    })) ?? [];
  const attractions =
    card.intelligence?.attractions && card.intelligence.attractions.length > 0
      ? card.intelligence.attractions
      : savedAttractions;
  const hasAttractions = attractions.length > 0;
  const cardStyle = imageUrl
    ? {
        backgroundImage: `linear-gradient(rgba(23, 33, 29, 0.72), rgba(23, 33, 29, 0.72)), url(${imageUrl})`,
      }
    : undefined;
  const temperatureRange =
    climate?.average_temperature_min_c !== null &&
    climate?.average_temperature_min_c !== undefined &&
    climate?.average_temperature_max_c !== null &&
    climate?.average_temperature_max_c !== undefined
      ? `${Math.round(climate.average_temperature_min_c)}-${Math.round(
          climate.average_temperature_max_c,
        )}C`
      : climate?.average_temperature_c !== null && climate?.average_temperature_c !== undefined
        ? `${Math.round(climate.average_temperature_c)}C avg`
        : "Temp N/A";
  const rainfall =
    climate?.precipitation_mm !== null && climate?.precipitation_mm !== undefined
      ? `${Math.round(climate.precipitation_mm)} mm rain`
      : "Rain N/A";
  const sunshine =
    climate?.sunshine_hours !== null && climate?.sunshine_hours !== undefined
      ? `${Math.round(climate.sunshine_hours)} h sun`
      : "Sun N/A";

  return (
    <Card
      className={cn("card recommendation-card candidate-result-card", imageUrl ? "has-image" : "")}
      style={cardStyle}
    >
      <CardHeader className="recommendation-card-header">
        <CardTitle>
          {city}, {country}
        </CardTitle>
        {recommendation ? (
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                className="score"
                type="button"
                variant="ghost"
                size="sm"
                aria-label={`Score breakdown for ${city}`}
              >
                {recommendation.score}
              </Button>
            </TooltipTrigger>
            {recommendation.score_breakdown ? (
              <TooltipContent className="score-tooltip-panel">
                <span>Climate: {recommendation.score_breakdown.climateScore}</span>
                <span>Attractions: {recommendation.score_breakdown.attractionScore}</span>
                <span>Popularity: {recommendation.score_breakdown.popularityScore}</span>
                {recommendation.score_breakdown.airQualityScore !== undefined ? (
                  <span>Air: {recommendation.score_breakdown.airQualityScore}</span>
                ) : null}
              </TooltipContent>
            ) : null}
          </Tooltip>
        ) : (
          <ScoreSkeleton />
        )}
      </CardHeader>
      <CardContent className="stack">
        {card.scoreError ? (
          <div className="candidate-card-error">
            <p>{card.scoreError}</p>
            <Button type="button" size="sm" variant="outline" onClick={() => onRetryScore(card.destination)}>
              <RotateCcw data-icon="inline-start" />
              Retry
            </Button>
          </div>
        ) : !recommendation ? (
          <>
            <ScoringSkeleton />
            <DetailSkeleton />
            <IntelligenceSkeleton />
          </>
        ) : (
          <>
            <Tooltip>
              <TooltipTrigger asChild>
                <p className="muted recommendation-description">{recommendation.summary ?? recommendation.reasons[0]}</p>
              </TooltipTrigger>
              <TooltipContent className="recommendation-summary-tooltip">
                {recommendation.summary ?? recommendation.reasons[0]}
              </TooltipContent>
            </Tooltip>
            {card.scoring ? <ScoringSkeleton /> : null}
            {card.detailsLoading ? (
              <DetailSkeleton />
            ) : (
              <div className="badge-row">
                <Dialog>
                  <DialogTrigger asChild>
                    <Button
                      className="app-pill attraction-pill"
                      type="button"
                      variant="outline"
                      size="sm"
                      disabled={!hasAttractions}
                    >
                      <ListChecks data-icon="inline-start" />
                      {hasAttractions
                        ? `${attractionCount ?? attractions.length} attractions nearby`
                        : "Attractions N/A"}
                    </Button>
                  </DialogTrigger>
                  <DialogContent>
                    <DialogHeader>
                      <DialogTitle>
                        Attractions near {city}, {country}
                      </DialogTitle>
                      <DialogDescription>
                        Nearby places from the destination intelligence lookup.
                      </DialogDescription>
                    </DialogHeader>
                    <div className="attraction-list">
                      {attractions.map((attraction) => (
                        <div className="attraction-list-item" key={`${attraction.name}-${attraction.source}`}>
                          <strong>{attraction.name}</strong>
                          <span>{attraction.category}</span>
                          {attraction.description ? <p>{attraction.description}</p> : null}
                        </div>
                      ))}
                    </div>
                  </DialogContent>
                </Dialog>
                <Pill>{temperatureRange}</Pill>
                <Pill>{rainfall}</Pill>
                <Pill>{sunshine}</Pill>
                <AirQualityPill recommendation={recommendation} />
              </div>
            )}
            {card.detailsLoading ? (
              <IntelligenceSkeleton />
            ) : null}
          </>
        )}
      </CardContent>
    </Card>
  );
}

export default function Page() {
  const [session, setSession] = useState<Session | null>(null);
  const [isSessionLoaded, setIsSessionLoaded] = useState(false);
  const [homeLocation, setHomeLocation] = useState<SelectedCity>(defaultHomeCity);
  const [homeQuery, setHomeQuery] = useState(defaultHomeCity.city);
  const [homeSuggestions, setHomeSuggestions] = useState<CitySuggestion[]>([]);
  const [isHomeSuggesting, setIsHomeSuggesting] = useState(false);
  const [travelWindows, setTravelWindows] = useState<PlanningWindow[]>([]);
  const [selectedTravelWindowId, setSelectedTravelWindowId] = useState<string | null>(null);
  const [visibleCalendarMonth, setVisibleCalendarMonth] = useState(() => new Date(2026, 4, 1));
  const [isAddingRange, setIsAddingRange] = useState(false);
  const [draftRange, setDraftRange] = useState<DraftRange | null>(null);
  const [isDraftComplete, setIsDraftComplete] = useState(false);
  const [rangePageIndex, setRangePageIndex] = useState(0);
  const [editingWindowId, setEditingWindowId] = useState<string | null>(null);
  const [editingLabel, setEditingLabel] = useState("");
  const [radiusKm, setRadiusKm] = useState(1800);
  const [searchMode, setSearchMode] = useState<SearchMode>("radius");
  const [searchBounds, setSearchBounds] = useState<SearchBounds | null>(null);
  const [isDrawingRectangle, setIsDrawingRectangle] = useState(false);
  const [minPopulation, setMinPopulation] = useState(250000);
  const [status, setStatus] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const [buttonProgressLabel, setButtonProgressLabel] = useState("Find destinations");
  const [candidateCards, setCandidateCards] = useState<CandidateCard[]>([]);
  const [activeSearchId, setActiveSearchId] = useState<string | null>(null);
  const [excludedCities, setExcludedCities] = useState<CitySuggestion[]>([]);
  const [excludedQuery, setExcludedQuery] = useState("");
  const [excludedSuggestions, setExcludedSuggestions] = useState<CitySuggestion[]>([]);
  const [isExcludedSuggesting, setIsExcludedSuggesting] = useState(false);
  const [holidayRegions, setHolidayRegions] = useState<HolidayRegion[]>([]);
  const [selectedHolidayRegion, setSelectedHolidayRegion] = useState<string | null>(null);
  const [publicHolidays, setPublicHolidays] = useState<PublicHoliday[]>([]);

  const homeCity = homeLocation.city;
  const isSignedIn = Boolean(session?.user);
  const canManageTravelWindows = isSessionLoaded && isSignedIn;
  const selectedTravelWindow = selectedTravelWindowId
    ? travelWindows.find((window) => window.id === selectedTravelWindowId) ?? null
    : null;
  const rangePageCount = Math.max(1, Math.ceil(travelWindows.length / rangePageSize));
  const visibleTravelWindows = travelWindows.slice(
    rangePageIndex * rangePageSize,
    rangePageIndex * rangePageSize + rangePageSize,
  );
  const activeRange = draftRange ?? selectedTravelWindow;
  const visibleCalendarDateRange = useMemo(() => {
    if (!activeRange) {
      return undefined;
    }
    if (draftRange && !isDraftComplete) {
      return { from: isoDateToLocalDate(draftRange.start_date) };
    }
    return dateRangeFromTravelRange(activeRange);
  }, [activeRange, draftRange, isDraftComplete]);
  const holidayDates = useMemo(
    () => publicHolidays.map((holiday) => isoDateToLocalDate(holiday.date)),
    [publicHolidays],
  );
  const holidayLabels = useMemo(
    () => Object.fromEntries(publicHolidays.map((holiday) => [holiday.date, holiday.name])),
    [publicHolidays],
  );
  const sortedCandidateCards = useMemo(
    () =>
      [...candidateCards].sort((left, right) => {
        if (left.recommendation && right.recommendation) {
          return right.recommendation.score - left.recommendation.score;
        }
        if (left.recommendation) {
          return -1;
        }
        if (right.recommendation) {
          return 1;
        }
        return left.order - right.order;
      }),
    [candidateCards],
  );
  const mapDestinations = useMemo(
    () =>
      sortedCandidateCards.map((card) => ({
        city: card.destination.city,
        country: card.destination.country,
        score: card.recommendation?.score,
        summary: card.recommendation?.reasons[0],
        coordinates:
          typeof card.destination.longitude === "number" && typeof card.destination.latitude === "number"
            ? ([card.destination.longitude, card.destination.latitude] as [number, number])
            : undefined,
      })),
    [sortedCandidateCards],
  );

  useEffect(() => {
    let isActive = true;

    getSession()
      .then((nextSession) => {
        if (!isActive) {
          return;
        }
        setSession(nextSession);
        setIsSessionLoaded(true);
        if (!nextSession?.user) {
          setTravelWindows([]);
          setSelectedTravelWindowId(null);
          setDraftRange(null);
          setIsDraftComplete(false);
          setIsAddingRange(false);
          setCandidateCards([]);
          setStatus("idle");
        }
        if (nextSession?.user?.email) {
          void fetchTravelWindows({
            userEmail: nextSession.user.email,
            providerSubject: nextSession.user.email,
          })
            .then((savedWindows) => {
              if (!isActive) {
                return;
              }
              setTravelWindows(savedWindows.map(planningWindowFromSaved));
              setSelectedTravelWindowId((currentSelectedId) =>
                currentSelectedId && savedWindows.some((window) => window.id === currentSelectedId)
                  ? currentSelectedId
                  : null,
              );
            })
            .catch((reason) => {
              if (isActive) {
                showPersistentError(errorMessage(reason, "Could not load saved travel windows."));
              }
            });
        }
      })
      .catch(() => {
        if (!isActive) {
          return;
        }
        setSession(null);
        setIsSessionLoaded(true);
        setTravelWindows([]);
        setSelectedTravelWindowId(null);
        setDraftRange(null);
        setIsDraftComplete(false);
        setIsAddingRange(false);
        setCandidateCards([]);
        setStatus("idle");
      });

    return () => {
      isActive = false;
    };
  }, []);

  useEffect(() => {
    setRangePageIndex((currentPage) => Math.min(currentPage, rangePageCount - 1));
  }, [rangePageCount]);

  useEffect(() => {
    const countryCode = homeLocation.country_code;
    if (!countryCode) {
      setHolidayRegions([]);
      setSelectedHolidayRegion(null);
      setPublicHolidays([]);
      return;
    }

    let isActive = true;
    fetchHolidayRegions(countryCode)
      .then((regions) => {
        if (!isActive) {
          return;
        }
        setHolidayRegions(regions);
        setSelectedHolidayRegion(preferredHolidayRegion(regions, homeLocation.admin1));
      })
      .catch(() => {
        if (!isActive) {
          return;
        }
        setHolidayRegions([]);
        setSelectedHolidayRegion(null);
        showPersistentError("Could not load holiday regions.");
      });

    return () => {
      isActive = false;
    };
  }, [homeLocation.admin1, homeLocation.country_code]);

  useEffect(() => {
    const countryCode = homeLocation.country_code;
    if (!countryCode) {
      setPublicHolidays([]);
      return;
    }

    let isActive = true;
    fetchPublicHolidays({
      countryCode,
      year: visibleCalendarMonth.getFullYear(),
      regionCode: selectedHolidayRegion,
    })
      .then((holidays) => {
        if (isActive) {
          setPublicHolidays(holidays);
        }
      })
      .catch((reason) => {
        if (isActive) {
          setPublicHolidays([]);
          showPersistentError(errorMessage(reason, "Could not load public holidays."));
        }
      });

    return () => {
      isActive = false;
    };
  }, [homeLocation.country_code, selectedHolidayRegion, visibleCalendarMonth]);

  useEffect(() => {
    const query = homeQuery.trim();
    if (query.length < 2 || query === homeLocation.city) {
      setHomeSuggestions([]);
      setIsHomeSuggesting(false);
      return undefined;
    }
    setIsHomeSuggesting(true);
    const timer = window.setTimeout(() => {
      void fetchCitySuggestions(query)
        .then(setHomeSuggestions)
        .catch(() => setHomeSuggestions([]))
        .finally(() => setIsHomeSuggesting(false));
    }, 180);
    return () => window.clearTimeout(timer);
  }, [homeLocation.city, homeQuery]);

  useEffect(() => {
    const query = excludedQuery.trim();
    if (query.length < 2) {
      setExcludedSuggestions([]);
      setIsExcludedSuggesting(false);
      return undefined;
    }
    setIsExcludedSuggesting(true);
    const timer = window.setTimeout(() => {
      void fetchCitySuggestions(query)
        .then((suggestions) =>
          setExcludedSuggestions(
            suggestions.filter(
              (suggestion) =>
                suggestion.id !== homeLocation.id &&
                !excludedCities.some((city) => city.id === suggestion.id),
            ),
          ),
        )
        .catch(() => setExcludedSuggestions([]))
        .finally(() => setIsExcludedSuggesting(false));
    }, 180);
    return () => window.clearTimeout(timer);
  }, [excludedCities, excludedQuery, homeLocation.id]);

  function showMonthForDate(isoDate: string) {
    const date = isoDateToLocalDate(isoDate);
    setVisibleCalendarMonth(new Date(date.getFullYear(), date.getMonth(), 1));
  }

  function showPersistentError(message: string) {
    toast.error(message, {
      closeButton: true,
      duration: Infinity,
    });
  }

  async function scoreCity(searchId: string, destination: Destination) {
    setCandidateCards((cards) =>
      cards.map((card) =>
        card.destination.id === destination.id
          ? { ...card, scoring: true, scoreError: undefined }
          : card,
      ),
    );
    try {
      const recommendation = await withRetry(
        () => scoreRecommendationSearchCity(searchId, destination.id),
        2,
      );
      setCandidateCards((cards) =>
        cards.map((card) =>
          card.destination.id === destination.id
            ? { ...card, recommendation, scoring: false, scoreError: undefined }
            : card,
        ),
      );
      return recommendation;
    } catch (reason) {
      const message = errorMessage(reason, `Could not score ${destination.city}.`);
      setCandidateCards((cards) =>
        cards.map((card) =>
          card.destination.id === destination.id
            ? { ...card, scoring: false, scoreError: message }
            : card,
        ),
      );
      return null;
    }
  }

  async function loadCityDetails(searchId: string, destination: Destination) {
    setCandidateCards((cards) =>
      cards.map((card) =>
        card.destination.id === destination.id
          ? { ...card, detailsLoading: true, detailsError: undefined }
          : card,
      ),
    );
    try {
      const intelligence = await withRetry(
        () => fetchRecommendationSearchCityIntelligence(searchId, destination.id),
        2,
      );
      setCandidateCards((cards) =>
        cards.map((card) =>
          card.destination.id === destination.id
            ? { ...card, intelligence, detailsLoading: false, detailsError: undefined }
            : card,
        ),
      );
    } catch (reason) {
      setCandidateCards((cards) =>
        cards.map((card) =>
          card.destination.id === destination.id
            ? {
                ...card,
                detailsLoading: false,
                detailsError: errorMessage(reason, `Could not load details for ${destination.city}.`),
              }
            : card,
        ),
      );
    }
  }

  async function loadSavedResultsForWindow(window: PlanningWindow) {
    const searchId = window.latest_search?.id;
    if (!searchId || (window.latest_search?.result_count ?? 0) <= 0) {
      setCandidateCards([]);
      setActiveSearchId(null);
      return;
    }

    setStatus("loading");
    setButtonProgressLabel("Loading saved results...");
    setCandidateCards([]);
    setActiveSearchId(searchId);

    try {
      const savedResults = await fetchSavedRecommendationSearchResults(searchId);
      setCandidateCards(
        savedResults.map((recommendation, order) => ({
          destination: recommendation.destination,
          recommendation,
          scoring: false,
          detailsLoading: true,
          order,
        })),
      );
      await Promise.allSettled(
        savedResults.map((recommendation) =>
          loadCityDetails(searchId, recommendation.destination),
        ),
      );
      setStatus("ready");
    } catch (reason) {
      setStatus("error");
      showPersistentError(errorMessage(reason, "Could not load saved recommendations."));
    } finally {
      setButtonProgressLabel("Find destinations");
    }
  }

  function handleTravelWindowSelect(window: PlanningWindow) {
    if (status === "loading") {
      return;
    }
    setSelectedTravelWindowId(window.id);
    setSearchMode(window.latest_search?.search_mode ?? "radius");
    setSearchBounds(window.latest_search?.search_bounds ?? null);
    if (window.latest_search?.home_city) {
      const savedHomeCity = window.latest_search.home_city;
      const nextHome = {
        id: savedHomeCity.id,
        city: savedHomeCity.city,
        country: savedHomeCity.country,
        admin1: savedHomeCity.region,
        latitude: savedHomeCity.latitude ?? defaultHomeCity.latitude,
        longitude: savedHomeCity.longitude ?? defaultHomeCity.longitude,
        country_code: savedHomeCity.country_code,
      };
      setHomeLocation(nextHome);
      setHomeQuery(nextHome.city);
      setHomeSuggestions([]);
    }
    if (window.latest_search?.radius_km) {
      setRadiusKm(window.latest_search.radius_km);
    }
    if (window.latest_search?.min_population !== undefined) {
      setMinPopulation(window.latest_search.min_population);
    }
    setIsDrawingRectangle(false);
    showMonthForDate(window.start_date);
    setIsAddingRange(false);
    setDraftRange(null);
    setIsDraftComplete(false);
    void loadSavedResultsForWindow(window);
  }

  async function handleFindDestinations() {
    if (!canManageTravelWindows) {
      showPersistentError("Sign in to save travel windows and find destinations.");
      return;
    }

    const isSavingDraftRange = draftRange !== null && isDraftComplete;
    const targetWindow = isSavingDraftRange
      ? planningWindowFromDraft(draftRange, travelWindows)
      : selectedTravelWindow;

    if (!targetWindow) {
      return;
    }

    if (searchMode === "rectangle" && !searchBounds) {
      showPersistentError("Draw a rectangle on the map before finding destinations.");
      return;
    }

    if (isSavingDraftRange) {
      setTravelWindows((currentWindows) => [...currentWindows, targetWindow]);
      setSelectedTravelWindowId(targetWindow.id);
      setDraftRange(null);
      setIsDraftComplete(false);
      setIsAddingRange(false);
    }

    setStatus("loading");
    setButtonProgressLabel("Creating search...");
    setCandidateCards([]);
    setActiveSearchId(null);

    try {
      const search = await createRecommendationSearch({
        travel_window: {
          id: targetWindow.id,
          label: targetWindow.label,
          start_date: targetWindow.start_date,
          end_date: targetWindow.end_date,
          status: targetWindow.status,
        },
        home_city_id: homeLocation.id,
        radius_km: radiusKm,
        search_mode: searchMode,
        search_bounds: searchMode === "rectangle" ? searchBounds : null,
        min_population: minPopulation,
        candidate_limit: 10,
        excluded_city_ids: [homeLocation.id, ...excludedCities.map((city) => city.id)],
        user_email: session?.user?.email ?? null,
        user_name: session?.user?.name ?? null,
        provider_subject: session?.user?.email ?? null,
      });
      setActiveSearchId(search.id);

      const savedResults = await fetchSavedRecommendationSearchResults(search.id);
      if (savedResults.length > 0) {
        setCandidateCards(
          savedResults.map((recommendation, order) => ({
            destination: recommendation.destination,
            recommendation,
            scoring: false,
            detailsLoading: true,
            order,
          })),
        );
        await Promise.allSettled(
          savedResults.map((recommendation) =>
            loadCityDetails(search.id, recommendation.destination),
          ),
        );
        setButtonProgressLabel("Find destinations");
        setStatus("ready");
        return;
      }

      setButtonProgressLabel("Loading list of cities...");
      const cities = await fetchRecommendationSearchCities(search.id);
      setCandidateCards(
        cities.map((city, order) => ({
          destination: city.destination,
          scoring: true,
          detailsLoading: true,
          order,
        })),
      );

      let scoredCount = 0;
      setButtonProgressLabel(`Scoring cities (0/${cities.length})...`);
      const scoreTasks = cities.map(async ({ destination }) => {
        const result = await scoreCity(search.id, destination);
        scoredCount += 1;
        setButtonProgressLabel(`Scoring cities (${scoredCount}/${cities.length})...`);
        return result;
      });

      let detailsCount = 0;
      const detailTasks = cities.map(async ({ destination }) => {
        await loadCityDetails(search.id, destination);
        detailsCount += 1;
        setButtonProgressLabel(`Loading details (${detailsCount}/${cities.length})...`);
      });

      await Promise.allSettled([...scoreTasks, ...detailTasks]);
      setButtonProgressLabel("Find destinations");
      setStatus("ready");
    } catch (reason) {
      setStatus("error");
      setButtonProgressLabel("Find destinations");
      showPersistentError(errorMessage(reason, "Could not load recommendations."));
    }
  }

  function handleCalendarRangeSelect(range: DateRange | undefined) {
    if (!canManageTravelWindows || !isAddingRange || status === "loading") {
      return;
    }
    if (!range?.from) {
      setDraftRange(null);
      setIsDraftComplete(false);
      return;
    }
    const startDate = toLocalIsoDate(range.from);
    const endDate = range.to ? toLocalIsoDate(range.to) : startDate;
    setDraftRange(orderedRange(startDate, endDate));
    setIsDraftComplete(Boolean(range.to));
  }

  function handleRangeButtonClick() {
    if (!canManageTravelWindows || status === "loading") {
      return;
    }
    if (!isAddingRange) {
      setIsAddingRange(true);
      setDraftRange(null);
      setIsDraftComplete(false);
      setSelectedTravelWindowId(null);
      setIsDrawingRectangle(false);
      return;
    }
    if (!draftRange || !isDraftComplete) {
      return;
    }
    const newWindow = planningWindowFromDraft(draftRange, travelWindows);
    setTravelWindows((currentWindows) => [...currentWindows, newWindow]);
    setSelectedTravelWindowId(newWindow.id);
    setDraftRange(null);
    setIsDraftComplete(false);
    setIsAddingRange(false);
  }

  function handleCancelRange() {
    setIsAddingRange(false);
    setDraftRange(null);
    setIsDraftComplete(false);
  }

  function handleSaveRename() {
    const trimmedLabel = editingLabel.trim();
    if (!editingWindowId || trimmedLabel.length === 0) {
      return;
    }
    setTravelWindows((currentWindows) =>
      currentWindows.map((window) =>
        window.id === editingWindowId ? { ...window, label: trimmedLabel } : window,
      ),
    );
    setEditingWindowId(null);
    setEditingLabel("");
  }

  async function handleRemoveTravelWindow(windowId: string) {
    const userEmail = session?.user?.email;
    if (!userEmail) {
      showPersistentError("Sign in to remove saved travel windows.");
      return;
    }

    const previousWindows = travelWindows;
    setTravelWindows((currentWindows) => currentWindows.filter((item) => item.id !== windowId));
    if (selectedTravelWindowId === windowId) {
      setSelectedTravelWindowId(null);
      setCandidateCards([]);
      setActiveSearchId(null);
    }

    try {
      await deleteTravelWindow(windowId, {
        user_email: userEmail,
        provider_subject: userEmail,
      });
    } catch (reason) {
      setTravelWindows(previousWindows);
      showPersistentError(errorMessage(reason, "Could not remove travel window."));
    }
  }

  async function handleUseCurrentLocation() {
    if (!navigator.geolocation) {
      showPersistentError("Current location is not available in this browser.");
      return;
    }
    navigator.geolocation.getCurrentPosition(
      async (position) => {
        try {
          const nearest = await fetchNearestCity({
            latitude: position.coords.latitude,
            longitude: position.coords.longitude,
          });
          const nextHome = cityFromSuggestion(nearest);
          setHomeLocation(nextHome);
          setHomeQuery(nextHome.city);
          setHomeSuggestions([]);
          setIsDrawingRectangle(false);
        } catch (reason) {
          showPersistentError(errorMessage(reason, "Could not find the nearest city."));
        }
      },
      () => showPersistentError("Could not read your current location."),
    );
  }

  return (
    <TooltipProvider>
      <main>
        <header className="topbar">
          <div className="brand">
            <h1>Solo</h1>
            <span className="caption">Long-weekend map planner</span>
          </div>
          <div className="topbar-actions">
            <div className="home-city-picker">
              <Label className="sr-only" htmlFor="home-city">
                Home city
              </Label>
              <Input
                id="home-city"
                aria-label="Home city"
                value={homeQuery}
                disabled={status === "loading"}
                onChange={(event) => setHomeQuery(event.target.value)}
              />
              {homeQuery.trim().length >= 2 && homeQuery.trim() !== homeLocation.city && (isHomeSuggesting || homeSuggestions.length > 0) ? (
                <ul className="autocomplete-list home-city-results" aria-label="Home city suggestions">
                  {isHomeSuggesting ? (
                    <AutocompleteLoadingRows />
                  ) : (
                    homeSuggestions.map((suggestion) => (
                      <li key={suggestion.id}>
                        <button
                          className="autocomplete-option"
                          type="button"
                          onClick={() => {
                            const nextHome = cityFromSuggestion(suggestion);
                            setHomeLocation(nextHome);
                            setHomeQuery(nextHome.city);
                            setHomeSuggestions([]);
                            setIsDrawingRectangle(false);
                          }}
                        >
                          {suggestion.name}, {suggestion.country}
                        </button>
                      </li>
                    ))
                  )}
                </ul>
              ) : null}
            </div>
            <Button type="button" variant="outline" size="icon" aria-label="Use current location" onClick={handleUseCurrentLocation}>
              <LocateFixed />
            </Button>
            <AuthButton />
          </div>
        </header>

        <section className="workspace">
          <aside className="panel stack">
            <div>
              <h2>Pick travel windows</h2>
              <p className="muted">
                Bank holidays are highlighted. Select a window and compare destination fit.
              </p>
            </div>

            <Card className="card stack">
              <CardContent className="stack">
                <div className="calendar-card-header">
                  <Pill>Public holidays</Pill>
                  {holidayRegions.length > 1 ? (
                    <Label className="holiday-region-control">
                      <span className="sr-only">Holiday region</span>
                      <select
                        aria-label="Holiday region"
                        className="holiday-region-select"
                        value={selectedHolidayRegion ?? ""}
                        onChange={(event) => setSelectedHolidayRegion(event.target.value || null)}
                      >
                        {holidayRegions.map((region) => (
                          <option key={region.region_code} value={region.region_code}>
                            {region.name}
                          </option>
                        ))}
                      </select>
                    </Label>
                  ) : null}
                </div>
                <Calendar
                  mode="range"
                  month={visibleCalendarMonth}
                  onMonthChange={setVisibleCalendarMonth}
                  selected={visibleCalendarDateRange}
                  onSelect={handleCalendarRangeSelect}
                  disabled={!canManageTravelWindows || status === "loading"}
                  modifiers={{ holiday: holidayDates }}
                  holidayLabels={holidayLabels}
                  labels={{
                    labelNext: () => "Next month",
                    labelPrevious: () => "Previous month",
                  }}
                  weekStartsOn={1}
                  className="travel-calendar"
                />
                {draftRange ? (
                  <p className="muted">
                    Draft range: {formatWindowLabel(draftRange.start_date, draftRange.end_date)}
                  </p>
                ) : isAddingRange ? (
                  <p className="muted">Pick a start date, then an end date.</p>
                ) : null}
              </CardContent>
            </Card>

            <Card className="card stack">
              <CardHeader className="card-heading-row">
                <CardTitle>Candidate travel windows</CardTitle>
                <div className="range-create-actions">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    disabled={
                      !canManageTravelWindows ||
                      status === "loading" ||
                      (isAddingRange && !isDraftComplete)
                    }
                    onClick={handleRangeButtonClick}
                  >
                    {isAddingRange ? "Save draft range" : "Add range"}
                  </Button>
                  {isAddingRange ? (
                    <Button variant="outline" size="sm" type="button" disabled={!canManageTravelWindows || status === "loading"} onClick={handleCancelRange}>
                      Cancel range
                    </Button>
                  ) : null}
                </div>
              </CardHeader>
              <CardContent className="stack">
                {canManageTravelWindows ? (
                  <>
                    <Badge className="score-badge" variant="secondary">
                      {travelWindows.length} {travelWindows.length === 1 ? "range" : "ranges"}
                    </Badge>
                    <div className="range-list" aria-label="Candidate range list">
                      {visibleTravelWindows.map((window) => {
                        const isSelected = window.id === selectedTravelWindowId;
                        return (
                          <div className="range-item" key={window.id}>
                            <Button
                              aria-pressed={isSelected}
                              className={cn(
                                "range-button h-auto min-h-24 w-full shrink-0 justify-stretch whitespace-normal px-3 py-3 text-left",
                                isSelected && "active",
                              )}
                              type="button"
                              variant="outline"
                              disabled={status === "loading"}
                              aria-label={`Select ${window.label}`}
                              onClick={() => handleTravelWindowSelect(window)}
                            >
                              <span>
                                <strong>{window.dates}</strong>
                              </span>
                              <span>
                                <Pill>{window.status}</Pill>
                              </span>
                            </Button>
                            {editingWindowId === window.id ? (
                              <div className="range-editor">
                                <div className="field-stack">
                                  <Label htmlFor={`range-label-${window.id}`}>Range label</Label>
                                  <Input
                                    id={`range-label-${window.id}`}
                                    value={editingLabel}
                                    onChange={(event) => setEditingLabel(event.target.value)}
                                  />
                                </div>
                                <Button variant="outline" size="sm" type="button" onClick={handleSaveRename}>
                                  Save range
                                </Button>
                              </div>
                            ) : (
                              <div className="range-actions">
                                <Button
                                  type="button"
                                  variant="outline"
                                  size="sm"
                                  disabled={status === "loading"}
                                  aria-label={`Rename ${window.label}`}
                                  onClick={() => {
                                    setEditingWindowId(window.id);
                                    setEditingLabel(window.label);
                                  }}
                                >
                                  Rename
                                </Button>
                                <Button
                                  type="button"
                                  variant="outline"
                                  size="sm"
                                  disabled={status === "loading"}
                                  aria-label={`Archive ${window.label}`}
                                  onClick={() =>
                                    setTravelWindows((currentWindows) =>
                                      currentWindows.map((item) =>
                                        item.id === window.id
                                          ? {
                                              ...item,
                                              status: item.status === "archived" ? "candidate" : "archived",
                                            }
                                          : item,
                                      ),
                                    )
                                  }
                                >
                                  Archive
                                </Button>
                                <Button
                                  type="button"
                                  variant="destructive"
                                  size="sm"
                                  disabled={status === "loading"}
                                  aria-label={`Remove ${window.label}`}
                                  onClick={() => void handleRemoveTravelWindow(window.id)}
                                >
                                  Remove
                                </Button>
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </>
                ) : (
                  <p className="muted">Sign in to add and save travel windows.</p>
                )}
                {rangePageCount > 1 ? (
                  <div className="pagination-controls">
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      disabled={!canManageTravelWindows || status === "loading" || rangePageIndex === 0}
                      onClick={() => setRangePageIndex((currentPage) => Math.max(0, currentPage - 1))}
                    >
                      Previous ranges
                    </Button>
                    <span className="muted">
                      Page {rangePageIndex + 1} of {rangePageCount}
                    </span>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      disabled={!canManageTravelWindows || status === "loading" || rangePageIndex >= rangePageCount - 1}
                      onClick={() =>
                        setRangePageIndex((currentPage) =>
                          Math.min(rangePageCount - 1, currentPage + 1),
                        )
                      }
                    >
                      Next ranges
                    </Button>
                  </div>
                ) : null}
              </CardContent>
            </Card>

            <Card className="card stack">
              <CardHeader>
                <CardTitle>Search area</CardTitle>
              </CardHeader>
              <CardContent className="stack">
                <div className="search-mode-toggle" aria-label="Search mode">
                  <Button
                    type="button"
                    variant={searchMode === "radius" ? "default" : "outline"}
                    disabled={status === "loading"}
                    aria-pressed={searchMode === "radius"}
                    onClick={() => {
                      setSearchMode("radius");
                      setIsDrawingRectangle(false);
                    }}
                  >
                    Radius
                  </Button>
                  <Button
                    type="button"
                    variant={searchMode === "rectangle" ? "default" : "outline"}
                    disabled={status === "loading"}
                    aria-pressed={searchMode === "rectangle"}
                    onClick={() => setSearchMode("rectangle")}
                  >
                    Rectangle
                  </Button>
                </div>
                {searchMode === "radius" ? (
                  <div className="field-stack">
                    <Label htmlFor="search-radius">Search radius: {radiusKm} km</Label>
                    <Slider
                      id="search-radius"
                      aria-label="Search radius"
                      min={100}
                      max={5000}
                      step={100}
                      disabled={status === "loading"}
                      value={[radiusKm]}
                      onValueChange={([nextRadius]) => setRadiusKm(nextRadius)}
                    />
                  </div>
                ) : (
                  <div className="field-stack rectangle-search-controls">
                    <div className="rectangle-action-row">
                      <Button
                        type="button"
                        variant={isDrawingRectangle ? "default" : "outline"}
                        disabled={status === "loading"}
                        onClick={() => setIsDrawingRectangle(true)}
                      >
                        {searchBounds ? "Redraw rectangle" : "Draw rectangle"}
                      </Button>
                      <Button
                        type="button"
                        variant="outline"
                        disabled={status === "loading" || !searchBounds}
                        onClick={() => {
                          setSearchBounds(null);
                          setIsDrawingRectangle(false);
                        }}
                      >
                        Clear
                      </Button>
                    </div>
                    <p className="muted">
                      {searchBounds
                        ? `Area selected: ${formatSearchBounds(searchBounds)}`
                        : isDrawingRectangle
                          ? "Drag on the map to select a rectangular search area."
                          : "Draw a rectangle on the map. Radius is not used in this mode."}
                    </p>
                  </div>
                )}
                <div className="field-stack">
                  <Label htmlFor="minimum-population">Minimum population</Label>
                  <Input
                    id="minimum-population"
                    aria-label="Minimum population"
                    min={0}
                    step={50000}
                    type="number"
                    disabled={status === "loading"}
                    value={minPopulation}
                    onChange={(event) => setMinPopulation(Number(event.target.value))}
                  />
                </div>
                <div className="field-stack autocomplete-field">
                  <Label htmlFor="excluded-city">Exclude cities</Label>
                  <Input
                    id="excluded-city"
                    aria-label="Exclude cities"
                    aria-controls="excluded-city-suggestions"
                    aria-expanded={excludedQuery.trim().length >= 2 && (isExcludedSuggesting || excludedSuggestions.length > 0)}
                    role="combobox"
                    value={excludedQuery}
                    disabled={status === "loading"}
                    onChange={(event) => setExcludedQuery(event.target.value)}
                  />
                  {excludedQuery.trim().length >= 2 && (isExcludedSuggesting || excludedSuggestions.length > 0) ? (
                    <ul
                      className="autocomplete-list excluded-city-results"
                      id="excluded-city-suggestions"
                      aria-label="Excluded city suggestions"
                    >
                      {isExcludedSuggesting ? (
                        <AutocompleteLoadingRows />
                      ) : (
                        excludedSuggestions.map((suggestion) => (
                          <li key={suggestion.id}>
                            <button
                              className="autocomplete-option"
                              type="button"
                              onClick={() => {
                                setExcludedCities((cities) => [...cities, suggestion]);
                                setExcludedQuery("");
                                setExcludedSuggestions([]);
                              }}
                            >
                              {suggestion.name}, {suggestion.country}
                            </button>
                          </li>
                        ))
                      )}
                    </ul>
                  ) : null}
                  {excludedCities.length > 0 ? (
                    <div className="excluded-city-tags" aria-label="Excluded cities">
                      {excludedCities.map((city) => (
                        <Badge className="excluded-city-tag" key={city.id} variant="secondary">
                          <span>
                            {city.name}, {city.country}
                          </span>
                          <button
                            className="pill-remove"
                            type="button"
                            aria-label={`Remove ${city.name} exclusion`}
                            disabled={status === "loading"}
                            onClick={() =>
                              setExcludedCities((cities) =>
                                cities.filter((item) => item.id !== city.id),
                              )
                            }
                          >
                            <X />
                          </button>
                        </Badge>
                      ))}
                    </div>
                  ) : null}
                </div>
                <Button
                  type="button"
                  disabled={
                    !canManageTravelWindows ||
                    !activeRange ||
                    status === "loading" ||
                    (searchMode === "rectangle" && !searchBounds)
                  }
                  onClick={handleFindDestinations}
                >
                  {status === "loading" ? (
                    <>
                      <Spinner data-icon="inline-start" />
                      {buttonProgressLabel}
                    </>
                  ) : (
                    "Find destinations"
                  )}
                </Button>
              </CardContent>
            </Card>
          </aside>

          <DestinationMap
            destinations={mapDestinations}
            homeCity={homeCity}
            homeCoordinates={[homeLocation.longitude, homeLocation.latitude]}
            radiusKm={radiusKm}
            searchMode={searchMode}
            searchBounds={searchBounds}
            isDrawingRectangle={isDrawingRectangle}
            onSearchBoundsChange={setSearchBounds}
            onDrawingRectangleChange={setIsDrawingRectangle}
            showDestinationPins={mapDestinations.length > 0}
          />

          <aside className="panel right-panel stack">
            <div>
              <h2>Best matches</h2>
              <p className="muted">
                {selectedTravelWindow
                  ? `Grouped by ${selectedTravelWindow.label}.`
                  : "Select a date range to find matches."}
              </p>
            </div>

            {sortedCandidateCards.map((card) => (
              <DestinationCandidateCard
                card={card}
                key={card.destination.id}
                onRetryScore={(destination) => {
                  if (activeSearchId) {
                    void scoreCity(activeSearchId, destination);
                  }
                }}
              />
            ))}
          </aside>
        </section>
      </main>
    </TooltipProvider>
  );
}
