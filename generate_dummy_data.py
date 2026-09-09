import pandas as pd
import numpy as np
import datetime
import os

def generate_academic_dummy_dataset(n_accounts=50, random_seed=42):
    """
    Generates a realistic synthetic banking transaction dataset strictly aligned with:
    'Model Hybrid LightGBM dan LSTM Dengan Keputusan Explainable AI Pada Sistem Deteksi Fraud Transaksi Perbankan'
    and 'Explainable AI-Based Hybrid LightGBM–LSTM for Banking Fraud Detection'.
    
    Specifications:
    - Exactly 50 accounts: 25 Fraud accounts, 25 Normal accounts.
    - Timeframe: January 1, 2025 to December 31, 2025.
    - Account count (50) != Transaction count (~2500-3500) != Sequence count.
    - Ground truth: 25 normal accounts (fraud_label=0), 25 fraud accounts (fraud_label=1 on fraud bursts).
    """
    np.random.seed(random_seed)
    
    # 25 Normal Account IDs and 25 Fraud Account IDs
    normal_accounts = [f"1001{i:04d}5021" for i in range(1, 26)]
    fraud_accounts = [f"9002{i:04d}7834" for i in range(1, 26)]
    
    records = []
    
    # 1. GENERATE NORMAL ACCOUNTS TRANSACTIONS
    for acc in normal_accounts:
        n_tx = np.random.randint(40, 75)
        salary_day = np.random.choice([25, 26, 27, 28])
        salary_amount = np.random.choice([6_500_000, 8_000_000, 12_500_000, 15_000_000, 20_000_000])
        
        for month in range(1, 13):
            date_str = f"2025-{month:02d}-{salary_day:02d}"
            time_str = f"{np.random.randint(7, 10):02d}:{np.random.randint(0, 60):02d}:{np.random.randint(0, 60):02d}"
            records.append({
                'TRANS DATE': date_str,
                'JAM TRX': time_str,
                'NOREK': acc,
                'REMARK': f"PAYROLL GAJI BULAN {month:02d}/2025 PT ENTERPRISE NUSANTARA",
                'MUTASI DEBET': "0",
                'MUTASI KREDIT': f"{salary_amount:,.0f}".replace(",", "."),
                'fraud_label': 0
            })
        
        start_date = datetime.date(2025, 1, 1)
        end_date = datetime.date(2025, 12, 31)
        days_range = (end_date - start_date).days
        
        for _ in range(n_tx - 12):
            random_day = start_date + datetime.timedelta(days=int(np.random.randint(0, days_range)))
            date_str = random_day.strftime('%Y-%m-%d')
            hour = np.random.randint(7, 22)
            time_str = f"{hour:02d}:{np.random.randint(0, 60):02d}:{np.random.randint(0, 60):02d}"
            
            tx_type = np.random.choice(['QRIS', 'ATM', 'TRF_FAMILY', 'BILL', 'TOPUP'])
            if tx_type == 'QRIS':
                amount = np.random.choice([15_000, 25_000, 45_000, 75_000, 120_000, 250_000])
                remark = f"QRIS PAYMENT TO MERCHANT {np.random.choice(['INDOMARET', 'ALFAMART', 'KOPI KENANGAN', 'SUPERINDO'])} #9360{np.random.randint(1000, 9999)}"
                debit_str = f"{amount:,.0f}".replace(",", ".")
                credit_str = "0"
            elif tx_type == 'ATM':
                amount = np.random.choice([100_000, 300_000, 500_000, 1_000_000, 1_500_000])
                remark = f"TARIK TUNAI ATM LINK CRM-{np.random.randint(1000, 9999)}"
                debit_str = f"{amount:,.0f}".replace(",", ".")
                credit_str = "0"
            elif tx_type == 'TRF_FAMILY':
                amount = np.random.choice([200_000, 500_000, 1_000_000, 2_000_000])
                dest_name = np.random.choice(['SITI RAHMAWATI', 'AHMAD FAUZI', 'DEWI LESTARI', 'HENDRA WIJAYA'])
                remark = f"TRANSFER TO {dest_name} REKENING SENDIRI/KELUARGA"
                debit_str = f"{amount:,.0f}".replace(",", ".")
                credit_str = "0"
            elif tx_type == 'BILL':
                amount = np.random.choice([150_000, 350_000, 600_000, 950_000])
                remark = f"PEMBAYARAN PLN-PRA / PDAM / WIFI TELKOM #{np.random.randint(100000, 999999)}"
                debit_str = f"{amount:,.0f}".replace(",", ".")
                credit_str = "0"
            else: # TOPUP
                amount = np.random.choice([50_000, 100_000, 200_000, 500_000])
                remark = f"TOP UP GOPAY/OVO/SHOPEEPAY VIA MOBILE BANKING #0812{np.random.randint(100000, 999999)}"
                debit_str = f"{amount:,.0f}".replace(",", ".")
                credit_str = "0"
                
            records.append({
                'TRANS DATE': date_str,
                'JAM TRX': time_str,
                'NOREK': acc,
                'REMARK': remark,
                'MUTASI DEBET': debit_str,
                'MUTASI KREDIT': credit_str,
                'fraud_label': 0
            })
            
    # 2. GENERATE FRAUD ACCOUNTS TRANSACTIONS
    for acc in fraud_accounts:
        n_tx = np.random.randint(45, 80)
        start_date = datetime.date(2025, 1, 1)
        end_date = datetime.date(2025, 12, 31)
        days_range = (end_date - start_date).days
        
        # Background normal-looking noise
        n_noise = int(n_tx * 0.3)
        for _ in range(n_noise):
            random_day = start_date + datetime.timedelta(days=int(np.random.randint(0, days_range)))
            date_str = random_day.strftime('%Y-%m-%d')
            hour = np.random.randint(8, 20)
            time_str = f"{hour:02d}:{np.random.randint(0, 60):02d}:{np.random.randint(0, 60):02d}"
            amount = np.random.choice([25_000, 50_000, 100_000])
            records.append({
                'TRANS DATE': date_str,
                'JAM TRX': time_str,
                'NOREK': acc,
                'REMARK': f"QRIS/PULSA REGULER #{np.random.randint(1000, 9999)}",
                'MUTASI DEBET': f"{amount:,.0f}".replace(",", "."),
                'MUTASI KREDIT': "0",
                'fraud_label': 0
            })
            
        # Specific Fraud Clusters (Money Mule, High Velocity, Smurfing)
        n_episodes = np.random.randint(3, 6)
        for ep in range(n_episodes):
            ep_day = start_date + datetime.timedelta(days=int(np.random.randint(15, days_range - 5)))
            ep_date_str = ep_day.strftime('%Y-%m-%d')
            
            inflow_amount = np.random.choice([15_000_000, 25_000_000, 50_000_000, 75_000_000, 100_000_000])
            base_hour = np.random.choice([1, 2, 3, 23, 14, 19])
            base_min = np.random.randint(5, 45)
            
            # Inflow
            records.append({
                'TRANS DATE': ep_date_str,
                'JAM TRX': f"{base_hour:02d}:{base_min:02d}:{np.random.randint(0, 30):02d}",
                'NOREK': acc,
                'REMARK': f"TRANSFER MASUK DARI DANA/VA/REK {np.random.randint(10000000, 99999999)} WS_OB",
                'MUTASI DEBET': "0",
                'MUTASI KREDIT': f"{inflow_amount:,.0f}".replace(",", "."),
                'fraud_label': 1
            })
            
            # Rapid cash-outs
            n_chunks = np.random.randint(3, 6)
            chunk_amount = int((inflow_amount * 0.95) / n_chunks)
            curr_min = base_min + 2
            
            for c_idx in range(n_chunks):
                curr_min += np.random.randint(1, 3)
                ch_hour = base_hour + (curr_min // 60)
                ch_min = curr_min % 60
                
                records.append({
                    'TRANS DATE': ep_date_str,
                    'JAM TRX': f"{ch_hour:02d}:{ch_min:02d}:{np.random.randint(0, 59):02d}",
                    'NOREK': acc,
                    'REMARK': f"TRANSFER KELUAR CEPAT KE REK MULE #{np.random.randint(10000000, 99999999)} TO TARGET {c_idx+1}",
                    'MUTASI DEBET': f"{chunk_amount:,.0f}".replace(",", "."),
                    'MUTASI KREDIT': "0",
                    'fraud_label': 1
                })

    df = pd.DataFrame(records)
    
    # Sort chronologically per account
    df['temp_dt'] = pd.to_datetime(df['TRANS DATE'] + ' ' + df['JAM TRX'], errors='coerce')
    df = df.sort_values(by=['NOREK', 'temp_dt']).reset_index(drop=True)
    df = df.drop(columns=['temp_dt'])
    
    return df

def get_dummy_raw_data():
    """Returns the standardized 50-account synthetic dataset."""
    return generate_academic_dummy_dataset(n_accounts=50)

if __name__ == "__main__":
    df = get_dummy_raw_data()
    for folder in ['assets', 'uploads', 'cleaned', 'reports', 'models']:
        os.makedirs(folder, exist_ok=True)
        
    df.to_excel("REK 1.xlsx", index=False)
    df.to_excel("mutasi_sample_50_rekening.xlsx", index=False)
    print(f"Generated academic dataset: {len(df)} transactions across {df['NOREK'].nunique()} accounts.")
