import numpy as np
import pandas as pd
import io

class HybridXAIEngine:
    """
    Scientific-grade Explainable AI (XAI) for Hybrid Models.
    Explains LightGBM, LSTM, and Fusion contributions as per Bab 3.7 Tesis.
    Enhanced to support academic-level transaction behavioral forensics (Q1/SINTA).
    """
    def __init__(self, lgbm_model, lstm_model, feature_cols):
        self.lgbm_model = lgbm_model
        self.lstm_model = lstm_model
        self.feature_cols = feature_cols
        self.explainer = None

    def explain_fusion(self, lgbm_prob, lstm_prob, rule_score_norm):
        """
        Explains how the hybrid fusion score was derived (Bab 3.8 Tesis).
        Formula: (0.40 * LGBM) + (0.40 * LSTM) + (0.20 * Rules)
        """
        w_lgbm, w_lstm, w_rules = 0.40, 0.40, 0.20
        
        lgbm_cont = lgbm_prob * w_lgbm
        lstm_cont = lstm_prob * w_lstm
        rules_cont = rule_score_norm * w_rules
        
        explanation = {
            'lgbm_contribution': lgbm_cont,
            'lstm_contribution': lstm_cont,
            'rules_contribution': rules_cont,
            'dominant_factor': 'LightGBM' if lgbm_cont > max(lstm_cont, rules_cont) else 
                               ('LSTM' if lstm_cont > rules_cont else 'Business Rules')
        }
        return explanation

    def get_lgbm_explanation(self, X_sample):
        """
        Standard SHAP explanation for the tabular model.
        """
        import shap
        if self.explainer is None:
            self.explainer = shap.TreeExplainer(self.lgbm_model)
        
        shap_values = self.explainer.shap_values(X_sample)
        # For binary classification, take values for class 1
        if isinstance(shap_values, list):
            shap_values = shap_values[1]
            
        return shap_values

    def get_operational_reasoning(self, X_row, shap_values_row):
        """
        Converts mathematical SHAP values into human-readable operational reasoning.
        """
        reasons = []
        top_indices = np.argsort(np.abs(shap_values_row))[-3:][::-1]
        
        for idx in top_indices:
            feature = self.feature_cols[idx]
            val = shap_values_row[idx]
            
            if val > 0:
                if 'velocity' in feature: reasons.append("High transaction velocity detected exceeding baseline.")
                elif 'nominal' in feature: reasons.append("Transaction amount deviates significantly from average.")
                elif 'hour' in feature: reasons.append("Anomalous transaction timing (Midnight/Off-hours).")
                else: reasons.append(f"Suspicious pattern in {feature}.")
        
        return reasons

    def explain_behavior(self, row, df, final_score, status, lgbm_prob, lstm_prob):
        """
        Comprehensive Scientific Behavioral Forensics explaining 6 critical indicators.
        Designed for SINTA/Q1 Academic Paper compatibility with deep KBBI natural Indonesian wording.
        """
        # 1. Isolation logic of account data under investigation
        account_id = row.get('account_id', 'UNKNOWN_ACC')
        acc_txs = df[df['account_id'] == account_id] if 'account_id' in df.columns else df
        
        # 1. ABNORMAL TRANSACTION TIME DETECTION
        # Check standard operational window (08:00 - 18:00 WIB is standard bank active hours, off-hours is late night)
        hour = int(row.get('hour', row['transaction_datetime'].hour if isinstance(row.get('transaction_datetime'), pd.Timestamp) else 12))
        is_night = (hour < 6 or hour >= 23)
        hist_hours = acc_txs['hour'].tolist() if 'hour' in acc_txs.columns else [hour]
        time_variance = np.std(hist_hours) if len(hist_hours) > 1 else 0
        mean_time = np.mean(hist_hours) if len(hist_hours) > 1 else 12
        is_abnormal_time = bool(is_night or (time_variance > 0 and abs(hour - mean_time) > 2 * time_variance))
        
        # 2. TRANSACTION VELOCITY DETECTION
        risk_vel = float(row.get('risk_velocity', 0))
        time_diff = float(row.get('time_diff_previous', 999))
        is_high_velocity = bool(risk_vel > 200 or time_diff < 1.5 or (len(acc_txs) > 1 and acc_txs['time_interval'].mean() < 5))
        
        # 3. REMARK ANOMALY DETECTION
        remark = str(row.get('remark_clean', '')).upper()
        # Reputable normal markers to reduce false positives
        normal_kw = ['GAJI', 'PAYROLL', 'SALARY', 'THR', 'BONUS', 'MARKETPLACE', 'SHOPEE', 'TOKOPEDIA', 'TOP UP', 
                     'DANA', 'OVO', 'GOPAY', 'LINKAJA', 'REKENING SENDIRI', 'KELUARGA', 'BULANAN', 'LISTRIK', 
                     'AIR', 'PULSA', 'OWN ACCOUNT', 'TRANSFER ANTAR REKENING', 'ADMIN FEE']
        has_normal_kw = any(kw in remark for kw in normal_kw)
        nominal_val = float(row.get('nominal_debit', 0)) + float(row.get('nominal_credit', 0))
        is_remark_anomaly = bool(not has_normal_kw and (nominal_val > 2000000 or len(remark) < 4 or any(p in remark for p in ['#', '*', '_'])))
        
        # 4. DESTINATION PATTERN ANOMALY DETECTION
        unique_dests = acc_txs['dest_id'].nunique() if 'dest_id' in acc_txs.columns else 1
        is_multidest_burst = bool(unique_dests > 5 and row.get('is_trusted_beneficiary', 0) == 0)
        
        # 5. FREQUENCY SPIKE DETECTION
        row_freq = float(row.get('transaction_frequency', len(acc_txs)))
        avg_hist_freq = float(df['transaction_frequency'].mean()) if 'transaction_frequency' in df.columns else 5.0
        is_frequency_spike = bool(row_freq > 2 * avg_hist_freq and row_freq > 10)
        
        # 6. SALDO BEHAVIOR ANOMALY (DRAINING / LIQUIDATION)
        is_liq = int(row.get('is_liquidation_event', 0)) == 1
        liq_ratio = float(row.get('liquidation_ratio', 0))
        is_saldo_anomaly = bool(is_liq or liq_ratio > 0.8)

        # Indicator weighting scheme as requested
        weights = {
            'Abnormal Transaction Time': 0.15,
            'Transaction Velocity': 0.20,
            'Remark Anomaly': 0.10,
            'Destination Pattern Anomaly': 0.15,
            'Frequency Spike': 0.15,
            'Saldo Behavior': 0.25
        }
        
        flags = {
            'Abnormal Transaction Time': is_abnormal_time,
            'Transaction Velocity': is_high_velocity,
            'Remark Anomaly': is_remark_anomaly,
            'Destination Pattern Anomaly': is_multidest_burst,
            'Frequency Spike': is_frequency_spike,
            'Saldo Behavior': is_saldo_anomaly
        }
        
        # Determine triggered indicators
        triggered_indicators = []
        total_triggered_weight = 0.0
        for name, value in flags.items():
            if value:
                triggered_indicators.append(name)
                total_triggered_weight += weights[name]
        
        # Map raw weighted score to explanation score, sync with final core ML model score
        explanation_score = 0.3 * total_triggered_weight + 0.7 * final_score
        
        # Generate Indonesian Academic translations of indicators
        id_names = {
            'Abnormal Transaction Time': 'Waktu Transaksi Abnormal (Abnormal Transaction Time)',
            'Transaction Velocity': 'Akselerasi Kecepatan Transaksi (Transaction Velocity)',
            'Remark Anomaly': 'Anomali Keterangan Deskripsi (Remark Anomaly)',
            'Destination Pattern Anomaly': 'Anomali Pola Destinasi Transaksi (Destination Pattern Anomaly)',
            'Frequency Spike': 'Lonjakan Frekuensi Transaksi (Frequency Spike)',
            'Saldo Behavior': 'Pola Mutasi Saldo Ekstrem (Saldo Behavior)'
        }
        
        triggered_id_labels = [id_names[x] for x in triggered_indicators]
        triggered_text = ", ".join(triggered_id_labels) if triggered_id_labels else "Ketiadaan penyimpangan parameter transaksional secara individual"

        # Generate SINTA/Q1 Academic-level Narrations in Indonesian with formal, non-accusatory terms
        if status == "NORMAL":
            narrative_dashboard = (
                "Berdasarkan hasil analisis komparatif fusi hibrida (Hybrid Fusion Engine), "
                "model tidak mendeteksi deviasi parameter transaksional yang signifikan pada rekening ini. "
                "Seluruh arus dana reguler terklasifikasi sebagai aktivitas keuangan bernilai normal (Normal). "
                "Karakteristik transaksi, termasuk pencatatan deskripsi (remark), waktu aktivitas (operational hour), "
                "serta korelasi destinasi rekening, sepenuhnya menunjukkan pola perilaku transaksional yang selaras "
                "dengan perilaku historis nasabah. Oleh karena itu, probabilitas risiko dinyatakan minimum (rendah), "
                "dan tidak merekomendasikan tindakan intervensi."
            )
            narrative_pdf = (
                "Analisis komparatif fusi kecerdasan hibrida menyimpulkan bahwa subyek akun menunjukkan konsistensi penuh "
                "terhadap parameter transaksi reguler historis. Tidak ditemukan signifikansi anomali temporalmaupun spasial. "
                "Faktor operasional mengonfirmasi aktivitas keuangan rutin standar tanpa potensi penyusupan sistem."
            )
            recommendations = [
                "Melakukan pencatatan administratif standar sebagai arsip pemantauan rutin.",
                "Mempertahankan hak akses operasional rekening tanpa pembatasan apa pun.",
                "Melanjutkan monitoring berkala sesuai kebijakan mitigasi bank."
            ]
        elif status == "HIGH RISK":
            narrative_dashboard = (
                f"Melalui fusi hibrida analitika LightGBM dan LSTM, teridentifikasi indikator risiko tingkat "
                f"menengah terakumulasi (High Risk). Aktivitas transaksi terpapar anomali parameter {triggered_text} "
                f"yang memicu deviasi parsial dari karakteristik perilaku historis (behavioral baseline). "
                f"Meskipun transaksional reguler masih mendominasi aktivitas keuangan secara global, dinamika transfer "
                f"dalam durasi pendek serta perubahan destinasi transaksi menunjukkan potensi paparan risiko operasional. "
                f"Rekening ini memerlukan penelaahan lebih mendalam (manual review) untuk memvalidasi keabsahan rangkaian transaksi tersebut."
            )
            narrative_pdf = (
                f"Sistem mengidentifikasi deviasi struktural transaksional intermediat (High Risk) berupa terpicunya "
                f"indikator {triggered_text}. Terdapat akselerasi operasional atau perilaku semantik deskripsi "
                f"yang kurang koheren dengan profil nasabah. Penemuan ini mengimplikasikan perlunya penilaian kepatuhan "
                f"internal komprehensif tanpa menerapkan tindakan represif langsung."
            )
            recommendations = [
                "Melakukan penelaahan mendalam (enhanced analyst review) terhadap rangkaian transaksi.",
                "Melakukan klarifikasi sekunder terhadap profil dan aktivitas nasabah.",
                "Memantau pola pergerakan dana selanjutnya pada periode operasional berikutnya."
            ]
        else: # FRAUD
            narrative_dashboard = (
                f"Hasil investigasi digital forensik berbasis fusi komputasi menunjukkan indikasi penyimpangan ekstrem "
                f"yang sangat signifikan, sehingga mengklasifikasikan akun ini ke dalam status terindikasi kecurangan tingkat tinggi (Fraud Indicator). "
                f"Anomali terdeteksi secara intensif pada parameter {triggered_text}. Karakteristik pencairan dana cepat (draining behavior) "
                f"yang disertai deviasi temporal siber di luar batas operasional normal mengindikasikan kuat adanya pembajakan kredensial (account takeover) "
                f"atau pola kejahatan keuangan terorganisir (mule account operation). Kondisi ini memerlukan intervensi pencegahan dini untuk melindungi integritas sistem perbankan."
            )
            narrative_pdf = (
                f"Melalui analisis forensik digital multi-dimensi, terdeteksi anomali operasional kritis yang selaras dengan "
                f"modus operandi siber perbankan berupa {triggered_text}. Karakteristik transfer pencairan berganda "
                f"dalam waktu minor (liquidation event) mengindikasikan risiko tinggi pengambilalihan akun secara ilegal (account takeover). "
                f"Sistem merekomendasikan tindakan preventif mendesak guna meminimalisir kebocoran dana nasabah lebih lanjut."
            )
            recommendations = [
                "Melakukan investigasi lanjutan komprehensif sesuai prosedur operasional standar (SOP).",
                "Memvalidasi riwayat transaksi, identitas nasabah, dan bukti pendukung oleh analis berwenang.",
                "Keputusan tindak lanjut operasional diserahkan sepenuhnya kepada analis/human decision maker."
            ]

        # Sync confidence level dynamically
        agreement = 1.0 - abs(lgbm_prob - lstm_prob)
        confidence = 0.75 + (agreement * 0.24)
        confidence_pct = f"{confidence * 100:.2f}%"

        return {
            'flags': flags,
            'triggered_indicators': triggered_indicators,
            'explanation_score': explanation_score,
            'narrative_dashboard': narrative_dashboard,
            'narrative_pdf': narrative_pdf,
            'confidence_level': confidence_pct,
            'recommendations': recommendations
        }
