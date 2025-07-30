import azure.functions as func
import datetime
import json
import logging

app = func.FunctionApp()
logging.info

# Handler pour le webhook d'alerte
@app.route(route="AlertHandler", methods=["POST"])
async def alert_handler(req: func.HttpRequest) -> func.HttpResponse:
    # Vérification du token secret transmis en paramètre d'URL
    import os
    expected_token = os.environ.get("WEBHOOK_TOKEN")
    received_token = req.params.get("token")

    if not expected_token or received_token != expected_token:
        logging.warning("Tentative d'accès non autorisée au Webhook.")
        return func.HttpResponse("Unauthorized", status_code=401)
        
    try:
        # Récupérer le payload JSON
        data = req.get_json()
        logging.info(f"Payload brut reçu: {data}")
    except Exception as e:
        logging.error(f"Erreur de parsing JSON: {e}")
        return func.HttpResponse("Invalid JSON", status_code=400)

    # Extraction adaptée au schéma commun
    essentials = data.get("data", {}).get("essentials", {})
    condition = data.get("data", {}).get("alertContext", {}).get("condition", {})
    all_of = condition.get("allOf", [{}])[0]

    name = essentials.get("alertRule", "")
    description = essentials.get("description", "")
    severity = essentials.get("severity", "")
    search_query = all_of.get("searchQuery", "")
    link_to_results = all_of.get("linkToSearchResultsUI", "")
    window_start = condition.get("windowStartTime", "")
    window_end = condition.get("windowEndTime", "")

    # Interrogation de l'API Application Insights pour récupérer les résultats KQL
    import os
    import requests
    APPINSIGHTS_APPID = os.environ.get("APPINSIGHTS_APPID")
    APPINSIGHTS_APIKEY = os.environ.get("APPINSIGHTS_APIKEY")


    extracted_events = []
    if APPINSIGHTS_APPID and APPINSIGHTS_APIKEY and search_query:
        url = f"https://api.applicationinsights.io/v1/apps/{APPINSIGHTS_APPID}/query"
        headers = {"x-api-key": APPINSIGHTS_APIKEY}
        params = {"query": search_query}
        try:
            resp = requests.get(url, headers=headers, params=params)
            if resp.status_code == 200:
                kql_json = resp.json()
                tables = kql_json.get("tables", [])
                if tables:
                    columns = tables[0].get("columns", [])
                    rows = tables[0].get("rows", [])
                    idx_name = next((i for i, c in enumerate(columns) if c["name"] == "name"), None)
                    idx_customDimensions = next((i for i, c in enumerate(columns) if c["name"] == "customDimensions"), None)
                    idx_machine = next((i for i, c in enumerate(columns) if c["name"] == "cloud_RoleInstance"), None)
                    for row in rows:
                        event_name = row[idx_name] if idx_name is not None else ""
                        custom_dimensions = row[idx_customDimensions] if idx_customDimensions is not None else ""
                        machine_name = row[idx_machine] if idx_machine is not None else ""
                        try:
                            custom_dimensions_dict = json.loads(custom_dimensions)
                        except Exception:
                            custom_dimensions_dict = {}
                        # Format général
                        custom_dim_html = "<br>".join([f"{k}: {v}" for k, v in custom_dimensions_dict.items()])
                        extracted_events.append(f"<b>{event_name}</b><br>{custom_dim_html}<br>Machine: {machine_name}")
                else:
                    extracted_events.append("Aucun résultat KQL.")
            else:
                extracted_events.append(f"Erreur API AppInsights: {resp.status_code} {resp.text}")
        except Exception as e:
            extracted_events.append(f"Exception API AppInsights: {str(e)}")
    else:
        extracted_events.append("API AppInsights non configurée ou requête KQL absente.")

    events_html = "<br><br>".join(extracted_events)

    # Mise en forme HTML enrichie avec les événements extraits
    html_content = f"""
    <html>
        <body>
            <h2>EPNMonitoring Alert</h2>
            <ul>
                <li><strong>Rule Name :</strong> {name}</li><br>
                <li><strong>Description :</strong> {description}</li><br>
                <li><strong>Time Window:</strong> {window_start} - {window_end}</li><br>
                <li><strong>Events :</strong><br><br>{events_html}</li><br>
                <li><strong>KQL Query:</strong><pre>{search_query}</pre></li>
            </ul>
        </body>
    </html>
    """

    # Envoi de l'email via SendGrid
    import os
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail

    SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY")
    TO_EMAIL = os.environ.get("TO_EMAIL")  # à définir dans les settings Azure
    FROM_EMAIL = os.environ.get("FROM_EMAIL", TO_EMAIL)

    if not SENDGRID_API_KEY or not TO_EMAIL:
        logging.error("SENDGRID_API_KEY ou TO_EMAIL non défini dans les variables d'environnement.")
        return func.HttpResponse("Configuration SendGrid manquante.", status_code=500)

    message = Mail(
        from_email=FROM_EMAIL,
        to_emails=TO_EMAIL,
        subject="EPNMonitoring Alert",
        html_content=html_content
    )

    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        logging.info(f"Email envoyé: {response.status_code}")
    except Exception as e:
        logging.error(f"Erreur d'envoi email: {e}")
        # Affiche le détail de l'erreur dans la réponse HTTP
        return func.HttpResponse(f"Erreur d'envoi email: {str(e)}", status_code=500)

    return func.HttpResponse("Alerte traitée et email envoyé.", status_code=200)