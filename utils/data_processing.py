"""  
Data processing utilities for Teletrax data  
"""
  
import pandas as pd  
from collections import Counter  
from typing import List, Dict, Tuple  
import re

def find_column(df, possible_names):  
    """Find a column by trying multiple possible names"""  
    for name in possible_names:  
        if name in df.columns:  
            return name  
    return None  

def load_data_file(file, file_type='auto'):  
    """  
    Load data from uploaded file (Excel or CSV)
      
    Args:  
        file: Uploaded file object  
        file_type: 'excel', 'csv', or 'auto' (default)
      
    Returns:  
        pandas DataFrame  

    """  
    if file_type == 'auto':  
        file_type = 'excel' if file.name.endswith('.xlsx') else 'csv'
      
    if file_type == 'excel':  
        return pd.read_excel(file)  
    else:  
        return pd.read_csv(file)

  
def extract_masterslug(slug_text: str) -> str:  
    """  
    Extract masterslug from slug line  
    Masterslug = first two words before '/'  
    If 'advisory' or 'flash' present, skip them and get next two words
      
    Args:  
        slug_text: Full slug line text
      
    Returns:  
        Masterslug (two words)  
    """  
    if pd.isna(slug_text) or not slug_text:  
        return ""
      
    slug_text = str(slug_text).strip()
      
    # Split by '/' and take the first part (before any slash)  
    parts = slug_text.split('/')  
    text_before_slash = parts[0].strip()
      
    # Split into words  
    words = text_before_slash.split()
      
    # Filter out 'advisory' and 'flash' (case-insensitive)  
    filtered_words = [w for w in words if w.lower() not in ['advisory', 'flash']]
      
    # Take first two words  
    if len(filtered_words) >= 2:  
        return ' '.join(filtered_words[:2])  
    elif len(filtered_words) == 1:  
        return filtered_words[0]  
    else:  
        return ""

  
def extract_top_masterslugs(df: pd.DataFrame, top_n: int = 3) -> Tuple[List[Dict], int]:  
    """  
    Extract top N masterslugs from raw data  
    Automatically finds the 'Slug line' column and extracts masterslugs
      
    Args:  
        df: DataFrame with slug/headline data  
        top_n: Number of top masterslugs to extract (default: 3)
      
    Returns:  
        Tuple of (list of top masterslugs with percentages, total count)  
    """  
    # Find the slug line column (case-insensitive search)  
    slug_column = None
      
    for col in df.columns:  
        if 'slug' in str(col).lower():  
            slug_column = df[col]  
            break
      
    # If no column named 'slug', fall back to first column  
    if slug_column is None:  
        slug_column = df.iloc[:, 0]
      
    # Extract masterslugs  
    masterslugs = slug_column.dropna().apply(extract_masterslug)
      
    # Remove empty masterslugs  
    masterslugs = masterslugs[masterslugs != ""]
      
    # Count occurrences  
    masterslug_counts = Counter(masterslugs)
      
    # Get top N  
    top_masterslugs = masterslug_counts.most_common(top_n)
      
    # Calculate total for percentages  
    total = sum(masterslug_counts.values())
      
    # Format results  
    results = []  
    for masterslug, count in top_masterslugs:  
        percentage = (count / total) * 100 if total > 0 else 0  
        results.append({  
            'slug': str(masterslug),  
            'count': count,  
            'percentage': percentage  
        })
      
    return results, total

  
def format_stats_text(edits: int, lives_on_air: int, total_lives: int,   
                     countries: int, total_detection_length: str, narrative: str) -> str:  
    """  
    Create formatted text for bottom left stats section
      
    Args:  
        edits: Total number of unique edit assets  
        lives_on_air: Number of unique live assets with duration < 3:00  
        total_lives: Total number of unique live assets (no filter)  
        countries: Total number of countries  
        detection_length: Total actual detection length (formatted string HH:MM:SS)  
        narrative: Custom narrative text
      
    Returns:  
        Formatted stats text  
    """  
    stats_text = f"""• Number of edits over one year: {edits:,}  
• Number of lives on air (timespan <3:00): {lives_on_air:,}  
• Number of lives total: {total_lives:,}  
• Number of countries: {countries:,}  
• Total actual detection length: {total_detection_length}
  
{narrative}"""
      
    return stats_text

  
