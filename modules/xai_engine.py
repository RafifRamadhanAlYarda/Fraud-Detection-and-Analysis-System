import shap
import pandas as pd
import matplotlib.pyplot as plt
import io
import base64

class XAIEngine:
    def __init__(self, model, feature_cols):
        self.model = model
        self.feature_cols = feature_cols
        self.explainer = None

    def explain(self, df):
        X = df[self.feature_cols]
        
        # Initialize explainer (tree-based for LightGBM)
        if not self.explainer:
            self.explainer = shap.TreeExplainer(self.model)
            
        shap_values = self.explainer.shap_values(X)
        
        # If binary classification, shap_values might be a list of two arrays
        if isinstance(shap_values, list):
            shap_v = shap_values[1]
        else:
            shap_v = shap_values

        return shap_v

    def get_summary_plot(self, df, shap_values):
        X = df[self.feature_cols]
        plt.figure(figsize=(10, 6))
        shap.summary_plot(shap_values, X, show=False)
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight')
        buf.seek(0)
        img_str = base64.b64encode(buf.read()).decode('utf-8')
        plt.close()
        return img_str

    def get_local_explanation(self, df, shap_values, idx=0):
        X = df[self.feature_cols]
        # In modern SHAP, we use .force_plot but it requires JS
        # For streamlit, we might just parse the top features
        
        row_shap = shap_values[idx]
        feature_importance = pd.DataFrame({
            'feature': self.feature_cols,
            'shap_value': row_shap
        }).sort_values('shap_value', ascending=False)
        
        reasons = []
        for _, row in feature_importance.head(3).iterrows():
            if row['shap_value'] > 0:
                reasons.append(f"High {row['feature']} contributed to risk")
        
        # Special logic based on flags
        if df.iloc[idx]['risk_velocity'] > 1000:
            reasons.append("High transaction velocity detected")
        if df.iloc[idx]['hour'] < 5:
            reasons.append("Midnight transaction anomaly")
            
        return reasons
