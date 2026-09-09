import unittest
import pandas as pd
import numpy as np
import os
from modules.cleansing import DataCleansingEngine
from modules.feature_engineering import engineer_features, MODEL_PREDICTOR_FEATURES
from modules.lightgbm_engine import LightGBMEngine
from modules.lstm_engine import LSTMEngine
from modules.fraud_rules_engine import OperationalRiskRulesEngine
from modules.fusion_engine import FusionScoringEngine, calculate_final_score, get_risk_category, get_recommendation
from modules.hybrid_xai_engine import HybridXAIEngine
from modules.operational_decision_engine import OperationalDecisionEngine
from modules.report_generator import PDFReportGenerator

class TestFDASFullRegression(unittest.TestCase):

    def setUp(self):
        self.cleansing_engine = DataCleansingEngine()
        self.lgbm_engine = LightGBMEngine()
        self.lstm_engine = LSTMEngine()
        self.rules_engine = OperationalRiskRulesEngine()
        self.fusion_engine = FusionScoringEngine()
        self.decision_engine = OperationalDecisionEngine()
        self.pdf_generator = PDFReportGenerator()

    def test_01_artifact_integrity_and_validation(self):
        """Verify LightGBM and LSTM artifacts pass strict validation checks."""
        lgbm_val = self.lgbm_engine.validate_model_artifact()
        self.assertTrue(lgbm_val['valid'], f"LightGBM validation failed: {lgbm_val['error']}")
        self.assertEqual(lgbm_val['status_code'], 'VALID')
        self.assertGreater(lgbm_val['feature_count'], 0)

        lstm_val = self.lstm_engine.validate_model_artifact()
        self.assertTrue(lstm_val['valid'], f"LSTM validation failed: {lstm_val['error']}")
        self.assertEqual(lstm_val['status_code'], 'VALID')
        self.assertGreater(lstm_val['feature_count'], 0)

        # Verify loading
        self.assertTrue(self.lgbm_engine.load_model())
        self.assertTrue(self.lstm_engine.load_model())

    def test_02_e2e_rek1_dataset_processing(self):
        """Verify end-to-end processing of REK 1.xlsx dataset without errors."""
        if os.path.exists("REK 1.xlsx"):
            raw_df = pd.read_excel("REK 1.xlsx")
            cleaned_df = self.cleansing_engine.run_cleansing(raw_df)
            self.assertGreater(len(cleaned_df), 0)
            
            # Feature engineering
            feat_df = engineer_features(cleaned_df)
            for col in self.lgbm_engine.feature_cols:
                self.assertIn(col, feat_df.columns)
            for col in self.lstm_engine.feature_cols:
                self.assertIn(col, feat_df.columns)

            # Inference
            lgbm_probs = self.lgbm_engine.predict_proba(feat_df)
            self.assertEqual(len(lgbm_probs), len(feat_df))
            self.assertTrue(np.all(lgbm_probs >= 0.0) and np.all(lgbm_probs <= 1.0))

            lstm_probs = self.lstm_engine.predict_proba(feat_df)
            self.assertEqual(len(lstm_probs), len(feat_df))
            self.assertTrue(np.all(lstm_probs >= 0.0) and np.all(lstm_probs <= 1.0))

            # SOP Evaluation
            sop_scores = []
            for _, row in feat_df.iterrows():
                eval_res = self.rules_engine.evaluate_rules(row.to_dict())
                sop_scores.append(eval_res['sop_score_normalized'])
            
            # Fusion
            hybrid_scores = self.fusion_engine.fuse(lgbm_probs, lstm_probs, np.array(sop_scores))
            self.assertEqual(len(hybrid_scores), len(feat_df))
            self.assertTrue(np.all(hybrid_scores >= 0.0) and np.all(hybrid_scores <= 1.0))

            # Verify math
            for i in range(len(hybrid_scores)):
                expected = 0.40 * lgbm_probs[i] + 0.40 * lstm_probs[i] + 0.20 * sop_scores[i]
                self.assertAlmostEqual(hybrid_scores[i], expected, places=4)

    def test_03_sop_rules_independence(self):
        """Verify OperationalRiskRulesEngine evaluates 5 rules independently without brilink."""
        sample_row = {
            'nominal': 100000000.0,
            'nominal_debit': 100000000.0,
            'nominal_credit': 0.0,
            'is_night': 1,
            'risk_velocity': 350.0,
            'time_interval': 1.0,
            'hour': 2,
            'remark_clean': 'TRANSFER KASINO'
        }
        res = self.rules_engine.evaluate_rules(sample_row)
        self.assertIn('total_rule_score', res)
        self.assertIn('sop_score_normalized', res)
        self.assertIn('triggered_rules', res)
        self.assertGreater(res['total_rule_score'], 0)

    def test_04_decision_support_and_no_auto_block(self):
        """Verify decisions act as recommendations (DSS) and never issue raw automatic blocking."""
        dec_fraud = self.decision_engine.generate_operational_decision('FRAUD', 0.85)
        self.assertIn('recommendation', dec_fraud)
        self.assertEqual(dec_fraud['action'], 'INVESTIGATION_RECOMMENDED')
        self.assertNotIn('AUTONOMOUS_BLOCK_EXECUTED', dec_fraud.get('recommendation', ''))

        dec_hr = self.decision_engine.generate_operational_decision('HIGH RISK', 0.55)
        self.assertIn('recommendation', dec_hr)
        self.assertEqual(dec_hr['action'], 'ENHANCED_REVIEW')

        dec_norm = self.decision_engine.generate_operational_decision('NORMAL', 0.15)
        self.assertIn('recommendation', dec_norm)
        self.assertEqual(dec_norm['action'], 'ROUTINE_MONITORING')

    def test_05_pdf_report_generation(self):
        """Verify PDF report generation completes successfully."""
        report_data = {
            'filename': 'Forensic_Report.pdf',
            'account_id': 'TEST-ACC-001',
            'total_transactions': 25,
            'total_accounts': 1,
            'lgbm_score': 0.82,
            'lstm_score': 0.78,
            'hybrid_score': 0.80,
            'status': 'FRAUD',
            'recommendation': 'Investigation recommended according to operational procedure; final decision remains with authorized analyst.',
            'reasons': ['High transaction velocity detected', 'Unusual night time activity'],
            'behavior_exp': {'summary': 'Behavioral anomaly detected.'},
            'generated_by': 'Auditor-Test'
        }
        pdf_bytes = self.pdf_generator.generate(report_data)
        self.assertIsInstance(pdf_bytes, bytes)
        self.assertGreater(len(pdf_bytes), 100)

if __name__ == '__main__':
    unittest.main()
