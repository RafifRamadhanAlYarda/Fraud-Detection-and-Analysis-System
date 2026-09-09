import pandas as pd
import numpy as np

class FraudLabelingEngine:
    """
    FDAS Target Label Construction Engine.
    Constructs ground-truth fraud labels (0: Normal, 1: Fraud) based on SOP risk rules.
    Operates as an independent stage after Cleansing and before Split/Resampling.
    Preserves existing academic ground truth labels when already present in the source dataset.
    """
    def __init__(self):
        pass

    def construct_target_labels(self, df):
        """
        Constructs the target fraud_label column.
        If fraud_label is already present (e.g. from academic research dataset),
        it validates and preserves it.
        """
        if df is None or df.empty:
            raise ValueError("Input dataframe is empty or None.")
            
        df = df.copy()
        
        if 'fraud_label' in df.columns and df['fraud_label'].nunique() > 1:
            # Preserve existing ground truth labels
            df['fraud_label'] = pd.to_numeric(df['fraud_label'], errors='coerce').fillna(0).astype(int)
            return df
            
        df['fraud_label'] = 0
        df['operational_risk_score'] = 0.0
        
        # Ensure numeric columns
        df['nominal_debit'] = pd.to_numeric(df['nominal_debit'], errors='coerce').fillna(0.0)
        df['nominal_credit'] = pd.to_numeric(df['nominal_credit'], errors='coerce').fillna(0.0)
        
        # Rule 1: Midnight Transaction Anomaly (00:00 - 04:00 with large debit)
        temp_dt = pd.to_datetime(df['transaction_datetime'], errors='coerce')
        hour = temp_dt.dt.hour
        midnight_mask = (hour < 4) & (df['nominal_debit'] > 1_000_000)
        df.loc[midnight_mask, 'operational_risk_score'] += 0.35
        
        # Rule 2: High Velocity Cash Out (< 5 mins interval with large debit)
        acc_col = 'account_id' if 'account_id' in df.columns else 'source_account_key'
        time_diff = df.groupby(acc_col)['transaction_datetime'].diff().dt.total_seconds().fillna(0.0)
        velocity_mask = (time_diff < 300) & (time_diff > 0) & (df['nominal_debit'] > 500_000)
        df.loc[velocity_mask, 'operational_risk_score'] += 0.40
        
        # Rule 3: Mule Account Rapid Liquidation (Inflow followed by > 80% Outflow within 15 mins)
        prev_credit = df.groupby(acc_col)['nominal_credit'].shift(1).fillna(0.0)
        mule_mask = (prev_credit > 1_000_000) & (df['nominal_debit'] > (prev_credit * 0.8)) & (time_diff < 900)
        df.loc[mule_mask, 'operational_risk_score'] += 0.60
        df.loc[mule_mask, 'fraud_label'] = 1

        # Final label decision (score >= 0.5 is labeled Fraud)
        df.loc[df['operational_risk_score'] >= 0.5, 'fraud_label'] = 1
        
        return df

    def generate_fraud_label(self, df):
        """Alias for backward compatibility."""
        return self.construct_target_labels(df)
