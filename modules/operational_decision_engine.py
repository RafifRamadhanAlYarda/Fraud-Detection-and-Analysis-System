class OperationalDecisionEngine:
    """
    Translates Fraud Scores into Bank Enterprise Operational Decision Support.
    Syncs strictly with Research Methodology Contract (DSS with Human Oversight).
    """
    def __init__(self):
        pass

    def generate_operational_decision(self, status, hybrid_score):
        """
        Thresholds & Actions:
        - FRAUD (>= 0.70): Investigation Recommended according to SOP; final decision with analyst
        - HIGH RISK ([0.40, 0.70)): Enhanced Analyst Review Recommended
        - NORMAL (< 0.40): Routine Monitoring
        """
        score_val = float(hybrid_score)
        if score_val > 1.0:
            score_val = score_val / 100.0
            
        if status == 'FRAUD' or score_val >= 0.70:
            return {
                'action': 'INVESTIGATION_RECOMMENDED',
                'priority': 'HIGH',
                'recommendation': self.generate_investigation_recommendation()
            }
        elif status == 'HIGH RISK' or score_val >= 0.40:
            return {
                'action': 'ENHANCED_REVIEW',
                'priority': 'MEDIUM',
                'recommendation': self.generate_review_recommendation()
            }
        else:
            return {
                'action': 'ROUTINE_MONITORING',
                'priority': 'LOW',
                'recommendation': self.generate_monitoring_recommendation()
            }

    def generate_investigation_recommendation(self):
        return (
            "- Investigation Recommended according to SOP\n"
            "- Analyst Validation Required\n"
            "- Review and verify transaction evidence with customer profile"
        )

    def generate_review_recommendation(self):
        return (
            "- Enhanced Analyst Review Recommended\n"
            "- Monitor fund liquidation patterns and transaction velocity\n"
            "- Cross-check transaction flow with historical customer baseline"
        )

    def generate_monitoring_recommendation(self):
        return (
            "- Routine monitoring. Transaksi dalam batas wajar statistik.\n"
            "- Standard periodic transaction review"
        )

    def get_operational_action(self, status, hybrid_score, p_lgbm=None, p_lstm=None, sop_score=None):
        """Convenience method returning structured decision for operational support."""
        dec = self.generate_operational_decision(status, hybrid_score)
        return {
            'status': status,
            'hybrid_score': hybrid_score,
            'recommended_action': dec['recommendation'],
            'action_code': dec['action'],
            'priority': dec['priority']
        }
