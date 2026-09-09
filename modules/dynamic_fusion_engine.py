from .fusion_engine import FusionScoringEngine

class DynamicFusionEngine(FusionScoringEngine):
    """
    Alias maintained for backward compatibility.
    Strictly locked to 0.40 * LightGBM + 0.40 * LSTM + 0.20 * SOP_Score.
    """
    pass
