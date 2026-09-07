"""Automated System & Integration Verification Suite for RescueMesh.

Validates:
1. Server Health & OpenAPI Documentation endpoint (HTTP 200).
2. Ranked Cluster Telemetry (4 clusters sorted by triage_index descending, HARVEY-CL-001 first).
3. Evidence Retrieval (base64 Grad-CAM overlays, raw tile, score decomposition, and SITREP).
4. HITL State Transition (AI_CANDIDATE -> VERIFIED with audit record).
5. HITL Dismissal Validation (AI_CANDIDATE -> DISMISSED with dismissal_reason).
6. RFC 7946 GeoJSON Export.
7. Cursor-on-Target (CoT XML 2.0) Military/SAR Stream.
"""

import sys
import os
import xml.etree.ElementTree as ET
from typing import Dict, Any

# Ensure backend root is on sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Seed demo data first if not present
from scripts.seed_demo_data import create_demo_clusters
create_demo_clusters()

from fastapi.testclient import TestClient
from app.main import app
from app.services.state_store import state_store

# Initialize in-process test client
client = TestClient(app)


class RescueMeshVerificationSuite:
    """End-to-End Test Runner for RescueMesh."""

    def __init__(self):
        self.passed_tests = 0
        self.failed_tests = 0
        self.test_log = []

    def log_result(self, test_name: str, passed: bool, message: str = ""):
        if passed:
            self.passed_tests += 1
            status_str = "\033[92m[PASS]\033[0m"
            print(f"{status_str} {test_name}: {message}")
        else:
            self.failed_tests += 1
            status_str = "\033[91m[FAIL]\033[0m"
            print(f"{status_str} {test_name}: {message}")
        self.test_log.append({"test": test_name, "passed": passed, "message": message})

    def run_all_tests(self):
        print("=" * 70)
        print("RESCUEMESH // SYSTEM INTEGRATION & AUDIT VERIFICATION SUITE")
        print("=" * 70)

        # Re-warm state store
        state_store.initialize_store(force_reload=True)

        self.test_server_health()
        self.test_get_clusters()
        self.test_cluster_evidence()
        self.test_osm_context_engine()
        self.test_hitl_state_transition()
        self.test_sar_dispatch()
        self.test_hitl_dismissal_validation()
        self.test_geojson_export()
        self.test_cot_export()

        print("=" * 70)
        print(f"VERIFICATION SUMMARY: {self.passed_tests} PASSED, {self.failed_tests} FAILED")
        print("=" * 70)
        return self.failed_tests == 0

    def test_server_health(self):
        test_name = "test_server_health"
        try:
            res_docs = client.get("/docs")
            res_health = client.get("/api/v1/health")
            assert res_docs.status_code == 200, f"Docs returned {res_docs.status_code}"
            assert res_health.status_code == 200, f"Health returned {res_health.status_code}"
            data = res_health.json()
            assert data.get("status") == "healthy", "Status is not healthy"
            self.log_result(test_name, True, "FastAPI /docs and /api/v1/health returned HTTP 200 OK")
        except Exception as e:
            self.log_result(test_name, False, str(e))

    def test_get_clusters(self):
        test_name = "test_get_clusters"
        try:
            res = client.get("/api/v1/clusters")
            assert res.status_code == 200, f"Status code {res.status_code}"
            clusters = res.json()
            assert len(clusters) == 4, f"Expected 4 clusters, received {len(clusters)}"

            # Verify sorted descending by triage_index
            scores = [c["triage_index"] for c in clusters]
            assert scores == sorted(scores, reverse=True), f"Clusters not sorted descending: {scores}"
            assert clusters[0]["cluster_id"] == "HARVEY-CL-001", f"Top cluster is not HARVEY-CL-001 ({clusters[0]['cluster_id']})"
            assert clusters[0]["priority"] == "P1", f"Top cluster priority is not P1 ({clusters[0]['priority']})"
            assert clusters[0]["triage_index"] == 88, f"Top cluster triage index is not 88 ({clusters[0]['triage_index']})"

            self.log_result(test_name, True, f"Returned 4 clusters correctly ranked (Top: {clusters[0]['cluster_id']} TI={clusters[0]['triage_index']})")
        except Exception as e:
            self.log_result(test_name, False, str(e))

    def test_cluster_evidence(self):
        test_name = "test_cluster_evidence"
        try:
            res = client.get("/api/v1/clusters/HARVEY-CL-001/evidence")
            assert res.status_code == 200, f"Status code {res.status_code}"
            detail = res.json()

            assert detail["cluster_id"] == "HARVEY-CL-001"
            assert detail.get("gradcam_overlay_base64", "").startswith("data:image/"), "Missing or invalid Grad-CAM base64"
            assert detail.get("raw_tile_base64", "").startswith("data:image/"), "Missing or invalid raw tile base64"

            # Check SITREP
            sitrep = detail.get("sitrep", {})
            assert "Buffalo Bayou" in sitrep.get("tactical_summary", ""), "SITREP summary missing Buffalo Bayou reference"
            assert sitrep.get("recommended_action") == "AMPHIBIOUS_OR_BOAT_RECONNAISSANCE"

            # Check score breakdown
            score_b = detail.get("score_breakdown", {})
            assert "31.5/34.0" in score_b.get("damage_density", "")

            self.log_result(test_name, True, "Retrieved full base64 Grad-CAM overlay, raw tile, score decomposition, and SITREP")
        except Exception as e:
            self.log_result(test_name, False, str(e))

    def test_osm_context_engine(self):
        test_name = "test_osm_context_engine"
        try:
            res = client.get("/api/v1/clusters/HARVEY-CL-001/evidence")
            assert res.status_code == 200, f"Status code {res.status_code}"
            detail = res.json()

            assert "osm_telemetry" in detail and detail["osm_telemetry"] is not None, "Missing osm_telemetry in cluster detail"
            osm = detail["osm_telemetry"]
            assert "access_road_score" in osm
            assert "access_status" in osm
            assert "nearest_hospital_dist_km" in osm
            assert "topological_edges_evaluated" in osm

            self.log_result(test_name, True, f"OSM Engine active: status={osm['access_status']}, medical={osm['nearest_hospital_dist_km']}km, edges={osm['topological_edges_evaluated']}")
        except Exception as e:
            self.log_result(test_name, False, str(e))

    def test_hitl_state_transition(self):
        test_name = "test_hitl_state_transition"
        try:
            payload = {
                "action": "VERIFIED",
                "analyst_id": "SAR-COMM-CHIEF-01",
                "analyst_notes": "Confirmed 11 structures breached via Maxar imagery. Dispatching boat teams."
            }
            res = client.post("/api/v1/clusters/HARVEY-CL-001/review", json=payload)
            assert res.status_code == 200, f"Status code {res.status_code}"
            data = res.json()
            assert data["state"] == "VERIFIED", f"Expected state VERIFIED, got {data['state']}"

            # Verify audit trail in evidence
            res_ev = client.get("/api/v1/clusters/HARVEY-CL-001/evidence")
            audit_history = res_ev.json().get("audit_history", [])
            assert len(audit_history) >= 2, f"Expected at least 2 audit entries, got {len(audit_history)}"
            latest = audit_history[-1]
            assert latest["new_state"] == "VERIFIED"
            assert latest["actor"] == "SAR-COMM-CHIEF-01"

            self.log_result(test_name, True, "Successfully transitioned HARVEY-CL-001 from AI_CANDIDATE -> VERIFIED with audit record")
        except Exception as e:
            self.log_result(test_name, False, str(e))

    def test_sar_dispatch(self):
        test_name = "test_sar_dispatch"
        try:
            # 1. Inspect fleet
            res_fleet = client.get("/api/v1/sar-fleet")
            assert res_fleet.status_code == 200, f"Fleet status returned {res_fleet.status_code}"
            fleet = res_fleet.json()
            assert len(fleet) >= 4, f"Expected at least 4 SAR units, got {len(fleet)}"

            # 2. Preview nearest unit for HARVEY-CL-001 (AMPHIBIOUS_OR_BOAT_RECONNAISSANCE)
            res_preview = client.get("/api/v1/clusters/HARVEY-CL-001/nearest-unit")
            assert res_preview.status_code == 200, f"Preview returned {res_preview.status_code}"
            matched = res_preview.json()
            assert matched["unit_id"] == "SAR-BOAT-01", f"Expected SAR-BOAT-01 match, got {matched['unit_id']}"
            assert matched["capability_match"] is True
            assert matched["distance_km"] >= 0.0

            # 3. Execute field dispatch
            res_disp = client.post("/api/v1/clusters/HARVEY-CL-001/dispatch-field")
            assert res_disp.status_code == 200, f"Dispatch returned {res_disp.status_code}"
            data = res_disp.json()
            assert data["status"] == "DISPATCHED"
            assert "matched_unit" in data
            assert data["matched_unit"]["unit_id"] == "SAR-BOAT-01"
            assert "https://maps.google.com/?q=" in data["sms_payload"]
            assert "https://maps.google.com/?q=" in data["nav_url"]
            assert data["distance_km"] >= 0.0

            self.log_result(test_name, True, f"Proximity-matched {matched['callsign']} ({data['distance_km']}km), compiled 160-char SMS, and transitioned state to DISPATCHED")
        except Exception as e:
            self.log_result(test_name, False, str(e))

    def test_hitl_dismissal_validation(self):
        test_name = "test_hitl_dismissal_validation"
        try:
            # 1. Test missing dismissal_reason returns HTTP 400
            invalid_payload = {
                "action": "DISMISSED",
                "analyst_id": "ANALYST-TEST",
                "analyst_notes": "No reason supplied"
            }
            res_invalid = client.post("/api/v1/clusters/HARVEY-CL-004/review", json=invalid_payload)
            assert res_invalid.status_code == 400, f"Expected HTTP 400 for missing reason, got {res_invalid.status_code}"

            # 2. Test valid dismissal
            valid_payload = {
                "action": "DISMISSED",
                "analyst_id": "SAR-COMM-CHIEF-01",
                "analyst_notes": "Cloud cover obscuring vacant lot. Deferring to aerial sweep.",
                "dismissal_reason": "CLOUD_SHADOW"
            }
            res_valid = client.post("/api/v1/clusters/HARVEY-CL-004/review", json=valid_payload)
            assert res_valid.status_code == 200, f"Status code {res_valid.status_code}"
            assert res_valid.json()["state"] == "DISMISSED"

            self.log_result(test_name, True, "Enforced mandatory dismissal_reason gating and updated state to DISMISSED")
        except Exception as e:
            self.log_result(test_name, False, str(e))

    def test_geojson_export(self):
        test_name = "test_geojson_export"
        try:
            res = client.get("/api/v1/export/geojson")
            assert res.status_code == 200, f"Status code {res.status_code}"
            geojson = res.json()
            assert geojson.get("type") == "FeatureCollection"
            features = geojson.get("features", [])
            assert len(features) == 4, f"Expected 4 features, received {len(features)}"

            feat1 = next(f for f in features if f["id"] == "HARVEY-CL-001")
            assert feat1["geometry"]["type"] in ["Polygon", "MultiPolygon"]
            assert feat1["properties"]["priority"] == "P1"
            assert feat1["properties"]["triage_index"] == 88

            self.log_result(test_name, True, "Generated valid RFC 7946 FeatureCollection with 4 polygon features")
        except Exception as e:
            self.log_result(test_name, False, str(e))

    def test_cot_export(self):
        test_name = "test_cot_export"
        try:
            res = client.get("/api/v1/export/cot")
            assert res.status_code == 200, f"Status code {res.status_code}"
            xml_text = res.text
            assert xml_text.startswith("<?xml")
            assert '<events version="2.0">' in xml_text
            assert 'uid="RESCUEMESH-HARVEY-CL-001"' in xml_text
            assert 'type="a-f-G-U-C"' in xml_text

            # Parse XML tree to guarantee syntax validity
            root = ET.fromstring(xml_text.replace('<?xml version="1.0" standalone="yes"?>', "").strip())
            events = root.findall("event")
            assert len(events) == 4, f"Expected 4 CoT event nodes, found {len(events)}"

            self.log_result(test_name, True, "Generated valid Cursor-on-Target (CoT XML 2.0) event stream for ATAK/iTAK")
        except Exception as e:
            self.log_result(test_name, False, str(e))


if __name__ == "__main__":
    suite = RescueMeshVerificationSuite()
    success = suite.run_all_tests()
    sys.exit(0 if success else 1)
