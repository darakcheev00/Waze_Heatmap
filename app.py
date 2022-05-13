from dash import Dash, dcc, html, Input, Output
import plotly.express as px
import pandas as pd

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
df = df[["lat","long"]]

fig = px.density_mapbox(df, lat='lat', lon='long', radius=10,
                        center=dict(lat=43.68, lon=-79.42), zoom=8,
                        mapbox_style="open-street-map")

my_graph = dcc.Graph(figure=fig, style={'height': '100vh'})
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


# @app.callback(
#     [Output("price-chart", "figure")],
#     [Input("time-filter", "value")],
# )

if __name__ == '__main__':
    app.run_server(debug=True)