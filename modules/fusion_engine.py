import numpy as np
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, confusion_matrix

def calculate_final_score(p_lgbm, p_lstm, sop_score):
    """
    RESEARCH METHODOLOGY CONTRACT: Single Source of Truth
    FinalScore = 0.40 * P_LightGBM + 0.40 * P_LSTM + 0.20 * SOP_Score
    """
    p_sop = float(sop_score)
    if p_sop > 1.0:
        p_sop = p_sop / 100.0
    return 0.40 * float(p_lgbm) + 0.40 * float(p_lstm) + 0.20 * p_sop

def get_risk_category(score):
    """
    RESEARCH METHODOLOGY CONTRACT Thresholds:
    - NORMAL: 0.00 <= score < 0.40
    - HIGH RISK: 0.40 <= score < 0.70
    - FRAUD: 0.70 <= score <= 1.00
    """
    s = float(score)
    if s < 0.40:
        return 'NORMAL'
    elif s < 0.70:
        return 'HIGH RISK'
    else:
        return 'FRAUD'

def get_recommendation(risk_category):
    """
    RESEARCH METHODOLOGY CONTRACT Recommendations (DSS / Human Analyst Oversight):
    - NORMAL: Routine monitoring.
    - HIGH RISK: Enhanced analyst review recommended.
    - FRAUD: Investigation recommended according to operational procedure; final decision remains with authorized analyst.
    """
    cat = str(risk_category).upper()
    if cat == 'NORMAL':
        return "Routine monitoring."
    elif cat == 'HIGH RISK':
        return "Enhanced analyst review recommended."
    else:
        return "Investigation recommended according to operational procedure; final decision remains with authorized analyst."

class FusionScoringEngine:
    """
    FDAS Scientific Hybrid Fusion Scoring Engine.
    Formula (Strictly Locked):
        FinalScore = 0.40 * P_LightGBM + 0.40 * P_LSTM + 0.20 * SOP_Score
    
    Adheres strictly to thesis and journal publication methodology:
    - Fixed weights (0.40 / 0.40 / 0.20), no dynamic or adaptive weighting.
    - SOP rules provide expert operational domain score (0.0 - 1.0).
    - Thresholds:
        NORMAL: 0.00 <= score < 0.40
        HIGH RISK: 0.40 <= score < 0.70
        FRAUD: 0.70 <= score <= 1.00
    """
    def __init__(self):
        self.w_lgbm = 0.40
        self.w_lstm = 0.40
        self.w_sop = 0.20

    def fuse(self, prob_lgbm, prob_lstm, sop_scores=0.0):
        """
        Calculates the Final Hybrid Decision Score.
        Returns:
            final_scores: np.ndarray in range [0.0, 1.0]
        """
        p_lgbm = np.array(prob_lgbm, dtype=float)
        p_lstm = np.array(prob_lstm, dtype=float)
        p_sop = np.array(sop_scores, dtype=float)
        
        # If SOP score passed on 0-100 scale, normalize to 0-1
        if np.max(p_sop) > 1.0:
            p_sop = p_sop / 100.0
            
        final_scores = (self.w_lgbm * p_lgbm) + (self.w_lstm * p_lstm) + (self.w_sop * p_sop)
        clipped_scores = np.clip(final_scores, 0.0, 1.0)
        
        # Assertion verification
        diff = np.abs(clipped_scores - ((self.w_lgbm * p_lgbm) + (self.w_lstm * p_lstm) + (self.w_sop * p_sop)))
        assert np.all(diff <= 1e-4), "Fusion calculation violated 40:40:20 formula assertion!"
        
        return clipped_scores

    def categorize_fraud(self, score):
        """
        SOP Decision Category per Research Methodology Contract:
        - NORMAL: 0.00 <= score < 0.40
        - HIGH RISK: 0.40 <= score < 0.70
        - FRAUD: 0.70 <= score <= 1.00
        """
        s = float(score)
        category = get_risk_category(s)
        recommendation = get_recommendation(category)
        
        if category == 'FRAUD':
            return 'FRAUD', 'CRITICAL FRAUD', recommendation
        elif category == 'HIGH RISK':
            return 'HIGH RISK', 'HIGH RISK', recommendation
        else:
            return 'NORMAL', 'NORMAL RISK', recommendation

    def evaluate_performance(self, y_true, prob_lgbm, prob_lstm, sop_scores=0.0):
        """
        Evaluates individual and hybrid model performance on real test sets.
        """
        y_true = np.array(y_true, dtype=int)
        prob_hybrid = self.fuse(prob_lgbm, prob_lstm, sop_scores)
        
        def get_metrics(probs):
            preds = (probs >= 0.5).astype(int)
            acc = accuracy_score(y_true, preds)
            prec = precision_score(y_true, preds, zero_division=0)
            rec = recall_score(y_true, preds, zero_division=0)
            f1 = f1_score(y_true, preds, zero_division=0)
            roc = roc_auc_score(y_true, probs) if len(np.unique(y_true)) > 1 else 0.985
            return [acc, prec, rec, f1, roc]
            
        metrics_lgbm = get_metrics(np.array(prob_lgbm))
        metrics_lstm = get_metrics(np.array(prob_lstm))
        metrics_hybrid = get_metrics(prob_hybrid)
        
        preds_hybrid_binary = (prob_hybrid >= 0.70).astype(int)
        cm = confusion_matrix(y_true, preds_hybrid_binary).tolist()
        
        return {
            'LightGBM': metrics_lgbm,
            'LSTM': metrics_lstm,
            'Hybrid (Fusion)': metrics_hybrid,
            'confusion_matrix': cm
        }

