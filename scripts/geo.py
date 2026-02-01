"""Geospatial helper functions."""

from __future__ import annotations

import numpy as np
import pandas as pd


def haversine_distance(
    lat1: float | np.ndarray,
    lon1: float | np.ndarray,
    lat2: float | np.ndarray,
    lon2: float | np.ndarray,
) -> np.ndarray:
    """Return distance in km between two WGS84 coordinates using the Haversine formula."""
    lat1_rad = np.radians(lat1)
    lon1_rad = np.radians(lon1)
    lat2_rad = np.radians(lat2)
    lon2_rad = np.radians(lon2)
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    a = (
        np.sin(dlat / 2) ** 2
        + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(dlon / 2) ** 2
    )
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    return 6371.0 * c


def find_nearest_schools(
    df_schools: pd.DataFrame, lat: float, lon: float, top_n: int = 5
) -> pd.DataFrame:
    """Return top_n nearest schools to a given location.

    Parameters
    ----------
    df_schools: DataFrame
        Must contain columns 'SzkolaLat' and 'SzkolaLon'.
    lat, lon: float
        Location coordinates.
    top_n: int
        Number of closest schools to return.
    """
    df = df_schools.dropna(subset=["SzkolaLat", "SzkolaLon"]).copy()
    if df.empty:
        return df
    df["DistanceKm"] = haversine_distance(
        lat, lon, df["SzkolaLat"].to_numpy(), df["SzkolaLon"].to_numpy()
    )
    return df.sort_values("DistanceKm").head(top_n)
