"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import "maplibre-gl/dist/maplibre-gl.css";
import type { SearchBounds, SearchMode } from "@/lib/types";

type MapDestination = {
  city: string;
  country: string;
  score?: number;
  summary?: string;
  coordinates?: [number, number];
};

type DestinationMapProps = {
  destinations: MapDestination[];
  homeCity: string;
  homeCoordinates: [number, number];
  radiusKm: number;
  searchMode: SearchMode;
  searchBounds: SearchBounds | null;
  isDrawingRectangle: boolean;
  onSearchBoundsChange: (bounds: SearchBounds | null) => void;
  onDrawingRectangleChange: (isDrawing: boolean) => void;
  showDestinationPins: boolean;
};

const defaultMapStyle = {
  version: 8 as const,
  glyphs: "https://demotiles.maplibre.org/font/{fontstack}/{range}.pbf",
  sources: {
    osm: {
      type: "raster" as const,
      tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
      tileSize: 256,
      attribution: "OpenStreetMap contributors",
    },
  },
  layers: [
    {
      id: "osm-raster",
      type: "raster" as const,
      source: "osm",
    },
  ],
};

export function buildDefaultMapStyle() {
  return defaultMapStyle;
}

function zoomForRadius(radiusKm: number): number {
  if (radiusKm <= 900) {
    return 5;
  }
  if (radiusKm <= 2200) {
    return 4;
  }
  return 3;
}

export function mapViewForHome(homeCoordinates: [number, number], radiusKm: number) {
  return {
    center: homeCoordinates,
    zoom: zoomForRadius(radiusKm),
  };
}

export function mapViewForBounds(bounds: SearchBounds) {
  const longitudeSpan = Math.abs(bounds.east - bounds.west);
  const latitudeSpan = Math.abs(bounds.north - bounds.south);
  const span = Math.max(longitudeSpan, latitudeSpan);
  const zoom = span <= 5 ? 6 : span <= 15 ? 5 : span <= 30 ? 4 : 3;

  return {
    center: [Number(((bounds.west + bounds.east) / 2).toFixed(6)), Number(((bounds.south + bounds.north) / 2).toFixed(6))] as [number, number],
    zoom,
  };
}

function createCityMarkerElement(city: string, variant: "home" | "destination"): HTMLDivElement {
  const marker = document.createElement("div");
  marker.className = `city-marker city-marker-${variant}`;
  marker.setAttribute("aria-label", `${city} city marker`);

  const dot = document.createElement("span");
  dot.className = "city-marker-dot";
  dot.setAttribute("aria-hidden", "true");

  const label = document.createElement("span");
  label.className = "city-marker-label";
  label.textContent = city;

  marker.append(dot, label);
  return marker;
}

function circleFeature(center: [number, number], radiusKm: number) {
  const points = 96;
  const earthRadiusKm = 6371;
  const [longitude, latitude] = center;
  const latitudeRadians = (latitude * Math.PI) / 180;
  const coordinates = Array.from({ length: points + 1 }, (_, index) => {
    const angle = (index / points) * Math.PI * 2;
    const latitudeOffset = (radiusKm / earthRadiusKm) * (180 / Math.PI) * Math.sin(angle);
    const longitudeOffset =
      ((radiusKm / earthRadiusKm) * (180 / Math.PI) * Math.cos(angle)) /
      Math.cos(latitudeRadians);
    return [longitude + longitudeOffset, latitude + latitudeOffset];
  });

  return {
    type: "Feature" as const,
    properties: {},
    geometry: {
      type: "Polygon" as const,
      coordinates: [coordinates],
    },
  };
}

function rectangleFeature(bounds: SearchBounds) {
  const coordinates = [
    [bounds.west, bounds.south],
    [bounds.east, bounds.south],
    [bounds.east, bounds.north],
    [bounds.west, bounds.north],
    [bounds.west, bounds.south],
  ];

  return {
    type: "Feature" as const,
    properties: {},
    geometry: {
      type: "Polygon" as const,
      coordinates: [coordinates],
    },
  };
}

function removeLayerIfExists(map: import("maplibre-gl").Map, layerId: string) {
  if (map.getLayer(layerId)) {
    map.removeLayer(layerId);
  }
}

function removeSourceIfExists(map: import("maplibre-gl").Map, sourceId: string) {
  if (map.getSource(sourceId)) {
    map.removeSource(sourceId);
  }
}

function normalizedBounds(
  start: { lng: number; lat: number },
  end: { lng: number; lat: number },
): SearchBounds | null {
  const west = Math.max(-180, Math.min(start.lng, end.lng));
  const east = Math.min(180, Math.max(start.lng, end.lng));
  const south = Math.max(-90, Math.min(start.lat, end.lat));
  const north = Math.min(90, Math.max(start.lat, end.lat));

  if (west === east || south === north) {
    return null;
  }

  return { west, south, east, north };
}

