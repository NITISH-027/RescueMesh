"""RescueMesh Backend Runner Script."""

import os
import uvicorn
from app.config import settings

if __name__ == "__main__":
    # Ensure seed demo data is populated before startup
    seed_path = os.path.join(os.path.dirname(__file__), "data", "seed_aoi.json")
    if not os.path.exists(seed_path):
        try:
            from scripts.seed_demo_data import create_demo_clusters
            create_demo_clusters()
        except Exception as e:
            print(f"[Startup Warning] Could not automatically generate seed data: {e}")

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info",
    )
