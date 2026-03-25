# =============================================================================
# Procfile — Process Declaration for Railway / Heroku
# =============================================================================
# This file tells Railway what command to run to start your app.
#
# - "web:" means this is a web process (serves HTTP).
# - Railway automatically sets the $PORT environment variable.
# - We use 0.0.0.0 (not localhost) so the app is reachable from outside.
# - --workers 2: Runs 2 copies of the app for better performance.
#   (Railway free tier has limited RAM, so 2 workers is a safe default.)
# =============================================================================

web: uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 2
