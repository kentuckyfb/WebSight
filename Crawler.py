import requests
import ssl
import OpenSSL
import socket
import pandas as pd
from bs4 import BeautifulSoup
import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output, State
import plotly.graph_objs as go
import time
from datetime import datetime
from dash_iconify import DashIconify

# Glassmorphism style
GLASS_STYLE = {
    "background": "rgba(0, 50, 0, 0.2)",  # Darker green tint
    "boxShadow": "0 8px 32px rgba(0, 0, 0, 0.37)",
    "backdropFilter": "blur(10px)",
    "borderRadius": "20px",
    "border": "1px solid rgba(255, 255, 255, 0.2)",
    "padding": "20px",
    "margin": "20px",
}

# Function to fetch website speed metrics
def fetch_load_speed(url):
    start_time = time.time()
    response = requests.get(url)
    load_time = time.time() - start_time
    return {"status_code": response.status_code, "load_time": load_time}

# Function to get SSL details
def get_ssl_details(url):
    hostname = url.replace("https://", "").replace("http://", "").split("/")[0]
    context = ssl.create_default_context()
    with socket.create_connection((hostname, 443)) as sock:
        with context.wrap_socket(sock, server_hostname=hostname) as ssock:
            cert = ssock.getpeercert(binary_form=True)
            x509 = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_ASN1, cert)
            return {"issuer": x509.get_issuer().CN, "expiry_date": x509.get_notAfter().decode("utf-8")[:8]}

# Function to parse HTML for SEO metrics
def fetch_seo_metrics(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    title = soup.title.string if soup.title else "No title"
    meta_description = soup.find("meta", attrs={"name": "description"})
    return {"title": title, "meta_description": meta_description["content"] if meta_description else "No description"}

# Function to fetch server location
def fetch_server_location(url):
    hostname = url.replace("https://", "").replace("http://", "").split("/")[0]
    ip_address = socket.gethostbyname(hostname)
    response = requests.get(f"http://ip-api.com/json/{ip_address}")
    if response.status_code == 200:
        location_data = response.json()
        return f"{location_data.get('city', 'Unknown')}, {location_data.get('country', 'Unknown')}"
    return "Location not found"

# Collect website data
def collect_data(url):
    return {
        **fetch_load_speed(url),
        **get_ssl_details(url),
        **fetch_seo_metrics(url),
        "server_location": fetch_server_location(url),
        "url": url,
        "date_tested": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

# Dashboard setup
def create_dashboard():
    app = dash.Dash(__name__, external_stylesheets=["https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css"])
    app.title = "WebSight: Performance Analyzer"
    app.index_string = """
    <!DOCTYPE html>
    <html>
        <head>
            {%metas%}
            <title>{%title%}</title>
            {%favicon%}
            {%css%}
            <style>
                body {
                    margin: 0;
                    padding: 0;
                }
            </style>
        </head>
        <body>
            {%app_entry%}
            <footer>{%config%}{%scripts%}{%renderer%}</footer>
        </body>
    </html>
    """
    app.layout = html.Div(
        style={"backgroundColor": "#121212", "color": "#E0E0E0", "fontFamily": "'Roboto', sans-serif", "padding": "20px", "textAlign": "center"},
        children=[
            html.H1("WebSight", style={"color": "#4CAF50", "fontWeight": "bold"}),

            html.Div(
                [
                    dcc.Input(
                        id="url-input",
                        type="text",
                        placeholder=" Enter website URL...",
                        style={"width": "50%", "padding": "12px", "border": "1px solid #444", "borderRadius": "5px", "backgroundColor": "#1E1E1E", "color": "#E0E0E0"}
                    ),
                    html.Button(
                        [
                            DashIconify(icon="carbon:play", width=24),
                            ""
                        ],
                        id="run-test-button",
                        style={"marginLeft": "10px", "padding": "8px 8px", "backgroundColor": "#4CAF50", "border": "none", "color": "#FFF", "borderRadius": "5px", "cursor": "pointer", "height": "40px","width": "40px"},
                    ),
                ],
                style=GLASS_STYLE,  # Apply glassmorphism to input section
            ),

            html.Div(id="results-table", style={"marginTop": "20px"}),

            dcc.Graph(id="load-time-graph", style=GLASS_STYLE),  # Apply glassmorphism to graph

            html.Button(
                [
                    DashIconify(icon="mdi:file-export-outline", width=24),
                    ""
                ],
                id="export-button",
                style={"marginTop": "20px", "padding": "8px 15px", "backgroundColor": "#2196F3", "border": "none", "color": "#FFF", "borderRadius": "5px", "cursor": "pointer"},
            ),

            html.Div(id="export-status", style={"marginTop": "10px", "color": "#4CAF50"})
        ]
    )

    data_records = []

    @app.callback(
        [Output("results-table", "children"), Output("load-time-graph", "figure")],
        [Input("run-test-button", "n_clicks")],
        [State("url-input", "value")]
    )
    def update_results(n_clicks, url):
        if n_clicks and url:
            data = collect_data(url)
            data_records.append(data)
            df = pd.DataFrame(data_records)
            return (
                dash_table.DataTable(
                    columns=[{"name": col, "id": col} for col in df.columns],
                    data=df.to_dict("records"),
                    style_table={"border": "1px solid #444"},
                    style_header={"backgroundColor": "#333", "color": "#FFF"},
                    style_cell={"backgroundColor": "#1E1E1E", "color": "#FFF", "border": "1px solid #444"},
                ),
                go.Figure(
                    [go.Bar(x=df["url"], y=df["load_time"], marker_color="#4CAF50")],
                    layout=go.Layout(
                        title="Load Time by URL",
                        plot_bgcolor="#121212",
                        paper_bgcolor="#121212",
                        font={"color": "#FFF"},
                        xaxis_title="URL",
                        yaxis_title="Load Time (s)",
                    ),
                ),
            )
        return "", {}

    @app.callback(Output("export-status", "children"), Input("export-button", "n_clicks"))
    def export_to_csv(n_clicks):
        if n_clicks and data_records:
            pd.DataFrame(data_records).to_csv(f"website_metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv", index=False)
            return "Data exported to CSV."
        return ""

    return app

if __name__ == "__main__":
    create_dashboard().run_server(debug=True)
