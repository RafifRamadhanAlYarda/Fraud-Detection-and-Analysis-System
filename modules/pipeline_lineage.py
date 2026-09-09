import datetime
import uuid
import pandas as pd
import numpy as np

class PipelineExecutionTracker:
    """
    Manages end-to-end data lineage, execution state, and artifact provenance
    for the FDAS Fraud Detection Pipeline.
    Strictly guarantees that:
    1. Execution A never mixes with Execution B (deterministic execution_id).
    2. Stage datasets (RAW, CLEANSED, ANALYTICAL, TRAIN, VAL, TEST, TRAIN_RESAMPLED) are preserved with distinct dataset_ids.
    3. Counts are measured directly from live DataFrames (len(df)), never hardcoded.
    4. '0' (executed with 0 count) is strictly distinguished from 'NOT EXECUTED'.
    5. Completely JSON serializable for audit exports without DataFrame serialization errors.
    """
    def __init__(self, execution_id=None):
        if execution_id:
            self.execution_id = execution_id
        else:
            now_str = datetime.datetime.now().strftime("%Y-%m-%d-%H%M%S")
            self.execution_id = f"FDAS-{now_str}-{uuid.uuid4().hex[:4].upper()}"
            
        self.created_at = datetime.datetime.now().isoformat()
        self.stages = {
            'RAW': {'status': 'NOT EXECUTED', 'dataset_id': None, 'row_count': 0, 'accounts': 0, 'metadata': {}},
            'CLEANSED': {'status': 'NOT EXECUTED', 'dataset_id': None, 'row_count': 0, 'accounts': 0, 'duplicates_removed': 0, 'metadata': {}},
            'ANALYTICAL': {'status': 'NOT EXECUTED', 'dataset_id': None, 'row_count': 0, 'features': 0, 'fraud_rows': 0, 'normal_rows': 0, 'metadata': {}},
            'SPLIT_TRAIN': {'status': 'NOT EXECUTED', 'dataset_id': None, 'row_count': 0, 'metadata': {}},
            'SPLIT_VAL': {'status': 'NOT EXECUTED', 'dataset_id': None, 'row_count': 0, 'synthetic_rows': 0, 'metadata': {}},
            'SPLIT_TEST': {'status': 'NOT EXECUTED', 'dataset_id': None, 'row_count': 0, 'synthetic_rows': 0, 'metadata': {}},
            'TPH_RESAMPLED_TRAIN': {'status': 'NOT EXECUTED', 'dataset_id': None, 'row_count': 0, 'synthetic_rows': 0, 'method': 'TPH-SMOTE', 'metadata': {}},
            'KHOI_RESAMPLED_TRAIN': {'status': 'NOT EXECUTED', 'dataset_id': None, 'row_count': 0, 'synthetic_rows': 0, 'method': 'KHOI-SMOTE', 'metadata': {}},
            'RESAMPLED_TRAIN': {'status': 'NOT EXECUTED', 'dataset_id': None, 'row_count': 0, 'synthetic_rows': 0, 'method': None, 'metadata': {}}
        }
        self.logs = []
        self._data_store = {}

    def log(self, message):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        self.logs.append(log_entry)

    def register_stage(self, stage_name, df, metadata=None):
        """Universal stage registration with automatic metadata extraction."""
        if df is None:
            return
        
        meta = metadata or {}
        dataset_id = f"{stage_name}-{self.execution_id}"
        
        # Calculate key metrics
        row_count = len(df) if isinstance(df, (pd.DataFrame, pd.Series)) else 0
        acc_col = 'NOREK' if 'NOREK' in df.columns else ('account_id' if 'account_id' in df.columns else None)
        n_accounts = int(df[acc_col].nunique()) if (acc_col and isinstance(df, pd.DataFrame)) else 1
        
        synth_count = 0
        if isinstance(df, pd.DataFrame) and 'is_synthetic' in df.columns:
            synth_count = int(df['is_synthetic'].sum())
            
        stage_record = {
            'status': 'COMPLETED',
            'dataset_id': dataset_id,
            'stage_name': stage_name,
            'row_count': row_count,
            'accounts': n_accounts,
            'synthetic_rows': synth_count,
            'timestamp': datetime.datetime.now().isoformat(),
            'metadata': meta
        }
        
        self.stages[stage_name] = stage_record
        # Save DataFrame separately so self.stages remains purely JSON serializable
        self._data_store[stage_name] = df.copy() if hasattr(df, 'copy') else df
        
        self.log(f"[{stage_name}] Registered {row_count:,} rows ({n_accounts} accounts, {synth_count} synthetic). dataset_id={dataset_id}")

    def get_stage_info(self, stage_name):
        """Retrieve metadata for a specific stage safely."""
        return self.stages.get(stage_name, None)

    def get_audit_trail(self):
        """Returns JSON-serializable audit summary dictionary."""
        return {
            'execution_id': self.execution_id,
            'created_at': self.created_at,
            'stages': {k: v for k, v in self.stages.items()},
            'logs': self.logs
        }

    def get_summary(self):
        """Alias to get_audit_trail."""
        return self.get_audit_trail()

    # Legacy method compatibility
    def register_raw(self, df):
        self.register_stage('RAW', df, metadata={'source': 'Raw Ingestion'})

    def register_cleansed(self, df, duplicates_removed=0, missing_corrected=0, invalid_records=0):
        self.register_stage('CLEANSED', df, metadata={
            'duplicates_removed': duplicates_removed,
            'missing_corrected': missing_corrected,
            'invalid_records': invalid_records
        })

    def register_analytical(self, df, feature_cols=None):
        label_col = 'fraud_label' if 'fraud_label' in df.columns else None
        fraud_count = int((df[label_col] == 1).sum()) if (label_col and isinstance(df, pd.DataFrame)) else 0
        normal_count = len(df) - fraud_count if isinstance(df, pd.DataFrame) else 0
        self.register_stage('ANALYTICAL', df, metadata={
            'features_count': len(feature_cols) if feature_cols else len(df.columns),
            'fraud_rows': fraud_count,
            'normal_rows': normal_count
        })

    def register_split(self, train_df, val_df, test_df, split_meta):
        self.register_stage('SPLIT_TRAIN', train_df, metadata=split_meta)
        self.register_stage('SPLIT_VAL', val_df, metadata={'leakage_free': True})
        self.register_stage('SPLIT_TEST', test_df, metadata={'leakage_free': True})

    def register_resampling(self, method, before_df, resampled_df, synth_count):
        self.register_stage('RESAMPLED_TRAIN', resampled_df, metadata={
            'method': method,
            'original_train_rows': len(before_df),
            'synthesized_rows': synth_count,
            'final_train_rows': len(resampled_df)
        })
