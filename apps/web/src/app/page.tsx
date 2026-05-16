"use client";

import { useEffect, useMemo, useState } from "react";
import { DestinationMap } from "./destination-map";
import { fetchDestinationIntelligence, fetchRecommendations } from "@/lib/api";
import { formatWindowLabel } from "@/lib/date-windows";
import { inferPaceFromRange } from "@/lib/travel-pacing";
import type {
  DestinationIntelligence,
  HomeLocation,
  RecommendationGroup,
  TravelWindow,
} from "@/lib/types";

type PlanningWindow = TravelWindow & {
  dates: string;
  label: string;
  linked_holiday: string | null;
  status: "candidate" | "planned" | "archived";
  notes: string;
};

type DraftRange = {
  start_date: string;
  end_date: string;
};

type CalendarDate = {
  day: string;
  isoDate: string;
  label: string;
  isCurrentMonth: boolean;
};

const initialTravelWindows: PlanningWindow[] = [
  {
    id: "may",
    label: "Spring bank holiday",
    dates: "22-25 May 2026",
    start_date: "2026-05-22",
    end_date: "2026-05-25",
    linked_holiday: "Spring bank holiday",
    status: "candidate",
    notes: "Warm long weekend with food and relaxed neighborhoods.",
  },
  {
    id: "august",
    label: "Summer bank holiday",
    dates: "28-31 Aug 2026",
    start_date: "2026-08-28",
    end_date: "2026-08-31",
    linked_holiday: "Summer bank holiday",
    status: "candidate",
    notes: "Long daylight, harbor walks, and easy solo dinners.",
  },
  {
    id: "christmas",
    label: "Christmas window",
    dates: "24-28 Dec 2026",
    start_date: "2026-12-24",
    end_date: "2026-12-28",
    linked_holiday: "Christmas Day",
    status: "candidate",
    notes: "Seasonal markets, museums, and atmospheric evenings.",
  },
];

const rangePageSize = 6;

const monthTitle = new Intl.DateTimeFormat("en-GB", {
  month: "long",
  timeZone: "UTC",
  year: "numeric",
});

const dayLabel = new Intl.DateTimeFormat("en-GB", {
  day: "numeric",
  month: "short",
  timeZone: "UTC",
  year: "numeric",
});

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

function toIsoDate(date: Date): string {
  return `${date.getUTCFullYear()}-${padDatePart(date.getUTCMonth() + 1)}-${padDatePart(
    date.getUTCDate(),
  )}`;
}

function formatCalendarTitle(year: number, monthIndex: number): string {
  return monthTitle.format(new Date(Date.UTC(year, monthIndex, 1)));
}

function buildCalendarDates(year: number, monthIndex: number): CalendarDate[] {
  const firstOfMonth = new Date(Date.UTC(year, monthIndex, 1));
  const mondayOffset = (firstOfMonth.getUTCDay() + 6) % 7;
  const firstVisibleDate = new Date(Date.UTC(year, monthIndex, 1 - mondayOffset));

  return Array.from({ length: 42 }, (_, index) => {
    const date = new Date(firstVisibleDate);
    date.setUTCDate(firstVisibleDate.getUTCDate() + index);

    return {
      day: String(date.getUTCDate()),
      isoDate: toIsoDate(date),
      label: dayLabel.format(date),
      isCurrentMonth: date.getUTCMonth() === monthIndex,
    };
  });
}

function isWithinRange(date: string, startDate: string, endDate: string): boolean {
  return date >= startDate && date <= endDate;
}

function orderedRange(firstDate: string, secondDate: string): DraftRange {
  return firstDate <= secondDate
    ? { start_date: firstDate, end_date: secondDate }
    : { start_date: secondDate, end_date: firstDate };
}

