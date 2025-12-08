"""
Chart generation utilities using Matplotlib
"""

import plotly.graph_objects as go
import matplotlib.pyplot as plt
from matplotlib import patches
from mpl_toolkits.mplot3d import Axes3D
import pandas as pd
import numpy as np
from typing import List, Dict
from io import BytesIO
from config.colours import (
    LINE_CHART_COLOR, 
    PIE_COLORS, 
    CHART_FONT, 
    CHART_BG_COLOR, 
    GRID_COLOR
)

# GENERATE CHARTS

def generate_time_series_chart(df: pd.DataFrame,   
                               channel_name: str = "",  
                               title: str = "Use by Month",  
                               total_detection_length: str = "00:00:00",  
                               height: int = 400) -> go.Figure:  
    """  
    Generate time series line chart with selective month labels (Jan, May, Sep)
      
    Args:  
        df: DataFrame with Month and # Assets columns  
        channel_name: Channel name for title  
        title: Chart title suffix  
        total_detection_length: Total detection length across last 365 days  
        height: Chart height in pixels
      
    Returns:  
        Plotly Figure object  
    """  
    fig = go.Figure()
      
    # Parse dates  
    try:  
        dates = pd.to_datetime(df.iloc[:, 0])  
        formatted_dates = dates.dt.strftime('%b %Y')  
    except:  
        formatted_dates = df.iloc[:, 0]  
        dates = pd.to_datetime(formatted_dates, format='%b %Y', errors='coerce')
      
    # Add line trace  
    fig.add_trace(go.Scatter(  
        x=formatted_dates,  
        y=df.iloc[:, 1],  
        mode='lines',  
        line=dict(color=LINE_CHART_COLOR, width=3.5),  
        name='Assets',  
        hovertemplate='%{x}<br>Assets: %{y:,}<extra></extra>'  
    ))
      
    # Create custom tick values - only Jan, May, Sep of each year  
    if dates is not None and not dates.isna().all():  
        # Get unique years  
        years = dates.dt.year.unique()
        
        # Create tick positions for Jan, May, Sep of each year  
        tick_vals = []  
        tick_text = []
        
        for year in sorted(years):  
            for month in [1, 5, 9]:  # January, May, September  
                # Find if this month exists in the data  
                mask = (dates.dt.year == year) & (dates.dt.month == month)  
                if mask.any():  
                    # Get the index of this month  
                    idx = mask.idxmax()  
                    tick_vals.append(formatted_dates.iloc[idx])  
                    tick_text.append(f"{['Jan', 'May', 'Sep'][(month-1)//4]} {year}")
        
        # Set custom ticks (no vertical grid lines)  
        xaxis_config = dict(  
            tickmode='array',  
            tickvals=tick_vals,  
            ticktext=tick_text,  
            tickangle=-45,  
            showgrid=False, 
            tickfont=dict(size=9)  
        )  
    else:  
        # Fallback if date parsing fails  
        xaxis_config = dict(  
            showgrid=False,    
            tickangle=-45,  
            tickfont=dict(size=9)  
        )
    
    # Build title  
    full_title = f"{channel_name}: {title}"  
    if total_detection_length and total_detection_length != "00:00:00":  
        full_title += f"<br><sub>Total Detection Length (last 365 days): {total_detection_length}</sub>"
    
    # Update layout  
    fig.update_layout(  
        title=dict(  
            text=full_title,  
            font=dict(size=20, family=CHART_FONT, color='#333', weight='bold'),  
            x=0.5,  
            xanchor='center'  
        ),  
        xaxis_title="",  
        yaxis_title="",  
        plot_bgcolor='white',  
        paper_bgcolor='white',  
        height=height,  
        margin=dict(l=60, r=30, t=80, b=80),  
        font=dict(family=CHART_FONT, size=10),  
        showlegend=False,  
        xaxis=xaxis_config,  # Use the config directly (already has showgrid=False)  
        yaxis=dict(  
            showgrid=True,  # Keep horizontal gridlines  
            gridcolor='#E5E5E5',  
            tickformat=','  
        ),  
        hovermode='x unified'  
    )    

    return fig  

