"""Spatial Clustering Service for RescueMesh.

Clusters discrete damage/flood evidence points into coherent geographic response sectors
using DBSCAN with metric Haversine projections and Shapely polygonization.
"""

import math
from typing import List, Dict, Any, Tuple
import numpy as np
from sklearn.cluster import DBSCAN
from shapely.geometry import MultiPoint, Point, Polygon, mapping

from app.models.schemas import TileAnalysisResult, SectorCluster, GeoPoint, PriorityLevel
from app.config import settings

# Earth radius in meters
EARTH_RADIUS_METERS = 6371000.0


def cluster_damage_assets(
    assets: List[Dict[str, Any]],
    eps_meters: float = 200.0,
    min_samples: int = 3,
    evidence_threshold: float = 0.45,
) -> List[Dict[str, Any]]:
    """Clusters asset damage evidence points using Haversine DBSCAN.

    Args:
        assets: List of asset/tile dicts with 'id'/'tile_id', 'lat', 'lon', and evidence score ('evidence_score' or 'E_i').
        eps_meters: Spatial neighborhood threshold in meters.
        min_samples: Core point density threshold.
        evidence_threshold: Minimum evidence score required for inclusion (default: 0.45).

    Returns:
        List of structured cluster dictionaries with geometry, centroid, area, and member assets.
    """
    if not assets:
        return []

    # 1. Filter assets with valid evidence E_i >= evidence_threshold
    filtered_assets = []
    for a in assets:
        e_i = a.get("evidence_score", a.get("E_i", a.get("scores", {}).get("composite_triage_score", 0.0) / 100.0))
        if e_i >= evidence_threshold:
            filtered_assets.append(a)

    if not filtered_assets:
        # Fallback: if all evidence is low, retain top assets to avoid empty response
        filtered_assets = assets

    # 2. Convert coordinates (lat, lon) to radians for Haversine distance
    coords_deg = np.array([
        [float(a.get("lat", a.get("location", {}).get("latitude", 0.0))),
         float(a.get("lon", a.get("location", {}).get("longitude", 0.0)))]
        for a in filtered_assets
    ])
    coords_rad = np.radians(coords_deg)

    # Convert eps meters to radians
    eps_rad = eps_meters / EARTH_RADIUS_METERS

    # 3. Run Haversine DBSCAN
    if len(coords_rad) >= min_samples:
        db = DBSCAN(eps=eps_rad, min_samples=min_samples, metric="haversine", algorithm="ball_tree")
        labels = db.fit_predict(coords_rad)
    else:
        # Single cluster or noise if fewer points than min_samples
        labels = np.array([0 if len(coords_rad) > 0 else -1 for _ in coords_rad])

    # 4. Aggregate clusters and handle noise (-1) as isolated single-asset candidates
    clusters_dict: Dict[int, List[Dict[str, Any]]] = {}
    isolated_assets: List[Dict[str, Any]] = []

    for label, asset in zip(labels, filtered_assets):
        if label == -1:
            isolated_assets.append(asset)
        else:
            clusters_dict.setdefault(label, []).append(asset)

    results: List[Dict[str, Any]] = []
    cluster_counter = 1

    # Process grouped DBSCAN clusters
    for label, group in clusters_dict.items():
        cluster_info = _build_cluster_payload(
            cluster_id=f"CLUSTER-{cluster_counter:02d}",
            label=int(label),
            group=group,
            is_isolated=False
        )
        results.append(cluster_info)
        cluster_counter += 1

    # Process isolated noise points (-1) so critical isolated assets are preserved
    for iso_idx, iso_asset in enumerate(isolated_assets):
        cluster_info = _build_cluster_payload(
            cluster_id=f"CLUSTER-ISO-{cluster_counter:02d}",
            label=-1,
            group=[iso_asset],
            is_isolated=True
        )
        results.append(cluster_info)
        cluster_counter += 1

    return results


def _build_cluster_payload(
    cluster_id: str,
    label: int,
    group: List[Dict[str, Any]],
    is_isolated: bool = False
) -> Dict[str, Any]:
    """Helper to compute centroid, convex hull boundary polygon, area (km2), and radius (m)."""
    lats = [float(a.get("lat", a.get("location", {}).get("latitude", 0.0))) for a in group]
    lons = [float(a.get("lon", a.get("location", {}).get("longitude", 0.0))) for a in group]
    asset_ids = [str(a.get("id", a.get("tile_id", f"asset_{idx}"))) for idx, a in enumerate(group)]

    centroid_lat = float(np.mean(lats))
    centroid_lon = float(np.mean(lons))

    # Construct geometry polygon using Shapely
    points = [Point(lon, lat) for lon, lat in zip(lons, lats)]
    if len(points) >= 3:
        hull = MultiPoint(points).convex_hull
        polygon_geom = hull.buffer(0.0003)  # ~30-33m expansion buffer
    elif len(points) == 2:
        hull = MultiPoint(points).convex_hull
        polygon_geom = hull.buffer(0.0003)
    else:
        polygon_geom = points[0].buffer(0.0003)

    # Calculate area in km2 (geodesic degree-to-km transformation at centroid lat)
    lat_km_per_deg = 111.139
    lon_km_per_deg = 111.139 * math.cos(math.radians(centroid_lat))
    poly_deg2 = polygon_geom.area
    area_km2 = max(0.005, float(poly_deg2 * lat_km_per_deg * lon_km_per_deg))

    # Estimated radius in meters
    radius_meters = max(25.0, math.sqrt((area_km2 * 1e6) / math.pi))

    min_lon, min_lat, max_lon, max_lat = polygon_geom.bounds

    return {
        "cluster_id": cluster_id,
        "cluster_label": label,
        "is_isolated_asset": is_isolated,
        "centroid": {
            "latitude": round(centroid_lat, 6),
            "longitude": round(centroid_lon, 6)
        },
        "bounding_box": [
            round(min_lon, 6),
            round(min_lat, 6),
            round(max_lon, 6),
            round(max_lat, 6)
        ],
        "geometry": mapping(polygon_geom),
        "area_km2": round(area_km2, 4),
        "radius_meters": round(radius_meters, 1),
        "asset_count": len(group),
        "member_asset_ids": asset_ids,
        "member_assets": group,
    }


