import pandas as pd
import numpy as np

def calculate_sop_score(velocity_score, geo_score, freq_score, dest_score, amount_dev_score):
    """
    RESEARCH METHODOLOGY CONTRACT: Single Source of Truth for SOP Score
    Weights:
      1. Transaction Velocity Check = 0.25
      2. Geographic Anomaly Check = 0.15
      3. Transaction Frequency Anomaly = 0.20
      4. Destination Pattern Check = 0.20
      5. Transaction Amount Deviation = 0.20
    Total: 1.00 (Normalized 0.0 - 1.0)
    """
    v = np.clip(float(velocity_score), 0.0, 1.0)
    g = np.clip(float(geo_score), 0.0, 1.0)
    f = np.clip(float(freq_score), 0.0, 1.0)
    d = np.clip(float(dest_score), 0.0, 1.0)
    a = np.clip(float(amount_dev_score), 0.0, 1.0)
    
    sop_score = (0.25 * v) + (0.15 * g) + (0.20 * f) + (0.20 * d) + (0.20 * a)
    return float(np.clip(sop_score, 0.0, 1.0))

class OperationalRiskRulesEngine:
    """
    FDAS Operational SOP Validation Layer (Bab 3.8 / Research Methodology Contract).
    Evaluates 5 standardized banking operational indicators:
      1. Transaction Velocity Check (0.25)
      2. Geographic Anomaly Check (0.15)
      3. Transaction Frequency Anomaly (0.20)
      4. Destination Pattern Check (0.20)
      5. Transaction Amount Deviation (0.20)
    
    This layer serves strictly as an Operational Validation Layer for Decision Support,
    NOT as a machine learning classifier, training feature, or ground truth label.
    """
    def __init__(self):
        self.indicator_weights = {
            'velocity': 0.25,
            'geographic': 0.15,
            'frequency': 0.20,
            'destination': 0.20,
            'amount_dev': 0.20
        }

    def evaluate_indicators(self, tx_data, history_data=None):
        """
        Calculates normalized 0.0 - 1.0 scores for each of the 5 SOP indicators
        and computes the combined SOP Score.
        """
        # 1. Transaction Velocity Check (Weight 0.25)
        # Assesses speed of fund movement and rapid credit-to-debit dissipation
        time_diff = float(tx_data.get('time_diff_previous', tx_data.get('time_interval', 999)))
        nominal_d = float(tx_data.get('nominal_debit', 0.0))
        risk_vel = float(tx_data.get('risk_velocity', 0.0))
        
        velocity_score = 0.0
        if time_diff < 1.0 and nominal_d > 1000000:
            velocity_score = 1.0
        elif time_diff < 5.0 and nominal_d > 500000:
            velocity_score = 0.85
        elif risk_vel > 150:
            velocity_score = 0.70
        elif time_diff < 15.0:
            velocity_score = 0.40
        else:
            velocity_score = 0.10

        # 2. Geographic Anomaly Check (Weight 0.15)
        # Evaluates location distance jumps, IP/Terminal geolocation mismatch
        is_geo_anom = bool(tx_data.get('is_impossible_travel', tx_data.get('is_abnormal_location', False)))
        location_risk = float(tx_data.get('location_risk_score', 0.0))
        if is_geo_anom or location_risk > 0.8:
            geo_score = 1.0
        elif location_risk > 0.4:
            geo_score = 0.60
        else:
            geo_score = 0.05

        # 3. Transaction Frequency Anomaly (Weight 0.20)
        # Measures temporal burst intensity against account baseline
        r1h = float(tx_data.get('rolling_tx_count_1h', 1.0))
        r24h = float(tx_data.get('rolling_tx_count_24h', 1.0))
        burst_flag = int(tx_data.get('burst_incoming_flag', 0))
        
        if burst_flag == 1 or r1h >= 10:
            freq_score = 1.0
        elif r1h >= 5:
            freq_score = 0.75
        elif r24h >= 20:
            freq_score = 0.60
        elif r1h >= 3:
            freq_score = 0.35
        else:
            freq_score = 0.10

        # 4. Destination Pattern Check (Weight 0.20)
        # Evaluates novel destination accounts, recipient diversity, mule liquidation targets
        liquidation_ratio = float(tx_data.get('liquidation_ratio', 0.0))
        dest_novelty = int(tx_data.get('destination_novelty_flag', tx_data.get('is_new_destination', 0)))
        is_circular = bool(tx_data.get('is_circular', False))
        
        if is_circular or (liquidation_ratio > 0.80 and dest_novelty == 1):
            dest_score = 1.0
        elif liquidation_ratio > 0.80:
            dest_score = 0.80
        elif dest_novelty == 1:
            dest_score = 0.50
        else:
            dest_score = 0.10

        # 5. Transaction Amount Deviation (Weight 0.20)
        # Relative deviation from historical account mean
        nominal_dev = float(tx_data.get('nominal_dev', 0.0))
        if nominal_dev > 8.0:
            amount_dev_score = 1.0
        elif nominal_dev > 4.0:
            amount_dev_score = 0.75
        elif nominal_dev > 2.0:
            amount_dev_score = 0.50
        elif nominal_dev > 1.0:
            amount_dev_score = 0.25
        else:
            amount_dev_score = 0.05

        # Anti-False Positive Reductions (e.g. verified payroll or own-account transfers)
        if tx_data.get('is_payroll', 0) == 1 or tx_data.get('is_own_account', 0) == 1:
            velocity_score *= 0.3
            freq_score *= 0.3
            dest_score *= 0.2
            amount_dev_score *= 0.5

        # Combined Weighted SOP Score (Single Source of Truth)
        total_sop = calculate_sop_score(
            velocity_score, geo_score, freq_score, dest_score, amount_dev_score
        )

        return {
            'sop_score': total_sop,
            'velocity_score': float(velocity_score),
            'geographic_score': float(geo_score),
            'frequency_score': float(freq_score),
            'destination_score': float(dest_score),
            'amount_dev_score': float(amount_dev_score),
            'indicators_summary': {
                'Transaction Velocity Check (25%)': f"{velocity_score*100:.1f}%",
                'Geographic Anomaly Check (15%)': f"{geo_score*100:.1f}%",
                'Transaction Frequency Anomaly (20%)': f"{freq_score*100:.1f}%",
                'Destination Pattern Check (20%)': f"{dest_score*100:.1f}%",
                'Transaction Amount Deviation (20%)': f"{amount_dev_score*100:.1f}%"
            }
        }

    def evaluate_rules(self, tx_data, history_data=None):
        """
        Legacy compatibility wrapper returning total_rule_score (0.0 - 1.0) and status.
        """
        res = self.evaluate_indicators(tx_data, history_data)
        score = res['sop_score']
        
        triggered = []
        if res['velocity_score'] >= 0.7: triggered.append("Velocity Anomaly (Score >= 0.7)")
        if res['geographic_score'] >= 0.7: triggered.append("Geographic Anomaly (Score >= 0.7)")
        if res['frequency_score'] >= 0.7: triggered.append("Frequency Burst Anomaly (Score >= 0.7)")
        if res['destination_score'] >= 0.7: triggered.append("Destination Pattern Anomaly (Score >= 0.7)")
        if res['amount_dev_score'] >= 0.7: triggered.append("Amount Baseline Deviation (Score >= 0.7)")
        
        status = 'FRAUD' if score >= 0.70 else ('HIGH RISK' if score >= 0.40 else 'NORMAL')
        
        return {
            'total_rule_score': score * 100.0,
            'sop_score_normalized': score,
            'triggered_rules': triggered,
            'status': status,
            'details': res
        }


    def get_rules_metadata(self):
        """Returns SOP indicators configuration for the UI."""
        return [
            {'name': 'Transaction Velocity Check', 'severity': 'High', 'weight': 25, 'description': 'Perpindahan dana cepat dan disipasi debit-kredit mendadak.'},
            {'name': 'Geographic Anomaly Check', 'severity': 'Medium', 'weight': 15, 'description': 'Perpindahan lokasi fisik/terminal/IP tidak wajar.'},
            {'name': 'Transaction Frequency Anomaly', 'severity': 'High', 'weight': 20, 'description': 'Lonjakan frekuensi transaksi di atas baseline historis.'},
            {'name': 'Destination Pattern Check', 'severity': 'High', 'weight': 20, 'description': 'Pola transfer rekening tujuan baru atau indikasi likuidasi mule.'},
            {'name': 'Transaction Amount Deviation', 'severity': 'Medium', 'weight': 20, 'description': 'Penyimpangan nominal transaksi dari rata-rata historis rekening.'}
        ]
