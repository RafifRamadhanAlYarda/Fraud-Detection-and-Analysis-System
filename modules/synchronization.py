import numpy as np
import pandas as pd

def create_lstm_sequences(df, window_size=10, feature_cols=None):
    """
    Groups data by account and creates sequences for LSTM with padding.
    """
    if feature_cols is None:
        feature_cols = ['nominal_debit', 'nominal_credit', 'time_interval', 'risk_velocity', 'transaction_category_encoded']
    
    sequences = []
    labels = []
    
    for account_id, group in df.groupby('account_id'):
        group = group.sort_values('transaction_datetime')
        data = group[feature_cols].values
        label = group['fraud_label'].values
        
        # Sliding window with padding for start of sequence
        for i in range(len(data)):
            if i + 1 < window_size:
                # Pad with zeros
                pad_width = window_size - (i + 1)
                seq = np.pad(data[:i+1], ((pad_width, 0), (0, 0)), mode='constant')
            else:
                seq = data[i - window_size + 1: i + 1]
            
            sequences.append(seq)
            labels.append(label[i])
                
    return np.array(sequences), np.array(labels)
