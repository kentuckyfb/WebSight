import requests
import ssl
import OpenSSL
import socket
import pandas as pd
from bs4 import BeautifulSoup
import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import plotly.graph_objs as go
import time
from datetime import datetime

# Function to fetch website speed metrics
def fetch_load_speed(url):
    start_time = time.time()
    response = requests.get(url)
    load_time = time.time() - start_time
    return {
        "status_code": response.status_code,
        "load_time": load_time
    }

# Function to get SSL details
def get_ssl_details(url):
    hostname = url.replace("https://", "").replace("http://", "").split("/")[0]
    context = ssl.create_default_context()
    with socket.create_connection((hostname, 443)) as sock:
        with context.wrap_socket(sock, server_hostname=hostname) as ssock:
            cert = ssock.getpeercert(binary_form=True)
            x509 = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_ASN1, cert)
            issuer = x509.get_issuer().get_components()
            expiry_date = x509.get_notAfter().decode("utf-8")
            issuer = x509.get_issuer().get_components()
            issuer = [str(item) for item in issuer]
            if isinstance(issuer, list):
                # Handle list case (e.g., join list elements)
                issuer = ", ".join(issuer)  # Example: join list elements
            else:
                issuer = issuer.decode('utf-8')
            return {
                "issuer": issuer,
                "expiry_date": expiry_date[:8]
            }
        

        

# Function to parse HTML for SEO metrics
def fetch_seo_metrics(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    title = soup.title.string if soup.title else "No title found"
    meta_description = soup.find("meta", attrs={"name": "description"})
    meta_description = meta_description["content"] if meta_description else "No description found"
    return {
        "title": title,
        "meta_description": meta_description
    }

# Function to fetch server location
def fetch_server_location(url):
    hostname = url.replace("https://", "").replace("http://", "").split("/")[0]
    ip_address = socket.gethostbyname(hostname)
    response = requests.get(f"http://ip-api.com/json/{ip_address}")
    if response.status_code == 200:
        location_data = response.json()
        if location_data["status"] == "success":
            return f"{location_data['city']}, {location_data['country']}"
        else:
            return "Location not found"
    return "API request failed"

# Combine all data into a DataFrame
def collect_data(url):
    speed_metrics = fetch_load_speed(url)
    ssl_details = get_ssl_details(url)
    seo_metrics = fetch_seo_metrics(url)
    server_location = fetch_server_location(url)

    data = {
        "URL": url,
        "Status Code": speed_metrics["status_code"],
        "Load Time (s)": speed_metrics["load_time"],
        "SSL Issuer": ssl_details["issuer"],
        "SSL Expiry": ssl_details["expiry_date"],
        "Title": seo_metrics["title"],
        "Meta Description": seo_metrics["meta_description"],
        "Server Location": server_location,
        "Date Tested": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    return data

    
# Dashboard setup
def create_dashboard():
    app = dash.Dash(__name__)
    app.title = "WebSight: Web Performance Analyzer"
    app.layout = html.Div(
        style={
            "backgroundColor": "#111",  # Darker background
            "color": "#fff",
            "fontFamily": "Roboto, sans-serif",
            "padding": "100px",
            "minHeight": "100vh"  # Set minimum height for full viewport
        },
        children=[
            html.H1(
                "WebSight: Web Performance Analyzer",
                style={
                    "textAlign": "center",
                    "color": "#4A90E2",
                    "fontWeight": "bold",
                    "marginBottom": "20px"  # Add some space below the heading
                }
            ),

            html.Div(
                [
                    dcc.Input(
                        id="url-input",
                        type="text",
                        placeholder="Enter website URL...",
                        style={
                            "width": "70%",
                            "marginRight": "10px",
                            "padding": "10px",
                            "border": "1px solid #444",  # Slightly lighter border
                            "borderRadius": "5px",
                            "backgroundColor": "#333",  # Darker input background
                            "color": "#fff"
                        }
                    ),
                    html.Button(
                        "Run Test",
                        id="run-test-button",
                        style={
                            "padding": "10px",
                            "backgroundColor": "#4A90E2",
                            "color": "#FFFFFF",
                            "border": "none",
                            "borderRadius": "5px",
                            "cursor": "pointer",
                            "fontWeight": "bold"
                        }
                    )
                ],
                style={"textAlign": "center", "marginBottom": "20px"}
            ),

            html.Div(id="results-table", style={"marginBottom": "20px", "overflowX": "auto"}),

            dcc.Graph(id="load-time-graph"),

            html.Button(
                "Export to CSV",
                id="export-button",
                style={
                    "padding": "10px",
                    "backgroundColor": "#50E3C2",
                    "color": "#FFFFFF",
                    "border": "none",
                    "borderRadius": "5px",
                    "cursor": "pointer",
                    "fontWeight": "bold"
                }
            ),

            html.Div(id="export-status", style={"marginTop": "10px", "textAlign": "center", "color": "#4A90E2", "fontWeight": "normal"})
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
             
            # Ensure the int64 is converted to a standard Python type (int)
            df["Status Code"] = df["Status Code"].astype(int).astype(str) 
            df["Load Time (s)"] = df["Load Time (s)"].astype(float)
           

            table = html.Table(
                style={"width": "100%", "border": "1px solid #444", "textAlign": "left", "marginBottom": "20px"},
                children=[
                    html.Thead(
                        html.Tr([html.Th(col, style={"border": "1px solid #444", "padding": "8px", "fontWeight": "bold", "backgroundColor": "#333"}) for col in df.columns])
                    ),
                    html.Tbody([
                        html.Tr([
                            html.Td(df.iloc[i]["URL"], style={"border": "1px solid #444", "padding": "8px"}),
                            html.Td(df.iloc[i]["Status Code"], style={"border": "1px solid #444", "padding": "8px"}),
                            html.Td(df.iloc[i]["Load Time (s)"], style={"border": "1px solid #444", "padding": "8px"}),
                            html.Td(df.iloc[i]["SSL Issuer"], style={"border": "1px solid #444", "padding": "8px"}),
                            html.Td(df.iloc[i]["SSL Expiry"], style={"border": "1px solid #444", "padding": "8px"}),
                            html.Td(df.iloc[i]["Title"], style={"border": "1px solid #444", "padding": "8px"}),
                            html.Td(df.iloc[i]["Meta Description"], style={"border": "1px solid #444", "padding": "8px"}),
                            html.Td(df.iloc[i]["Server Location"], style={"border": "1px solid #444", "padding": "8px"}),
                            html.Td(df.iloc[i]["Date Tested"], style={"border": "1px solid #444", "padding": "8px"}),

                        ]) for i in range(len(df))

                    ])
                ]
            )

            figure = {
                "data": [
                    go.Bar(x=df["URL"], y=df["Load Time (s)"], marker_color="#50E3C2", name="Load Time")
                ],
                "layout": go.Layout(
                    title="WebSight: Web Performance Analyzer",
                    plot_bgcolor="#333",  # Dark background for plot area
                    paper_bgcolor="#222",  # Dark background for the entire plot
                    font={"color": "#fff"},  # White text color
                    xaxis={"title": "URL"},
                    yaxis={"title": "Load Time (s)"}
                )
            }

            return table, figure

        return "", {}

    @app.callback(
        Output("export-status", "children"),
        Input("export-button", "n_clicks")
    )
    def export_to_csv(n_clicks):
        if n_clicks:
            df = pd.DataFrame(data_records)
            df.to_csv(f"website_metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv", index=False)
            return "Data exported to CSV."
        return ""

    return app



# Main execution
if __name__ == "__main__":
    app = create_dashboard()
    app.run_server(debug=True)