class SpatialClusteringService:
    """Aggregates individual tiles/assets into actionable operational sectors."""

    SECTOR_CODENAMES = [
        "Sector Alpha (Buffalo Bayou)",
        "Sector Bravo (Greenspoint Hub)",
        "Sector Charlie (Meyerland Basin)",
        "Sector Delta (San Jacinto East)",
        "Sector Echo (Addicks Reservoir Spill)",
        "Sector Foxtrot (Clear Creek Corridor)",
        "Sector Golf (Port Houston North)",
        "Sector Hotel (Medical Center Perimeter)"
    ]

    RECOMMENDED_ACTIONS = {
        PriorityLevel.CRITICAL: "Immediate Swift Water Rescue Deployment & Aerial Extraction",
        PriorityLevel.HIGH: "Amphibious Vehicle Patrol & High-Water Supply Drop",
        PriorityLevel.MEDIUM: "Secondary Evacuation Route Clearing & Substation Inspection",
        PriorityLevel.LOW: "Routine Reconnaissance & Perimeter Monitoring",
    }

    def cluster_damage_assets(
        self,
        assets: List[Dict[str, Any]],
        eps_meters: float = 200.0,
        min_samples: int = 3,
        evidence_threshold: float = 0.45,
    ) -> List[Dict[str, Any]]:
        return cluster_damage_assets(
            assets=assets,
            eps_meters=eps_meters,
            min_samples=min_samples,
            evidence_threshold=evidence_threshold,
        )

    def cluster_tiles(self, tiles: List[TileAnalysisResult]) -> List[SectorCluster]:
        """Backward-compatible cluster partitioner for TileAnalysisResult objects."""
        if not tiles:
            return []

        # Convert tiles to asset dicts
        asset_dicts = []
        for t in tiles:
            asset_dicts.append({
                "tile_id": t.tile_id,
                "filename": t.filename,
                "lat": t.location.latitude,
                "lon": t.location.longitude,
                "evidence_score": t.scores.composite_triage_score / 100.0,
                "scores": t.scores.dict(),
                "tile_obj": t
            })

        # Run DBSCAN clustering with calibrated 800m neighborhood
        clusters_raw = cluster_damage_assets(asset_dicts, eps_meters=800.0, min_samples=2, evidence_threshold=0.0)

        sector_clusters: List[SectorCluster] = []
        for idx, c in enumerate(clusters_raw):
            name = self.SECTOR_CODENAMES[idx % len(self.SECTOR_CODENAMES)]
            member_tiles = [item["tile_obj"] for item in c["member_assets"] if "tile_obj" in item]
            if not member_tiles:
                continue

            scores = [t.scores.composite_triage_score for t in member_tiles]
            mean_score = float(np.mean(scores))
            max_score = float(np.max(scores))

            if max_score >= 75.0 or mean_score >= 65.0:
                urgency = PriorityLevel.CRITICAL
                primary_threat = "Severe Rapid Inundation & Trapped Civilians"
                isolated_pop = int(1200 + (max_score * 45))
            elif max_score >= 50.0:
                urgency = PriorityLevel.HIGH
                primary_threat = "Roadway Inundation & Structural Debris"
                isolated_pop = int(600 + (max_score * 25))
            else:
                urgency = PriorityLevel.MEDIUM
                primary_threat = "Local Drainage Backflow & Power Grid Interruption"
                isolated_pop = int(200 + (max_score * 10))

            sector = SectorCluster(
                sector_id=f"SEC-{chr(65 + idx)}",
                sector_name=name,
                center=GeoPoint(
                    latitude=c["centroid"]["latitude"],
                    longitude=c["centroid"]["longitude"]
                ),
                bounding_box=c["bounding_box"],
                tile_count=len(member_tiles),
                mean_triage_score=round(mean_score, 1),
                max_triage_score=round(max_score, 1),
                urgency_level=urgency,
                primary_threat=primary_threat,
                estimated_isolated_pop=isolated_pop,
                recommended_action=self.RECOMMENDED_ACTIONS[urgency],
                tiles=member_tiles,
            )
            sector_clusters.append(sector)

        return sector_clusters


clustering_service = SpatialClusteringService()
