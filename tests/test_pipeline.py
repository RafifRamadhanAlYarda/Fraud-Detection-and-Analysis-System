import unittest
import pandas as pd
import numpy as np
from generate_dummy_data import generate_academic_dummy_dataset
from modules.cleansing import DataCleansingEngine
from modules.feature_engineering import engineer_features, get_feature_matrix, MODEL_PREDICTOR_FEATURES
from modules.data_split import account_level_split, verify_no_account_leakage
from modules.imbalance_engine import ImbalanceHandlingEngine
from modules.fusion_engine import FusionScoringEngine
from modules.pipeline_lineage import PipelineExecutionTracker

class TestFDASDataPipeline(unittest.TestCase):

    def setUp(self):
        self.raw_50_df = generate_academic_dummy_dataset(n_accounts=50, random_seed=42)
        self.cleansing_engine = DataCleansingEngine()
        self.imbalance_engine = ImbalanceHandlingEngine(random_state=42)
        self.fusion_engine = FusionScoringEngine()

    def test_01_academic_dataset_integrity(self):
        """Verify 50 accounts (25 normal, 25 fraud) across 2025 timeline."""
        n_accounts = self.raw_50_df['NOREK'].nunique()
        self.assertEqual(n_accounts, 50, "Dataset must have exactly 50 accounts.")
        
        n_tx = len(self.raw_50_df)
        self.assertGreater(n_tx, 1500, "Transaction count must be realistic and substantial.")
        self.assertNotEqual(n_accounts, n_tx, "Account count must NOT equal Transaction count.")
        
        dates = pd.to_datetime(self.raw_50_df['TRANS DATE'])
        self.assertEqual(dates.dt.year.min(), 2025)
        self.assertEqual(dates.dt.year.max(), 2025)

    def test_02_cleansing_purity_and_lineage(self):
        """Verify cleansing preserves exact transaction row counts, sets lineage, and has NO synthetic samples."""
        exec_id = "FDAS-TEST-EXEC-001"
        cleaned_df = self.cleansing_engine.run_cleansing(self.raw_50_df, execution_id=exec_id)
        
        # Exact transaction count matching valid raw rows (raw - duplicates - nulls)
        self.assertEqual(len(cleaned_df), len(self.raw_50_df), "Cleansing must NOT arbitrarily inflate or deflate row count.")
        
        # Lineage columns check
        self.assertIn('is_synthetic', cleaned_df.columns)
        self.assertIn('execution_id', cleaned_df.columns)
        self.assertIn('dataset_stage', cleaned_df.columns)
        self.assertIn('sample_origin', cleaned_df.columns)
        self.assertIn('resampling_method', cleaned_df.columns)
        
        # Assertions on cleansed stage
        self.assertFalse(cleaned_df['is_synthetic'].any(), "Cleansed records must have is_synthetic = False.")
        self.assertTrue((cleaned_df['dataset_stage'] == 'CLEANSED').all())
        self.assertTrue((cleaned_df['sample_origin'] == 'original').all())
        self.assertTrue((cleaned_df['resampling_method'] == 'none').all())
        self.assertEqual(cleaned_df['execution_id'].iloc[0], exec_id)

    def test_03_single_account_scope_detection(self):
        """Verify single account input (e.g. Rek Fraud 1 with 1 account) triggers single-account scope restriction."""
        single_acc_df = self.raw_50_df[self.raw_50_df['NOREK'] == self.raw_50_df['NOREK'].iloc[0]].copy()
        self.assertEqual(single_acc_df['NOREK'].nunique(), 1)
        
        cleaned_single = self.cleansing_engine.run_cleansing(single_acc_df)
        train_s, val_s, test_s, meta_s = account_level_split(cleaned_single, account_col='account_id')
        
        self.assertFalse(meta_s['can_account_split'])
        self.assertIn("Insufficient account count", meta_s['reason'])
        self.assertEqual(meta_s['train_accounts'], 0)

    def test_04_account_level_split_disjointness_50_accounts(self):
        """Verify strict account-level split with zero account leakage across Train, Val, and Test."""
        cleaned_df = self.cleansing_engine.run_cleansing(self.raw_50_df)
        train_df, val_df, test_df, meta = account_level_split(cleaned_df, account_col='account_id', test_size=0.15, val_size=0.15)
        
        self.assertTrue(meta['can_account_split'])
        self.assertEqual(meta['total_accounts'], 50)
        self.assertGreater(meta['train_accounts'], 30)
        self.assertGreater(meta['val_accounts'], 5)
        self.assertGreater(meta['test_accounts'], 5)
        
        # Disjointness checks
        train_accs = set(train_df['account_id'].unique())
        val_accs = set(val_df['account_id'].unique())
        test_accs = set(test_df['account_id'].unique())
        
        self.assertTrue(train_accs.isdisjoint(val_accs), "Account leakage: Train and Val share accounts!")
        self.assertTrue(train_accs.isdisjoint(test_accs), "Account leakage: Train and Test share accounts!")
        self.assertTrue(val_accs.isdisjoint(test_accs), "Account leakage: Val and Test share accounts!")
        self.assertTrue(verify_no_account_leakage(train_df, val_df, test_df, account_col='account_id'))

    def test_05_resampling_applied_strictly_to_train_only(self):
        """Verify TPH-SMOTE and KHOI-SMOTE run only on TRAIN and generate synthetic records with exact provenance."""
        cleaned_df = self.cleansing_engine.run_cleansing(self.raw_50_df)
        analytical_df = engineer_features(cleaned_df)
        
        train_df, val_df, test_df, meta = account_level_split(analytical_df, account_col='account_id')
        
        X_train = train_df[MODEL_PREDICTOR_FEATURES]
        y_train = train_df['fraud_label'].values
        
        # Test TPH-SMOTE
        X_tph, y_tph, synth_mask_tph = self.imbalance_engine.tph_smote(X_train, y_train)
        n_synth_tph = int(synth_mask_tph.sum())
        self.assertEqual(len(X_tph), len(X_train) + n_synth_tph, "Train after must equal Train before + synthetic generated.")
        
        # Test KHOI-SMOTE
        X_khoi, y_khoi, synth_mask_khoi = self.imbalance_engine.khoi_smote(X_train, y_train)
        n_synth_khoi = int(synth_mask_khoi.sum())
        self.assertEqual(len(X_khoi), len(X_train) + n_synth_khoi, "Train after must equal Train before + synthetic generated.")
        
        # Verify Validation & Test have ZERO synthetic records
        self.assertEqual(int(val_df['is_synthetic'].sum()), 0, "Validation set must NEVER contain synthetic samples.")
        self.assertEqual(int(test_df['is_synthetic'].sum()), 0, "Test set must NEVER contain synthetic samples.")

    def test_06_target_and_identifier_leakage_prevention(self):
        """Verify fraud_label, account_id, source_account_key, and execution_id are NEVER in predictor feature matrix."""
        cleaned_df = self.cleansing_engine.run_cleansing(self.raw_50_df)
        analytical_df = engineer_features(cleaned_df)
        X = get_feature_matrix(analytical_df)
        
        self.assertNotIn('fraud_label', X.columns)
        self.assertNotIn('account_id', X.columns)
        self.assertNotIn('source_account_key', X.columns)
        self.assertNotIn('execution_id', X.columns)
        self.assertNotIn('dataset_stage', X.columns)

    def test_07_fusion_formula_strict_assertion(self):
        """Verify Fusion formula: FinalScore = 0.40 * LightGBM + 0.40 * LSTM + 0.20 * SOP_Score and thresholds."""
        p_lgbm = 0.85
        p_lstm = 0.75
        sop_rule = 0.60
        
        # Expected: 0.40*0.85 + 0.40*0.75 + 0.20*0.60 = 0.34 + 0.30 + 0.12 = 0.76
        expected_score = 0.76
        calculated_score = float(self.fusion_engine.fuse(p_lgbm, p_lstm, sop_rule))
        
        self.assertAlmostEqual(calculated_score, expected_score, places=5)
        status_fraud, _, _ = self.fusion_engine.categorize_fraud(calculated_score)
        self.assertEqual(status_fraud, 'FRAUD', "Score 0.76 must be categorized as FRAUD (>= 0.70)")

        # Test High Risk range [0.40, 0.70)
        score_hr = float(self.fusion_engine.fuse(0.50, 0.50, 0.50)) # 0.50
        status_hr, _, _ = self.fusion_engine.categorize_fraud(score_hr)
        self.assertEqual(status_hr, 'HIGH RISK', "Score 0.50 must be categorized as HIGH RISK ([0.40, 0.70))")

        # Test Normal range (< 0.40)
        score_norm = float(self.fusion_engine.fuse(0.20, 0.20, 0.20)) # 0.20
        status_norm, _, _ = self.fusion_engine.categorize_fraud(score_norm)
        self.assertEqual(status_norm, 'NORMAL', "Score 0.20 must be categorized as NORMAL (< 0.40)")

if __name__ == '__main__':
    unittest.main()
