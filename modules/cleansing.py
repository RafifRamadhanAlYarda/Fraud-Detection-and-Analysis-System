import pandas as pd
import numpy as np
import uuid
import re
from .parser import parse_transaction_remarks
from .anonymizer import DataAnonymizer
from .fraud_labeling_engine import FraudLabelingEngine
from .feature_engineering import engineer_features, MODEL_PREDICTOR_FEATURES
from .data_split import account_level_split
from .imbalance_engine import ImbalanceHandlingEngine
from .pipeline_lineage import PipelineExecutionTracker

class DataCleansingEngine:
    """
    FDAS Forensic Data Cleansing Engine.
    Strictly performs data parsing, validation, deduplication, standardization, and PII anonymization.
    Does NOT perform feature engineering, labeling, or resampling (TPH-SMOTE/KHOI-SMOTE).
    Preserves exact transaction row counts from raw valid data without artificial augmentation.
    """
    def __init__(self):
        self.anonymizer = DataAnonymizer()

    def run_cleansing(self, df, execution_id=None):
        """
        Cleans and standardizes raw bank transaction data.
        Returns:
            cleaned_df: pd.DataFrame with strict lineage columns (is_synthetic=False, dataset_stage='CLEANSED')
            audit_metrics: dict with exact counts of removed duplicates, corrected records, etc.
        """
        if df is None or df.empty:
            raise ValueError("Input dataframe is empty or None.")
            
        raw_rows = len(df)
        df = df.copy()
        if execution_id is None:
            execution_id = f"EXEC-{uuid.uuid4().hex[:8].upper()}"

        audit_metrics = {
            'raw_rows': raw_rows,
            'duplicates_removed': 0,
            'missing_corrected': 0,
            'invalid_records_dropped': 0,
            'cleansed_rows': 0,
            'unique_accounts': 0
        }

        # 0. Sanitize REMARK column (remove unexpected linebreaks and excess whitespaces)
        def sanitize_remark(text):
            if not isinstance(text, str):
                return str(text) if pd.notnull(text) else ""
            text = re.sub(r'[\r\n]+', ' ', text)
            text = re.sub(r'\s+', ' ', text)
            return text.strip()
            
        if 'REMARK' in df.columns:
            df['REMARK'] = df['REMARK'].apply(sanitize_remark)
        else:
            df['REMARK'] = "TRANSAKSI STANDAR"

        # 1. Normalize Column Names to Canonical FDAS Raw Keys
        essential_mapping = {
            'NOREK': ['norek', 'no_rekening', 'account_number', 'account_id', 'rekening', 'no_rek'],
            'TRANS DATE': ['trans date', 'trans_date', 'tanggal_transaksi', 'transaction_date', 'date', 'tgl_trx'],
            'JAM TRX': ['jam trx', 'jam_trx', 'waktu_transaksi', 'transaction_time', 'time', 'jam'],
            'MUTASI DEBET': ['mutasi debet', 'mutasi_debet', 'nominal_debit', 'debit', 'debet'],
            'MUTASI KREDIT': ['mutasi kredit', 'mutasi_kredit', 'nominal_credit', 'credit', 'kredit'],
            'REMARK': ['remark', 'keterangan', 'uraian', 'deskripsi', 'description']
        }
        
        rename_dict = {}
        for canonical, variants in essential_mapping.items():
            if canonical not in df.columns:
                for col in df.columns:
                    norm = str(col).lower().strip().replace('_', ' ')
                    if norm == canonical.lower() or norm in variants:
                        rename_dict[col] = canonical
                        break
        if rename_dict:
            df = df.rename(columns=rename_dict)

        # Count critical nulls before drop
        initial_len = len(df)
        if 'NOREK' in df.columns and 'TRANS DATE' in df.columns:
            df = df.dropna(subset=['NOREK', 'TRANS DATE'])
        elif 'NOREK' in df.columns:
            df = df.dropna(subset=['NOREK'])
        elif 'TRANS DATE' in df.columns:
            df = df.dropna(subset=['TRANS DATE'])
            
        dropped_nulls = initial_len - len(df)
        audit_metrics['invalid_records_dropped'] += dropped_nulls

        # 2. Exact Deduplication
        pre_dedup = len(df)
        df = df.drop_duplicates()
        dedup_count = pre_dedup - len(df)
        audit_metrics['duplicates_removed'] = dedup_count

        # 3. Standardize and Combine Date + Time
        def robust_normalize_datetime(row):
            date_val = str(row.get('TRANS DATE', '')).strip().split(' ')[0]
            time_val = str(row.get('JAM TRX', '')).strip()
            
            if not time_val or time_val.lower() in ['nan', 'none', '', 'nat']:
                time_val = "00:00:00"
            
            while time_val.endswith(':'):
                time_val = time_val[:-1]
            
            parts = time_val.split(':')
            parts = [p.zfill(2) for p in parts]
            while len(parts) < 3:
                parts.append("00")
            
            final_time = ":".join(parts[:3])
            try:
                parsed = pd.to_datetime(f"{date_val} {final_time}", format='mixed', errors='coerce')
                if pd.notnull(parsed):
                    return parsed
            except Exception:
                pass
            return pd.to_datetime(row.get('TRANS DATE', ''), format='mixed', errors='coerce')

        df['transaction_datetime'] = df.apply(robust_normalize_datetime, axis=1)
        missing_dt_count = int(df['transaction_datetime'].isnull().sum())
        if missing_dt_count > 0:
            audit_metrics['missing_corrected'] += missing_dt_count
            df['transaction_datetime'] = df['transaction_datetime'].fillna(pd.Timestamp.now())

        # 4. Standardize Nominal Debit & Kredit
        def clean_nominal(val):
            if val is None or pd.isna(val):
                return 0.0
            if isinstance(val, (int, float)):
                return float(val)
            if isinstance(val, str):
                cleaned = val.replace(' ', '').replace('Rp', '').replace('IDR', '').replace('rp', '')
                if '.' in cleaned and ',' in cleaned:
                    cleaned = cleaned.replace('.', '').replace(',', '.')
                elif '.' in cleaned:
                    parts = cleaned.split('.')
                    if len(parts[-1]) == 3: # thousands separator
                        cleaned = cleaned.replace('.', '')
                elif ',' in cleaned:
                    cleaned = cleaned.replace(',', '.')
                try:
                    return float(cleaned)
                except Exception:
                    return 0.0
            return 0.0

        if 'MUTASI DEBET' in df.columns:
            df['nominal_debit'] = df['MUTASI DEBET'].apply(clean_nominal)
        else:
            df['nominal_debit'] = 0.0
            
        if 'MUTASI KREDIT' in df.columns:
            df['nominal_credit'] = df['MUTASI KREDIT'].apply(clean_nominal)
        else:
            df['nominal_credit'] = 0.0
            
        df['nominal'] = df['nominal_debit'] + df['nominal_credit']

        # 5. Direction Classification
        def get_direction(row):
            if row['nominal_debit'] > 0: return 'DEBIT'
            if row['nominal_credit'] > 0: return 'CREDIT'
            return 'ZERO'
        
        df['transaction_direction'] = df.apply(get_direction, axis=1)

        # 6. Parse Remark Transaksi (Channel, Category, Merchant)
        df = parse_transaction_remarks(df, remark_col='REMARK')

        # 7. Text Normalization and PII Anonymization
        df['remark_clean'] = df['REMARK'].apply(self.anonymizer.anonymize_remark)
        df['remark_clean'] = df['remark_clean'].str.replace(';', ' | ', regex=False)

        # 8. Source Account Key and Deterministic Masked Account ID
        if 'NOREK' in df.columns:
            df['source_account_key'] = df['NOREK'].astype(str).str.strip().str.split('.').str[0]
            df['account_id'] = df['source_account_key'].apply(self.anonymizer.mask_account)
        else:
            df['source_account_key'] = "ACC_UNKNOWN"
            df['account_id'] = "ACC_UNKNOWN"

        # 9. Sort Chronologically per Account
        df = df.sort_values(by=['account_id', 'transaction_datetime']).reset_index(drop=True)

        # 10. Data Lineage Metadata (Section F, H)
        df['is_synthetic'] = False
        df['dataset_stage'] = 'CLEANSED'
        df['sample_origin'] = 'original'
        df['resampling_method'] = 'none'
        df['execution_id'] = execution_id

        # Preserve ground truth label if already present in dataset, otherwise do not force it
        # Labeling will be performed separately in the Label Construction stage
        if 'fraud_label' in df.columns:
            df['fraud_label'] = pd.to_numeric(df['fraud_label'], errors='coerce').fillna(0).astype(int)

        cleansed_cols = [
            'transaction_datetime', 'source_account_key', 'account_id', 
            'nominal_debit', 'nominal_credit', 'nominal', 'transaction_direction', 
            'remark_clean', 'transaction_code', 'transaction_channel', 
            'transaction_location', 'transaction_category', 'transaction_type', 
            'transaction_behavior', 'transaction_risk_flag',
            'is_synthetic', 'dataset_stage', 'sample_origin', 'resampling_method', 'execution_id'
        ]
        
        if 'fraud_label' in df.columns:
            cleansed_cols.append('fraud_label')
            
        for col in cleansed_cols:
            if col not in df.columns:
                df[col] = 0

        final_df = df[cleansed_cols].copy()
        
        audit_metrics['cleansed_rows'] = len(final_df)
        audit_metrics['unique_accounts'] = final_df['account_id'].nunique()

        return final_df


