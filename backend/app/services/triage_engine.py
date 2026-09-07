"""Triage Engine for RescueMesh.

Implements the Multi-Factor Decision Analysis (MCDA) Triage Index formula to rank
spatial damage clusters and individual assets by operational urgency.
"""

from typing import Dict, Any, List, Optional
import numpy as np

from app.config import settings, TriageHeuristicWeights
from app.models.schemas import PriorityLevel, DamageScoreBreakdown, GeoPoint


class TriageEngine:
    """Multi-Criteria Decision Analysis (MCDA) triage scoring and ranking engine."""

    def __init__(self, custom_weights: Optional[TriageHeuristicWeights] = None):
        self.weights = custom_weights or settings.TRIAGE_WEIGHTS

    def update_weights(self, new_weights: TriageHeuristicWeights):
        """Updates runtime dynamic heuristic weights."""
        self.weights = new_weights

    def evaluate_cluster_triage(
        self,
        cluster: Dict[str, Any],
        blocked_road_ratio: Optional[float] = None,
        has_ingress_within_500m: Optional[bool] = None,
        population_exposure: Optional[float] = None,
        critical_facility_distances_km: Optional[List[float]] = None,
    ) -> Dict[str, Any]:
        """Calculates MCDA Composite Triage Index (TI_c in [0, 100]) and priority tier for a spatial cluster.

        Formulation:
        1. Damage Evidence Density (D_c):
           D_c = min(1.0, sum(E_i) / (10.0 * (A_c + 0.01)))
        2. Road Network Isolation (A_c):
           A_c = 0.6 * blocked_ratio + 0.4 * (1 if no ingress else 0)
        3. Vulnerability / Critical Facilities (V_c):
           V_c = min(1.0, 0.5 * pop_exposure + 0.5 * sum(1 / (dist_km + 0.1)))
        4. Scale of Destruction (S_c):
           S_c = min(1.0, sum(I(E_i >= 0.65)) / 10.0)
        5. Information Gap / Uncertainty (U_c):
           U_c = 1.0 - (1 / |c|) * sum(Q_i * p_i)

        Composite Triage Index:
        TI_c = 100 * (0.34 * D_c + 0.22 * A_c + 0.20 * V_c + 0.14 * S_c + 0.10 * U_c)
        """
        member_assets = cluster.get("member_assets", [])
        area_km2 = float(cluster.get("area_km2", 0.05))

        if not member_assets:
            return self._default_empty_triage_result(cluster.get("cluster_id", "UNKNOWN"))

        # Extract asset metrics (E_i, Q_i, p_i, F_i)
        e_scores = []
        q_scores = []
        p_scores = []
        f_scores = []

        for a in member_assets:
            # Evidence score E_i
            e_val = a.get("evidence_score", a.get("E_i", 0.0))
            if not e_val and "scores" in a:
                e_val = a["scores"].get("composite_triage_score", 0.0) / 100.0
            e_scores.append(float(e_val))

            # Observability score Q_i
            q_val = a.get("observability_score", a.get("Q_i", 0.85))
            q_scores.append(float(q_val))

            # Damage probability p_i
            p_val = a.get("damage_probability", a.get("p_i", e_val))
            p_scores.append(float(p_val))

            # Flood proxy F_i
            f_val = a.get("flood_proxy", a.get("F_i", 0.0))
            if not f_val and "scores" in a:
                f_val = a["scores"].get("flood_inundation_score", 0.0)
            f_scores.append(float(f_val))

        num_assets = len(member_assets)

        # 1. Damage Evidence Density (D_c)
        sum_evidence = float(np.sum(e_scores))
        d_c = min(1.0, sum_evidence / (10.0 * (area_km2 + 0.01)))

        # 2. Road Network Isolation (A_c)
        if blocked_road_ratio is None:
            # Heuristic estimate from mean flood & damage extent
            mean_f = float(np.mean(f_scores)) if f_scores else 0.0
            mean_d = float(np.mean(p_scores)) if p_scores else 0.0
            blocked_road_ratio = min(1.0, max(0.05, 0.65 * mean_f + 0.35 * mean_d))

        if has_ingress_within_500m is None:
            has_ingress_within_500m = blocked_road_ratio < 0.70

        ingress_penalty = 1.0 if not has_ingress_within_500m else 0.0
        a_c = min(1.0, max(0.0, (0.60 * blocked_road_ratio) + (0.40 * ingress_penalty)))

        # 3. Vulnerability / Critical Facility Factor (V_c)
        if population_exposure is None:
            # Derived from asset count and centroid proximity
            population_exposure = min(1.0, (num_assets * 0.15) + (area_km2 * 0.20))

        facility_proximity_sum = 0.0
        if critical_facility_distances_km is None:
            # Default proximity estimates: Texas Medical Center / Substation corridors
            critical_facility_distances_km = [1.2, 2.5]

        for dist in critical_facility_distances_km:
            facility_proximity_sum += 1.0 / (max(0.01, dist) + 0.1)

        v_c = min(1.0, (0.50 * population_exposure) + (0.50 * min(1.0, facility_proximity_sum / 5.0)))

        # 4. Scale of Destruction (S_c)
        severe_count = sum(1 for e in e_scores if e >= 0.65)
        s_c = min(1.0, severe_count / 10.0)

        # 5. Information Gap / Uncertainty (U_c)
        # U_c = 1.0 - (1 / |c|) * sum(Q_i * p_i)
        qp_product = [q * p for q, p in zip(q_scores, p_scores)]
        mean_qp = float(np.mean(qp_product)) if qp_product else 0.5
        u_c = min(1.0, max(0.0, 1.0 - mean_qp))

        # Composite Triage Index TI_c in [0, 100]
        points_d = 0.34 * d_c * 100.0
        points_a = 0.22 * a_c * 100.0
        points_v = 0.20 * v_c * 100.0
        points_s = 0.14 * s_c * 100.0
        points_u = 0.10 * u_c * 100.0

        raw_ti = points_d + points_a + points_v + points_s + points_u
        ti_score = float(np.clip(raw_ti, 0.0, 100.0))

        # Priority Tier Assignment
        if ti_score >= 80.0:
            priority = "P1"
            priority_level = PriorityLevel.CRITICAL
            priority_label = "P1 - Urgent / Immediate Tactical Response"
        elif ti_score >= 60.0:
            priority = "P2"
            priority_level = PriorityLevel.HIGH
            priority_label = "P2 - Priority Verification / Dispatch"
        elif ti_score >= 40.0:
            priority = "P3"
            priority_level = PriorityLevel.MEDIUM
            priority_label = "P3 - Secondary Assessment"
        else:
            priority = "P4"
            priority_level = PriorityLevel.LOW
            priority_label = "P4 - Routine Monitoring"

        return {
            "cluster_id": cluster.get("cluster_id", "CLUSTER-01"),
            "triage_index": int(round(ti_score)),
            "triage_index_raw": round(ti_score, 2),
            "priority": priority,
            "priority_level": priority_level,
            "priority_label": priority_label,
            "score_breakdown": {
                "damage_density": f"{points_d:.1f}/34.0",
                "isolation": f"{points_a:.1f}/22.0",
                "vulnerability": f"{points_v:.1f}/20.0",
                "scale_of_destruction": f"{points_s:.1f}/14.0",
                "information_gap": f"{points_u:.1f}/10.0",
                "points": {
                    "damage_density": round(points_d, 2),
                    "isolation": round(points_a, 2),
                    "vulnerability": round(points_v, 2),
                    "scale_of_destruction": round(points_s, 2),
                    "information_gap": round(points_u, 2),
                },
                "raw_factors": {
                    "D_c": round(d_c, 3),
                    "A_c": round(a_c, 3),
                    "V_c": round(v_c, 3),
                    "S_c": round(s_c, 3),
                    "U_c": round(u_c, 3),
                },
            },
            "telemetry": {
                "asset_count": num_assets,
                "severe_damage_count": severe_count,
                "area_km2": area_km2,
                "mean_observability_Q": round(float(np.mean(q_scores)), 3) if q_scores else 0.0,
                "mean_flood_proxy_F": round(float(np.mean(f_scores)), 3) if f_scores else 0.0,
                "blocked_road_ratio": round(blocked_road_ratio, 3),
                "has_ingress_within_500m": has_ingress_within_500m,
            }
        }

    def _default_empty_triage_result(self, cluster_id: str) -> Dict[str, Any]:
        return {
            "cluster_id": cluster_id,
            "triage_index": 0,
            "triage_index_raw": 0.0,
            "priority": "P4",
            "priority_level": PriorityLevel.LOW,
            "priority_label": "P4 - Routine Monitoring",
            "score_breakdown": {
                "damage_density": "0.0/34.0",
                "isolation": "0.0/22.0",
                "vulnerability": "0.0/20.0",
                "scale_of_destruction": "0.0/14.0",
                "information_gap": "0.0/10.0",
                "points": {
                    "damage_density": 0.0,
                    "isolation": 0.0,
                    "vulnerability": 0.0,
                    "scale_of_destruction": 0.0,
                    "information_gap": 0.0,
                },
                "raw_factors": {"D_c": 0.0, "A_c": 0.0, "V_c": 0.0, "S_c": 0.0, "U_c": 0.0},
            },
            "telemetry": {
                "asset_count": 0,
                "severe_damage_count": 0,
                "area_km2": 0.0,
                "mean_observability_Q": 0.0,
                "mean_flood_proxy_F": 0.0,
                "blocked_road_ratio": 0.0,
                "has_ingress_within_500m": True,
            }
        }

    def calculate_score(self, features: Dict[str, float]) -> DamageScoreBreakdown:
        """Calculates tile-level damage score breakdown based on active weights."""
        s_dam = features.get("structural_damage", 0.0)
        f_inun = features.get("flood_inundation", 0.0)
        c_infra = features.get("critical_infrastructure", 0.0)
        p_vuln = features.get("population_vulnerability", 0.0)
        a_isol = features.get("access_isolation", 0.0)

        raw_composite = (
            (s_dam * self.weights.structural_damage) +
            (f_inun * self.weights.flood_inundation) +
            (c_infra * self.weights.critical_infrastructure) +
            (p_vuln * self.weights.population_vulnerability) +
            (a_isol * self.weights.access_isolation)
        ) * 100.0

        composite = round(min(100.0, max(0.0, raw_composite)), 1)

        return DamageScoreBreakdown(
            structural_damage_score=s_dam,
            flood_inundation_score=f_inun,
            critical_infrastructure_score=c_infra,
            population_vulnerability_score=p_vuln,
            access_isolation_score=a_isol,
            composite_triage_score=composite,
        )

    def determine_priority(self, composite_score: float) -> PriorityLevel:
        """Maps composite 0-100 score to priority level."""
        if composite_score >= 75.0:
            return PriorityLevel.CRITICAL
        elif composite_score >= 50.0:
            return PriorityLevel.HIGH
        elif composite_score >= 25.0:
            return PriorityLevel.MEDIUM
        return PriorityLevel.LOW


triage_engine = TriageEngine()
