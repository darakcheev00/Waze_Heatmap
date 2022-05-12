from dash import Dash, dcc, html, Input, Output
import dash_bootstrap_components as dbc
import plotly.express as px
import pandas as pd

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = Dash(__name__, external_stylesheets=external_stylesheets)

log_file_path = 'f12log.csv'
df = pd.read_csv(log_file_path, header = 0, names = ['date', 'lat', 'long'], parse_dates=['date'])
df = df[["lat","long"]]
fig = px.density_mapbox(df, lat='lat', lon='long', radius=10,
                        center=dict(lat=0, lon=180), zoom=0,
                        mapbox_style="stamen-terrain")

my_graph = dcc.Graph(figure=fig)

app.layout = html.Div([my_graph])

if __name__ == '__main__':
    app.run_server(debug=True)