import { buildDefaultMapStyle } from "./destination-map";

describe("DestinationMap city labels", () => {
  it("uses OpenStreetMap raster tiles for zoom-level city labels", () => {
    const style = buildDefaultMapStyle();

    expect(style.sources.osm).toEqual(
      expect.objectContaining({
        type: "raster",
        tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
      }),
    );
    expect(style.layers).toEqual([
      expect.objectContaining({ id: "osm-raster", source: "osm", type: "raster" }),
    ]);
  });

  it("returns a stable default style object across renders", () => {
    expect(buildDefaultMapStyle()).toBe(buildDefaultMapStyle());
  });
});
