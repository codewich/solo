import { render, screen } from "@testing-library/react";
import { createElement } from "react";
import { buildDefaultMapStyle } from "./destination-map";
import { DestinationMap } from "./destination-map";

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

  it("shows the selected search radius", () => {
    render(
      createElement(DestinationMap, {
        destinations: [],
        homeCity: "London",
        homeCoordinates: [-0.1276, 51.5072],
        radiusKm: 900,
        showDestinationPins: false,
      }),
    );

    expect(screen.getByLabelText("Search radius 900 km")).toBeInTheDocument();
  });
});
