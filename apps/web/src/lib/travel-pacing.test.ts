import { inferPaceFromRange } from "./travel-pacing";

describe("inferPaceFromRange", () => {
  it("uses rushed pace for short windows", () => {
    expect(inferPaceFromRange({ start_date: "2026-05-22", end_date: "2026-05-23" })).toBe(
      "rushed",
    );
  });

  it("uses balanced pace for three or four day windows", () => {
    expect(inferPaceFromRange({ start_date: "2026-05-22", end_date: "2026-05-25" })).toBe(
      "balanced",
    );
  });

  it("uses wandering pace for longer windows", () => {
    expect(inferPaceFromRange({ start_date: "2026-12-24", end_date: "2026-12-30" })).toBe(
      "wandering",
    );
  });
});
