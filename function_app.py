import azure.functions as func
import datetime
import json
import logging

app = func.FunctionApp()

# Handler pour le webhook d'alerte
@app.route(route="AlertHandler", methods=["POST"])
async def alert_handler(req: func.HttpRequest) -> func.HttpResponse:
    try:
        # Récupérer le payload JSON
        data = req.get_json()
    except Exception as e:
        logging.error(f"Erreur de parsing JSON: {e}")
        return func.HttpResponse("Invalid JSON", status_code=400)

    # Extraction des champs
    name = data.get("Name", "")
    custom_dimensions = data.get("customDimensions", {})
    app_version = data.get("application_Version", "")
    cloud_role_instance = data.get("cloud_RoleInstance", "")

    # Mise en forme HTML
    html_content = f"""
    <html>
        <body>
            <h2>Nouvelle alerte App Insights</h2>
            <ul>
                <li><strong>Name:</strong> {name}</li>
                <li><strong>Application Version:</strong> {app_version}</li>
                <li><strong>Cloud Role Instance:</strong> {cloud_role_instance}</li>
                <li><strong>Custom Dimensions:</strong><pre>{json.dumps(custom_dimensions, indent=2, ensure_ascii=False)}</pre></li>
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
        subject="Alerte App Insights",
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