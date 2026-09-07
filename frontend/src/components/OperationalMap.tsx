"use client";

import React, { useEffect, useRef, useState } from "react";
import maplibregl, { Map as MapLibreMap, Marker } from "maplibre-gl";
import { ClusterTelemetry } from "@/types/triage";
import {
  Layers,
  Eye,
  Crosshair,
  AlertTriangle,
  Plus,
  Minus,
  RotateCcw,
  Satellite,
  Map as MapIcon,
} from "lucide-react";

interface OperationalMapProps {
  clusters: ClusterTelemetry[];
  selectedCluster: ClusterTelemetry | null;
  onSelectCluster: (cluster: ClusterTelemetry) => void;
}

const HOUSTON_CENTER: [number, number] = [-95.3698, 29.7604];
const DEFAULT_ZOOM = 12.0;

export const OperationalMap: React.FC<OperationalMapProps> = ({
  clusters,
  selectedCluster,
  onSelectCluster,
}) => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const markersRef = useRef<{ [key: string]: Marker }>({});

  const [basemapStyle, setBasemapStyle] = useState<"dark" | "satellite">("satellite");
  const [showRoadBlocks, setShowRoadBlocks] = useState(true);
  const [cursorCoords, setCursorCoords] = useState<{ lat: number; lon: number }>({
    lat: 29.7604,
    lon: -95.3698,
  });
  const [currentZoom, setCurrentZoom] = useState<number>(DEFAULT_ZOOM);

  // Basemap style definitions (Default: Real High-Res Satellite + Reference Labels Hybrid)
  const getMapStyle = (type: "dark" | "satellite"): maplibregl.StyleSpecification => {
    if (type === "dark") {
      // Esri Dark Canvas
      return {
        version: 8,
        sources: {
          "esri-dark-canvas": {
            type: "raster",
            tiles: [
              "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}",
            ],
            tileSize: 256,
            attribution: "© Esri, HERE, Garmin, © OpenStreetMap contributors",
          },
          "esri-dark-reference": {
            type: "raster",
            tiles: [
              "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Reference/MapServer/tile/{z}/{y}/{x}",
            ],
            tileSize: 256,
          },
        },
        layers: [
          {
            id: "esri-dark-base",
            type: "raster",
            source: "esri-dark-canvas",
            minzoom: 0,
            maxzoom: 19,
          },
          {
            id: "esri-dark-labels",
            type: "raster",
            source: "esri-dark-reference",
            minzoom: 0,
            maxzoom: 19,
          },
        ],
      };
    }

    // High-Resolution Satellite Imagery + Subtle Clean Street/Place Labels
    return {
      version: 8,
      sources: {
        "esri-satellite": {
          type: "raster",
          tiles: [
            "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
          ],
          tileSize: 256,
          attribution: "© Esri, Maxar, Earthstar Geographics",
        },
        "esri-places-reference": {
          type: "raster",
          tiles: [
            "https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}",
          ],
          tileSize: 256,
        },
      },
      layers: [
        {
          id: "satellite-layer",
          type: "raster",
          source: "esri-satellite",
          minzoom: 0,
          maxzoom: 19,
        },
        {
          id: "satellite-labels-layer",
          type: "raster",
          source: "esri-places-reference",
          minzoom: 0,
          maxzoom: 19,
          paint: {
            "raster-opacity": 0.75,
          },
        },
      ],
    };
  };

  // Initialize MapLibre GL
  useEffect(() => {
    if (!mapContainerRef.current) return;

    const map = new maplibregl.Map({
      container: mapContainerRef.current,
      style: getMapStyle(basemapStyle),
      center: HOUSTON_CENTER,
      zoom: DEFAULT_ZOOM,
      attributionControl: false,
      pitch: 0,
    });

    map.on("mousemove", (e) => {
      setCursorCoords({
        lat: parseFloat(e.lngLat.lat.toFixed(4)),
        lon: parseFloat(e.lngLat.lng.toFixed(4)),
      });
    });

    map.on("zoom", () => {
      setCurrentZoom(parseFloat(map.getZoom().toFixed(1)));
    });

    map.on("load", () => {
      // 1. Road Ingress Block Vectors Source
      map.addSource("road-blocks", {
        type: "geojson",
        data: {
          type: "FeatureCollection",
          features: [
            {
              type: "Feature",
              properties: { name: "I-10 Buffalo Bayou Breach" },
              geometry: {
                type: "LineString",
                coordinates: [
                  [-95.48, 29.78],
                  [-95.42, 29.775],
                  [-95.36, 29.765],
                ],
              },
            },
            {
              type: "Feature",
              properties: { name: "Loop 610 West Flooding" },
              geometry: {
                type: "LineString",
                coordinates: [
                  [-95.46, 29.80],
                  [-95.46, 29.74],
                  [-95.45, 29.68],
                ],
              },
            },
            {
              type: "Feature",
              properties: { name: "Brays Bayou Inundation" },
              geometry: {
                type: "LineString",
                coordinates: [
                  [-95.45, 29.69],
                  [-95.39, 29.70],
                  [-95.32, 29.71],
                ],
              },
            },
          ],
        },
      });

      // Muted slate-amber tactical corridor vectors
      map.addLayer({
        id: "road-blocks-layer",
        type: "line",
        source: "road-blocks",
        layout: {
          "line-join": "round",
          "line-cap": "round",
        },
        paint: {
          "line-color": "#d97706",
          "line-width": 1.5,
          "line-dasharray": [2, 4],
          "line-opacity": 0.6,
        },
      });
    });

    mapRef.current = map;

    return () => {
      map.remove();
    };
  }, []);

  // Update Basemap Style dynamically
  useEffect(() => {
    if (!mapRef.current) return;
    mapRef.current.setStyle(getMapStyle(basemapStyle));
  }, [basemapStyle]);

  // Update Layer Visibility
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.isStyleLoaded()) return;

    if (map.getLayer("road-blocks-layer")) {
      map.setLayoutProperty(
        "road-blocks-layer",
        "visibility",
        showRoadBlocks ? "visible" : "none"
      );
    }
  }, [showRoadBlocks, basemapStyle]);

  // Sync Tactical GIS Reticle Markers for Clusters
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    // Clear old markers
    Object.values(markersRef.current).forEach((m) => m.remove());
    markersRef.current = {};

    clusters.forEach((cluster) => {
      const isSelected = cluster.cluster_id === selectedCluster?.cluster_id;
      const isP1 = cluster.priority === "P1" || cluster.priority === "CRITICAL";
      const isP2 = cluster.priority === "P2" || cluster.priority === "HIGH";

      const dotColor = isP1
        ? "bg-rose-500"
        : isP2
        ? "bg-amber-400"
        : "bg-zinc-300";

      // Create Tactical GIS Reticle HTML Pin Element
      const el = document.createElement("div");
      el.className = "tactical-marker cursor-pointer select-none flex flex-col items-center";
      el.innerHTML = `
        <div class="flex flex-col items-center">
          <!-- Floating Monospace Micro-Label -->
          <div class="mb-1.5 px-1.5 py-0.5 rounded bg-zinc-950/90 border ${
            isSelected ? "border-white text-white font-bold" : "border-zinc-700/60 text-zinc-300"
          } text-[10px] tracking-wider font-mono shadow-xl flex items-center gap-1">
            <span>${cluster.cluster_id}</span>
            <span class="text-zinc-500 font-normal">TI:${cluster.triage_index}</span>
          </div>

          <!-- Tactical GIS Center Dot & Reticle Ring -->
          <div class="relative flex items-center justify-center w-5 h-5">
            ${
              isP1 && cluster.state !== "DISMISSED"
                ? `<div class="absolute inset-0 rounded-full ring-1 ring-rose-400/40 marker-pulse-ring pointer-events-none"></div>`
                : isSelected
                ? `<div class="absolute inset-0 rounded-full ring-1 ring-white/60 pointer-events-none"></div>`
                : ""
            }
            <div class="w-2 h-2 rounded-full ${dotColor} ${
              isSelected ? "ring-2 ring-white ring-offset-1 ring-offset-black" : "ring-1 ring-black"
            }"></div>
          </div>
        </div>
      `;

      el.addEventListener("click", (e) => {
        e.stopPropagation();
        onSelectCluster(cluster);
      });

      const marker = new maplibregl.Marker({ element: el })
        .setLngLat([cluster.centroid_lon, cluster.centroid_lat])
        .addTo(map);

      markersRef.current[cluster.cluster_id] = marker;
    });
  }, [clusters, selectedCluster, onSelectCluster]);

  // Smooth Camera Fly-To when selectedCluster changes
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !selectedCluster) return;

    map.flyTo({
      center: [selectedCluster.centroid_lon, selectedCluster.centroid_lat],
      zoom: 13.8,
      speed: 1.2,
      curve: 1.4,
      essential: true,
    });
  }, [selectedCluster]);

  const handleZoomIn = () => mapRef.current?.zoomIn();
  const handleZoomOut = () => mapRef.current?.zoomOut();
  const handleResetView = () => {
    mapRef.current?.flyTo({
      center: HOUSTON_CENTER,
      zoom: DEFAULT_ZOOM,
      speed: 1.2,
    });
  };

  return (
    <div className="absolute inset-0 w-full h-full z-0 overflow-hidden bg-[#0A0B0E] select-none">
      {/* Map Container */}
      <div ref={mapContainerRef} className="w-full h-full" />

      {/* Floating Layer Controls (Top Left below floating header) */}
      <div className="absolute top-16 left-88 z-10 hidden md:flex items-center gap-1 backdrop-blur-xl bg-zinc-950/85 border border-zinc-800/80 p-1 rounded-lg shadow-xl text-xs font-sans">
        <button
          onClick={() => setBasemapStyle(basemapStyle === "dark" ? "satellite" : "dark")}
          className="px-2.5 py-1 rounded text-zinc-300 hover:text-white hover:bg-zinc-800/60 transition-colors flex items-center gap-1.5"
        >
          {basemapStyle === "satellite" ? (
            <>
              <Satellite className="h-3.5 w-3.5 text-zinc-300" />
              <span>Esri Satellite</span>
            </>
          ) : (
            <>
              <MapIcon className="h-3.5 w-3.5 text-zinc-300" />
              <span>Dark Canvas</span>
            </>
          )}
        </button>

        <span className="w-px h-3.5 bg-zinc-800 mx-0.5" />

        <button
          onClick={() => setShowRoadBlocks(!showRoadBlocks)}
          className={`px-2.5 py-1 rounded transition-colors flex items-center gap-1.5 ${
            showRoadBlocks
              ? "bg-zinc-800 text-amber-300 font-medium"
              : "text-zinc-500 hover:text-zinc-300"
          }`}
        >
          <AlertTriangle className="h-3.5 w-3.5" />
          <span>Road Ingress</span>
        </button>
      </div>

      {/* Floating GIS Zoom & Navigation Controls (Bottom Left) */}
      <div className="absolute bottom-5 left-88 z-10 hidden md:flex flex-col gap-1 backdrop-blur-xl bg-zinc-950/85 border border-zinc-800/80 p-1 rounded-lg shadow-xl text-zinc-300">
        <button
          onClick={handleZoomIn}
          className="p-1.5 rounded hover:bg-zinc-800 hover:text-white transition-colors"
          title="Zoom In"
        >
          <Plus className="h-4 w-4" />
        </button>
        <button
          onClick={handleZoomOut}
          className="p-1.5 rounded hover:bg-zinc-800 hover:text-white transition-colors"
          title="Zoom Out"
        >
          <Minus className="h-4 w-4" />
        </button>
        <button
          onClick={handleResetView}
          className="p-1.5 rounded hover:bg-zinc-800 hover:text-white transition-colors"
          title="Reset Houston AOI View"
        >
          <RotateCcw className="h-3.5 w-3.5" />
        </button>
      </div>

      {/* Floating Telemetry Coordinates Bar (Bottom Center - PRESERVED EXACTLY) */}
      <div className="absolute bottom-5 left-1/2 -translate-x-1/2 z-10 backdrop-blur-xl bg-slate-950/80 border border-white/10 px-4 py-1.5 rounded-full shadow-xl flex items-center gap-3 text-[11px] font-mono text-slate-400">
        <div className="flex items-center gap-1.5 text-slate-300">
          <Crosshair className="h-3.5 w-3.5 text-blue-400" />
          <span>
            {cursorCoords.lat.toFixed(4)}°N, {Math.abs(cursorCoords.lon).toFixed(4)}°W
          </span>
        </div>
        <span className="text-slate-700">•</span>
        <span>Zoom: {currentZoom}x</span>
        <span className="text-slate-700">•</span>
        <span>EPS: 800m Metric</span>
        <span className="text-slate-700">•</span>
        <span>EPSG:3857</span>
      </div>
    </div>
  );
};
