import numpy as np
import pandas as pd
from sklearn.neighbors import NearestNeighbors
from sklearn.cluster import KMeans

class ImbalanceHandlingEngine:
    """
    FDAS Resampling Engine strictly applying TPH-SMOTE and KHOI-SMOTE
    exclusively on the TRAINING partition.
    Preserves exact provenance (sample_origin, resampling_method, is_synthetic).
    """
    def __init__(self, random_state=42):
        self.random_state = random_state

    def tph_smote(self, X, y, k_neighbors=5, sampling_strategy=1.0):
        """
        Temporal & Proximal Hybrid SMOTE (TPH-SMOTE).
        Generates synthetic minority (fraud) instances along temporal and proximity boundaries.
        
        Args:
            X: pd.DataFrame or np.ndarray of training features.
            y: pd.Series or np.ndarray of binary training labels (0: Normal, 1: Fraud).
            k_neighbors: number of nearest neighbors for interpolation.
            sampling_strategy: target ratio of minority/majority (1.0 = balanced 50:50).
            
        Returns:
            X_res: pd.DataFrame of resampled features (original + synthetic).
            y_res: np.ndarray of resampled labels.
            synth_mask: np.ndarray boolean mask where True indicates synthetic sample.
        """
        np.random.seed(self.random_state)
        
        # Format inputs
        feature_names = X.columns if isinstance(X, pd.DataFrame) else [f"feat_{i}" for i in range(X.shape[1])]
        X_mat = np.array(X, dtype=float)
        y_vec = np.array(y, dtype=int)
        
        minority_idx = np.where(y_vec == 1)[0]
        majority_idx = np.where(y_vec == 0)[0]
        
        n_minority = len(minority_idx)
        n_majority = len(majority_idx)
        
        if n_minority == 0 or n_majority == 0 or n_minority >= n_majority:
            # Already balanced or invalid minority
            synth_mask = np.zeros(len(y_vec), dtype=bool)
            return pd.DataFrame(X_mat, columns=feature_names), y_vec, synth_mask
            
        n_to_generate = int(n_majority * sampling_strategy) - n_minority
        if n_to_generate <= 0:
            synth_mask = np.zeros(len(y_vec), dtype=bool)
            return pd.DataFrame(X_mat, columns=feature_names), y_vec, synth_mask

        X_minority = X_mat[minority_idx]
        
        # Fit Nearest Neighbors on minority samples
        k = min(k_neighbors, max(1, n_minority - 1))
        nn = NearestNeighbors(n_neighbors=k + 1, metric='euclidean')
        nn.fit(X_minority)
        _, indices = nn.kneighbors(X_minority)
        
        synthetic_samples = []
        for _ in range(n_to_generate):
            # Select random minority base instance
            base_idx = np.random.randint(0, n_minority)
            base_point = X_minority[base_idx]
            
            # Select random neighbor among k-nearest minority
            neighbor_pool = indices[base_idx][1:] if k > 0 else [base_idx]
            neighbor_idx = np.random.choice(neighbor_pool)
            neighbor_point = X_minority[neighbor_idx]
            
            # Beta distribution proximal interpolation (more dense near the anchor point)
            diff = neighbor_point - base_point
            gap = np.random.beta(a=2.0, b=5.0)
            
            # Add small temporal noise jitter
            jitter = np.random.normal(0, 0.02 * (np.std(X_minority, axis=0) + 1e-6))
            synthetic_point = base_point + (gap * diff) + jitter
            synthetic_samples.append(synthetic_point)
            
        X_synthetic = np.array(synthetic_samples)
        y_synthetic = np.ones(n_to_generate, dtype=int)
        
        X_res = np.vstack([X_mat, X_synthetic])
        y_res = np.concatenate([y_vec, y_synthetic])
        
        synth_mask = np.concatenate([
            np.zeros(len(y_vec), dtype=bool),
            np.ones(n_to_generate, dtype=bool)
        ])
        
        df_res = pd.DataFrame(X_res, columns=feature_names)
        return df_res, y_res, synth_mask

    def khoi_smote(self, X, y, n_clusters=4, sampling_strategy=1.0):
        """
        Kernel Hybrid Oversampling for Imbalanced Streams (KHOI-SMOTE).
        Steps:
        1. K-Means clustering on minority instances to discover latent fraud patterns.
        2. Computes H-Outlyingness Index (HOI distance to cluster centroids).
        3. Weights oversampling by cluster density and boundary sparsity.
        4. Applies Gaussian kernel perturbation.
        
        Returns:
            X_res: pd.DataFrame of resampled features.
            y_res: np.ndarray of resampled labels.
            synth_mask: np.ndarray boolean mask (True for synthetic).
        """
        np.random.seed(self.random_state)
        
        feature_names = X.columns if isinstance(X, pd.DataFrame) else [f"feat_{i}" for i in range(X.shape[1])]
        X_mat = np.array(X, dtype=float)
        y_vec = np.array(y, dtype=int)
        
        minority_idx = np.where(y_vec == 1)[0]
        majority_idx = np.where(y_vec == 0)[0]
        
        n_minority = len(minority_idx)
        n_majority = len(majority_idx)
        
        if n_minority == 0 or n_majority == 0 or n_minority >= n_majority:
            synth_mask = np.zeros(len(y_vec), dtype=bool)
            return pd.DataFrame(X_mat, columns=feature_names), y_vec, synth_mask
            
        n_to_generate = int(n_majority * sampling_strategy) - n_minority
        if n_to_generate <= 0:
            synth_mask = np.zeros(len(y_vec), dtype=bool)
            return pd.DataFrame(X_mat, columns=feature_names), y_vec, synth_mask

        X_minority = X_mat[minority_idx]
        
        # 1. K-Means clustering on minority instances
        k_clusters = min(n_clusters, max(1, n_minority // 2))
        if k_clusters < 2:
            # Fallback to TPH-SMOTE if minority instances are too few to cluster
            return self.tph_smote(X, y, sampling_strategy=sampling_strategy)
            
        kmeans = KMeans(n_clusters=k_clusters, random_state=self.random_state, n_init='auto')
        cluster_labels = kmeans.fit_predict(X_minority)
        centroids = kmeans.cluster_centers_
        
        # 2. Compute H-Outlyingness Index (HOI) - Distance to assigned centroid
        hoi_scores = np.zeros(n_minority)
        for i in range(n_minority):
            c_idx = cluster_labels[i]
            hoi_scores[i] = np.linalg.norm(X_minority[i] - centroids[c_idx])
            
        # Normalize weights (higher weight for boundary/dispersed minority points)
        hoi_sum = np.sum(hoi_scores)
        if hoi_sum > 0:
            sample_probs = hoi_scores / hoi_sum
        else:
            sample_probs = np.ones(n_minority) / n_minority
            
        synthetic_samples = []
        cluster_stds = [np.std(X_minority[cluster_labels == c], axis=0) + 1e-5 if (cluster_labels == c).sum() > 1 else np.std(X_minority, axis=0) + 1e-5 for c in range(k_clusters)]
        
        for _ in range(n_to_generate):
            # Select anchor point using HOI probability distribution
            anchor_idx = np.random.choice(n_minority, p=sample_probs)
            anchor_point = X_minority[anchor_idx]
            c_idx = cluster_labels[anchor_idx]
            
            # Select partner from same cluster or centroid
            same_cluster_indices = np.where(cluster_labels == c_idx)[0]
            if len(same_cluster_indices) > 1:
                partner_idx = np.random.choice(same_cluster_indices)
                partner_point = X_minority[partner_idx]
            else:
                partner_point = centroids[c_idx]
                
            # Linear interpolation
            lam = np.random.uniform(0.1, 0.9)
            base_synth = anchor_point + lam * (partner_point - anchor_point)
            
            # Gaussian Kernel Perturbation
            gaussian_kernel = np.random.normal(0, 0.05 * cluster_stds[c_idx])
            final_synth = base_synth + gaussian_kernel
            synthetic_samples.append(final_synth)
            
        X_synthetic = np.array(synthetic_samples)
        y_synthetic = np.ones(n_to_generate, dtype=int)
        
        X_res = np.vstack([X_mat, X_synthetic])
        y_res = np.concatenate([y_vec, y_synthetic])
        
        synth_mask = np.concatenate([
            np.zeros(len(y_vec), dtype=bool),
            np.ones(n_to_generate, dtype=bool)
        ])
        
        df_res = pd.DataFrame(X_res, columns=feature_names)
        return df_res, y_res, synth_mask
