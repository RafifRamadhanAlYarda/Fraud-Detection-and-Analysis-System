import re
import pandas as pd
from datetime import datetime

class RemarkParser:
    def __init__(self, dictionary_df=None):
        self.dictionary = dictionary_df
        # Mapping keywords to categories based on BRI Kamus
        self.keyword_map = {
            'ATM': 'TARIK_TUNAI',
            'CRM': 'TARIK_TUNAI',
            'NBMB': 'TRANSFER_MOBILE',
            'QRIS': 'QRIS_PAYMENT',
            'BRIVA': 'VIRTUAL_ACCOUNT_PAYMENT',
            'PUL-': 'PEMBELIAN_PULSA',
            'PLN-PRA': 'TOPUP_PLN',
            'EDC': 'BELANJA_EDC',
            'WBNK': 'TRANSFER_AGENT',
            'BFST': 'BI_FAST',
            'MDB': 'TRANSAKSI_OTOMATIS'
        }

    def load_transaction_dictionary(self, file_path):
        try:
            self.dictionary = pd.read_excel(file_path)
            return True
        except Exception as e:
            print(f"Error loading dictionary: {e}")
            return False

    def parse_transaction_remark(self, remark):
        if not isinstance(remark, str):
            return self.get_empty_parse()
        
        remark_up = remark.upper()
        res = {
            'transaction_code': remark[:4],
            'transaction_channel': 'UNKNOWN',
            'transaction_location': 'UNKNOWN',
            'transaction_category': 'OTHERS',
            'transaction_type': 'DEBIT' if 'FEE' in remark_up or 'ADMIN' in remark_up else 'GENERAL',
            'transaction_behavior': 'NORMAL',
            'transaction_risk_flag': 0
        }

        # 1. Match from keyword map
        for kw, cat in self.keyword_map.items():
            if kw in remark_up:
                res['transaction_category'] = cat
                res['transaction_channel'] = kw.replace('-', '')
                break

        # 2. Extract Location (Simple logic: capture numeric TID or branch code)
        loc_match = re.search(r'(ATM|EDC|CRM)(\d{6,8})', remark_up)
        if loc_match:
            res['transaction_location'] = loc_match.group(2)
        
        # 3. Behavioral Analysis (Preliminary)
        if 'MDB' in remark_up or 'AUTO' in remark_up:
            res['transaction_behavior'] = 'RECURRING'
        
        return res

    def get_empty_parse(self):
        return {
            'transaction_code': 'NONE',
            'transaction_channel': 'NONE',
            'transaction_location': 'NONE',
            'transaction_category': 'NONE',
            'transaction_type': 'NONE',
            'transaction_behavior': 'NONE',
            'transaction_risk_flag': 0
        }

def parse_transaction_remarks(df, remark_col='REMARK'):
    parser = RemarkParser()
    parsed_data = df[remark_col].apply(parser.parse_transaction_remark).apply(pd.Series)
    return pd.concat([df.reset_index(drop=True), parsed_data.reset_index(drop=True)], axis=1)
