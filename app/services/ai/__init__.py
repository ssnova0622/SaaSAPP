# Re-export so "from app.services.ai import AIPredictor" works (package shadows app.services.ai.py)
from app.services.ai.predictor import AIPredictor

__all__ = ["AIPredictor"]
