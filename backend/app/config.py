"""RescueMesh Configuration Module

Defines system-wide settings, default geospatial bounding boxes for Hurricane Harvey AOI,
and heuristic multi-criteria triage scoring weights.
"""

from typing import Dict, List
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class GeoBoundingBox(BaseModel):
    """Bounding box coordinates for an Area of Interest (AOI)."""
    min_lat: float = Field(default=29.5000, description="Southernmost latitude")
    max_lat: float = Field(default=30.0500, description="Northernmost latitude")
    min_lon: float = Field(default=-95.7500, description="Westernmost longitude")
    max_lon: float = Field(default=-95.0500, description="Easternmost longitude")
    center_lat: float = Field(default=29.7604, description="Houston Harvey Epicenter Latitude")
    center_lon: float = Field(default=-95.3698, description="Houston Harvey Epicenter Longitude")
    default_zoom: int = Field(default=11, description="Default tactical map zoom level")


class TriageHeuristicWeights(BaseModel):
    """Multi-criteria operational triage weighting scheme (sum to 1.0)."""
    structural_damage: float = Field(
        default=0.35,
        description="Weight for detected structural collapse, roof shearing, and debris"
    )
    flood_inundation: float = Field(
        default=0.30,
        description="Weight for standing flood water, storm surge, and submerged roadways"
    )
    critical_infrastructure: float = Field(
        default=0.15,
        description="Weight for proximity to hospitals, power substations, and water plants"
    )
    population_vulnerability: float = Field(
        default=0.10,
        description="Weight for demographic vulnerability and high-density residential footprint"
    )
    access_isolation: float = Field(
        default=0.10,
        description="Weight for cut-off access routes and road obstruction index"
    )


class VisionModelSettings(BaseModel):
    """Configuration for deep learning feature extraction & CAM visualization."""
    backbone_name: str = Field(default="resnet50", description="Torchvision or TIMM backbone")
    embedding_dim: int = Field(default=2048, description="Embedding feature vector size")
    tile_size_px: int = Field(default=512, description="Imagery tile resolution in pixels")
    overlap_px: int = Field(default=64, description="Overlap between neighboring spatial patches")
    confidence_threshold: float = Field(default=0.60, description="Minimum confidence for alert generation")
    device: str = Field(default="cpu", description="Compute device: 'cuda', 'mps', or 'cpu'")


class ClusteringSettings(BaseModel):
    """Configuration for spatial DBSCAN clustering & anomaly grouping."""
    spatial_eps_meters: float = Field(default=800.0, description="Spatial neighborhood distance in meters")
    min_samples: int = Field(default=3, description="Minimum cluster size to form high-priority sector")
    feature_weight: float = Field(default=0.4, description="Weighting of semantic embedding distance vs lat/lon")


class Settings(BaseSettings):
    """Master Application Configuration."""
    model_config = SettingsConfigDict(
        env_prefix="RESCUEMESH_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    APP_NAME: str = "RescueMesh"
    APP_VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = True

    # CORS settings for frontend communication
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:8001",
        "http://127.0.0.1:8001",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    # Hurricane Harvey Houston Area of Interest
    DEFAULT_AOI_NAME: str = "Hurricane Harvey - Greater Houston Metro"
    AOI_BOUNDS: GeoBoundingBox = GeoBoundingBox()

    # Triage heuristic scoring weights
    TRIAGE_WEIGHTS: TriageHeuristicWeights = TriageHeuristicWeights()

    # Sub-system configs
    VISION: VisionModelSettings = VisionModelSettings()
    CLUSTERING: ClusteringSettings = ClusteringSettings()

    # File paths
    RAW_TILES_DIR: str = "data/raw_tiles"
    SEED_AOI_PATH: str = "data/seed_aoi.json"

    # Twilio Live Tactical SMS Gateway
    TWILIO_ACCOUNT_SID: str = "AC5f260df4f904a80af8430d5cb883485f"
    TWILIO_AUTH_TOKEN: str = "19a93be415aa9e72b5fccbee52bb2230"
    TWILIO_FROM_NUMBER: str = "+17372212163"
    SAR_TEST_PHONE_NUMBER: str = "+918667516393"


settings = Settings()
