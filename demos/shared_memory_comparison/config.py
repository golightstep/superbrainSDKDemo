import os

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DASHBOARD_DIR = os.path.join(BASE_DIR, "dashboard")
MARKET_DATA_FILE = os.path.join(BASE_DIR, "market_data.json")
LOG_FILE = os.path.join(BASE_DIR, "knowledge_sharing.log")

# Simulation Settings
TRADITIONAL_POLL_INTERVAL = 2.0  # seconds
SCRAPER_INTERVAL = 1.0           # seconds
ANALYSIS_INTERVAL = 0.2          # seconds
FACT_CHECK_INTERVAL = 0.2        # seconds
SUPERBRAIN_TICK = 0.1            # Slowed down from 0.01 to prevent I/O thrashing

# Shared Memory Fabric Keys
CONTEXT_NAME = "ai_newsroom_fabric"
REPORTER_KEY = "studio:market:raw"
ANALYST_KEY = "studio:sentiment:processed"
FACT_CHECKER_KEY = "studio:fact:verified"
PRODUCER_KEY = "studio:broadcast:cue"
METRICS_KEY = "studio:system:metrics"
TIMELINE_KEY = "studio:timeline:events"

# Conflict Simulation
CONFLICT_MODE_FILE = os.path.join(BASE_DIR, "conflict_active.flag")