def prepare_country_data(df: pd.DataFrame, target_percentage: float = 0.70) -> pd.DataFrame:  
    """  
    Prepare country data for pie chart with smart grouping
      
    Args:  
        df: DataFrame with country codes and hit counts  
        target_percentage: Target percentage for top countries (default: 0.70 = 70%)
      
    Returns:  
        Processed DataFrame with top countries and "Rest of World"  
    """  

    # Check if dataframe is empty or has no columns  
    if df is None or df.empty or len(df.columns) == 0:  
        return pd.DataFrame()
    
    # Make a clean copy  
    df_clean = df.copy()

    # Check again after copy  
    if df_clean.empty or len(df_clean.columns) == 0:  
        return pd.DataFrame()
      
    # Get column names  
    location_col = df_clean.columns[0]  
    hits_col = df_clean.columns[1]
      
    # Remove rows with 'Unmatched' or 'XX' in the location code (case-insensitive)  
    df_clean = df_clean[~df_clean[location_col].astype(str).str.upper().isin(['UNMATCHED', 'XX'])]
      
    # Ensure hits column is numeric  
    df_clean[hits_col] = pd.to_numeric(df_clean[hits_col], errors='coerce')  
    df_clean = df_clean.dropna(subset=[hits_col])
      
    # Sort by hit count descending  
    df_sorted = df_clean.sort_values(by=hits_col, ascending=False).reset_index(drop=True)
      
    # Calculate total hits  
    total_hits = df_sorted[hits_col].sum()
      
    if total_hits == 0:  
        return df_sorted
      
    # Find top countries that account for ~70% of usage  
    cumulative_sum = 0  
    top_n = 0
      
    for idx in range(len(df_sorted)):  
        cumulative_sum += df_sorted.loc[idx, hits_col]  
        top_n += 1
          
        # Stop when we reach target percentage or max 8 countries  
        if (cumulative_sum / total_hits >= target_percentage) or (top_n >= 8):  
            break
      
    # Ensure at least 5 countries if available  
    top_n = max(min(top_n, len(df_sorted)), min(5, len(df_sorted)))
      
    # Take top N countries  
    top_countries = df_sorted.head(top_n).copy()
      
    # Group the rest as "Rest of World"  
    if len(df_sorted) > top_n:  
        rest_sum = df_sorted.iloc[top_n:][hits_col].sum()
          
        if rest_sum > 0:  
            # Create rest of world row with same column structure  
            rest_row = pd.DataFrame({  
                location_col: ['Rest of World'],  
                hits_col: [int(rest_sum)]  
            })  
            df_chart = pd.concat([top_countries, rest_row], ignore_index=True)  
        else:  
            df_chart = top_countries  
    else:  
        df_chart = top_countries
      
    # Reset index to ensure clean positional access  
    df_chart = df_chart.reset_index(drop=True)
      
    return df_chart  
  
def validate_data_structure(df: pd.DataFrame, expected_columns: int = 2) -> bool:  
    """  
    Validate that DataFrame has expected structure
      
    Args:  
        df: DataFrame to validate  
        expected_columns: Expected number of columns
      
    Returns:  
        True if valid, raises ValueError if not  
    """  
    if df is None or df.empty:  
        raise ValueError("DataFrame is empty")
      
    if len(df.columns) < expected_columns:  
        raise ValueError(f"Expected at least {expected_columns} columns, got {len(df.columns)}")
      
    return True

def get_earliest_date(df: pd.DataFrame) -> str:
    """
    Get the earliest date from the dataset.

    Preference:
    1) A column whose name matches UTC detection start (e.g. 'UTC detection start')
    2) Any column with 'date', 'time', 'timestamp', or 'detection start' in its name
    3) First column (as a last resort)

    Returns:
        Formatted date string (e.g., "30 October 2024"), or "2024" as fallback.
    """
    date_series = None

    # 1) Explicitly prefer UTC detection start–style columns
    preferred_patterns = [
        "utc detection start",
        "utc_detection_start",
        "utc detection",
        "detection start utc",
    ]

    for col in df.columns:
        col_lower = str(col).lower()
        if any(pat in col_lower for pat in preferred_patterns):
            try:
                parsed = pd.to_datetime(df[col], errors="coerce", utc=True)
                if parsed.notna().any():
                    date_series = parsed
                    break
            except Exception:
                continue

    # 2) Generic date/time/detection-start heuristic if still not found
    if date_series is None:
        for col in df.columns:
            col_lower = str(col).lower()
            if any(keyword in col_lower for keyword in ["date", "time", "timestamp", "detection start"]):
                try:
                    parsed = pd.to_datetime(df[col], errors="coerce", utc=True)
                    if parsed.notna().any():
                        date_series = parsed
                        break
                except Exception:
                    continue

    # 3) Fallback to first column, if nothing else worked
    if date_series is None and len(df.columns) > 0:
        try:
            parsed = pd.to_datetime(df.iloc[:, 0], errors="coerce", utc=True)
            if parsed.notna().any():
                date_series = parsed
        except Exception:
            pass

    # Extract earliest date and format
    if date_series is not None and date_series.notna().any():
        try:
            earliest = date_series.min().date()  # just the date portion
            # Format as "30 October 2024" (strip leading zero from day)
            day = str(earliest.day)
            month_year = earliest.strftime("%B %Y")
            return f"{day} {month_year}"
        except Exception:
            pass

    # Fallback: just return current year (or whatever default you want)
    return "2024"