export function DestinationMap({
  destinations,
  homeCity,
  homeCoordinates,
  radiusKm,
  searchMode,
  searchBounds,
  isDrawingRectangle,
  onSearchBoundsChange,
  onDrawingRectangleChange,
  showDestinationPins,
}: DestinationMapProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<import("maplibre-gl").Map | null>(null);
  const markerRefs = useRef<import("maplibre-gl").Marker[]>([]);
  const resizeObserverRef = useRef<ResizeObserver | null>(null);
  const homeLongitude = homeCoordinates[0];
  const homeLatitude = homeCoordinates[1];
  const currentHomeCoordinates = useMemo(
    () => [homeLongitude, homeLatitude] as [number, number],
    [homeLongitude, homeLatitude],
  );
  const initialMapViewRef = useRef(mapViewForHome(currentHomeCoordinates, radiusKm));
  const [isMapReady, setIsMapReady] = useState(false);
  const mapStyle = process.env.NEXT_PUBLIC_MAP_STYLE_URL ?? defaultMapStyle;
  const visibleDestinations = useMemo(
    () =>
      destinations
        .filter(
          (destination): destination is MapDestination & { coordinates: [number, number] } =>
            Boolean(destination.coordinates),
        ),
    [destinations],
  );

  useEffect(() => {
    let isMounted = true;

    async function loadMap() {
      if (!containerRef.current || mapRef.current || navigator.userAgent.includes("jsdom")) {
        return;
      }

      const maplibregl = await import("maplibre-gl");
      if (!isMounted || !containerRef.current) {
        return;
      }

      mapRef.current = new maplibregl.Map({
        attributionControl: { compact: true },
        ...initialMapViewRef.current,
        container: containerRef.current,
        style: mapStyle,
      });
      mapRef.current.addControl(
        new maplibregl.NavigationControl({ showCompass: false }),
        "top-right",
      );
      mapRef.current.once("load", () => {
        const map = mapRef.current;
        if (!map) {
          return;
        }

        map.resize();
        setIsMapReady(true);
      });
      resizeObserverRef.current = new ResizeObserver(() => mapRef.current?.resize());
      resizeObserverRef.current.observe(containerRef.current);
    }

    loadMap();

    return () => {
      isMounted = false;
      markerRefs.current.forEach((marker) => marker.remove());
      markerRefs.current = [];
      resizeObserverRef.current?.disconnect();
      resizeObserverRef.current = null;
      mapRef.current?.remove();
      mapRef.current = null;
    };
  }, [mapStyle]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !isMapReady) {
      return;
    }
    if (searchMode === "rectangle" && searchBounds) {
      map.jumpTo(mapViewForBounds(searchBounds));
      return;
    }
    map.jumpTo(mapViewForHome(currentHomeCoordinates, radiusKm));
  }, [currentHomeCoordinates, isMapReady, radiusKm, searchBounds, searchMode]);

  useEffect(() => {
    let isMounted = true;

    async function renderMarkers() {
      const map = mapRef.current;
      if (!map || !isMapReady) {
        return;
      }

      const maplibregl = await import("maplibre-gl");
      if (!isMounted) {
        return;
      }

      markerRefs.current.forEach((marker) => marker.remove());
      markerRefs.current = [];

      const homeMarker = new maplibregl.Marker({
        element: createCityMarkerElement(homeCity, "home"),
      })
        .setLngLat(currentHomeCoordinates)
        .setPopup(new maplibregl.Popup({ offset: 18 }).setText(`${homeCity} home base`))
        .addTo(map);
      markerRefs.current.push(homeMarker);

      if (searchMode === "radius" && !map.getSource("search-radius")) {
        removeLayerIfExists(map, "search-rectangle-fill");
        removeLayerIfExists(map, "search-rectangle-line");
        removeSourceIfExists(map, "search-rectangle");
        map.addSource("search-radius", {
          type: "geojson",
          data: circleFeature(currentHomeCoordinates, radiusKm),
        });
        map.addLayer({
          id: "search-radius-fill",
          type: "fill",
          source: "search-radius",
          paint: {
            "fill-color": "#24745a",
            "fill-opacity": 0.12,
          },
        });
        map.addLayer({
          id: "search-radius-line",
          type: "line",
          source: "search-radius",
          paint: {
            "line-color": "#24745a",
            "line-opacity": 0.48,
            "line-width": 2,
          },
        });
      } else if (searchMode === "radius") {
        const source = map.getSource("search-radius") as
          | { setData: (data: ReturnType<typeof circleFeature>) => void }
          | undefined;
        source?.setData(circleFeature(currentHomeCoordinates, radiusKm));
      } else {
        removeLayerIfExists(map, "search-radius-fill");
        removeLayerIfExists(map, "search-radius-line");
        removeSourceIfExists(map, "search-radius");
        if (searchBounds && !map.getSource("search-rectangle")) {
          map.addSource("search-rectangle", {
            type: "geojson",
            data: rectangleFeature(searchBounds),
          });
          map.addLayer({
            id: "search-rectangle-fill",
            type: "fill",
            source: "search-rectangle",
            paint: {
              "fill-color": "#24745a",
              "fill-opacity": 0.12,
            },
          });
          map.addLayer({
            id: "search-rectangle-line",
            type: "line",
            source: "search-rectangle",
            paint: {
              "line-color": "#24745a",
              "line-opacity": 0.62,
              "line-width": 2,
            },
          });
        } else if (searchBounds) {
          const source = map.getSource("search-rectangle") as
            | { setData: (data: ReturnType<typeof rectangleFeature>) => void }
            | undefined;
          source?.setData(rectangleFeature(searchBounds));
        } else {
          removeLayerIfExists(map, "search-rectangle-fill");
          removeLayerIfExists(map, "search-rectangle-line");
          removeSourceIfExists(map, "search-rectangle");
        }
      }

      if (showDestinationPins) {
        visibleDestinations.forEach((destination) => {
          const marker = new maplibregl.Marker({
            element: createCityMarkerElement(destination.city, "destination"),
          })
            .setLngLat(destination.coordinates)
            .setPopup(
              new maplibregl.Popup({ offset: 18 }).setText(
                `${destination.city}, ${destination.country}${
                  destination.score !== undefined ? `: ${destination.score}` : ""
                }. ${destination.summary ?? ""}`.trim(),
              ),
            )
            .addTo(map);
          markerRefs.current.push(marker);
        });
      }
    }

    renderMarkers();

    return () => {
      isMounted = false;
    };
  }, [
    homeCity,
    currentHomeCoordinates,
    isMapReady,
    radiusKm,
    searchBounds,
    searchMode,
    showDestinationPins,
    visibleDestinations,
  ]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !isMapReady || searchMode !== "rectangle" || !isDrawingRectangle) {
      map?.dragPan.enable();
      return;
    }

    const activeMap = map;
    let startPoint: { lng: number; lat: number } | null = null;

    function finishDrawing() {
      activeMap.dragPan.enable();
      onDrawingRectangleChange(false);
    }

    function handleMouseDown(event: import("maplibre-gl").MapMouseEvent) {
      startPoint = event.lngLat;
      activeMap.dragPan.disable();
    }

    function handleMouseMove(event: import("maplibre-gl").MapMouseEvent) {
      if (!startPoint) {
        return;
      }
      const nextBounds = normalizedBounds(startPoint, event.lngLat);
      if (nextBounds) {
        onSearchBoundsChange(nextBounds);
      }
    }

    function handleMouseUp(event: import("maplibre-gl").MapMouseEvent) {
      if (startPoint) {
        const nextBounds = normalizedBounds(startPoint, event.lngLat);
        if (nextBounds) {
          onSearchBoundsChange(nextBounds);
        }
      }
      startPoint = null;
      finishDrawing();
    }

    activeMap.getCanvas().style.cursor = "crosshair";
    activeMap.on("mousedown", handleMouseDown);
    activeMap.on("mousemove", handleMouseMove);
    activeMap.on("mouseup", handleMouseUp);

    return () => {
      activeMap.getCanvas().style.cursor = "";
      activeMap.off("mousedown", handleMouseDown);
      activeMap.off("mousemove", handleMouseMove);
      activeMap.off("mouseup", handleMouseUp);
      activeMap.dragPan.enable();
    };
  }, [
    isDrawingRectangle,
    isMapReady,
    onDrawingRectangleChange,
    onSearchBoundsChange,
    searchMode,
  ]);

  return (
    <section className="map real-map" aria-label="Europe destination map">
      <div className="map-canvas" data-testid="maplibre-map" ref={containerRef} />
      <div className="map-overlay-pins" aria-label="Visible destination markers">
        <div className="map-chip map-chip-home">{homeCity} home base</div>
        {searchMode === "radius" ? (
          <div className="map-chip map-chip-radius" aria-label={`Search radius ${radiusKm} km`}>
            {radiusKm} km radius
          </div>
        ) : (
          <div className="map-chip map-chip-radius" aria-label="Rectangle search area">
            {searchBounds ? "Rectangle area" : "Draw rectangle"}
          </div>
        )}
        {showDestinationPins
          ? visibleDestinations.map((destination) => (
              <div
                className="map-chip"
                key={destination.city}
                aria-label={`${destination.city} city marker`}
              >
                {destination.city}
                {destination.score !== undefined ? ` ${destination.score}` : null}
                {destination.summary ? <span>{destination.summary}</span> : null}
              </div>
            ))
          : null}
      </div>
    </section>
  );
}
