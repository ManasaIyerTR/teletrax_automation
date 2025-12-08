"""
Teletrax Presentation Generator - Main Streamlit App
"""

import streamlit as st
import pandas as pd
from io import BytesIO
from PIL import Image
from utils import (
    load_data_file,
    extract_top_masterslugs,  
    format_stats_text,
    generate_time_series_chart,
    generate_3d_beveled_pie_chart,  
    generate_multi_channel_charts,
    create_slug_visualization,
    create_single_channel_ppt,
    create_multi_channel_ppt,
    calculate_total_edits,  
    calculate_lives_on_air,  
    calculate_total_lives,  
    calculate_total_countries,  
    calculate_total_detection_length,
    parse_timespan_to_seconds,
    find_column,
    get_earliest_date,
    generate_channel_airtime_pie
)

# Page configuration
st.set_page_config(
    page_title="Teletrax Automation Tool",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #2B5B7E;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        margin-bottom: 2rem;
    }
    </style>
""", unsafe_allow_html=True)

# Header
st.markdown('<p class="main-header">📊 Teletrax Presentation Generator</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Automate your client presentations with data-driven visualizations</p>', unsafe_allow_html=True)

# Sidebar Configuration
with st.sidebar:  
    st.header("⚙️ Configuration")
      
    presentation_type = st.radio(  
        "Presentation Type",  
        ["Single Channel", "Multi-Channel"],  
        help="Choose single channel for one broadcaster, multi-channel for comparison"  
    )
      
    st.markdown("---")
      
    # Channel configuration  
    if presentation_type == "Single Channel":  
        channel_name = st.text_input("Channel Name", "TF1", help="e.g., CNN, BBC, NRK")  
        channel_names = [channel_name]  
        num_channels = 1  
    else:  
        num_channels = st.number_input("Number of Channels", min_value=2, max_value=10, value=3)  
        channel_names = []  
        st.subheader("Channel Names")  
        for i in range(num_channels):  
            ch = st.text_input(f"Channel {i+1}", f"Channel {i+1}", key=f"ch_name_{i}")  
            channel_names.append(ch)
      
    date_range = st.text_input("Date Range", "Q4 2024", help="e.g., Q4 2024, Jan-Dec 2024")
      
    st.markdown("---")  
    st.subheader("📊 Bottom Left Stats")
      
    st.info("💡 Upload 'Bottom Left Stats Data' file to auto-calculate, or enter manually below")
      
    # These will be overridden if file is uploaded  
    total_edits = st.number_input("Total Edits", min_value=0, value=0, step=1, key="manual_edits")  
    lives_on_air = st.number_input("Lives on Air (<3:00)", min_value=0, value=0, step=1, key="manual_lives_air")  
    total_lives = st.number_input("Total Lives", min_value=0, value=0, step=1, key="manual_lives")  
    total_countries = st.number_input("Total Countries", min_value=0, value=0, step=1, key="manual_countries")  
    #total_duration = st.text_input("Total Duration on Air", "00:00:00", help="Format: HH:MM:SS", key="manual_duration")
      
    total_detection_length = st.text_input(  
        "Total Detection Length (365 days)",   
        "00:00:00",  
        help="Total detection length across last 365 days. Format: HH:MM:SS",  
        key="manual_detection_length"  
    )
      
    st.markdown("---")  
    st.subheader("📝 Custom Text")
      
    custom_narrative = st.text_area(  
        "Narrative (Bottom Left)",  
        "Usage continues to rise – both in terms of time on air and in the numbers of assets used.",  
        height=100,  
        help="Custom text to appear below the stats"  
    )  
    
    slug_context = st.text_input(
        "Slug Context", 
        "Mideast",
        help="Context label for main slug (e.g., 'Mideast', 'Gaza effect')"
    )

# Main content area  
st.header("📁 Upload Data Files")
  
col1, col2 = st.columns(2)
  
with col1:  
    st.subheader("Required Files")
      
    time_series_file = st.file_uploader(  
        "📈 Time Series Data (Top Left)",  
        type=['xlsx', 'csv'],  
        help="Upload file with columns: Month, # Assets"  
    )
      
    # Conditional upload based on presentation type  
    if presentation_type == "Single Channel":  
        country_file = st.file_uploader(  
            "🌍 Country Distribution (Top Right)",  
            type=['xlsx', 'csv'],  
            help="Upload file with columns: Location code, # Hits"  
        )  
    else:  
        # Multi-channel: no separate country file needed  
        country_file = None  
        st.info("ℹ️ **Top Right Chart**: Channel airtime distribution will be generated from the Bottom Left file.")
      
    slug_file = st.file_uploader(  
        "📰 Slug Line Data (Bottom Right)",  
        type=['xlsx', 'csv'],  
        help="Upload file with slug line column for masterslug extraction"  
    )
  
with col2:  
    st.subheader("Optional Files")
      
    # Bottom Left Data Upload  
    bottom_left_file = st.file_uploader(  
        "📊 Bottom Left Stats Data (Optional)",  
        type=['xlsx', 'csv'],  
        help="Upload file with columns: Service, Detection duration, Location code. If not provided, enter stats manually in sidebar."  
    )
       
    if presentation_type == "Multi-Channel":  
        st.subheader("📺 Multi-Channel Files (Optional)")  
        st.info("💡Upload individual country distribution files below if you want per-channel breakdowns on Slide 2.")
          
        channel_files = {}  
        for i in range(num_channels):  
            ch_file = st.file_uploader(  
                f"{channel_names[i]} - Country Data (Optional)",  
                type=['xlsx', 'csv'],  
                key=f"channel_file_{i}",  
                help=f"Optional: Country distribution for {channel_names[i]} on Slide 2"  
            )  
            if ch_file:  
                channel_files[channel_names[i]] = ch_file  
  
    else:
        st.info("💡 **Tip:** Make sure your data files match the expected format:\n\n"
                "- **Time Series:** Month | # Assets\n"
                "- **Country:** Location code | # Hits")
               

# Generate Button
st.markdown("---")

if st.button("🚀 Generate Presentation", type="primary", use_container_width=True):  
    # Validation  
    if not time_series_file or not slug_file:  
        st.error("❌ Please upload all required files!")  
    elif presentation_type == "Multi-Channel" and len(channel_files) == 0:  
        st.error("❌ Please upload at least one channel file for multi-channel presentation!")  
    else:  
        with st.spinner("🔄 Processing data and generating charts..."):  
            try:  
                # Load data  
                df_time = load_data_file(time_series_file)  
                
                if country_file:  
                    df_country = load_data_file(country_file)  
                else:  
                    # Extract from bottom_left or create empty  
                    df_country = pd.DataFrame()   
                
                df_slug = load_data_file(slug_file)
                  
                st.success("✅ Data loaded successfully!")
                  
             
                 
               # Calculate bottom left stats if file provided  
                if bottom_left_file:  
                    st.info("📊 Calculating bottom left stats from uploaded data...")  
                    df_bottom_left = load_data_file(bottom_left_file)
                    
                    # Show column names for debugging  
                    with st.expander("🔍 Debug: Detailed Analysis"):  
                        st.write("**Columns in uploaded file:**")  
                        for i, col in enumerate(df_bottom_left.columns):  
                            st.write(f"{i}: '{col}'")  
                        st.write(f"**Total rows:** {len(df_bottom_left)}")
                        
                        # Analyze LIVE data specifically  
                        if 'Service' in df_bottom_left.columns:  
                            st.write("---")  
                            st.subheader("LIVE Broadcast Analysis")
                            
                            live_df = df_bottom_left[df_bottom_left['Service'].str.upper() == 'LIVE'].copy()  
                            st.write(f"**Total LIVE hits:** {len(live_df)}")
                            
                            # Check Asset age column  
                            asset_age_col = find_column(df_bottom_left, ['Asset age (time span)', 'Asset age (timespan)', 'Asset age'])  
                            if asset_age_col:  
                                st.write(f"**Asset age column found:** '{asset_age_col}'")
                                
                                # Show sample asset age values  
                                st.write("**Sample asset age values from LIVE broadcasts:**")  
                                sample_ages = live_df[asset_age_col].head(20).tolist()  
                                for i, age in enumerate(sample_ages):  
                                    parsed = parse_timespan_to_seconds(age)  
                                    st.write(f"{i+1}. Raw: '{age}' → Parsed: {parsed} seconds ({parsed < 180})")
                                
                                # Parse all asset ages  
                                live_df['age_seconds'] = live_df[asset_age_col].apply(parse_timespan_to_seconds)
                                
                                valid_ages = live_df[live_df['age_seconds'] > 0]  
                                st.write(f"**Valid age values:** {len(valid_ages)} out of {len(live_df)}")
                                
                                if len(valid_ages) > 0:  
                                    st.write(f"- Min: {valid_ages['age_seconds'].min()} sec")  
                                    st.write(f"- Max: {valid_ages['age_seconds'].max()} sec")  
                                    st.write(f"- Mean: {valid_ages['age_seconds'].mean():.1f} sec")
                                    
                                    under_180 = valid_ages[valid_ages['age_seconds'] < 180]  
                                    st.write(f"**Rows with age < 180 sec:** {len(under_180)}")
                                    
                                    # Check headline column  
                                    headline_col = find_column(df_bottom_left, ['Headline', 'Asset: Headline', 'Asset headline'])  
                                    if headline_col:  
                                        st.write(f"**Headline column found:** '{headline_col}'")
                                        
                                        # Count unique headlines under 180 sec  
                                        unique_headlines_under_180 = under_180[headline_col].dropna().nunique()  
                                        st.write(f"**Unique headlines with age < 180 sec:** {unique_headlines_under_180}")
                                        
                                        # Show sample  
                                        st.write("**Sample headlines under 180 sec:**")  
                                        st.dataframe(under_180[[headline_col, asset_age_col, 'age_seconds']].head(10))  
                                    else:  
                                        st.error("❌ Headline column not found!")  
                                else:  
                                    st.error("⚠️ No valid asset age values parsed!")  
                            else:  
                                st.error("❌ Asset age column not found!")
                            
                            # Check total unique headlines for all LIVE  
                            headline_col = find_column(df_bottom_left, ['Headline', 'Asset: Headline', 'Asset headline'])  
                            if headline_col:  
                                total_unique_headlines = live_df[headline_col].dropna().nunique()  
                                st.write(f"**Total unique LIVE headlines (no age filter):** {total_unique_headlines}")
                    
                    # Calculate stats  
                    total_edits = calculate_total_edits(df_bottom_left, use_unique_assets=True)  
                    lives_on_air = calculate_lives_on_air(df_bottom_left, max_duration_seconds=180, use_unique_assets=True)  
                    total_lives = calculate_total_lives(df_bottom_left, use_unique_assets=True)  
                    total_countries = calculate_total_countries(df_bottom_left)  
                    total_detection_length = calculate_total_detection_length(df_bottom_left)
                    
                    st.success(f"✅ **Calculated Stats:**")
  
                    # Use 4 columns for better spacing  
                    col_a, col_b, col_c, col_d = st.columns(4)
                    
                    with col_a:  
                        st.metric("Total Edits", f"{total_edits:,}")  
                    with col_b:  
                        st.metric("Lives on Air (<3:00)", f"{lives_on_air:,}")  
                    with col_c:  
                        st.metric("Total Lives", f"{total_lives:,}")  
                    with col_d:  
                        st.metric("Countries", total_countries)
                    
                    # Detection length in its own row for visibility  
                    st.metric("Total Actual Detection Length", total_detection_length)   
                                
                try:  
                    # Get earliest date from the data  
                    earliest_date = get_earliest_date(df_slug)  
                    st.write(f"🔍 Debug - Earliest date found: '{earliest_date}'")  
                except Exception as e:  
                    st.error(f"Error getting earliest date: {str(e)}")  
                    earliest_date = "January 2024"  # Fallback  
                
                # Process masterslug data  
                top_masterslugs, total_slugs = extract_top_masterslugs(df_slug, top_n=3)
                
                # Auto-extract context from top masterslug  
                if top_masterslugs:  
                    auto_context = top_masterslugs[0]['slug'].replace('-', ' ').title()  
                else:  
                    auto_context = "Content"
                  
                stats_text = format_stats_text(  
                    total_edits, lives_on_air, total_lives,  
                    total_countries, total_detection_length, custom_narrative  
                )  
                slug_viz = create_slug_visualization(top_masterslugs, auto_context, earliest_date)
                  
                # Generate main charts  
                fig_time = generate_time_series_chart(  
                    df_time,  
                    channel_name=channel_names[0] if channel_names else "",  
                    title="Use by Month",  
                    total_detection_length=total_detection_length  
                )
                  
                # Generate country pie chart (only if we have data)  
                if df_country is not None and not df_country.empty and len(df_country.columns) > 0:  
                    country_chart_img = generate_3d_beveled_pie_chart(  
                        df_country,  
                        channel_name=channel_names[0] if channel_names else "",  
                        title="Use by country",  
                        subtitle=date_range  
                    )  
                else:  
                    # Create empty BytesIO if no country data  
                    country_chart_img = BytesIO()  
                    if presentation_type == "Single Channel":  
                        st.warning("⚠️ No country distribution data available")  

                # Generate main charts
                fig_time = generate_time_series_chart(
                    df_time,
                    channel_name=channel_names[0] if channel_names else "",
                    title="Use by Month"
                )
                fig_country = generate_3d_beveled_pie_chart(
                    df_country,
                    channel_name=channel_names[0] if channel_names else "",
                    title="Use by Country",
                    subtitle=date_range
                )
                # Display previews
                st.markdown("---")
                st.header("📊 Chart Previews")
                
                preview_col1, preview_col2 = st.columns(2)
                
                with preview_col1:
                    st.markdown("**Top Left: Time Series**")
                    st.plotly_chart(fig_time, use_container_width=True)
                    
                with preview_col2:  
                    if presentation_type == "Multi-Channel":  
                        st.markdown("**Top Right: Channel Airtime Distribution**")  
                        # Show channel airtime chart  
                        if bottom_left_file:  
                            try:  
                                channel_airtime_preview = generate_channel_airtime_pie(  
                                    df_bottom_left,  
                                    title="Time on air by channel",  
                                    subtitle="Material under 30 days"  
                                )  
                                channel_airtime_preview.seek(0)  
                                st.image(channel_airtime_preview, use_container_width=True)  
                            except:  
                                st.markdown("**Top Right: Country Distribution**")  
                                country_chart_img.seek(0)  
                                st.image(country_chart_img, use_container_width=True)  
                        else:  
                            st.markdown("**Top Right: Country Distribution**")  
                            country_chart_img.seek(0)  
                            st.image(country_chart_img, use_container_width=True)  
                    else:  
                        st.markdown("**Top Right: Country Distribution**")  
                        country_chart_img.seek(0)  
                        st.image(country_chart_img, use_container_width=True)  

                preview_col3, preview_col4 = st.columns(2)
                
                with preview_col3:
                    st.markdown("**Bottom Left: Stats & Narrative**")
                    st.text_area("", value=stats_text, height=250, disabled=True, key="stats_preview")
                    
                with preview_col4:  
                    st.markdown("**Bottom Right: Top Masterslug**")
                    
                    # Orange percentage  
                    st.markdown(f"<h1 style='text-align: center; color: #D97847; margin: 10px 0;'>{slug_viz['percentage']:.0f}%</h1>",   
                            unsafe_allow_html=True)
                    
                    # New text format  
                    earliest_date = slug_viz.get('earliest_date', '2024')  
                    st.markdown(f"<p style='text-align: center; font-size: 14px; color: #666;'>of detections since {earliest_date}<br>about {slug_viz['clean_slug']}</p>",   
                            unsafe_allow_html=True)
                    
                    st.markdown("---")  
                    st.markdown("**Top 3 Masterslugs:**")  
                    for i, slug_data in enumerate(top_masterslugs, 1):  
                        clean = slug_data['slug'].replace('-', ' ').title()  
                        st.markdown(f"{i}. **{clean}**: {slug_data['percentage']:.1f}% "  
                                f"({slug_data['count']:,} detections)")  
                
                # Multi-channel charts
                channel_charts = {}
                if presentation_type == "Multi-Channel" and channel_files:
                    st.markdown("---")
                    st.header("📺 Multi-Channel Analysis")
                    
                    # Load channel data
                    channel_data = {}
                    for ch_name, ch_file in channel_files.items():
                        channel_data[ch_name] = load_data_file(ch_file)
                    
                    # Generate charts (now returns BytesIO images)
                    channel_charts = generate_multi_channel_charts(channel_data)
                    
                    # Display in grid
                    num_cols = min(3, len(channel_charts))
                    cols = st.columns(num_cols)
                    
                    for idx, (ch_name, img_buffer) in enumerate(channel_charts.items()):
                        with cols[idx % num_cols]:
                            img_buffer.seek(0)
                            st.image(img_buffer, caption=ch_name, use_container_width=True)
                
                
                # Generate PowerPoint  
                config = {  
                    'channel_name': channel_names[0] if len(channel_names) == 1 else ', '.join(channel_names),  
                    'channel_names': channel_names,  
                    'date_range': date_range  
                }
                
                if presentation_type == "Single Channel":  
                    ppt_stream = create_single_channel_ppt(  
                        config, fig_time, country_chart_img, stats_text, slug_viz  
                    )  

                # Debug channel airtime  
                if bottom_left_file and presentation_type == "Multi-Channel":  
                    st.write("🔍 Debug - Channel Airtime Data:")  
                    from utils.data_processing import calculate_channel_airtime  
                    df_airtime = calculate_channel_airtime(df_bottom_left, max_age_days=30)  
                    st.dataframe(df_airtime)
                    
                    # Show raw channel names  
                    if 'Channel: Name' in df_bottom_left.columns:  
                        st.write("Unique channels in data:")  
                        st.write(df_bottom_left['Channel: Name'].unique())  

                # Generate PowerPoint
                st.markdown("---")
                st.header("📥 Download Presentation")
                
                with st.spinner("📄 Generating PowerPoint..."):
                    config = {
                        'channel_name': channel_names[0] if len(channel_names) == 1 else ', '.join(channel_names),
                        'channel_names': channel_names,
                        'date_range': date_range
                    }
                    
                    if presentation_type == "Single Channel":
                        ppt_stream = create_single_channel_ppt(
                            config, fig_time, country_chart_img, stats_text, slug_viz  # Changed
                        )
                    else:
                        ppt_stream = create_multi_channel_ppt(
                            config, fig_time, country_chart_img, stats_text, slug_viz, channel_charts, df_bottom_left if bottom_left_file else None 
                        )
                    
                    # Download button
                    filename = f"{'_'.join(channel_names)}_teletrax_report.pptx".replace(' ', '_')
                    
                    st.download_button(
                        label="⬇️ Download PowerPoint Presentation",
                        data=ppt_stream,
                        file_name=filename,
                        mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                        use_container_width=True
                    )
                    
                    st.success("✅ Presentation generated successfully!")
                
            except Exception as e:
                st.error(f"❌ Error processing data: {str(e)}")
                with st.expander("Show error details"):
                    st.exception(e)

# Footer
st.markdown("---")
st.markdown("""
    <div style='text-align: center; color: #666; padding: 20px;'>
        <p>Teletrax Automation Tool v1.0 | Built with Streamlit & Plotly</p>
    </div>
""", unsafe_allow_html=True)