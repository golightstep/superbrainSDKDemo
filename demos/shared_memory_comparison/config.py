import os

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DASHBOARD_DIR = os.path.join(BASE_DIR, "dashboard")
MARKET_DATA_FILE = os.path.join(BASE_DIR, "market_data.json")
LOG_FILE = os.path.join(BASE_DIR, "knowledge_sharing.log")

# Simulation Settings
# Simulation Settings
TRADITIONAL_POLL_INTERVAL = 0.01  # Reduced from 2.0 to be honest
SCRAPER_INTERVAL = 0.01          # Reduced from 1.0
ANALYSIS_INTERVAL = 0.01         # Reduced
FACT_CHECK_INTERVAL = 0.01       # Reduced
SUPERBRAIN_TICK = 0.001          # Set to 1ms for honest high-performance demo

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
