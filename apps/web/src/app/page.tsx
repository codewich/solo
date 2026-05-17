"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { toast } from "sonner";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Calendar } from "@/components/ui/calendar";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import { Slider } from "@/components/ui/slider";
import { Spinner } from "@/components/ui/spinner";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { DestinationMap } from "./destination-map";
import { ApiRequestError, fetchDestinationIntelligence, fetchRecommendations } from "@/lib/api";
import { formatWindowLabel } from "@/lib/date-windows";
import { cn } from "@/lib/utils";
import type { DateRange } from "react-day-picker";
import type {
  DestinationIntelligence,
  HomeLocation,
  Recommendation,
  RecommendationGroup,
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

type IntelligenceError = {
  destinationId: string;
  city: string;
  message: string;
  severity: "warning" | "error";
};

type DestinationCardProps = {
  item: Recommendation;
  intelligence?: DestinationIntelligence;
  isIntelligenceLoading: boolean;
  shouldLazyLoad: boolean;
  onVisible: () => void;
};

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

function DestinationCard({
  item,
  intelligence,
  isIntelligenceLoading,
  shouldLazyLoad,
  onVisible,
}: DestinationCardProps) {
  const cardRef = useRef<HTMLDivElement | null>(null);
  const city = item.destination.city;
  const country = item.destination.country;
  const why = item.reasons[0];
  const imageUrl = item.image_url ?? item.imageUrl;
  const attractionCount = item.attraction_count ?? item.attractionCount;
  const airQuality = item.air_quality ?? item.airQuality;
  const climate = item.climate ?? intelligence?.climate;
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
        : null;
  const rainfall =
    climate?.precipitation_mm !== null && climate?.precipitation_mm !== undefined
      ? `${Math.round(climate.precipitation_mm)} mm rain`
      : null;
  const sunshine =
    climate?.sunshine_hours !== null && climate?.sunshine_hours !== undefined
      ? `${Math.round(climate.sunshine_hours)} h sun`
      : null;
  const cardStyle = imageUrl
    ? {
        backgroundImage: `linear-gradient(rgba(23, 33, 29, 0.72), rgba(23, 33, 29, 0.72)), url(${imageUrl})`,
      }
    : undefined;

  useEffect(() => {
    if (!shouldLazyLoad || !cardRef.current || typeof IntersectionObserver === "undefined") {
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          onVisible();
          observer.disconnect();
        }
      },
      { rootMargin: "160px" },
    );
    observer.observe(cardRef.current);
    return () => observer.disconnect();
  }, [onVisible, shouldLazyLoad]);

  return (
    <Card
      className={cn("card recommendation-card", imageUrl ? "has-image" : "")}
      key={city}
      ref={cardRef}
      style={cardStyle}
    >
      <CardHeader className="recommendation-card-header">
        <CardTitle>
          {city}, {country}
        </CardTitle>
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              className="score"
              type="button"
              variant="ghost"
              size="sm"
              aria-label={`Score breakdown for ${city}`}
            >
              {item.score}
              {item.score_breakdown ? (
                <span className="sr-only">
                  Climate: {item.score_breakdown.climateScore}
                  {" "}
                  Attractions: {item.score_breakdown.attractionScore}
                  {" "}
                  Popularity: {item.score_breakdown.popularityScore}
                  {" "}
                  Affordability: {item.score_breakdown.affordabilityScore}
                  {item.score_breakdown.airQualityScore !== undefined
                    ? ` Air: ${item.score_breakdown.airQualityScore}`
                    : ""}
                </span>
              ) : null}
            </Button>
          </TooltipTrigger>
          {item.score_breakdown ? (
            <TooltipContent className="score-tooltip-panel">
              <span>Climate: {item.score_breakdown.climateScore}</span>
              <span>Attractions: {item.score_breakdown.attractionScore}</span>
              <span>Popularity: {item.score_breakdown.popularityScore}</span>
              <span>Affordability: {item.score_breakdown.affordabilityScore}</span>
              {item.score_breakdown.airQualityScore !== undefined ? (
                <span>Air: {item.score_breakdown.airQualityScore}</span>
              ) : null}
            </TooltipContent>
          ) : null}
        </Tooltip>
      </CardHeader>
      <CardContent className="stack">
      <p className="muted">{why}</p>
      <div className="badge-row">
        <Pill>4 days</Pill>
        <Pill>solo-friendly</Pill>
        <Pill>walkable</Pill>
        {attractionCount !== undefined ? <Pill>{attractionCount} attractions nearby</Pill> : null}
      </div>
      {climate ? (
        <div className="climate-summary">
          <div className="badge-row">
            {temperatureRange ? <Pill>{temperatureRange}</Pill> : null}
            {rainfall ? <Pill>{rainfall}</Pill> : null}
            {sunshine ? <Pill>{sunshine}</Pill> : null}
          </div>
          <p className="muted">{climate.summary}</p>
        </div>
      ) : null}
      {airQuality?.summary ? <p className="muted">{airQuality.summary}</p> : null}
      {isIntelligenceLoading ? (
        <div
          aria-label={`Loading intelligence for ${city}`}
          className="destination-intelligence-loading"
          role="status"
        >
          <Spinner aria-hidden="true" />
          <span>Loading intelligence</span>
        </div>
      ) : null}
      {intelligence ? (
        <div className="destination-intelligence">
          {intelligence.attractions?.[0] ? (
            <Pill>{intelligence.attractions[0].name}</Pill>
          ) : null}
          {intelligence.hotels?.status === "available" &&
          intelligence.hotels.currency &&
          intelligence.hotels.median_nightly_price !== null ? (
            <Pill>
              {intelligence.hotels.currency}{" "}
              {Math.round(intelligence.hotels.median_nightly_price)} median hotel
            </Pill>
          ) : (
            <Pill>Hotel prices unavailable</Pill>
          )}
          {intelligence.cost_of_living?.summary ? (
            <p className="muted">{intelligence.cost_of_living.summary}</p>
          ) : null}
        </div>
      ) : null}
      </CardContent>
    </Card>
  );
}

