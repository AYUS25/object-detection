"""
config.py
=========
Configuration parameters for the Smart Vision Assistant.
Terminal-output visual perception engine — no voice/TTS.
"""

# ──────────────────────────────────────────────────────────────────────────────
# CAMERA
# ──────────────────────────────────────────────────────────────────────────────
CAMERA_INDEX: int = 0               # 0 = default webcam
FRAME_WIDTH: int = 640              # Capture width
FRAME_HEIGHT: int = 480             # Capture height
CAMERA_FPS: int = 30                # Target camera capture rate

# ──────────────────────────────────────────────────────────────────────────────
# DETECTION (YOLO11m)
# ──────────────────────────────────────────────────────────────────────────────
YOLO_MODEL: str = "yolo11m.pt"      # Model weights filename
MODELS_DIR: str = "models"          # Local directory for cached weights
INFERENCE_SIZE: int = 640           # YOLO input resolution (640 = better small-object detection)
CONFIDENCE_THRESHOLD: float = 0.45  # Minimum detection confidence (lower = catch more objects)
NMS_IOU_THRESHOLD: float = 0.45     # Non-max suppression IoU
MAX_DETECTIONS: int = 100           # Cap per-frame detection count
TRACKER_TYPE: str = "botsort.yaml"  # BoT-SORT (appearance + motion re-ID)

# Frame skipping: run YOLO every Nth frame to protect FPS
# When FPS < FRAME_SKIP_FPS_THRESHOLD, inference is run every FRAME_SKIP_N frames
FRAME_SKIP_N: int = 2               # Run inference every 2nd frame when FPS is low
FRAME_SKIP_FPS_THRESHOLD: float = 15.0  # Skip frames if FPS drops below this

# ──────────────────────────────────────────────────────────────────────────────
# SCENE MEMORY
# ──────────────────────────────────────────────────────────────────────────────
# Performance & Inference
SKIP_FRAMES = 1
FRAME_TIMEOUT = 0.5           # Max time to wait for a frame (seconds)
OBJECT_NEW_GRACE = 2.0        # Seconds before an object is considered 'stable'
OBJECT_STALE_TIMEOUT = 2.0    # Seconds before a lost object is permanently removed

# Spatial & Analytics
DEBUG_SPATIAL_JITTER = False  # If True, prints raw vs EMA coordinates to console

# ──────────────────────────────────────────────────────────────────────────────
# REPORTING ENGINE
# ──────────────────────────────────────────────────────────────────────────────
REPORT_INTERVAL: float = 15.0       # Seconds between console scene reports
REPORT_TO_FILE: bool = True         # Also log reports to reports/ directory
STABILITY_WINDOW: float = 10.0      # Seconds of stability history for % metric

# ──────────────────────────────────────────────────────────────────────────────
# GEMINI VERIFICATION  (async background — never blocks detection loop)
# ──────────────────────────────────────────────────────────────────────────────
GEMINI_MODEL: str = "gemini-2.0-flash-lite"  # Cheapest multimodal flash model
GEMINI_VERIFY_THRESHOLD: float = 0.70        # Auto-verify detections below this conf
GEMINI_MAX_PENDING: int = 6                  # Max items queued for verification
GEMINI_VERIFY_COOLDOWN: float = 3.0          # Minimum seconds between API calls
GEMINI_SESSION_BUDGET: int = 60              # Hard cap on API calls per session
GEMINI_MIN_OBJECT_AGE: float = 1.5          # Only verify objects seen for ≥N seconds
DEEP_ANALYSIS_ENABLED: bool = True           # Request rich Gemini descriptions for all objects
DEBUG_BYPASS_FPS_GATING: bool = True        # Ignore FPS limits for Gemini queueing

# ──────────────────────────────────────────────────────────────────────────────
# DISPLAY / HUD  (cv2.imshow window — kept for visual debugging)
# ──────────────────────────────────────────────────────────────────────────────
SHOW_OVERLAYS_DEFAULT: bool = True   # Start with bounding boxes on
FONT_SCALE: float = 0.50             # Base font scale for overlays

# Colour palette (BGR format)
COLOUR_BOX_DEFAULT  = (0, 220, 80)   # Default bounding box (green)
COLOUR_BOX_VERIFIED = (0, 180, 255)  # Gemini-verified object (orange)
COLOUR_BOX_NEW      = (0, 255, 255)  # Newly appeared object (yellow)
COLOUR_TEXT         = (255, 255, 255)
COLOUR_HUD_BG       = (0, 0, 0)
COLOUR_FPS          = (0, 255, 200)
COLOUR_WARNING      = (0, 100, 255)

# ──────────────────────────────────────────────────────────────────────────────
# FPS MONITORING  (adaptive frame-skip thresholds)
# ──────────────────────────────────────────────────────────────────────────────
FPS_WARN_THRESHOLD: float = 12.0    # Warn in HUD if FPS falls below this
FPS_CRITICAL_THRESHOLD: float = 8.0 # Disable Gemini auto-verify below this
