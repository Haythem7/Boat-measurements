import streamlit as st
import pandas as pd
import plotly.express as px
import random

# Title
st.title("Boat Measures Visualization")

# Load data
df = pd.read_excel("cleaned_dataset.xlsx")
df.columns = df.columns.str.strip()  # Remove leading/trailing spaces
df["DATE"] = pd.to_datetime(df["DATE"])

# Extract unique station coordinates
station_coords = df.groupby("NEW_ NAME")[["LATITUDE", "LONGITUDE"]].first().reset_index()

# Parameter options
param_options = ["SECCHI", "T(°C)", "SpCOND(uS/cm)", "ODO(mg/l)", "TOTAL_CHLO(ug/l)", "PROBE_PH", "Turbidity (NTU)"]
selected_param = st.selectbox("Choose a parameter to visualize", param_options)

# Station selection
station_names = df["NEW_ NAME"].unique()
selected_station = st.selectbox("Choose a station", station_names)

# Get selected station coordinates
selected_coords = station_coords[station_coords["NEW_ NAME"] == selected_station].iloc[0]

# Map with highlighted selected station
fig_map = px.scatter_mapbox(
    station_coords,
    lat="LATITUDE",
    lon="LONGITUDE",
    hover_name="NEW_ NAME",
    zoom=5,
    height=500,
    color_discrete_sequence=["blue"]
)

# Highlight selected station in red
fig_map.add_trace(px.scatter_mapbox(
    pd.DataFrame([selected_coords]),
    lat="LATITUDE",
    lon="LONGITUDE",
    hover_name="NEW_ NAME",
    color_discrete_sequence=["red"],
    zoom=10
).data[0])

# Zoom on the selected station
fig_map.update_layout(
    mapbox_style="open-street-map",
    mapbox_zoom=10,
    mapbox_center={"lat": selected_coords["LATITUDE"], "lon": selected_coords["LONGITUDE"]},
    margin={"r":0, "t":0, "l":0, "b":0}
)

st.plotly_chart(fig_map)

# Filter data for selected station
station_df = df[df["NEW_ NAME"] == selected_station]

# Select 6 random unique dates
unique_dates = station_df["DATE"].dropna().unique()
if len(unique_dates) < 6:
    st.warning("Not enough dates to select 6. Showing all available dates.")
    selected_dates = unique_dates
else:
    selected_dates = sorted(random.sample(list(unique_dates), 6))

# Filter data for selected dates only
plot_df = station_df[station_df["DATE"].isin(selected_dates)].copy()
plot_df = plot_df.sort_values("DATE")

# Plot line chart
fig_line = px.line(
    plot_df,
    x="DATE",
    y=selected_param,
    markers=True,
    title=f"{selected_param} over selected dates for {selected_station}"
)

# Add TOTAL_DEPTH under each point
for i, row in plot_df.iterrows():
    fig_line.add_annotation(
        x=row["DATE"],
        y=row[selected_param],
        text=f"{row['TOTAL_DEPTH']} m",
        showarrow=False,
        yshift=-30,
        font=dict(size=9, color="gray")
    )

st.plotly_chart(fig_line)
