# Delphos X Automation

Publica tweets en @DelphosInnova via GitHub Actions.

## Secrets necesarios

En GitHub → Settings → Secrets → Actions:
- `X_AUTH_TOKEN` — cookie auth_token de x.com
- `X_CT0` — cookie ct0 de x.com

## Cómo lo llama n8n

```
POST https://api.github.com/repos/alvaroruiz152-gif/delphos-x-automation/dispatches
Authorization: Bearer GITHUB_TOKEN
{
  "event_type": "post_tweet",
  "client_payload": {
    "text": "El tweet a publicar",
    "reply_to": null,
    "action": "tweet"
  }
}
```
