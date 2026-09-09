import pandas as pd
import numpy as np

def account_level_split(df, account_col='account_id', test_size=0.15, val_size=0.15, random_state=42):
    """
    Strict Account-Level Partitioning (Disjoint by Bank Account ID).
    Splits accounts into 70% Train, 15% Validation, 15% Test.
    Guarantees:
        train_accounts ∩ val_accounts = ∅
        train_accounts ∩ test_accounts = ∅
        val_accounts ∩ test_accounts = ∅
    
    If the dataset has insufficient unique accounts (< 3, e.g. single-account file),
    it flags can_account_split = False with an explicit research scope explanation.
    """
    if df is None or df.empty:
        raise ValueError("Input dataframe is empty or None.")
        
    df = df.copy()
    
    # Identify account column
    if account_col not in df.columns:
        if 'source_account_key' in df.columns:
            account_col = 'source_account_key'
        elif 'NOREK' in df.columns:
            account_col = 'NOREK'
        else:
            raise KeyError(f"Account column '{account_col}' not found in dataframe.")

    unique_accounts = df[account_col].unique()
    n_accounts = len(unique_accounts)
    
    # Check for single-account / insufficient accounts
    if n_accounts < 3:
        # Cannot do an account-level 70:15:15 split across disjoint accounts
        split_meta = {
            'can_account_split': False,
            'reason': (
                f"Insufficient account count for account-level split. "
                f"Dataset input contains only {n_accounts} unique account(s). "
                f"Account-level disjoint split (70:15:15) requires multiple accounts (target 50 accounts in research scope). "
                f"This file represents a single-account transaction history."
            ),
            'total_accounts': n_accounts,
            'total_rows': len(df),
            'train_accounts': 0,
            'val_accounts': 0,
            'test_accounts': 0,
            'split_type': 'SINGLE_ACCOUNT_RESTRICTED'
        }
        # For single account processing, return the dataset with metadata
        return df, pd.DataFrame(columns=df.columns), pd.DataFrame(columns=df.columns), split_meta

    # Multiple accounts available (e.g. 50 accounts)
    np.random.seed(random_state)
    shuffled_accounts = np.random.permutation(unique_accounts)
    
    # Calculate account allocations
    n_test_acc = max(1, int(np.round(n_accounts * test_size)))
    n_val_acc = max(1, int(np.round(n_accounts * val_size)))
    n_train_acc = n_accounts - n_test_acc - n_val_acc
    
    if n_train_acc <= 0:
        n_train_acc = max(1, n_accounts - 2)
        n_val_acc = 1
        n_test_acc = 1

    train_accs = set(shuffled_accounts[:n_train_acc])
    val_accs = set(shuffled_accounts[n_train_acc:n_train_acc + n_val_acc])
    test_accs = set(shuffled_accounts[n_train_acc + n_val_acc:])

    # Strictly verify disjoint sets
    assert train_accs.isdisjoint(val_accs), "Account leakage: Train and Validation sets share accounts!"
    assert train_accs.isdisjoint(test_accs), "Account leakage: Train and Test sets share accounts!"
    assert val_accs.isdisjoint(test_accs), "Account leakage: Validation and Test sets share accounts!"

    train_df = df[df[account_col].isin(train_accs)].copy().reset_index(drop=True)
    val_df = df[df[account_col].isin(val_accs)].copy().reset_index(drop=True)
    test_df = df[df[account_col].isin(test_accs)].copy().reset_index(drop=True)

    # Set lineage stages
    train_df['dataset_stage'] = 'TRAIN_ORIGINAL'
    val_df['dataset_stage'] = 'VALIDATION'
    test_df['dataset_stage'] = 'TEST'
    
    val_df['is_synthetic'] = False
    test_df['is_synthetic'] = False

    split_meta = {
        'can_account_split': True,
        'split_type': 'ACCOUNT_LEVEL_DISJOINT',
        'total_accounts': n_accounts,
        'total_rows': len(df),
        'train_accounts': len(train_accs),
        'val_accounts': len(val_accs),
        'test_accounts': len(test_accs),
        'train_rows': len(train_df),
        'val_rows': len(val_df),
        'test_rows': len(test_df),
        'train_account_ids': list(train_accs),
        'val_account_ids': list(val_accs),
        'test_account_ids': list(test_accs)
    }

    return train_df, val_df, test_df, split_meta

def verify_no_account_leakage(train_df, val_df, test_df, account_col='account_id'):
    """
    Explicit assertion function to verify absolute account-level disjointness.
    """
    if train_df.empty or (val_df.empty and test_df.empty):
        return True
        
    train_acc = set(train_df[account_col].unique())
    val_acc = set(val_df[account_col].unique()) if not val_df.empty else set()
    test_acc = set(test_df[account_col].unique()) if not test_df.empty else set()
    
    inter_train_val = train_acc.intersection(val_acc)
    inter_train_test = train_acc.intersection(test_acc)
    inter_val_test = val_acc.intersection(test_acc)
    
    if inter_train_val or inter_train_test or inter_val_test:
        raise AssertionError(
            f"Account leakage detected!\n"
            f"Train ∩ Val: {inter_train_val}\n"
            f"Train ∩ Test: {inter_train_test}\n"
            f"Val ∩ Test: {inter_val_test}"
        )
    return True
