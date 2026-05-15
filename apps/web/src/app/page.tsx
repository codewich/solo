"use client";

import { useState } from "react";
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

const pinClasses = ["pin-lisbon", "pin-seville", "pin-porto", "pin-prague", "pin-copenhagen"];

const calendarDays = [
  "27",
  "28",
  "29",
  "30",
  "1",
  "2",
  "3",
  "4",
  "5",
  "6",
  "7",
  "8",
  "9",
  "10",
  "11",
  "12",
  "13",
  "14",
  "15",
  "16",
  "17",
  "18",
  "19",
  "20",
  "21",
  "22",
  "23",
  "24",
  "25",
  "26",
  "27",
  "28",
  "29",
  "30",
  "31",
];

const mayCalendarDates = calendarDays.map((day, index) => {
  const month = index < 4 ? "04" : "05";
  const year = 2026;
  return {
    day,
    isoDate: `${year}-${month}-${day.padStart(2, "0")}`,
    label: `${Number(day)} ${month === "04" ? "Apr" : "May"} 2026`,
  };
});

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
  const visibleCalendarRange = draftRange ?? selectedTravelWindow;

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

  function handleMayDateClick(date: string) {
    if (!draftAnchorDate || isDraftComplete) {
      setDraftAnchorDate(date);
      setDraftRange({ start_date: date, end_date: date });
      setIsDraftComplete(false);
      return;
    }

    setDraftRange(orderedRange(draftAnchorDate, date));
    setIsDraftComplete(true);
  }

  function handleAddRange() {
    if (!draftRange) {
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
              <strong>May 2026</strong>
              <span className="pill">GB holidays</span>
            </div>
            <div className="calendar" aria-label="May 2026 calendar">
              {["M", "T", "W", "T", "F", "S", "S"].map((day, index) => (
                <div className="dow" key={`${day}-${index}`}>
                  {day}
                </div>
              ))}
              {mayCalendarDates.map(({ day, isoDate, label }, index) => {
                const isHoliday = isoDate === "2026-05-04" || isoDate === "2026-05-25";
                const isSelected = isWithinRange(
                  isoDate,
                  visibleCalendarRange.start_date,
                  visibleCalendarRange.end_date,
                );
                return (
                  <button
                    className={`day${isHoliday ? " holiday" : ""}${isSelected ? " selected" : ""}`}
                    key={`${isoDate}-${index}`}
                    type="button"
                    aria-label={label}
                    onClick={() => handleMayDateClick(isoDate)}
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
            ) : null}
          </div>

          <div className="card stack">
            <div className="row">
              <strong>Candidate travel windows</strong>
              <button className="secondary-button" type="button" onClick={handleAddRange}>
                Add range
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
                      onClick={() => setSelectedTravelWindowId(window.id)}
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

        <section className="map" aria-label="Europe destination map">
          <div className="route" />
          <div className="pin pin-home">
            {homeCity}
            <span>home base</span>
          </div>
          {activeRecommendations.length > 0
            ? activeRecommendations.slice(0, 5).map((item, index) => (
                <button
                  className={`pin ${pinClasses[index] ?? "pin-lisbon"}`}
                  type="button"
                  key={`${item.travel_window_id}-${item.destination.id}`}
                >
                  {item.destination.city} {item.score}
                  <span>{item.reasons[0]}</span>
                </button>
              ))
            : staticRecommendations.map((item, index) => (
                <div className={`pin ${pinClasses[index]}`} key={item.city}>
                  {item.city} {item.score}
                  <span>May: {index === 0 ? "warm + food" : "destination fit"}</span>
                </div>
              ))}
          <div className="map-note">
            <strong>Map behavior</strong>
            <p className="muted">
              Clicking a date window will filter pins. Clicking a pin will open reasons and an
              itinerary preview.
            </p>
          </div>
        </section>

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