const initialTravelWindows: PlanningWindow[] = [
  {
    id: "may",
    label: "Spring bank holiday",
    dates: "22-25 May 2026",
    start_date: "2026-05-22",
    end_date: "2026-05-25",
    status: "candidate",
  },
  {
    id: "august",
    label: "Summer bank holiday",
    dates: "28-31 Aug 2026",
    start_date: "2026-08-28",
    end_date: "2026-08-31",
    status: "candidate",
  },
  {
    id: "christmas",
    label: "Christmas window",
    dates: "24-28 Dec 2026",
    start_date: "2026-12-24",
    end_date: "2026-12-28",
    status: "candidate",
  },
];

const rangePageSize = 6;
const emptyRecommendations: Recommendation[] = [];
const searchProgressSteps = [
  { label: "Loading list of cities (1/9)...", value: 12 },
  { label: "Filtering candidate cities (2/9)...", value: 24 },
  { label: "Scoring climate fit (3/9)...", value: 36 },
  { label: "Checking attractions (4/9)...", value: 48 },
  { label: "Estimating affordability (5/9)...", value: 60 },
  { label: "Checking air quality (6/9)...", value: 72 },
  { label: "Ranking best matches (7/9)...", value: 84 },
  { label: "Loading destination intelligence (8/9)...", value: 92 },
  { label: "Preparing results (9/9)...", value: 100 },
];

const gbHolidayDates = new Map([
  ["2026-05-04", "Early May bank holiday"],
  ["2026-05-25", "Spring bank holiday"],
  ["2026-08-31", "Summer bank holiday"],
  ["2026-12-25", "Christmas Day"],
  ["2026-12-28", "Boxing Day substitute"],
]);

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

