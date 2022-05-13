from dash import Dash, dcc, html, Input, Output
import plotly.express as px
import pandas as pd
import numpy as np
import datetime

external_stylesheets = [
    {
        "href": "https://fonts.googleapis.com/css2?"
                "family=Lato:wght@400;700&display=swap",
        "rel": "stylesheet",
    },
]
app = Dash(__name__, external_stylesheets=external_stylesheets)
app.title = "Police and Accident Hotspots"

log_file_path = 'f12log.csv'
df = pd.read_csv(log_file_path, header = 0, names = ['date', 'lat', 'long'], parse_dates=['date'])
df['time'] = pd.to_datetime(df['date']).dt.time

fig = px.density_mapbox(df, lat='lat', lon='long', radius=10,
                        center=dict(lat=43.68, lon=-79.42), zoom=8,
                        mapbox_style="open-street-map")

my_graph = dcc.Graph(id='heatmap', figure=fig, style={'height': '100vh'})
#Police and Accident Hotspots
app.layout = html.Div(
                children=[
                    html.Div(
                        children=[
                            html.P(children="🚨🚔🚨", className="header-emoji"),
                            html.H1(
                                children="-___-", className="header-title"
                            ),
                            html.P(
                                children="Analyze the behavior de popo",
                                className="header-description",
                            ),
                        ],
                        className="header",
                    ),
                    html.Div(
                        children=[
                            html.Div(children="Time (hour of day)", className="menu-title"),
                            dcc.Dropdown(
                                id="time-filter",
                                options=[
                                    {"label": hour, "value": hour}
                                    for hour in range(0,24)
                                ],
                                value="Year",
                                clearable=False,
                                className="dropdown",
                            )
                        
                        ],
                        className="menu",
                    ),
                    html.Div(
                        my_graph,
                    )
                    
                ]
            )

#THA GARBAGE IS IN THE OUTPUT
@app.callback(
    [Output("heatmap", "plotly.graph_objs._figure.Figure")],
    [Input("time-filter", "value")]
)

def update_map(time):
    start_time = datetime.time(hour=time)
    end_time = datetime.time(hour=time+1)

    mask = ((df.time > start_time) & (df.time < end_time))

    df_filtered = df.loc[mask, :]
    heat_map_figure = px.density_mapbox(df_filtered, lat='lat', lon='long', radius=10,
                        center=dict(lat=43.68, lon=-79.42), zoom=8,
                        mapbox_style="open-street-map")

    return heat_map_figure

if __name__ == '__main__':
    app.run_server(debug=True)