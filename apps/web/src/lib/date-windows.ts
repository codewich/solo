const dayMs = 24 * 60 * 60 * 1000;

export function durationDays(startDate: string, endDate: string): number {
  const start = new Date(`${startDate}T00:00:00Z`);
  const end = new Date(`${endDate}T00:00:00Z`);
  return Math.floor((end.getTime() - start.getTime()) / dayMs) + 1;
}

export function formatWindowLabel(startDate: string, endDate: string): string {
  const start = new Date(`${startDate}T00:00:00Z`);
  const end = new Date(`${endDate}T00:00:00Z`);
  const month = new Intl.DateTimeFormat("en-GB", { month: "short", timeZone: "UTC" });
  const year = new Intl.DateTimeFormat("en-GB", { year: "numeric", timeZone: "UTC" });
  return `${start.getUTCDate()} ${month.format(start)}-${end.getUTCDate()} ${month.format(end)} ${year.format(end)}`;
}