export default function Page() {
  const homeLocation: HomeLocation = {
    city: "London",
    country: "United Kingdom",
    admin1: "England",
    latitude: 51.5072,
    longitude: -0.1276,
  };
  const [travelWindows, setTravelWindows] = useState(initialTravelWindows);
  const [selectedTravelWindowId, setSelectedTravelWindowId] = useState<string | null>(null);
  const [visibleCalendarMonth, setVisibleCalendarMonth] = useState(() => new Date(2026, 4, 1));
  const [isAddingRange, setIsAddingRange] = useState(false);
  const [draftRange, setDraftRange] = useState<DraftRange | null>(null);
  const [isDraftComplete, setIsDraftComplete] = useState(false);
  const [rangePageIndex, setRangePageIndex] = useState(0);
  const [editingWindowId, setEditingWindowId] = useState<string | null>(null);
  const [editingLabel, setEditingLabel] = useState("");
  const [groups, setGroups] = useState<RecommendationGroup[]>([]);
  const [destinationIntelligence, setDestinationIntelligence] = useState<
    Record<string, DestinationIntelligence>
  >({});
  const [intelligenceErrors, setIntelligenceErrors] = useState<IntelligenceError[]>([]);
  const [intelligenceLoadingIds, setIntelligenceLoadingIds] = useState<string[]>([]);
  const [radiusKm, setRadiusKm] = useState(1800);
  const [minPopulation, setMinPopulation] = useState(250000);
  const [status, setStatus] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const [loadingStepIndex, setLoadingStepIndex] = useState(0);
  const loadedIntelligenceIdsRef = useRef(new Set<string>());
  const loadingIntelligenceIdsRef = useRef(new Set<string>());
  const failedIntelligenceIdsRef = useRef(new Set<string>());
  const intelligenceRequestVersionRef = useRef(0);

  const homeCity = homeLocation.city;
  const selectedTravelWindow = selectedTravelWindowId
    ? travelWindows.find((window) => window.id === selectedTravelWindowId) ?? null
    : null;
  const rangePageCount = Math.max(1, Math.ceil(travelWindows.length / rangePageSize));
  const visibleTravelWindows = travelWindows.slice(
    rangePageIndex * rangePageSize,
    rangePageIndex * rangePageSize + rangePageSize,
  );
  const activeRange = draftRange ?? selectedTravelWindow;
  const activeGroup = selectedTravelWindowId
    ? groups.find((group) => group.travel_window.id === selectedTravelWindowId)
    : undefined;
  const activeRecommendations = activeGroup?.recommendations ?? emptyRecommendations;
  const mapDestinations = useMemo(
    () =>
      activeRecommendations.slice(0, 5).map((item) => ({
            city: item.destination.city,
            country: item.destination.country,
            score: item.score,
            summary: item.reasons[0],
            coordinates:
              typeof item.destination.longitude === "number" &&
              typeof item.destination.latitude === "number"
                ? ([item.destination.longitude, item.destination.latitude] as [number, number])
                : undefined,
          })),
    [activeRecommendations],
  );
  const visibleCalendarRange = activeRange;
  const visibleCalendarDateRange = useMemo(() => {
    if (!visibleCalendarRange) {
      return undefined;
    }
    // When draft range is incomplete (only one date selected), show only the "from" date
    // to prevent react-day-picker from showing a completed range
    if (draftRange && !isDraftComplete) {
      return { from: isoDateToLocalDate(draftRange.start_date) };
    }
    return dateRangeFromTravelRange(visibleCalendarRange);
  }, [visibleCalendarRange, draftRange, isDraftComplete]);
  const holidayDates = useMemo(
    () => Array.from(gbHolidayDates.keys()).map(isoDateToLocalDate),
    [],
  );
  const holidayLabels = useMemo(() => Object.fromEntries(gbHolidayDates), []);
  const loadingStep = searchProgressSteps[loadingStepIndex] ?? searchProgressSteps[0];

  useEffect(() => {
    setRangePageIndex((currentPage) => Math.min(currentPage, rangePageCount - 1));
  }, [rangePageCount]);

  useEffect(() => {
    if (status !== "loading") {
      return undefined;
    }

    const progressTimer = window.setInterval(() => {
      setLoadingStepIndex((currentStep) => Math.min(currentStep + 1, 6));
    }, 600);

    return () => window.clearInterval(progressTimer);
  }, [status]);

  function showMonthForDate(isoDate: string) {
    const date = isoDateToLocalDate(isoDate);
    setVisibleCalendarMonth(new Date(date.getFullYear(), date.getMonth(), 1));
  }

  const loadDestinationIntelligence = useCallback(
    async (item: Recommendation, travelWindow: TravelWindow, requestVersion: number) => {
      const id = item.destination.id;
      if (
        loadedIntelligenceIdsRef.current.has(id) ||
        loadingIntelligenceIdsRef.current.has(id) ||
        failedIntelligenceIdsRef.current.has(id) ||
        typeof item.destination.latitude !== "number" ||
        typeof item.destination.longitude !== "number"
      ) {
        return;
      }

      loadingIntelligenceIdsRef.current.add(id);
      setIntelligenceLoadingIds((currentIds) =>
        currentIds.includes(id) ? currentIds : [...currentIds, id],
      );

      try {
        const intelligence = await fetchDestinationIntelligence({
          city_id: item.destination.id,
          destination_city: item.destination.city,
          country: item.destination.country,
          latitude: item.destination.latitude,
          longitude: item.destination.longitude,
          start_date: travelWindow.start_date,
          end_date: travelWindow.end_date,
        });
        if (requestVersion !== intelligenceRequestVersionRef.current) {
          return;
        }
        loadedIntelligenceIdsRef.current.add(id);
        setDestinationIntelligence((currentIntelligence) => ({
          ...currentIntelligence,
          [id]: intelligence,
        }));
        setIntelligenceErrors((currentErrors) => [
          ...currentErrors.filter((error) => error.destinationId !== id),
          ...(intelligence.warnings?.map((warning) => ({
            destinationId: id,
            city: item.destination.city,
            message: warning.message,
            severity: "warning" as const,
          })) ?? []),
        ]);
      } catch (reason) {
        if (requestVersion !== intelligenceRequestVersionRef.current) {
          return;
        }
        failedIntelligenceIdsRef.current.add(id);
        setIntelligenceErrors((currentErrors) => [
          ...currentErrors.filter((error) => error.destinationId !== id),
          {
            destinationId: id,
            city: item.destination.city,
            message:
              reason instanceof ApiRequestError
                ? reason.message
                : "Destination intelligence request failed.",
            severity: "error",
          },
        ]);
      } finally {
        loadingIntelligenceIdsRef.current.delete(id);
        if (requestVersion === intelligenceRequestVersionRef.current) {
          setIntelligenceLoadingIds((currentIds) =>
            currentIds.filter((currentId) => currentId !== id),
          );
        }
      }
    },
    [],
  );

  async function handleFindDestinations() {
    const isSavingDraftRange = draftRange !== null && isDraftComplete;
    const targetWindow = isSavingDraftRange
      ? planningWindowFromDraft(draftRange, travelWindows)
      : selectedTravelWindow;

    if (!targetWindow) {
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
    setLoadingStepIndex(0);
    setIntelligenceErrors([]);
    setIntelligenceLoadingIds([]);
    loadedIntelligenceIdsRef.current.clear();
    loadingIntelligenceIdsRef.current.clear();
    failedIntelligenceIdsRef.current.clear();
    intelligenceRequestVersionRef.current += 1;
    const intelligenceRequestVersion = intelligenceRequestVersionRef.current;
    try {
      const results = await fetchRecommendations({
        home_city: homeCity,
        center_latitude: homeLocation.latitude,
        center_longitude: homeLocation.longitude,
        radius_km: radiusKm,
        min_population: minPopulation,
        candidate_limit: 12,
        travel_windows: [
          {
            id: targetWindow.id,
            label: targetWindow.label,
            start_date: targetWindow.start_date,
            end_date: targetWindow.end_date,
            status: targetWindow.status,
          },
        ],
      });
      setLoadingStepIndex(6);
      const activeWindow = results.find((group) => group.travel_window.id === targetWindow.id)
        ?.travel_window;
      const activeItems =
        results.find((group) => group.travel_window.id === targetWindow.id)?.recommendations ?? [];
      const intelligenceTargets = activeItems.slice(0, 3).filter(
        (item) =>
          typeof item.destination.latitude === "number" &&
          typeof item.destination.longitude === "number",
      );
      setDestinationIntelligence({});
      setGroups((currentGroups) => [
        ...currentGroups.filter((group) => group.travel_window.id !== targetWindow.id),
        ...results,
      ]);
      setLoadingStepIndex(7);
      setStatus("ready");
      const intelligenceWindow = activeWindow ?? targetWindow;
      void Promise.all(
        intelligenceTargets.map((item) =>
          loadDestinationIntelligence(item, intelligenceWindow, intelligenceRequestVersion),
        ),
      );
    } catch (reason) {
      setIntelligenceLoadingIds([]);
      setStatus("error");
      toast.error(
        reason instanceof ApiRequestError ? reason.message : "Could not load recommendations.",
      );
    }
  }

  function handleCalendarRangeSelect(range: DateRange | undefined) {
    if (!isAddingRange) {
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
    if (!isAddingRange) {
      setIsAddingRange(true);
      setDraftRange(null);
      setIsDraftComplete(false);
      setSelectedTravelWindowId(null);
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

  function handleStartRename(window: PlanningWindow) {
    setEditingWindowId(window.id);
    setEditingLabel(window.label);
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

  function handleArchiveRange(id: string) {
    setTravelWindows((currentWindows) =>
      currentWindows.map((window) =>
        window.id === id
          ? {
              ...window,
              status: window.status === "archived" ? "candidate" : "archived",
            }
          : window,
      ),
    );
  }

  function handleRemoveRange(id: string) {
    if (travelWindows.length === 1) {
      return;
    }

    const nextWindows = travelWindows.filter((window) => window.id !== id);
    setTravelWindows(nextWindows);
    setRangePageIndex((currentPage) =>
      Math.min(currentPage, Math.max(0, Math.ceil(nextWindows.length / rangePageSize) - 1)),
    );
    if (selectedTravelWindowId === id) {
      setSelectedTravelWindowId(null);
    }
    if (editingWindowId === id) {
      setEditingWindowId(null);
      setEditingLabel("");
    }
  }

  return (
    <TooltipProvider>
    <main>
      <header className="topbar">
        <div className="brand">
          <h1>Solo</h1>
          <span className="caption">Long-weekend map planner</span>
        </div>
        <div className="row">
          <Pill>Home city: {homeCity}</Pill>
          <AuthButton />
          <Button type="button">
            Save planner
          </Button>
        </div>
      </header>

      <section className="workspace">
        <aside className="panel stack">
          <div>
            <h2>Pick travel windows</h2>
            <p className="muted">
              Bank holidays are highlighted. Select several windows and compare destination fit for
              each one.
            </p>
          </div>

          <Card className="card stack">
            <CardContent className="stack">
            <div className="calendar-card-header">
              <Pill>GB holidays</Pill>
            </div>
            <Calendar
              mode="range"
              month={visibleCalendarMonth}
              onMonthChange={setVisibleCalendarMonth}
              selected={visibleCalendarDateRange}
              onSelect={handleCalendarRangeSelect}
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
                  disabled={isAddingRange && !isDraftComplete}
                  onClick={handleRangeButtonClick}
                >
                  {isAddingRange ? "Save draft range" : "Add range"}
                </Button>
                {isAddingRange ? (
                  <Button variant="outline" size="sm" type="button" onClick={handleCancelRange}>
                    Cancel range
                  </Button>
                ) : null}
              </div>
            </CardHeader>
            <CardContent className="stack">
            <Badge className="score-badge" variant="secondary">{travelWindows.length} ranges</Badge>
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
                      aria-label={`Select ${window.label}`}
                      onClick={() => {
                        setSelectedTravelWindowId(window.id);
                        showMonthForDate(window.start_date);
                        setIsAddingRange(false);
                        setDraftRange(null);
                        setIsDraftComplete(false);
                      }}
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
                          aria-label={`Rename ${window.label}`}
                          onClick={() => handleStartRename(window)}
                        >
                          Rename
                        </Button>
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          aria-label={`Archive ${window.label}`}
                          onClick={() => handleArchiveRange(window.id)}
                        >
                          Archive
                        </Button>
                        <Button
                          type="button"
                          variant="destructive"
                          size="sm"
                          aria-label={`Remove ${window.label}`}
                          onClick={() => handleRemoveRange(window.id)}
                        >
                          Remove
                        </Button>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
            {rangePageCount > 1 ? (
              <div className="pagination-controls">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  disabled={rangePageIndex === 0}
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
                  disabled={rangePageIndex >= rangePageCount - 1}
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
            <div className="field-stack">
              <Label htmlFor="search-radius">Search radius: {radiusKm} km</Label>
              <Slider
                id="search-radius"
                aria-label="Search radius"
                min={100}
                max={5000}
                step={100}
                value={[radiusKm]}
                onValueChange={([nextRadius]) => setRadiusKm(nextRadius)}
              />
            </div>
            <div className="field-stack">
              <Label htmlFor="minimum-population">Minimum population</Label>
              <Input
                id="minimum-population"
                aria-label="Minimum population"
                min={0}
                step={50000}
                type="number"
                value={minPopulation}
                onChange={(event) => setMinPopulation(Number(event.target.value))}
              />
            </div>
            <Button
              type="button"
              disabled={!activeRange || status === "loading"}
              onClick={handleFindDestinations}
            >
              {status === "loading" ? (
                <>
                  <Spinner data-icon="inline-start" />
                  {loadingStep.label}
                </>
              ) : (
                "Find destinations"
              )}
            </Button>
            {status === "loading" ? (
              <Progress aria-label={loadingStep.label} value={loadingStep.value} />
            ) : null}
            {intelligenceErrors.map((error) => (
              <Alert
                variant={error.severity === "error" ? "destructive" : "default"}
                key={error.destinationId}
              >
                <AlertDescription>
                  {error.severity === "warning"
                    ? `Some destination intelligence is unavailable for ${error.city}: ${error.message}`
                    : `Could not load destination intelligence for ${error.city}: ${error.message}`}
                </AlertDescription>
              </Alert>
            ))}
            </CardContent>
          </Card>
        </aside>

        <DestinationMap
          destinations={mapDestinations}
          homeCity={homeCity}
          homeCoordinates={[homeLocation.longitude, homeLocation.latitude]}
          radiusKm={radiusKm}
          showDestinationPins={activeRecommendations.length > 0}
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

          {activeRecommendations.map((item, index) => {
            const id = item.destination.id;
            const intelligence = destinationIntelligence[id];
            const isIntelligenceLoading = intelligenceLoadingIds.includes(id);
            const canLazyLoad =
              index >= 3 &&
              activeGroup?.travel_window !== undefined &&
              !intelligence &&
              !isIntelligenceLoading &&
              !intelligenceErrors.some((error) => error.destinationId === id);
            const intelligenceWindow = activeGroup?.travel_window ?? selectedTravelWindow;

            return (
              <DestinationCard
                intelligence={intelligence}
                isIntelligenceLoading={isIntelligenceLoading}
                item={item}
                key={id}
                onVisible={() => {
                  if (intelligenceWindow) {
                    void loadDestinationIntelligence(
                      item,
                      intelligenceWindow,
                      intelligenceRequestVersionRef.current,
                    );
                  }
                }}
                shouldLazyLoad={canLazyLoad}
              />
            );
          })}
        </aside>
      </section>
    </main>
    </TooltipProvider>
  );
}