function linkedHolidayForRange(range: DraftRange): string | null {
  if (isWithinRange("2026-05-25", range.start_date, range.end_date)) {
    return "Spring bank holiday";
  }
  if (isWithinRange("2026-05-04", range.start_date, range.end_date)) {
    return "Early May bank holiday";
  }
  return null;
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
    linked_holiday: linkedHolidayForRange(range),
    status: "candidate",
    notes: "New candidate range.",
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
  const [visibleCalendarMonth, setVisibleCalendarMonth] = useState({ year: 2026, monthIndex: 4 });
  const [isAddingRange, setIsAddingRange] = useState(false);
  const [draftRange, setDraftRange] = useState<DraftRange | null>(null);
  const [draftAnchorDate, setDraftAnchorDate] = useState<string | null>(null);
  const [isDraftComplete, setIsDraftComplete] = useState(false);
  const [rangePageIndex, setRangePageIndex] = useState(0);
  const [editingWindowId, setEditingWindowId] = useState<string | null>(null);
  const [editingLabel, setEditingLabel] = useState("");
  const [groups, setGroups] = useState<RecommendationGroup[]>([]);
  const [destinationIntelligence, setDestinationIntelligence] = useState<
    Record<string, DestinationIntelligence>
  >({});
  const [status, setStatus] = useState<"idle" | "loading" | "ready" | "error">("idle");

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
  const pace = activeRange ? inferPaceFromRange(activeRange) : null;
  const activeGroup = selectedTravelWindowId
    ? groups.find((group) => group.travel_window.id === selectedTravelWindowId)
    : undefined;
  const activeRecommendations = activeGroup?.recommendations ?? [];
  const mapDestinations = useMemo(
    () =>
      activeRecommendations.slice(0, 5).map((item) => ({
            city: item.destination.city,
            country: item.destination.country,
            score: item.score,
            summary: item.reasons[0],
          })),
    [activeRecommendations],
  );
  const visibleCalendarRange = activeRange;
  const visibleCalendarDates = buildCalendarDates(
    visibleCalendarMonth.year,
    visibleCalendarMonth.monthIndex,
  );
  const visibleCalendarTitle = formatCalendarTitle(
    visibleCalendarMonth.year,
    visibleCalendarMonth.monthIndex,
  );
  const todayIsoDate = toIsoDate(new Date());

  useEffect(() => {
    setRangePageIndex((currentPage) => Math.min(currentPage, rangePageCount - 1));
  }, [rangePageCount]);

  function shiftVisibleMonth(offset: number) {
    setVisibleCalendarMonth((currentMonth) => {
      const nextMonth = new Date(
        Date.UTC(currentMonth.year, currentMonth.monthIndex + offset, 1),
      );
      return {
        year: nextMonth.getUTCFullYear(),
        monthIndex: nextMonth.getUTCMonth(),
      };
    });
  }

  function showMonthForDate(isoDate: string) {
    const date = new Date(`${isoDate}T00:00:00Z`);
    setVisibleCalendarMonth({
      year: date.getUTCFullYear(),
      monthIndex: date.getUTCMonth(),
    });
  }

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
      setDraftAnchorDate(null);
      setDraftRange(null);
      setIsDraftComplete(false);
      setIsAddingRange(false);
    }

    setStatus("loading");
    try {
      const results = await fetchRecommendations({
        home_city: homeCity,
        travel_windows: [
          {
            id: targetWindow.id,
            label: targetWindow.label,
            start_date: targetWindow.start_date,
            end_date: targetWindow.end_date,
            linked_holiday: targetWindow.linked_holiday,
            status: targetWindow.status,
            notes: targetWindow.notes,
          },
        ],
        preferences: {
          pace: inferPaceFromRange(targetWindow),
          climate: "warm",
          budget_sensitivity: 3,
          popularity: "mix",
          interests: { food: 5, history: 3, museums: 2, nature: 2, architecture: 4 },
        },
        excluded_destination_ids: [],
      });
      const activeWindow = results.find((group) => group.travel_window.id === targetWindow.id)
        ?.travel_window;
      const activeItems =
        results.find((group) => group.travel_window.id === targetWindow.id)?.recommendations ?? [];
      const intelligenceEntries = await Promise.all(
        activeItems
          .slice(0, 3)
          .filter(
            (item) =>
              typeof item.destination.latitude === "number" &&
              typeof item.destination.longitude === "number",
          )
          .map(async (item) => {
            const intelligence = await fetchDestinationIntelligence({
              destination_city: item.destination.city,
              country: item.destination.country,
              latitude: item.destination.latitude as number,
              longitude: item.destination.longitude as number,
              start_date: activeWindow?.start_date ?? targetWindow.start_date,
              end_date: activeWindow?.end_date ?? targetWindow.end_date,
            });
            return [item.destination.id, intelligence] as const;
          }),
      );
      setDestinationIntelligence(Object.fromEntries(intelligenceEntries));
      setGroups((currentGroups) => [
        ...currentGroups.filter((group) => group.travel_window.id !== targetWindow.id),
        ...results,
      ]);
      setStatus("ready");
    } catch {
      setStatus("error");
    }
  }

  function handleCalendarDateClick(date: string) {
    if (!isAddingRange) {
      return;
    }

    if (!draftAnchorDate || isDraftComplete) {
      setDraftAnchorDate(date);
      setDraftRange({ start_date: date, end_date: date });
      setIsDraftComplete(false);
      return;
    }

    setDraftRange(orderedRange(draftAnchorDate, date));
    setIsDraftComplete(true);
  }

  function handleRangeButtonClick() {
    if (!isAddingRange) {
      setIsAddingRange(true);
      setDraftAnchorDate(null);
      setDraftRange(null);
      setIsDraftComplete(false);
      return;
    }

    if (!draftRange || !isDraftComplete) {
      return;
    }

    const newWindow = planningWindowFromDraft(draftRange, travelWindows);

    setTravelWindows((currentWindows) => [...currentWindows, newWindow]);
    setSelectedTravelWindowId(newWindow.id);
    setDraftAnchorDate(null);
    setDraftRange(null);
    setIsDraftComplete(false);
    setIsAddingRange(false);
  }

  function handleCancelRange() {
    setIsAddingRange(false);
    setDraftAnchorDate(null);
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
    <main>
      <header className="topbar">
        <div className="brand">
          <h1>Solo</h1>
          <span className="caption">Long-weekend map planner</span>
        </div>
        <div className="row">
          <span className="pill">Home city: {homeCity}</span>
          <button className="primary-button" type="button">
            Save planner
          </button>
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

          <div className="card stack">
            <div className="row">
              <div className="month-controls">
                <button
                  className="icon-button"
                  type="button"
                  aria-label="Previous month"
                  onClick={() => shiftVisibleMonth(-1)}
                >
                  {"<"}
                </button>
                <strong>{visibleCalendarTitle}</strong>
                <button
                  className="icon-button"
                  type="button"
                  aria-label="Next month"
                  onClick={() => shiftVisibleMonth(1)}
                >
                  {">"}
                </button>
              </div>
              <span className="pill">GB holidays</span>
            </div>
            <div className="calendar" aria-label={`${visibleCalendarTitle} calendar`}>
              {["M", "T", "W", "T", "F", "S", "S"].map((day, index) => (
                <div className="dow" key={`${day}-${index}`}>
                  {day}
                </div>
              ))}
              {visibleCalendarDates.map(({ day, isoDate, label, isCurrentMonth }, index) => {
                const isHoliday = gbHolidayDates.has(isoDate);
                const isSelected =
                  visibleCalendarRange !== null &&
                  isWithinRange(
                    isoDate,
                    visibleCalendarRange.start_date,
                    visibleCalendarRange.end_date,
                  );
                const isToday = isoDate === todayIsoDate;
                return (
                  <button
                    className={`day${!isCurrentMonth ? " outside-month" : ""}${
                      isHoliday ? " holiday" : ""
                    }${isSelected ? " selected" : ""}${isToday ? " current-day" : ""}${
                      isAddingRange ? " picking" : ""
                    }`}
                    key={`${isoDate}-${index}`}
                    type="button"
                    aria-label={label}
                    aria-disabled={!isAddingRange}
                    onClick={() => handleCalendarDateClick(isoDate)}
                  >
                    {day}
                  </button>
                );
              })}
            </div>
            {draftRange ? (
              <p className="muted">
                Draft range: {formatWindowLabel(draftRange.start_date, draftRange.end_date)}
              </p>
            ) : isAddingRange ? (
              <p className="muted">Pick a start date, then an end date.</p>
            ) : null}
          </div>

          <div className="card stack">
            <div className="row">
              <strong>Candidate travel windows</strong>
              <div className="range-create-actions">
                <button
                  className="secondary-button"
                  type="button"
                  disabled={isAddingRange && !isDraftComplete}
                  onClick={handleRangeButtonClick}
                >
                  {isAddingRange ? "Save draft range" : "Add range"}
                </button>
                {isAddingRange ? (
                  <button className="secondary-button" type="button" onClick={handleCancelRange}>
                    Cancel range
                  </button>
                ) : null}
              </div>
            </div>
            <span className="score">{travelWindows.length} ranges</span>
            <div className="range-list" aria-label="Candidate range list">
              {visibleTravelWindows.map((window) => {
                const isSelected = window.id === selectedTravelWindowId;
                return (
                  <div className="range-item" key={window.id}>
                    <button
                      aria-pressed={isSelected}
                      className={`range-button${isSelected ? " active" : ""}`}
                      type="button"
                      aria-label={`Select ${window.label}`}
                      onClick={() => {
                        setSelectedTravelWindowId(window.id);
                        showMonthForDate(window.start_date);
                        setIsAddingRange(false);
                        setDraftAnchorDate(null);
                        setDraftRange(null);
                        setIsDraftComplete(false);
                      }}
                    >
                      <span>
                        <strong>{window.dates}</strong>
                        <small>{window.notes}</small>
                      </span>
                      <span>
                        <span className="pill">{window.status}</span>
                        <span className="pill">{window.linked_holiday}</span>
                      </span>
                    </button>
                    {editingWindowId === window.id ? (
                      <div className="range-editor">
                        <label>
                          Range label
                          <input
                            value={editingLabel}
                            onChange={(event) => setEditingLabel(event.target.value)}
                          />
                        </label>
                        <button className="secondary-button" type="button" onClick={handleSaveRename}>
                          Save range
                        </button>
                      </div>
                    ) : (
                      <div className="range-actions">
                        <button
                          className="secondary-button"
                          type="button"
                          aria-label={`Rename ${window.label}`}
                          onClick={() => handleStartRename(window)}
                        >
                          Rename
                        </button>
                        <button
                          className="secondary-button"
                          type="button"
                          aria-label={`Archive ${window.label}`}
                          onClick={() => handleArchiveRange(window.id)}
                        >
                          Archive
                        </button>
                        <button
                          className="secondary-button danger-button"
                          type="button"
                          aria-label={`Remove ${window.label}`}
                          onClick={() => handleRemoveRange(window.id)}
                        >
                          Remove
                        </button>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
            {rangePageCount > 1 ? (
              <div className="pagination-controls">
                <button
                  className="secondary-button"
                  type="button"
                  disabled={rangePageIndex === 0}
                  onClick={() => setRangePageIndex((currentPage) => Math.max(0, currentPage - 1))}
                >
                  Previous ranges
                </button>
                <span className="muted">
                  Page {rangePageIndex + 1} of {rangePageCount}
                </span>
                <button
                  className="secondary-button"
                  type="button"
                  disabled={rangePageIndex >= rangePageCount - 1}
                  onClick={() =>
                    setRangePageIndex((currentPage) =>
                      Math.min(rangePageCount - 1, currentPage + 1),
                    )
                  }
                >
                  Next ranges
                </button>
              </div>
            ) : null}
          </div>

          <div className="card stack">
            <strong>Preference lens</strong>
            <div className="row">
              <span className="pill">
                {pace ? `${pace[0].toUpperCase() + pace.slice(1)} pace` : "Choose a range"}
              </span>
              <span className="pill">Warm</span>
              <span className="pill">Food</span>
            </div>
            <p className="muted">Excluded: Paris, Amsterdam, Barcelona</p>
            <button
              className="primary-button"
              type="button"
              disabled={!activeRange || status === "loading"}
              onClick={handleFindDestinations}
            >
              {status === "loading" ? "Finding..." : "Find destinations"}
            </button>
            {status === "error" ? <p role="alert">Could not load recommendations.</p> : null}
          </div>
        </aside>

        <DestinationMap
          destinations={mapDestinations}
          homeCity={homeCity}
          homeCoordinates={[homeLocation.longitude, homeLocation.latitude]}
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

          {activeRecommendations.map((item) => {
            const city = item.destination.city;
            const country = item.destination.country;
            const why = item.reasons[0];
            const id = item.destination.id;
            const intelligence = destinationIntelligence[id];

            return (
            <div className="card" key={city}>
              <div className="row">
                <h3>
                  {city}, {country}
                </h3>
                <span className="score">{item.score}</span>
              </div>
              <p className="muted">{why}</p>
              <div className="row">
                <span className="pill">4 days</span>
                <span className="pill">solo-friendly</span>
                <span className="pill">walkable</span>
              </div>
              {intelligence ? (
                <div className="destination-intelligence">
                  {intelligence.climate.average_temperature_c !== null ? (
                    <span className="pill">
                      {intelligence.climate.average_temperature_c}C average
                    </span>
                  ) : null}
                  {intelligence.attractions[0] ? (
                    <span className="pill">{intelligence.attractions[0].name}</span>
                  ) : null}
                  {intelligence.hotels.status === "available" &&
                  intelligence.hotels.currency &&
                  intelligence.hotels.median_nightly_price !== null ? (
                    <span className="pill">
                      {intelligence.hotels.currency}{" "}
                      {Math.round(intelligence.hotels.median_nightly_price)} median hotel
                    </span>
                  ) : (
                    <span className="pill">Hotel prices unavailable</span>
                  )}
                  <p className="muted">{intelligence.cost_of_living.summary}</p>
                </div>
              ) : null}
            </div>
            );
          })}
        </aside>
      </section>
    </main>
  );
}
