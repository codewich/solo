import { durationDays, formatWindowLabel } from "./date-windows";

describe("date window helpers", () => {
  it("counts inclusive days", () => {
    expect(durationDays("2026-05-23", "2026-05-25")).toBe(3);
  });

  it("formats a readable window label", () => {
    expect(formatWindowLabel("2026-08-29", "2026-08-31")).toBe("29 Aug-31 Aug 2026");
  });
});