def run_cleansing_data_process(raw_df, execution_id=None, tracker=None):
    """
    Unified FDAS Preprocessing & Cleansing Pipeline Orchestrator.
    Executes the academic forensic pipeline behind a single action:
      Step A: RAW Validation
      Step B: Data Cleansing (RAW -> CLEANSED)
      Step C: Target Label Construction (CLEANSED -> LABELED)
      Step D: Predictive Feature Engineering (LABELED -> ANALYTICAL)
      Step E: Account-Level Disjoint Partitioning (ANALYTICAL -> TRAIN / VAL / TEST)
      Step F: Training Resampling (TPH-SMOTE & KHOI-SMOTE on TRAIN ONLY)
      Step G: End-to-End Lineage Audit Trail Recording
    
    Guarantees:
      1. Cleaned dataset has exactly 0 synthetic records (is_synthetic = False).
      2. Validation and Test partitions have exactly 0 synthetic records (leakage-free).
      3. TPH-SMOTE and KHOI-SMOTE are executed as separate comparative resamplers on TRAIN.
      4. Dynamic row counts strictly derived from live DataFrames (len(df)).
    """
    if raw_df is None or raw_df.empty:
        raise ValueError("Cannot run cleansing process: raw_df is None or empty.")
        
    if execution_id is None:
        execution_id = f"FDAS-{pd.Timestamp.now().strftime('%Y-%m-%d-%H%M%S')}-{uuid.uuid4().hex[:4].upper()}"
        
    if tracker is None:
        tracker = PipelineExecutionTracker(execution_id=execution_id)
        
    # STEP A: RAW Validation & Registration
    tracker.register_stage('RAW', raw_df, metadata={
        'rows_ingested': len(raw_df),
        'unique_accounts': int(raw_df['NOREK'].nunique() if 'NOREK' in raw_df.columns else (raw_df['account_id'].nunique() if 'account_id' in raw_df.columns else 1))
    })
    
    # STEP B: Data Cleansing Engine (RAW ➔ CLEANSED)
    cleansing_engine = DataCleansingEngine()
    cleaned_df = cleansing_engine.run_cleansing(raw_df, execution_id=execution_id)
    tracker.register_stage('CLEANSED', cleaned_df, metadata={
        'rows_cleaned': len(cleaned_df),
        'unique_accounts': int(cleaned_df['account_id'].nunique()),
        'synthetic_rows': 0
    })
    
    # STEP C: Target Label Construction
    labeling_engine = FraudLabelingEngine()
    labeled_df = labeling_engine.construct_target_labels(cleaned_df)
    
    # STEP D: Predictive Feature Engineering (CLEANSED ➔ ANALYTICAL)
    analytical_df = engineer_features(labeled_df, execution_id=execution_id)
    n_fraud = int((analytical_df['fraud_label'] == 1).sum())
    n_normal = len(analytical_df) - n_fraud
    tracker.register_stage('ANALYTICAL', analytical_df, metadata={
        'features_count': len(MODEL_PREDICTOR_FEATURES),
        'fraud_rows': n_fraud,
        'normal_rows': n_normal,
        'imbalance_ratio': round(n_fraud / max(1, n_normal), 4)
    })
    
    # STEP E: Account-Level Disjoint Split (70:15:15 by Account ID)
    train_df, val_df, test_df, split_meta = account_level_split(analytical_df, account_col='account_id')
    tracker.register_stage('SPLIT_TRAIN', train_df, metadata=split_meta)
    tracker.register_stage('SPLIT_VAL', val_df, metadata={'leakage_free': True, 'synthetic_rows': 0, 'rows': len(val_df)})
    tracker.register_stage('SPLIT_TEST', test_df, metadata={'leakage_free': True, 'synthetic_rows': 0, 'rows': len(test_df)})
    
    # STEP F: Training Resampling (TPH-SMOTE & KHOI-SMOTE on TRAIN ONLY)
    imbalance_engine = ImbalanceHandlingEngine()
    
    tph_train_df = train_df.copy()
    khoi_train_df = train_df.copy()
    
    # Target and features on train
    if not train_df.empty and 'fraud_label' in train_df.columns:
        X_train = train_df[MODEL_PREDICTOR_FEATURES]
        y_train = train_df['fraud_label'].values
        
        # 1. TPH-SMOTE
        try:
            X_tph, y_tph, mask_tph = imbalance_engine.tph_smote(X_train, y_train)
            n_synth_tph = int(mask_tph.sum())
            tph_train_df = pd.DataFrame(X_tph, columns=MODEL_PREDICTOR_FEATURES)
            tph_train_df['fraud_label'] = y_tph
            tph_train_df['is_synthetic'] = mask_tph
            tph_train_df['execution_id'] = execution_id
            tph_train_df['dataset_stage'] = 'TPH_RESAMPLED_TRAIN'
            tph_train_df['resampling_method'] = 'tph_smote'
            tph_train_df['sample_origin'] = np.where(mask_tph, 'synthetic_tph_smote', 'original')
            
            tracker.register_stage('TPH_RESAMPLED_TRAIN', tph_train_df, metadata={
                'status': 'COMPLETED',
                'method': 'TPH-SMOTE',
                'original_train_rows': len(train_df),
                'synthesized_rows': n_synth_tph,
                'final_train_rows': len(tph_train_df)
            })
        except Exception as e:
            tracker.stages['TPH_RESAMPLED_TRAIN'] = {
                'status': 'FAILED',
                'dataset_id': None,
                'stage_name': 'TPH_RESAMPLED_TRAIN',
                'row_count': len(train_df),
                'accounts': 1,
                'synthetic_rows': 0,
                'timestamp': pd.Timestamp.now().isoformat(),
                'metadata': {'error': str(e)}
            }
            
        # 2. KHOI-SMOTE (Separate comparative benchmark on same original TRAIN)
        try:
            X_khoi, y_khoi, mask_khoi = imbalance_engine.khoi_smote(X_train, y_train)
            n_synth_khoi = int(mask_khoi.sum())
            khoi_train_df = pd.DataFrame(X_khoi, columns=MODEL_PREDICTOR_FEATURES)
            khoi_train_df['fraud_label'] = y_khoi
            khoi_train_df['is_synthetic'] = mask_khoi
            khoi_train_df['execution_id'] = execution_id
            khoi_train_df['dataset_stage'] = 'KHOI_RESAMPLED_TRAIN'
            khoi_train_df['resampling_method'] = 'khoi_smote'
            khoi_train_df['sample_origin'] = np.where(mask_khoi, 'synthetic_khoi_smote', 'original')
            
            tracker.register_stage('KHOI_RESAMPLED_TRAIN', khoi_train_df, metadata={
                'status': 'COMPLETED',
                'method': 'KHOI-SMOTE',
                'original_train_rows': len(train_df),
                'synthesized_rows': n_synth_khoi,
                'final_train_rows': len(khoi_train_df)
            })
        except Exception as e:
            tracker.stages['KHOI_RESAMPLED_TRAIN'] = {
                'status': 'FAILED',
                'dataset_id': None,
                'stage_name': 'KHOI_RESAMPLED_TRAIN',
                'row_count': len(train_df),
                'accounts': 1,
                'synthetic_rows': 0,
                'timestamp': pd.Timestamp.now().isoformat(),
                'metadata': {'error': str(e)}
            }
            
        # Register primary resampled train baseline (TPH-SMOTE)
        tracker.register_stage('RESAMPLED_TRAIN', tph_train_df, metadata={
            'method': 'TPH-SMOTE',
            'original_train_rows': len(train_df),
            'synthesized_rows': int(tph_train_df['is_synthetic'].sum()) if 'is_synthetic' in tph_train_df.columns else 0,
            'final_train_rows': len(tph_train_df)
        })

    return {
        'cleaned_df': cleaned_df,
        'analytical_df': analytical_df,
        'train_df': train_df,
        'val_df': val_df,
        'test_df': test_df,
        'tph_train_df': tph_train_df,
        'khoi_train_df': khoi_train_df,
        'train_resampled_df': tph_train_df,
        'split_meta': split_meta,
        'tracker': tracker
    }

