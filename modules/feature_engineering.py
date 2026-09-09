import pandas as pd
import numpy as np

# Canonical list of model predictor features (Strictly excludes labels, IDs, or lineage keys)
MODEL_PREDICTOR_FEATURES = [
    'nominal_debit', 'nominal_credit', 'nominal_log',
    'time_interval', 'risk_velocity',
    'rolling_tx_count_1h', 'rolling_tx_count_24h',
    'hour', 'day_of_week', 'is_weekend', 'is_night',
    'nominal_dev', 'liquidation_ratio',
    'transaction_category_encoded', 'transaction_channel_encoded',
    'transaction_code_encoded', 'transaction_type_encoded',
    'transaction_behavior_encoded', 'transaction_direction_encoded',
    'transaction_risk_flag'
]

def engineer_features(df, execution_id=None):
    """
    Transforms CLEANSED dataset into ANALYTICAL dataset with rich predictive features.
    Strictly prevents target leakage (fraud_label and identifiers are separated from X).
    """
    if df is None or df.empty:
        raise ValueError("Input dataframe is empty or None.")
        
    df = df.copy()
    
    # 1. Datetime extraction
    df['transaction_datetime'] = pd.to_datetime(df['transaction_datetime'], errors='coerce').fillna(pd.Timestamp.now())
    df['hour'] = df['transaction_datetime'].dt.hour
    df['day_of_week'] = df['transaction_datetime'].dt.dayofweek
    df['is_weekend'] = df['day_of_week'].apply(lambda x: 1 if x >= 5 else 0)
    df['is_night'] = df['hour'].apply(lambda x: 1 if (x < 6 or x >= 22) else 0)

    # 2. Sort by account and datetime to compute sequential dynamics
    acc_col = 'account_id' if 'account_id' in df.columns else 'source_account_key'
    df = df.sort_values(by=[acc_col, 'transaction_datetime']).reset_index(drop=True)

    # 3. Numeric conversions
    df['nominal_debit'] = pd.to_numeric(df['nominal_debit'], errors='coerce').fillna(0.0)
    df['nominal_credit'] = pd.to_numeric(df['nominal_credit'], errors='coerce').fillna(0.0)
    df['nominal'] = df['nominal_debit'] + df['nominal_credit']
    df['nominal_log'] = np.log1p(df['nominal'])

    # 4. Sequential time interval & Risk Velocity
    df['time_interval'] = df.groupby(acc_col)['transaction_datetime'].diff().dt.total_seconds().fillna(0.0)
    df['risk_velocity'] = df['nominal'] / (df['time_interval'] + 1.0)

    # 5. True Rolling Transaction Frequency (1-hour and 24-hour windows per account)
    # Using efficient series-based rolling per account
    try:
        r1h_list = []
        r24h_list = []
        for _, group in df.groupby(acc_col):
            g_sorted = group.sort_values('transaction_datetime')
            g_indexed = g_sorted.set_index('transaction_datetime')
            r1h = g_indexed['nominal'].rolling('1h').count().values
            r24h = g_indexed['nominal'].rolling('24h').count().values
            r1h_list.extend(r1h)
            r24h_list.extend(r24h)
        df['rolling_tx_count_1h'] = r1h_list
        df['rolling_tx_count_24h'] = r24h_list
    except Exception:
        df['rolling_tx_count_1h'] = df.groupby(acc_col).cumcount() + 1
        df['rolling_tx_count_24h'] = df['rolling_tx_count_1h']

    # 6. Nominal Deviation from Account Mean
    acc_mean_nominal = df.groupby(acc_col)['nominal'].transform('mean').fillna(1.0)
    df['nominal_dev'] = (df['nominal'] - acc_mean_nominal) / (acc_mean_nominal + 1.0)

    # 7. Liquidation Ratio (Debits relative to previous Credit inflows)
    df['prev_credit'] = df.groupby(acc_col)['nominal_credit'].shift(1).fillna(0.0)
    df['liquidation_ratio'] = np.where(
        (df['nominal_debit'] > 0) & (df['prev_credit'] > 0),
        df['nominal_debit'] / (df['prev_credit'] + 1.0),
        0.0
    )
    df['liquidation_ratio'] = np.clip(df['liquidation_ratio'], 0.0, 10.0)

    # 8. Behavioral Categorical Encodings (Deterministic label encoding)
    cat_cols_map = {
        'transaction_category': 'transaction_category_encoded',
        'transaction_channel': 'transaction_channel_encoded',
        'transaction_code': 'transaction_code_encoded',
        'transaction_type': 'transaction_type_encoded',
        'transaction_behavior': 'transaction_behavior_encoded',
        'transaction_direction': 'transaction_direction_encoded'
    }
    
    for src_col, enc_col in cat_cols_map.items():
        if src_col in df.columns:
            # Deterministic categorical code
            df[enc_col] = df[src_col].astype('category').cat.codes
        else:
            df[enc_col] = 0

    if 'transaction_risk_flag' not in df.columns:
        df['transaction_risk_flag'] = 0
    df['transaction_risk_flag'] = pd.to_numeric(df['transaction_risk_flag'], errors='coerce').fillna(0).astype(int)

    # 9. Update dataset stage metadata
    df['dataset_stage'] = 'ANALYTICAL'
    if execution_id:
        df['execution_id'] = execution_id

    # 10. Ensure predictor features exist and are numeric
    for col in MODEL_PREDICTOR_FEATURES:
        if col not in df.columns:
            df[col] = 0.0
        else:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)

    return df

def get_feature_matrix(df):
    """
    Extracts the pure numeric feature matrix X.
    Strict assertion: NO target label or ID is included in X.
    """
    assert 'fraud_label' not in MODEL_PREDICTOR_FEATURES, "Target leakage detected: fraud_label in feature list!"
    assert 'account_id' not in MODEL_PREDICTOR_FEATURES, "Identifier leakage: account_id in feature list!"
    assert 'source_account_key' not in MODEL_PREDICTOR_FEATURES, "Identifier leakage: source_account_key in feature list!"
    assert 'execution_id' not in MODEL_PREDICTOR_FEATURES, "Lineage leakage: execution_id in feature list!"

    X = df[MODEL_PREDICTOR_FEATURES].copy()
    for col in MODEL_PREDICTOR_FEATURES:
        X[col] = pd.to_numeric(X[col], errors='coerce').fillna(0.0)
        
    return X