def calculate_channel_airtime(df: pd.DataFrame, max_age_days: int = 30) -> pd.DataFrame:  
    """  
    Calculate airtime distribution by channel for content under X days old
      
    Args:  
        df: DataFrame with Channel, Detection duration, Asset age columns  
        max_age_days: Maximum asset age in days (default 30)
      
    Returns:  
        DataFrame with Channel and Duration columns  
    """  
    # Find channel column  
    channel_col = None  
    for col in df.columns:  
        col_lower = str(col).lower()  
        if 'channel' in col_lower:  
            channel_col = col  
            break
      
    # Find detection duration column  
    duration_col = None  
    for col in df.columns:  
        col_lower = str(col).lower()  
        if 'detection' in col_lower and 'duration' in col_lower:  
            duration_col = col  
            break
      
    # Find asset age column  
    age_col = None  
    for col in df.columns:  
        col_lower = str(col).lower()  
        if 'asset' in col_lower and 'age' in col_lower:  
            age_col = col  
            break
      
    # If any required column is missing, return empty  
    if not all([channel_col, duration_col, age_col]):  
        return pd.DataFrame()
      
    # Filter for age < 30 days  
    df_filtered = df.copy()
      
    # Convert asset age to days  
    df_filtered['age_days'] = df_filtered[age_col].apply(  
        lambda x: parse_timespan_to_seconds(x) / 86400 if pd.notna(x) else 999  
    )
      
    # Filter for assets under 30 days  
    df_filtered = df_filtered[df_filtered['age_days'] < max_age_days]
      
    # Calculate total duration per channel  
    channel_durations = {}
      
    for channel in df_filtered[channel_col].unique():  
        if pd.isna(channel) or str(channel).strip() == '':  
            continue
              
        channel_data = df_filtered[df_filtered[channel_col] == channel]
          
        # Sum all durations for this channel  
        total_seconds = 0  
        for dur in channel_data[duration_col].dropna():  
            total_seconds += parse_timespan_to_seconds(dur)
          
        if total_seconds > 0:  
            channel_durations[str(channel).strip()] = total_seconds
      
    # Create result dataframe  
    if not channel_durations:  
        return pd.DataFrame()
      
    result = pd.DataFrame({  
        'Channel': list(channel_durations.keys()),  
        'Duration': list(channel_durations.values())  
    })
      
    # Sort by duration descending  
    result = result.sort_values('Duration', ascending=False).reset_index(drop=True)
      
    return result  
  
# ============================================  
# BOTTOM LEFT CALCULATION FUNCTIONS  
# ============================================

def parse_timespan_to_seconds(timespan_str: str) -> int:  
    """  
    Parse timespan string to seconds - handles various formats including 'X days HH:MM:SS'  
    """  
    try:  
        timespan_str = str(timespan_str).strip()
          
        # Skip if empty or NaN  
        if not timespan_str or timespan_str.lower() in ['nan', 'none', '', 'nat']:  
            return 0
          
        # Handle 'X days HH:MM:SS' format  
        if 'days' in timespan_str.lower() or 'day' in timespan_str.lower():  
            # Split by 'days' or 'day'  
            parts = timespan_str.lower().replace('days', '').replace('day', '').strip().split()
              
            if len(parts) >= 2:  
                # First part is days, second part is time  
                days = int(parts[0])  
                time_part = parts[1]
                  
                # Parse HH:MM:SS  
                time_parts = time_part.split(':')  
                if len(time_parts) == 3:  
                    h, m, s = int(time_parts[0]), int(time_parts[1]), int(time_parts[2])  
                    total_seconds = days * 86400 + h * 3600 + m * 60 + s  
                    return total_seconds  
                elif len(time_parts) == 2:  
                    m, s = int(time_parts[0]), int(time_parts[1])  
                    total_seconds = days * 86400 + m * 60 + s  
                    return total_seconds
          
        # Handle HH:MM:SS or MM:SS format (no days)  
        if ':' in timespan_str:  
            parts = timespan_str.split(':')  
            parts = [p.strip() for p in parts]
              
            if len(parts) == 3:  
                h, m, s = int(parts[0]), int(parts[1]), int(parts[2])  
                return h * 3600 + m * 60 + s  
            elif len(parts) == 2:  
                m, s = int(parts[0]), int(parts[1])  
                return m * 60 + s
          
        # Try parsing as plain number (seconds)  
        return int(float(timespan_str))  
    except Exception as e:  
        return 0  

  
