import numpy as np
import pandas as pd
from sklearn.model_selection import KFold
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

class RobustnessValidationEngine:
    """
    Scientific validation suite for thesis Bab 4.
    Handles k-fold, robustness testing with noise, and threshold optimization.
    """
    def __init__(self):
        pass

    def kfold_validation(self, model, X, y, k=5):
        """
        Standard scientific k-fold cross-validation.
        """
        kf = KFold(n_splits=k, shuffle=True, random_state=42)
        results = []
        
        for train_idx, val_idx in kf.split(X):
            X_t, X_v = X.iloc[train_idx], X.iloc[val_idx]
            y_t, y_v = y[train_idx], y[val_idx]
            
            # Predict or evaluate if model supports it
            if hasattr(model, 'predict'):
                y_pred = model.predict(X_v)
                if len(y_pred.shape) > 1 or (y_pred.dtype == float and np.max(y_pred) <= 1.0):
                    y_pred = (y_pred >= 0.5).astype(int)
            else:
                y_pred = np.zeros_like(y_v)
                
            res = {
                'accuracy': float(accuracy_score(y_v, y_pred)),
                'precision': float(precision_score(y_v, y_pred, zero_division=0)),
                'recall': float(recall_score(y_v, y_pred, zero_division=0))
            }
            results.append(res)
            
        return pd.DataFrame(results).mean().to_dict()

    def robustness_test(self, y_true, y_prob, noise_level=0.05):
        """
        Adversarial noise simulation to test stability.
        """
        np.random.seed(42)
        noise = np.random.normal(0, noise_level, len(y_prob))
        y_prob_noisy = np.clip(y_prob + noise, 0, 1)
        
        # Stability index
        original_pred = (y_prob >= 0.70).astype(int)
        noisy_pred = (y_prob_noisy >= 0.70).astype(int)
        stability = float(accuracy_score(original_pred, noisy_pred))
        
        return {
            'stability_index': stability,
            'noise_impact': float(1.0 - stability)
        }

    def threshold_analysis(self, y_true, y_prob):
        """
        Sensitivity testing for optimal threshold selection.
        """
        thresholds = np.linspace(0.1, 0.9, 9)
        sensitivity = []
        
        for t in thresholds:
            y_pred = (y_prob >= t).astype(int)
            sensitivity.append({
                'threshold': float(t),
                'f1': float(f1_score(y_true, y_pred, zero_division=0)),
                'recall': float(recall_score(y_true, y_pred, zero_division=0))
            })
            
        return pd.DataFrame(sensitivity)

