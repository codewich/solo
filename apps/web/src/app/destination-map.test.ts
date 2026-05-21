import { render, screen } from "@testing-library/react";
import { createElement } from "react";
import { vi } from "vitest";
import { buildDefaultMapStyle } from "./destination-map";
import { DestinationMap } from "./destination-map";
import { mapViewForBounds } from "./destination-map";
import { mapViewForHome } from "./destination-map";

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
        searchMode: "radius",
        searchBounds: null,
        isDrawingRectangle: false,
        onSearchBoundsChange: vi.fn(),
        onDrawingRectangleChange: vi.fn(),
        showDestinationPins: false,
      }),
    );

    expect(screen.getByLabelText("Search radius 900 km")).toBeInTheDocument();
  });

  it("shows rectangle mode status instead of radius when rectangle search is active", () => {
    render(
      createElement(DestinationMap, {
        destinations: [],
        homeCity: "London",
        homeCoordinates: [-0.1276, 51.5072],
        radiusKm: 900,
        searchMode: "rectangle",
        searchBounds: { west: -1, south: 48, east: 3, north: 52 },
        isDrawingRectangle: false,
        onSearchBoundsChange: vi.fn(),
        onDrawingRectangleChange: vi.fn(),
        showDestinationPins: false,
      }),
    );

    expect(screen.getByLabelText("Rectangle search area")).toHaveTextContent("Rectangle area");
    expect(screen.queryByLabelText("Search radius 900 km")).not.toBeInTheDocument();
  });

  it("centers the map view on the selected home city coordinates", () => {
    expect(mapViewForHome([-3.7038, 40.4168], 1200)).toEqual({
      center: [-3.7038, 40.4168],
      zoom: 4,
    });
  });

  it("centers rectangle searches on the selected bounds instead of the home city", () => {
    expect(mapViewForBounds({ west: 100, south: 20, east: 122, north: 32 })).toEqual({
      center: [111, 26],
      zoom: 4,
    });
  });
});
