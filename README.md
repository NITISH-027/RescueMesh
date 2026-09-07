# 🛰️ RescueMesh

> **Autonomous Tactical Decision Support & Explainable AI for Satellite-Driven Search and Rescue**  
> *Track 04: AI for Space & Earth Intelligence — Intellect Hack 2026*

[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-black?style=for-the-badge&logo=next.js&logoColor=white)](https://nextjs.org/)
[![PyTorch](https://img.shields.io/badge/PyTorch-EE4C2C?style=for-the-badge&logo=pytorch&logoColor=white)](https://pytorch.org/)
[![OpenStreetMap](https://img.shields.io/badge/OpenStreetMap-7EBC6F?style=for-the-badge&logo=openstreetmap&logoColor=white)](https://www.openstreetmap.org/)
[![Twilio](https://img.shields.io/badge/Twilio-F22F46?style=for-the-badge&logo=twilio&logoColor=white)](https://www.twilio.com/)

---

## 📌 Executive Summary

During large-scale natural disasters (hurricanes, catastrophic flash floods), high-resolution optical satellites capture critical ground conditions within hours. However, emergency incident management consistently suffers from three systemic bottlenecks:

1. **Analytical Paralysis:** Frontline commanders are overwhelmed by 10,000+ raw satellite tiles, burning through the golden 72-hour survival window during slow, error-prone manual audits.
2. **The "Black-Box" Trust Deficit:** Standard deep learning classification outputs cannot be verified on the fly, risking scarce rescue resources on sensor artifacts, shadow anomalies, or standing mud.
3. **The Last-Mile Disconnect:** Sophisticated GIS dashboards stay locked on incident command desktops, leaving frontline boat crews and ground units blind to high-altitude space intelligence.

**RescueMesh** bridges space intelligence and frontline field execution into a closed-loop system:
$$\text{Raw Satellite Swaths} \longrightarrow \text{ConvNeXt / Grad-CAM} \longrightarrow \text{Deterministic MCDA} \longrightarrow \text{Frontline Carrier SMS Dispatch (<2s)}$$

---

## 🏛️ System Architecture

```
                       +------------------------------------------+
                       |   High-Resolution Optical Satellite Data  |
                       |       (Hurricane Harvey AOI Patches)     |
                       +--------------------+---------------------+
                                            |
                                            v
                       +------------------------------------------+
                       |      Computer Vision & XAI Saliency       |
                       |   - ConvNeXt Feature Extraction Backbone |
                       |   - Grad-CAM Roofline Saliency Heatmaps  |
                       +--------------------+---------------------+
                                            |
                                            v
                       +------------------------------------------+
                       |     Spatial Aggregation & Road Topology  |
                       |   - DBSCAN Operational Sector Clustering  |
                       |   - OSMnx Road Cut & Isolation Ratios    |
                       |   - Overpass API Critical Asset Registry |
                       +--------------------+---------------------+
                                            |
                                            v
                       +------------------------------------------+
                       |       Deterministic Decision Engine      |
                       |   - 5-Factor Multi-Criteria Decision (MCDA)|
                       |   - P1-Critical to P4-Routine Triage Tier|
                       +--------------------+---------------------+
                                            |
                    +-----------------------+-----------------------+
                    |                                               |
                    v                                               v
+---------------------------------------+       +---------------------------------------+
|   Tactical Next.js Command Console    |       |     Zero-Latency Field Handoff         |
| - Sub-meter Esri World Imagery        |       | - Carrier-grade SMS via Twilio API    |
| - Interactive Grad-CAM Heatmap Toggle |       | - ATAK Cursor-on-Target (CoT) XML     |
| - Dynamic OSM Metric Telemetry        |       | - 1-Tap Google Maps Turn-by-Turn GPS  |
+---------------------------------------+       +---------------------------------------+
```

---

## 🔬 Core Methodologies

### 1. Explainable AI (XAI) Attribution
Rather than providing opaque classification labels, RescueMesh computes layer activations via **Grad-CAM** on the final convolutional layers of our fine-tuned vision backbone. The resulting heatmap is dynamically blended over building rooflines, providing visual proof of structural collapse and flood boundaries directly to the incident commander.

### 2. Deterministic Multi-Criteria Decision Analysis (MCDA)
Triage prioritization uses a fully deterministic linear additive weighting formula ($0\text{--}100$) to guarantee zero hallucinations:

$$TI(S) = 0.34 D_c + 0.22 A_c + 0.20 V_c + 0.14 S_c + 0.10 U_c$$

* **$D_c$ (Damage Density - 34%):** Ratio of collapsed structures detected via model saliency.
* **$A_c$ (Road Isolation - 22%):** Ratio of impassable/severed road network edges derived via OpenStreetMap topological graphs.
* **$V_c$ (Critical Vulnerability - 20%):** Proximity and density of high-risk facilities (hospitals, schools, eldercare, emergency shelters).
* **$S_c$ (Scale of Impact - 14%):** Spatial DBSCAN footprint and structural building count within the cluster.
* **$U_c$ (Information Gap - 10%):** Uncertainty penalty for cloud occlusion or degraded sensor resolution.

### 3. Tactical Handoff & Interoperability
* **Direct-to-Pocket SMS:** Sends concise, 160-character tactical dispatches with direct Google Maps navigation links via cellular control channels (operable over degraded 2G/3G networks).
* **ATAK Cursor-on-Target (CoT):** Generates standard military/first-responder XML event feeds for immediate integration with Android Team Awareness Kit devices.

---

## 🛠️ Technology Stack

| Layer | Technology |
| :--- | :--- |
| **Frontend Console** | Next.js (React 18/19), TypeScript, Tailwind CSS, Lucide Icons |
| **Geospatial Engine** | Leaflet / React-Leaflet, Esri World Imagery Basemap (`EPSG:3857`) |
| **Backend API** | Python 3.11+, FastAPI, Uvicorn, Pydantic |
| **AI / Deep Learning** | PyTorch, Torchvision, ConvNeXt Backbone, Grad-CAM, OpenCV |
| **Spatial Analysis** | GeoPandas, Shapely, OSMnx, PyProj, Scikit-learn (DBSCAN) |
| **Telecommunications** | Twilio REST API (Carrier-grade SMS gateway) |
| **Standards** | ATAK Cursor-on-Target (CoT) XML, RFC 7946 GeoJSON |

---

## 🚀 Quick Start Guide

### Prerequisites
* Python 3.11+
* Node.js 18+ and npm
* Git

### 1. Clone the Repository
```bash
git clone https://github.com/NITISH-027/RescueMesh.git
cd RescueMesh
```

### 2. Backend Setup
```bash
# Create and activate virtual environment
python -m venv venv

# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# Linux / macOS:
# source venv/bin/activate

# Install dependencies
cd backend
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env with your Twilio credentials and test phone number

# Start FastAPI backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```
* Backend Health Check: `http://127.0.0.1:8001`
* Interactive API Documentation (Swagger): `http://127.0.0.1:8001/docs`

### 3. Frontend Setup
Open a second terminal:
```bash
cd frontend
npm install
npm run dev
```
* Command Console URL: `http://localhost:3000`

---

## 🎯 Verification & Demo Workflow

1. **Access Console:** Open `http://localhost:3000`.
2. **Select Priority Sector:** Click `HARVEY-CL-001` (or any cluster) from the left triage queue.
3. **Verify XAI Saliency:** Toggle between **`[Raw Tile]`** and **`[Grad-CAM]`** in the sector inspector to audit the structural roofline damage heatmap.
4. **Audit OSM Telemetry:** Review dynamic road network status (`ISOLATED` / `ACCESSIBLE`), nearest trauma hospital distance, and evaluated topological edges.
5. **Execute Field Dispatch:** Click **`[⚡ Dispatch SAR to Nearest Unit]`** to trigger carrier-grade SMS transmission with one-tap turn-by-turn navigation directly to the field unit.

---

## 👥 Authors & Team

* **Team Name:** Vulcan
* **Institution:** Sri Sairam Engineering College
* **Competition:** Intellect Hack 2026
* **Track:** Track 04 — AI for Space & Earth Intelligence
