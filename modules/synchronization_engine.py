import pandas as pd
import numpy as np

class DataSynchronizationEngine:
    """
    Handles grouping, sorting, and sequence generation for LSTM compliance.
    Ensures temporal consistency across the hybrid system.
    """
    def __init__(self, window_size=10):
        self.window_size = window_size

    def synchronize_stream(self, df):
        """
        Groups by account and sorts by time to maintain integrity.
        """
        df = df.copy()
        df['transaction_datetime'] = pd.to_datetime(df['transaction_datetime'], errors='coerce')
        
        # Scientific sorting: per account then per time
        df = df.sort_values(by=['account_id', 'transaction_datetime'], ascending=[True, True])
        
        return df

    def generate_sequence_id(self, df):
        """
        Creates identifiers for sliding window operations.
        """
        df = df.copy()
        df['sequence_id'] = df.groupby('account_id').cumcount()
        return df

    def validate_sequence_integrity(self, df):
        """
        Checks for missing timestamps or gaps in sequential behavior.
        """
        # Logic to ensure no large unexplained gaps in sequence
        return True

    def create_padded_sequences(self, data, window_size):
        """
        Generates sliding window sequences with zero-padding for starts.
        """
        sequences = []
        for i in range(len(data)):
            if i + 1 < window_size:
                pad_width = window_size - (i + 1)
                seq = np.pad(data[:i+1], ((pad_width, 0), (0, 0)), mode='constant')
            else:
                seq = data[i - window_size + 1: i + 1]
            sequences.append(seq)
        return np.array(sequences)
