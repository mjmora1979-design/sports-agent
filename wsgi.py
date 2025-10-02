# wsgi.py
try:
    from sports_agent import app
except ImportError:
    from sports_agent_py import app  # fallback if your app is named sports_agent_py.py

# Optional sanity check
assert app is not None