def calculate_total_detection_length(df: pd.DataFrame) -> str:  
    """  
    Calculate total detection length from Detection duration column  
    """  
    duration_col_name = 'Detection duration'
      
    if duration_col_name not in df.columns:  
        return "00:00:00"
      
    total_seconds = 0
      
    for duration in df[duration_col_name].dropna():  
        seconds = parse_timespan_to_seconds(duration)  
        total_seconds += seconds
      
    if total_seconds == 0:  
        return "00:00:00"
      
    # Convert to HH:MM:SS  
    hours = total_seconds // 3600  
    minutes = (total_seconds % 3600) // 60  
    seconds = total_seconds % 60
      
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

  
def calculate_lives_on_air(df: pd.DataFrame, max_duration_seconds: int = 180,   
                          use_unique_assets: bool = True) -> int:  
    """  
    Count unique Headlines with Service=LIVE and Asset age < 3:00  
    """  
    service_col_name = 'Service'  
    asset_age_col_name = 'Asset age (time span)'  
    headline_col_name = 'Headline'
      
    # Check required columns exist  
    if service_col_name not in df.columns:  
        return 0  
    if asset_age_col_name not in df.columns:  
        return 0  
    if use_unique_assets and headline_col_name not in df.columns:  
        return 0
      
    qualifying_assets = set()
      
    for idx in df.index:  
        try:  
            # Check if LIVE  
            service = str(df.loc[idx, service_col_name]).strip().upper()  
            if service != 'LIVE':  
                continue
              
            # Get asset age  
            asset_age = df.loc[idx, asset_age_col_name]  
            age_seconds = parse_timespan_to_seconds(asset_age)
              
            # Check if under threshold  
            if age_seconds < max_duration_seconds:  
                if use_unique_assets:  
                    headline = str(df.loc[idx, headline_col_name]).strip()  
                    if headline and headline.lower() not in ['nan', 'none', '']:  
                        qualifying_assets.add(headline)  
                else:  
                    qualifying_assets.add(idx)  
        except Exception as e:  
            continue
      
    return len(qualifying_assets)

  
def calculate_total_lives(df: pd.DataFrame, use_unique_assets: bool = True) -> int:  
    """  
    Count unique Headlines with Service=LIVE (no age filter)  
    """  
    service_col_name = 'Service'  
    headline_col_name = 'Headline'
      
    if service_col_name not in df.columns:  
        return 0
      
    if use_unique_assets and headline_col_name not in df.columns:  
        return 0
      
    # Filter for LIVE  
    live_mask = df[service_col_name].astype(str).str.strip().str.upper() == 'LIVE'  
    live_df = df[live_mask]
      
    if use_unique_assets and headline_col_name in live_df.columns:  
        # Count unique headlines (excluding NaN/empty)  
        unique_headlines = live_df[headline_col_name].dropna()  
        unique_headlines = unique_headlines[unique_headlines.astype(str).str.strip() != '']  
        return int(unique_headlines.nunique())  
    else:  
        return len(live_df)

  
def calculate_total_edits(df: pd.DataFrame, use_unique_assets: bool = True) -> int:  
    """  
    Count unique Headlines where Service is NOT "LIVE"  
    """  
    service_col_name = 'Service'  
    headline_col_name = 'Headline'
      
    if service_col_name not in df.columns:  
        return len(df)
      
    if use_unique_assets and headline_col_name not in df.columns:  
        return 0
      
    # Filter for non-LIVE  
    non_live_mask = df[service_col_name].astype(str).str.strip().str.upper() != 'LIVE'  
    non_live_df = df[non_live_mask]
      
    if use_unique_assets and headline_col_name in non_live_df.columns:  
        # Count unique headlines (excluding NaN/empty)  
        unique_headlines = non_live_df[headline_col_name].dropna()  
        unique_headlines = unique_headlines[unique_headlines.astype(str).str.strip() != '']  
        return int(unique_headlines.nunique())  
    else:  
        return len(non_live_df)

  
def calculate_total_countries(df: pd.DataFrame) -> int:  
    """  
    Count unique countries from Location code column  
    """  
    location_col_name = 'Location code'
      
    if location_col_name not in df.columns:  
        return 0
      
    # Get unique values, excluding unwanted entries  
    unique_countries = df[location_col_name].dropna().astype(str).str.strip().str.upper()  
    unique_countries = unique_countries[~unique_countries.isin(['UNMATCHED', 'XX', ''])]
      
    return len(unique_countries.unique())  