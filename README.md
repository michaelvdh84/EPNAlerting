# EPNAlerting Function App

This Azure Function App receives alerts from Azure Monitor via a webhook, queries Application Insights for event details, and sends formatted email notifications using SendGrid.

## Features
- Secures the webhook endpoint with a shared token
- Parses Azure Monitor Common Alert Schema payloads
- Queries Application Insights API for KQL results
- Extracts and formats event details (name, customDimensions, machine)
- Sends HTML email notifications via SendGrid

## Prerequisites
- Azure Function App (Python)
- Application Insights resource
- SendGrid account and API key

## Configuration
Set the following environment variables in Azure (Configuration > Application settings):

| Name                | Description                                 |
|---------------------|---------------------------------------------|
| SENDGRID_API_KEY    | SendGrid API key for sending emails         |
| TO_EMAIL            | Recipient email address                     |
| FROM_EMAIL          | Sender email address                        |
| WEBHOOK_TOKEN       | Shared secret for webhook authentication    |
| APPINSIGHTS_APPID   | Application Insights App ID                 |
| APPINSIGHTS_APIKEY  | Application Insights API Key (read access)  |

## Deployment
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Publish to Azure:
   ```bash
   func azure functionapp publish <your-function-app-name>
   ```
3. Configure environment variables in Azure Portal.

## Usage
- Configure an Azure Monitor Action Group to call the webhook:
  ```
  https://<your-app>.azurewebsites.net/api/AlertHandler?code=<function-key>&token=<WEBHOOK_TOKEN>
  ```
- The function will validate the token, query Application Insights, and send an email with event details.

## Example Email Content
```
Event: WebsiteUnreachable
Site: https://www.dontcrybabyyouredead.be/
Reason: No such host is known. (www.dontcrybabyyouredead.be:443)
Machine: WS107972
```

## Troubleshooting
- Check Azure Function logs in the portal (Monitoring > Log stream)
- Ensure all environment variables are set
- Verify SendGrid and Application Insights API keys

## License
MIT
