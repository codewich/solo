"use client";

import { useState } from "react";
import { DestinationMap } from "./destination-map";
import { fetchRecommendations } from "@/lib/api";
import { formatWindowLabel } from "@/lib/date-windows";
import type { RecommendationGroup, TravelWindow } from "@/lib/types";

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

const staticRecommendations = [
  {
    city: "Lisbon",
    country: "Portugal",
    score: 92,
    why: "Warm, food-led, walkable, and flexible enough for a wandering pace.",
  },
  {
    city: "Seville",
    country: "Spain",
    score: 89,
    why: "Excellent spring energy, architecture, late dinners, and slower afternoons.",
  },
  {
    city: "Porto",
    country: "Portugal",
    score: 84,
    why: "Compact, atmospheric, good for low-pressure discovery and food.",
  },
];

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

export default function Page() {
  const [homeCity, setHomeCity] = useState("London");
  const [pace, setPace] = useState<"rushed" | "balanced" | "wandering">("wandering");
  const [travelWindows, setTravelWindows] = useState(initialTravelWindows);
  const [selectedTravelWindowId, setSelectedTravelWindowId] = useState(initialTravelWindows[0].id);
  const [visibleCalendarMonth, setVisibleCalendarMonth] = useState({ year: 2026, monthIndex: 4 });
  const [isAddingRange, setIsAddingRange] = useState(false);
  const [draftRange, setDraftRange] = useState<DraftRange | null>(null);
  const [draftAnchorDate, setDraftAnchorDate] = useState<string | null>(null);
  const [isDraftComplete, setIsDraftComplete] = useState(false);
  const [editingWindowId, setEditingWindowId] = useState<string | null>(null);
  const [editingLabel, setEditingLabel] = useState("");
  const [groups, setGroups] = useState<RecommendationGroup[]>([]);
  const [status, setStatus] = useState<"idle" | "loading" | "ready" | "error">("idle");

  const selectedTravelWindow =
    travelWindows.find((window) => window.id === selectedTravelWindowId) ?? travelWindows[0];
  const activeGroup =
    groups.find((group) => group.travel_window.id === selectedTravelWindowId) ?? groups[0];
  const activeRecommendations = activeGroup?.recommendations ?? [];
  const mapDestinations =
    activeRecommendations.length > 0
      ? activeRecommendations.slice(0, 5).map((item) => ({
          city: item.destination.city,
          country: item.destination.country,
          score: item.score,
          summary: item.reasons[0],
        }))
      : staticRecommendations.map((item) => ({
          city: item.city,
          country: item.country,
          score: item.score,
          summary: item.why,
        }));
  const visibleCalendarRange = draftRange ?? selectedTravelWindow;
  const visibleCalendarDates = buildCalendarDates(
    visibleCalendarMonth.year,
    visibleCalendarMonth.monthIndex,
  );
  const visibleCalendarTitle = formatCalendarTitle(
    visibleCalendarMonth.year,
    visibleCalendarMonth.monthIndex,
  );
  const todayIsoDate = toIsoDate(new Date());

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
    setStatus("loading");
    try {
      const results = await fetchRecommendations({
        home_city: homeCity,
        travel_windows: travelWindows.map(
          ({ id, label, start_date, end_date, linked_holiday, status, notes }) => ({
            id,
            label,
            start_date,
            end_date,
            linked_holiday,
            status,
            notes,
          }),
        ),
        preferences: {
          pace,
          climate: "warm",
          budget_sensitivity: 3,
          popularity: "mix",
          interests: { food: 5, history: 3, museums: 2, nature: 2, architecture: 4 },
        },
        excluded_destination_ids: [],
      });
      setGroups(results);
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

    const dates = formatWindowLabel(draftRange.start_date, draftRange.end_date);
    const newWindow: PlanningWindow = {
      id: `range-${Date.now()}`,
      label: dates,
      dates,
      start_date: draftRange.start_date,
      end_date: draftRange.end_date,
      linked_holiday: linkedHolidayForRange(draftRange),
      status: "candidate",
      notes: "New candidate range.",
    };

    setTravelWindows((currentWindows) => [...currentWindows, newWindow]);
    setSelectedTravelWindowId(newWindow.id);
    setDraftAnchorDate(null);
    setDraftRange(null);
    setIsDraftComplete(false);
    setIsAddingRange(false);
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
    if (selectedTravelWindowId === id) {
      setSelectedTravelWindowId(nextWindows[0].id);
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

          <label>
            Home city
            <input value={homeCity} onChange={(event) => setHomeCity(event.target.value)} />
          </label>

          <label>
            Travel pace
            <select value={pace} onChange={(event) => setPace(event.target.value as typeof pace)}>
              <option value="rushed">Rushed</option>
              <option value="balanced">Balanced</option>
              <option value="wandering">Wandering</option>
            </select>
          </label>

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
                const isSelected = isWithinRange(
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
              <button
                className="secondary-button"
                type="button"
                disabled={isAddingRange && !isDraftComplete}
                onClick={handleRangeButtonClick}
              >
                {isAddingRange ? "Save range" : "Add range"}
              </button>
            </div>
            <span className="score">{travelWindows.length} ranges</span>
            <div className="range-list" aria-label="Candidate range list">
              {travelWindows.map((window) => {
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
          </div>

          <div className="card stack">
            <strong>Preference lens</strong>
            <div className="row">
              <span className="pill">{pace[0].toUpperCase() + pace.slice(1)}</span>
              <span className="pill">Warm</span>
              <span className="pill">Food</span>
            </div>
            <p className="muted">Excluded: Paris, Amsterdam, Barcelona</p>
            <button className="primary-button" type="button" onClick={handleFindDestinations}>
              {status === "loading" ? "Finding..." : "Find destinations"}
            </button>
            {status === "error" ? <p role="alert">Could not load recommendations.</p> : null}
          </div>
        </aside>

        <DestinationMap destinations={mapDestinations} homeCity={homeCity} />

        <aside className="panel right-panel stack">
          <div>
            <h2>Best matches</h2>
            <p className="muted">Grouped by {selectedTravelWindow.label}.</p>
          </div>

          {(activeRecommendations.length > 0 ? activeRecommendations : staticRecommendations).map((item) => {
            const city = "destination" in item ? item.destination.city : item.city;
            const country = "destination" in item ? item.destination.country : item.country;
            const why = "reasons" in item ? item.reasons[0] : item.why;

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
            </div>
            );
          })}
        </aside>
      </section>
    </main>
  );
}
