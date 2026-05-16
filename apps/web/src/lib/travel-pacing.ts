import type { Pace } from "./types";

type DateRange = {
  start_date: string;
  end_date: string;
};

function utcDayNumber(value: string): number {
  return Date.parse(`${value}T00:00:00Z`) / 86_400_000;
}

export function durationDays(range: DateRange): number {
  return Math.max(1, Math.round(utcDayNumber(range.end_date) - utcDayNumber(range.start_date)) + 1);
}

export function inferPaceFromRange(range: DateRange): Pace {
  const days = durationDays(range);

  if (days <= 2) {
    return "rushed";
  }

  if (days <= 4) {
    return "balanced";
  }

  return "wandering";
}
