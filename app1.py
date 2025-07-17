import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# Title
st.title("Boat Measures Visualization")

# Load data
df = pd.read_excel("dataset_janauaca_20210715_OneSpreadsheet.xlsx")
df.columns = df.columns.str.strip()
df["DATE"] = pd.to_datetime(df["DATE"])
df["TIME_STR"] = df["TIME"].astype(str)  # Convert TIME to string

# Grouped parameters
parameter_groups = {
    "WaterQuality": [
        "SECCHI", "T(°C)", "SpCOND(uS/cm)", "ODO%", "ODO(mg/l)", "PROBE_CHLO-a(ug/l)",
        "N-NO3+N-NO2(uM)", "N-NO2 (uM)", "No2(mg/l)", "N-NO3corr(uM)", "N03(mg/l)",
        "P-PO4(uM)", "PO4(mg/l)", "Si-SiO4(uM)", "SiO4(mg/l)", "N-DIN (mgN/l )",
        "Ntot(uM)", "Ptot(uM)"
    ],
    "Hydrodynamics": [
        "BottomElevation_Buf50(m)", "SimWaterDepth_Buf50(m)", "SimVelU_Buf50(m.s-1)",
        "SimVelV_Buf50(m.s-1)", "SimVelMag_Buf50(m.s-1)", "SimVelDir_Buf50(Deg)",
        "EffFetch_24h(m)", "WaveFromEffFetch(m)", "FroudeNumber", "ReynoldNumber",
        "ResidenceTime_24h(s)", "SimplifiedResidenceTimek_24h(s)"
    ],
    "Hydro-model": [
        "Water Level (m)", "Volume (m3)", "Surface (m2)", "channel %", "upland %",
        "attz%", "rain %", "seepage %", "v_init %"
    ],
    "Weather": [
        "CumRainTrmm24h_1Day(mm)", "AirTemp_1Day(°)", "CumEvap1h_1Day(mm)",
        "SolarRad_1Day(W/m2)", "RelHum_1Day(%)", "AirPressure_1Day(kPa)"
    ]
}

# Station coordinates
station_coords = df.groupby("NEW_ NAME")[["LATITUDE", "LONGITUDE"]].first().reset_index()

# Station selection
station_names = df["NEW_ NAME"].unique()
selected_station = st.selectbox("Choose a station", station_names)

# Parameter selection
selected_group = st.selectbox("Choose parameter group", list(parameter_groups.keys()))
selected_param = st.selectbox("Choose a parameter", parameter_groups[selected_group])

# Coordinates for selected station
selected_coords = station_coords[station_coords["NEW_ NAME"] == selected_station].iloc[0]

# Map
fig_map = px.scatter_mapbox(
    station_coords,
    lat="LATITUDE",
    lon="LONGITUDE",
    hover_name="NEW_ NAME",
    zoom=5,
    height=500,
    color_discrete_sequence=["blue"]
)

fig_map.add_trace(px.scatter_mapbox(
    pd.DataFrame([selected_coords]),
    lat="LATITUDE",
    lon="LONGITUDE",
    hover_name="NEW_ NAME",
    color_discrete_sequence=["red"],
    zoom=10
).data[0])

fig_map.update_layout(
    mapbox_style="open-street-map",
    mapbox_zoom=10,
    mapbox_center={"lat": selected_coords["LATITUDE"], "lon": selected_coords["LONGITUDE"]},
    margin={"r": 0, "t": 0, "l": 0, "b": 0}
)

st.plotly_chart(fig_map)

# Filter data
station_df = df[df["NEW_ NAME"] == selected_station].copy()
valid_df = station_df[station_df[selected_param].notna()].copy()

# Group by month-year
valid_df["MONTH_YEAR"] = valid_df["DATE"].dt.to_period("M")
grouped = valid_df.groupby("MONTH_YEAR")
one_date_per_month = grouped.apply(lambda g: g.sample(1)).reset_index(drop=True)

# Select up to 10 unique dates (or fewer if not enough)
selected_dates = one_date_per_month["DATE"].sort_values().unique()
if len(selected_dates) > 10:
    selected_dates = pd.Series(selected_dates).sample(10).sort_values()

# Store selected dates in session state
state_key = f"{selected_station}_{selected_param}"
if state_key not in st.session_state:
    st.session_state[state_key] = selected_dates
selected_dates = st.session_state[state_key]

# Filter for selected dates
selected_dates_df = valid_df[valid_df["DATE"].isin(selected_dates)].copy()
selected_dates_df["DATE_STR"] = selected_dates_df["DATE"].dt.strftime("%Y-%m-%d")

# Fix repeated times: for each date, adjust duplicates by adding 1 minute
def adjust_duplicate_times(group):
    seen = {}
    new_times = []
    for t in group["TIME_STR"]:
        try:
            parsed_time = datetime.strptime(t, "%H:%M:%S")
        except:
            try:
                parsed_time = datetime.strptime(t, "%H:%M")
            except:
                parsed_time = datetime.strptime("00:00", "%H:%M")  # fallback if bad format

        key = parsed_time.strftime("%H:%M")
        count = seen.get(key, 0)
        adjusted_time = parsed_time + timedelta(minutes=count)
        seen[key] = count + 1
        new_times.append(adjusted_time.strftime("%H:%M"))

    return pd.Series(new_times, index=group.index)

# Apply to each date group
selected_dates_df["ADJUSTED_TIME"] = selected_dates_df.groupby("DATE_STR").apply(adjust_duplicate_times).reset_index(level=0, drop=True)

# Build annotation text per date with HTML <br> for line breaks
time_labels = selected_dates_df.groupby("DATE_STR")["ADJUSTED_TIME"].apply(
    lambda times: "<br>".join(sorted(times.dropna()))
)

# Plot scatter
fig_scatter = px.scatter(
    selected_dates_df,
    x="DATE_STR",
    y=selected_param,
    color="DATE_STR",
    labels={"DATE_STR": "Date"},
    hover_data={
        selected_param: True,
        "SAMPLE_DEPTH": True
    },
    title=f"{selected_param} values on selected dates at {selected_station}"
)

# Update layout
fig_scatter.update_layout(
    xaxis_title="Date",
    yaxis_title=selected_param,
    xaxis=dict(
        tickmode="array",
        tickvals=sorted(selected_dates_df["DATE_STR"].unique()),
        ticktext=sorted(selected_dates_df["DATE_STR"].unique())
    )
)

# Change to X marks
fig_scatter.update_traces(marker=dict(symbol="x", size=10))

# Compute y position for annotations (a bit below min Y)
y_min = selected_dates_df[selected_param].min()
y_annot = y_min - 0.05 * abs(y_min) if y_min != 0 else -1

# Add annotation per date
for date_str in sorted(selected_dates_df["DATE_STR"].unique()):
    times = time_labels.get(date_str, "")
    if times:
        fig_scatter.add_annotation(
            x=date_str,
            y=y_annot,
            text=times,
            showarrow=False,
            font=dict(size=10, color="black"),
            align="center",
            yshift=-10
        )

st.plotly_chart(fig_scatter)