def generate_3d_beveled_pie_chart(
    df: pd.DataFrame,
    channel_name: str = "",
    title: str = "Use by country",
    subtitle: str = "",
    target_percentage: float = 0.70,
    min_label_pct: float = 3.0,         
    inside_min_angle_deg: float = 18.0,  # >= angle -> label INSIDE
) -> BytesIO:
    """
    projected disk:
      - Flat top (ellipse projection), NO spherical highlight
      - Side wall only on the FRONT half, constant dark shade (disk feel)
      - Thin outer rim + tiny center bevel (very subtle)
      - Small slices at the FRONT, big slices at the BACK
      - Labels: big slices INSIDE, small slices OUTSIDE with elbow leader
      - Exact label text preserved: "{label}\\n{percent}%"
    """
    import numpy as np
    import matplotlib.pyplot as plt
    from matplotlib.patches import Wedge, Polygon
    from matplotlib.transforms import Affine2D
    from utils.data_processing import prepare_country_data
    from config.colours import PIE_COLORS
    from io import BytesIO

    # Check if input is empty  
    if df is None or df.empty or len(df.columns) == 0:  
        return BytesIO()
    
    # ---------- data ----------
    df_chart = prepare_country_data(df, target_percentage=target_percentage)
    if df_chart.empty or df_chart.shape[1] < 2:
        return BytesIO()

    # Check if preparation resulted in empty data  
    if df_chart.empty or len(df_chart.columns) == 0:  
        return BytesIO()
    
    loc_col, hits_col = df_chart.columns[:2]
    labels = df_chart[loc_col].astype(str).tolist()
    values = df_chart[hits_col].astype(float).tolist()
    total = float(sum(values))
    if total <= 0:
        return BytesIO()

    # Place SMALL slices at the FRONT (start at 270° and sweep clockwise)
    order = np.argsort(values)  # ascending: small -> large
    labels   = [labels[i] for i in order]
    values   = [values[i] for i in order]
    percents = [v / total * 100 for v in values]

    # Colors 
    colors_hex = (PIE_COLORS * ((len(values)//len(PIE_COLORS))+1))[:len(values)]
    def hx2rgb01(h): return tuple(int(h[1+i:3+i],16)/255 for i in (0,2,4))
    colors_rgb = [hx2rgb01(h) for h in colors_hex]

    # ---------- geometry / projection ----------
    R = 1.0
    y_scale = 0.40          # ellipse squash 
    wall_px = 0.14          # max side-wall thickness (front only), constant shade
    center = (0.0, 0.0)
    start_angle = 270.0     # FRONT center
    clockwise = True
    front_dir_deg = -90.0   # front direction (downward)

    # ---------- figure ----------
    fig, ax = plt.subplots(figsize=(10.0, 6.2), dpi=180)
    fig.patch.set_facecolor("white")
    ax.set_aspect("equal")
    ax.axis("off")

    to_ellipse = Affine2D().scale(1.0, y_scale) + ax.transData

    def norm(a): 
        a = a % 360.0
        return a if a >= 0 else a + 360.0

    def ang_sweep(a1, a2, step=2.0, cw=True):
        if cw:
            a2 = a1 - ((a1 - a2) % 360.0)
            if a2 > a1: a2 -= 360.0
            arr = np.arange(a1, a2 - 1e-6, -step)
            if arr[-1] != a2: arr = np.append(arr, a2)
        else:
            a2 = a1 + ((a2 - a1) % 360.0)
            if a2 < a1: a2 += 360.0
            arr = np.arange(a1, a2 + 1e-6, step)
            if arr[-1] != a2: arr = np.append(arr, a2)
        return arr

    # build slices
    theta = start_angle
    slices = []
    for lab, val, pct, col in zip(labels, values, percents, colors_rgb):
        ang = (val/total)*360.0
        t1, t2 = theta, (theta - ang if clockwise else theta + ang)
        slices.append((lab, pct, col, t1, t2))
        theta = t2

    # 1) draw all top wedges (FLAT colors — no radial/spherical shading)
    for lab, pct, col, t1, t2 in slices:
        w = Wedge(center, R, t2, t1, facecolor=col, edgecolor="#1a1a1a", linewidth=0.6)
        w.set_transform(to_ellipse)
        ax.add_patch(w)

    # 2) draw front-only side wall (constant darker shade -> disk, not sphere)
    for lab, pct, col, t1, t2 in slices:
        arc = ang_sweep(t1, t2, step=2.0, cw=clockwise)
        vis = []
        for a in arc:
            d = np.deg2rad((norm(a - front_dir_deg) + 180) % 360 - 180)
            if abs(d) <= np.pi/2:  # front half only
                vis.append((a, d))
        if len(vis) < 2:
            continue

        top_edge = []
        bot_edge = []
        for a, d in vis:
            x = R * np.cos(np.deg2rad(a))
            y_top = R * np.sin(np.deg2rad(a)) * y_scale
            # constant wall height (no taper) -> flat disk feel
            y_bot = y_top - wall_px
            top_edge.append((x, y_top))
            bot_edge.append((x, y_bot))

        poly_pts = top_edge + bot_edge[::-1]
        side = Polygon(poly_pts, closed=True,
                       facecolor=tuple(c * 0.55 for c in col),  # darker side
                       edgecolor="none", linewidth=0)
        ax.add_patch(side)

    # 3) thin outer rim (top)
    rim = Wedge(center, R*1.006, 0, 360, facecolor="none", edgecolor="#0d0d0d", linewidth=0.6)
    rim.set_transform(to_ellipse)
    ax.add_patch(rim)

    # 4) tiny center bevel (VERY subtle so it doesn’t look spherical)
    bevel = Wedge(center, R*0.14, 0, 360, facecolor="#000000", edgecolor="none", linewidth=0)
    bevel.set_alpha(0.07)          # much lower alpha
    bevel.set_transform(to_ellipse)
    ax.add_patch(bevel)

    # 5) faint back highlight band (linear look, not a dome)
    back_band = Wedge(center, R*1.00, 110, 70, facecolor="#ffffff", edgecolor="none")
    back_band.set_alpha(0.035)     # whisper-light
    back_band.set_transform(to_ellipse)
    ax.add_patch(back_band)

    # ---------- labels ----------
    theta = start_angle
    for lab, val, pct, col in zip(labels, values, percents, colors_rgb):
        ang = (val/total)*360.0
        t1, t2 = theta, (theta - ang if clockwise else theta + ang)
        mid = np.deg2rad((t1 + t2) / 2.0)
        ang_abs = abs(ang)

        # point on ellipse for leader start
        rx, ry = R*np.cos(mid), R*np.sin(mid)*y_scale

        if pct >= min_label_pct and ang_abs >= inside_min_angle_deg:
            # INSIDE (for bigger slices — usually at the back now)
            r_txt = 0.62 * R
            x, y = r_txt*np.cos(mid), r_txt*np.sin(mid)*y_scale
            ax.text(x, y, f"{lab}\n{pct:.0f}%", ha="center", va="center",
                    fontsize=10, fontweight="bold", color="white", fontfamily="Arial", zorder=10)
        elif pct >= min_label_pct:
            # OUTSIDE elbow leader
            r1 = 1.06 * R
            x1, y1 = r1*np.cos(mid), r1*np.sin(mid)*y_scale
            to_right = (np.cos(mid) >= 0)
            x2 = x1 + (0.22 if to_right else -0.22)
            y2 = y1
            ax.plot([rx, x1, x2], [ry, y1, y2], color="#444", linewidth=1.0, zorder=999)

            ha = "left" if to_right else "right"
            ax.text(x2, y2, f"{lab}\n{pct:.0f}%", ha=ha, va="center",
                    fontsize=9.5, fontweight="bold", color="white", fontfamily="Arial",
                    bbox=dict(boxstyle="round,pad=0.28", facecolor=col,
                              edgecolor="#1a1a1a", lw=0.7, alpha=0.96),
                    zorder=1000)

        theta = t2

    # bounds & title
    ax.set_xlim(-1.6, 1.6)
    ax.set_ylim(-1.25, 1.05)

    full_title = f"{channel_name} {subtitle}: {title}" if channel_name and subtitle else title
    plt.title(full_title, fontsize=20, fontfamily="Arial", color="#555", pad=8, fontweight="bold")

    # export
    buf = BytesIO()
    plt.savefig(buf, format="png", dpi=180, bbox_inches="tight", facecolor="white", pad_inches=0.08)
    buf.seek(0)
    plt.close(fig)
    return buf

def generate_multi_channel_charts(channel_data: Dict[str, pd.DataFrame],
                                  height: int = 350) -> Dict[str, BytesIO]:
    """
    Generate 3D pie charts for multiple channels
    
    Args:
        channel_data: Dictionary mapping channel names to DataFrames
        height: Not used for matplotlib, kept for compatibility
    
    Returns:
        Dictionary mapping channel names to BytesIO image objects
    """
    charts = {}
    
    for channel_name, df in channel_data.items():
        img_buffer = generate_3d_beveled_pie_chart(
            df,
            channel_name=f"{channel_name}",
            title="Usage by Country",
            subtitle="",
            target_percentage=0.70
        )
        charts[channel_name] = img_buffer
    
    return charts

def generate_channel_airtime_pie(
    df: pd.DataFrame,
    title: str = "Time on air by channel",
    subtitle: str = "Material under 30 days",
) -> BytesIO:
    """
    Generate projected 3D pie chart showing airtime distribution by channel.
    Same visual style as the country distribution chart (projected disk, front wall only,
    flat top, inside/outside labels).

    Args:
        df: DataFrame with Channel, Detection duration, Asset age columns
        title: Chart title
        subtitle: Chart subtitle

    Returns:
        BytesIO object with PNG image
    """
    import numpy as np
    import matplotlib.pyplot as plt
    from matplotlib.patches import Wedge, Polygon
    from matplotlib.transforms import Affine2D
    from utils.data_processing import calculate_channel_airtime

    # --- Prepare data ---
    df_chart = calculate_channel_airtime(df, max_age_days=30)

    if df_chart.empty or len(df_chart) == 0:
        return BytesIO()

    channels = df_chart["Channel"].astype(str).tolist()
    durations = df_chart["Duration"].astype(float).tolist()

    total = sum(durations)
    if total == 0:
        return BytesIO()

    percents = [d / total * 100 for d in durations]

    # Sort so smaller slices are at the front, bigger at the back (NRK look)
    order = np.argsort(durations)  # ascending: small -> large
    channels = [channels[i] for i in order]
    durations = [durations[i] for i in order]
    percents = [percents[i] for i in order]

    # Colors (reuse PIE_COLORS, repeat if needed)
    colors_hex = (PIE_COLORS * ((len(channels) // len(PIE_COLORS)) + 1))[: len(channels)]

    def hx2rgb01(h):
        h = h.lstrip("#")
        return tuple(int(h[i : i + 2], 16) / 255.0 for i in (0, 2, 4))

    colors_rgb = [hx2rgb01(h) for h in colors_hex]

    # --- Geometry / projection params (match the NRK-style chart you liked) ---
    R = 1.0
    y_scale = 0.4          # <- you said this tilt is perfect
    wall_px = 0.18         # front wall thickness
    center = (0.0, 0.0)

    start_angle = 270.0    # front center
    clockwise = True
    front_dir_deg = -90.0  # "front" direction (downwards)

    # Label logic
    min_label_pct = 3.0          # don't label micro slices
    inside_min_angle_deg = 18.0  # >= this angle => label inside, else outside

    # --- Matplotlib figure ---
    fig, ax = plt.subplots(figsize=(10.0, 6.2), dpi=180)
    fig.patch.set_facecolor("white")
    ax.set_aspect("equal")
    ax.axis("off")

    # Transform circle -> ellipse
    to_ellipse = Affine2D().scale(1.0, y_scale) + ax.transData

    def norm(a):
        a = a % 360.0
        return a if a >= 0 else a + 360.0

    def ang_sweep(a1, a2, step=2.0, cw=True):
        if cw:
            a2 = a1 - ((a1 - a2) % 360.0)
            if a2 > a1:
                a2 -= 360.0
            arr = np.arange(a1, a2 - 1e-6, -step)
            if arr[-1] != a2:
                arr = np.append(arr, a2)
        else:
            a2 = a1 + ((a2 - a1) % 360.0)
            if a2 < a1:
                a2 += 360.0
            arr = np.arange(a1, a2 + 1e-6, step)
            if arr[-1] != a2:
                arr = np.append(arr, a2)
        return arr

    # Build slice angle ranges
    theta = start_angle
    slices = []
    for ch, dur, pct, col in zip(channels, durations, percents, colors_rgb):
        ang = (dur / total) * 360.0
        t1, t2 = theta, (theta - ang if clockwise else theta + ang)
        slices.append((ch, pct, col, t1, t2))
        theta = t2

    # 1) Draw flat top wedges (no radial/spherical shading)
    for ch, pct, col, t1, t2 in slices:
        w = Wedge(center, R, t2, t1, facecolor=col, edgecolor="#1a1a1a", linewidth=0.6)
        w.set_transform(to_ellipse)
        ax.add_patch(w)

    # 2) Draw front-only side wall (constant darker shade -> disk, not sphere)
    for ch, pct, col, t1, t2 in slices:
        arc = ang_sweep(t1, t2, step=2.0, cw=clockwise)
        vis = []
        for a in arc:
            d = np.deg2rad((norm(a - front_dir_deg) + 180) % 360 - 180)
            if abs(d) <= np.pi / 2:  # front half only
                vis.append((a, d))
        if len(vis) < 2:
            continue

        top_edge = []
        bot_edge = []
        for a, d in vis:
            x = R * np.cos(np.deg2rad(a))
            y_top = R * np.sin(np.deg2rad(a)) * y_scale
            y_bot = y_top - wall_px  # constant wall height
            top_edge.append((x, y_top))
            bot_edge.append((x, y_bot))

        poly_pts = top_edge + bot_edge[::-1]
        side = Polygon(
            poly_pts,
            closed=True,
            facecolor=tuple(c * 0.55 for c in col),  # darker side
            edgecolor="none",
            linewidth=0,
        )
        ax.add_patch(side)

    # 3) Thin outer rim
    rim = Wedge(center, R * 1.006, 0, 360, facecolor="none", edgecolor="#0d0d0d", linewidth=0.6)
    rim.set_transform(to_ellipse)
    ax.add_patch(rim)

    # 4) Tiny center bevel (very subtle so it stays a disk, not a dome)
    bevel = Wedge(center, R * 0.14, 0, 360, facecolor="#000000", edgecolor="none", linewidth=0)
    bevel.set_alpha(0.07)
    bevel.set_transform(to_ellipse)
    ax.add_patch(bevel)

    # Optional: whisper-light back highlight band (keeps it NRK-ish but still flat)
    back_band = Wedge(center, R * 1.00, 110, 70, facecolor="#ffffff", edgecolor="none")
    back_band.set_alpha(0.03)
    back_band.set_transform(to_ellipse)
    ax.add_patch(back_band)

    # --- Labels (inside for big slices, outside w/ elbow for small), same text style as before ---
    theta = start_angle
    for ch, dur, pct, col in zip(channels, durations, percents, colors_rgb):
        ang = (dur / total) * 360.0
        t1, t2 = theta, (theta - ang if clockwise else theta + ang)
        mid = np.deg2rad((t1 + t2) / 2.0)
        ang_abs = abs(ang)

        # point on ellipse for leader start
        rx, ry = R * np.cos(mid), R * np.sin(mid) * y_scale

        if pct >= min_label_pct and ang_abs >= inside_min_angle_deg:
            # INSIDE
            r_txt = 0.62 * R
            x, y = r_txt * np.cos(mid), r_txt * np.sin(mid) * y_scale
            ax.text(
                x,
                y,
                f"{ch}\n{pct:.0f}%",
                ha="center",
                va="center",
                fontsize=10,
                fontweight="bold",
                color="white",
                fontfamily="Arial",
                zorder=10,
            )
        elif pct >= min_label_pct:
            # OUTSIDE with elbow leader
            r1 = 1.06 * R
            x1, y1 = r1 * np.cos(mid), r1 * np.sin(mid) * y_scale
            to_right = np.cos(mid) >= 0
            x2 = x1 + (0.22 if to_right else -0.22)
            y2 = y1

            # elbow leader line
            ax.plot([rx, x1, x2], [ry, y1, y2], color="#444", linewidth=1.0, zorder=999)

            ha = "left" if to_right else "right"
            ax.text(
                x2,
                y2,
                f"{ch}\n{pct:.0f}%",
                ha=ha,
                va="center",
                fontsize=9.5,
                fontweight="bold",
                color="white",
                fontfamily="Arial",
                bbox=dict(
                    boxstyle="round,pad=0.28",
                    facecolor=col,
                    edgecolor="#1a1a1a",
                    lw=0.7,
                    alpha=0.96,
                ),
                zorder=1000,
            )

        theta = t2

    # --- Bounds & title ---
    ax.set_xlim(-1.6, 1.6)
    ax.set_ylim(-1.25, 1.05)

    full_title = f"{title}\n{subtitle}" if subtitle else title
    plt.title(
        full_title,
        fontsize=16,
        fontfamily="Arial",
        pad=8,
        color="#555",
        fontweight="bold",
    )

    # --- Export to BytesIO ---
    img_buffer = BytesIO()
    plt.savefig(
        img_buffer,
        format="png",
        dpi=180,
        bbox_inches="tight",
        facecolor="white",
        edgecolor="none",
        pad_inches=0.05,
    )
    img_buffer.seek(0)
    plt.close(fig)

    return img_buffer

def create_slug_visualization(top_slugs: List[Dict],   
                              context: str = "",  
                              earliest_date: str = "") -> Dict:  
    """  
    Prepare data for masterslug visualization (bottom right)
      
    Args:  
        top_slugs: List of top masterslug dictionaries  
        context: Optional context text (auto-extracted from top slug)  
        earliest_date: Earliest date in dataset
      
    Returns:  
        Dictionary with visualization data  
    """  
    if not top_slugs:  
        return None
      
    main_slug = top_slugs[0]
      
    # Clean up masterslug - remove hyphens, capitalize  
    clean_slug = main_slug['slug'].replace('-', ' ').title()
      
    viz_data = {  
        'percentage': main_slug['percentage'],  
        'slug': main_slug['slug'],  
        'clean_slug': clean_slug,  
        'count': main_slug['count'],  
        'context': context if context else clean_slug,  
        'earliest_date': earliest_date,  
        'all_slugs': top_slugs  
    }
      
    return viz_data  