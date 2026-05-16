"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import "maplibre-gl/dist/maplibre-gl.css";

type MapDestination = {
  city: string;
  country: string;
  score: number;
  summary: string;
  coordinates?: [number, number];
};

type DestinationMapProps = {
  destinations: MapDestination[];
  homeCity: string;
  homeCoordinates: [number, number];
  radiusKm: number;
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

export function DestinationMap({
  destinations,
  homeCity,
  homeCoordinates,
  radiusKm,
  showDestinationPins,
}: DestinationMapProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<import("maplibre-gl").Map | null>(null);
  const markerRefs = useRef<import("maplibre-gl").Marker[]>([]);
  const resizeObserverRef = useRef<ResizeObserver | null>(null);
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
        center: [2.5, 48.8],
        container: containerRef.current,
        style: mapStyle,
        zoom: 4,
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
        .setLngLat(homeCoordinates)
        .setPopup(new maplibregl.Popup({ offset: 18 }).setText(`${homeCity} home base`))
        .addTo(map);
      markerRefs.current.push(homeMarker);

      if (!map.getSource("search-radius")) {
        map.addSource("search-radius", {
          type: "geojson",
          data: circleFeature(homeCoordinates, radiusKm),
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
      } else {
        const source = map.getSource("search-radius") as
          | { setData: (data: ReturnType<typeof circleFeature>) => void }
          | undefined;
        source?.setData(circleFeature(homeCoordinates, radiusKm));
      }

      if (showDestinationPins) {
        visibleDestinations.forEach((destination) => {
          const marker = new maplibregl.Marker({
            element: createCityMarkerElement(destination.city, "destination"),
          })
            .setLngLat(destination.coordinates)
            .setPopup(
              new maplibregl.Popup({ offset: 18 }).setText(
                `${destination.city}, ${destination.country}: ${destination.score}. ${destination.summary}`,
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
  }, [homeCity, homeCoordinates, isMapReady, radiusKm, showDestinationPins, visibleDestinations]);

  return (
    <section className="map real-map" aria-label="Europe destination map">
      <div className="map-canvas" data-testid="maplibre-map" ref={containerRef} />
      <div className="map-overlay-pins" aria-label="Visible destination markers">
        <div className="map-chip map-chip-home">{homeCity} home base</div>
        <div className="map-chip map-chip-radius" aria-label={`Search radius ${radiusKm} km`}>
          {radiusKm} km radius
        </div>
        {showDestinationPins
          ? visibleDestinations.map((destination) => (
              <div
                className="map-chip"
                key={destination.city}
                aria-label={`${destination.city} city marker`}
              >
                {destination.city} {destination.score}
                <span>{destination.summary}</span>
              </div>
            ))
          : null}
      </div>
    </section>
  );
}
