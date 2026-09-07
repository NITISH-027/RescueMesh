"""RescueMesh Pipeline Service.

Module: pipeline.py
Description: Pipeline orchestration and sector enrichment with dynamic OpenStreetMap context.
"""

from typing import Dict, Any
from shapely.geometry import Polygon
from app.services.osm_service import osm_engine


def enrich_cluster(cluster: Dict[str, Any]) -> Dict[str, Any]:
    """Enriches a cluster with real-time, coordinate-specific OpenStreetMap topological telemetry."""
    lat = float(cluster.get("centroid_lat", cluster.get("lat", 29.7604)))
    lon = float(cluster.get("centroid_lon", cluster.get("lon", -95.3698)))
    delta = 0.0025  # ~250m bounding box

    poly = Polygon([
        (lon - delta, lat - delta),
        (lon + delta, lat - delta),
        (lon + delta, lat + delta),
        (lon - delta, lat + delta)
    ])

    # Extract sector-specific isolation and damage ratios
    score_b = cluster.get("score_breakdown", {})
    if isinstance(score_b, dict):
        iso_str = score_b.get("road_isolation", "20.0/22.0")
        dmg_str = score_b.get("damage_density", "30.0/34.0")
        try:
            isolation_ratio = float(iso_str.split("/")[0]) / float(iso_str.split("/")[1])
        except Exception:
            isolation_ratio = float(cluster.get("road_isolation_score", 0.40))

        try:
            damage_density = float(dmg_str.split("/")[0]) / float(dmg_str.split("/")[1])
        except Exception:
            damage_density = 0.50
    else:
        isolation_ratio = float(cluster.get("road_isolation_score", 0.40))
        damage_density = 0.50

    # Compute unique OSM telemetry
    osm_data = osm_engine.analyze_cluster_context(
        cluster_polygon=poly,
        search_radius_m=500.0,
        isolation_ratio=isolation_ratio,
        damage_density=damage_density
    )

    cluster["osm_telemetry"] = osm_data
    return cluster
