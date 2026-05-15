"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import "maplibre-gl/dist/maplibre-gl.css";

type MapDestination = {
  city: string;
  country: string;
  score: number;
  summary: string;
};

type DestinationMapProps = {
  destinations: MapDestination[];
  homeCity: string;
};

const defaultMapStyle = "https://demotiles.maplibre.org/style.json";

const cityCoordinates: Record<string, [number, number]> = {
  Copenhagen: [12.5683, 55.6761],
  Lisbon: [-9.1393, 38.7223],
  London: [-0.1276, 51.5072],
  Porto: [-8.6291, 41.1579],
  Seville: [-5.9845, 37.3891],
};

export function DestinationMap({ destinations, homeCity }: DestinationMapProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<import("maplibre-gl").Map | null>(null);
  const markerRefs = useRef<import("maplibre-gl").Marker[]>([]);
  const resizeObserverRef = useRef<ResizeObserver | null>(null);
  const [isMapReady, setIsMapReady] = useState(false);
  const mapStyle = process.env.NEXT_PUBLIC_MAP_STYLE_URL ?? defaultMapStyle;
  const visibleDestinations = useMemo(
    () =>
      destinations
        .map((destination) => ({
          ...destination,
          coordinates: cityCoordinates[destination.city],
        }))
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
      mapRef.current.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
      mapRef.current.once("load", () => {
        mapRef.current?.resize();
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
      setIsMapReady(false);
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

      const homeCoordinates = cityCoordinates[homeCity] ?? cityCoordinates.London;
      const homeMarker = new maplibregl.Marker({ color: "#18221d" })
        .setLngLat(homeCoordinates)
        .setPopup(new maplibregl.Popup({ offset: 18 }).setText(`${homeCity} home base`))
        .addTo(map);
      markerRefs.current.push(homeMarker);

      visibleDestinations.forEach((destination) => {
        const marker = new maplibregl.Marker({ color: "#24745a" })
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

    renderMarkers();

    return () => {
      isMounted = false;
    };
  }, [homeCity, isMapReady, visibleDestinations]);

  return (
    <section className="map real-map" aria-label="Europe destination map">
      <div className="map-canvas" data-testid="maplibre-map" ref={containerRef} />
      <div className="map-overlay-pins" aria-label="Visible destination markers">
        <div className="map-chip map-chip-home">
          {homeCity}
          <span>home base</span>
        </div>
        {visibleDestinations.map((destination) => (
          <div className="map-chip" key={destination.city}>
            {destination.city} {destination.score}
            <span>{destination.summary}</span>
          </div>
        ))}
      </div>
    </section>
  );
}
