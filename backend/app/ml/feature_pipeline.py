import math
import numpy as np
import pandas as pd
from typing import List, Dict, Any, Tuple

class FeaturePipeline:
    """
    Leak-free feature extraction for multi-horizon storage forecasting.
    Strictly prevents lookahead leakage: feature row at timestamp t uses only
    telemetry data recorded at or before t.
    """

    LAG_STEPS = [1, 2, 6, 12, 24, 48, 168]
    ROLLING_WINDOWS = [6, 24]

    @classmethod
    def prepare_dataframe(cls, telemetry_records: List[Dict[str, Any]]) -> pd.DataFrame:
        if not telemetry_records:
            return pd.DataFrame()
        df = pd.DataFrame(telemetry_records)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values("timestamp").reset_index(drop=True)
        return df

    @classmethod
    def extract_features(cls, df: pd.DataFrame, target_col: str = "used_bytes") -> Tuple[pd.DataFrame, pd.Series]:
        """
        Extracts temporal and historical statistical features.
        Returns (X, y) where X contains no future lookahead.
        """
        if df.empty or len(df) < 24:
            raise ValueError("Insufficient telemetry history for feature extraction (minimum 24 samples required).")

        df = df.copy()
        
        # Calendar cyclical features
        hours = df["timestamp"].dt.hour
        days = df["timestamp"].dt.dayofweek
        df["hour_sin"] = np.sin(2.0 * np.pi * hours / 24.0)
        df["hour_cos"] = np.cos(2.0 * np.pi * hours / 24.0)
        df["day_sin"] = np.sin(2.0 * np.pi * days / 7.0)
        df["day_cos"] = np.cos(2.0 * np.pi * days / 7.0)
        df["is_weekend"] = (days >= 5).astype(float)

        # Lags on target
        for lag in cls.LAG_STEPS:
            if lag < len(df):
                df[f"{target_col}_lag_{lag}"] = df[target_col].shift(lag)

        # Rolling statistics on target
        for window in cls.ROLLING_WINDOWS:
            if window < len(df):
                df[f"{target_col}_roll_mean_{window}"] = df[target_col].shift(1).rolling(window=window).mean()
                df[f"{target_col}_roll_std_{window}"] = df[target_col].shift(1).rolling(window=window).std().fillna(0.0)
                df[f"{target_col}_roll_min_{window}"] = df[target_col].shift(1).rolling(window=window).min()
                df[f"{target_col}_roll_max_{window}"] = df[target_col].shift(1).rolling(window=window).max()

        # Differencing / Growth rate
        df[f"{target_col}_diff_1h"] = df[target_col].shift(1) - df[target_col].shift(2)
        df[f"{target_col}_diff_24h"] = df[target_col].shift(1) - df[target_col].shift(25)

        # Workload context features
        if "read_iops" in df.columns and "write_iops" in df.columns:
            total_iops = df["read_iops"].shift(1) + df["write_iops"].shift(1)
            df["total_iops_lag_1"] = total_iops
            df["read_ratio_lag_1"] = df["read_iops"].shift(1) / (total_iops + 1e-5)
        
        if "queue_depth" in df.columns:
            df["queue_depth_lag_1"] = df["queue_depth"].shift(1)

        # Filter to purely numeric feature columns to prevent string dtype issues in gradient boosters
        feature_cols = [
            c for c in df.columns
            if c not in ["timestamp", "device_id", "source_label", "is_synthetic", "telemetry_quality", "scenario_type", target_col]
            and pd.api.types.is_numeric_dtype(df[c])
        ]
        valid_mask = df[feature_cols].notna().all(axis=1) & df[target_col].notna()

        X = df.loc[valid_mask, feature_cols].reset_index(drop=True)
        y = df.loc[valid_mask, target_col].reset_index(drop=True)
        return X, y
