import os
import requests

API_KEY = os.environ["MISTRAL_API_KEY"]

# URL pour récupérer les modèles
url = "https://api.mistral.ai/v1/models"

# En-têtes HTTP
headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# Requête GET pour obtenir les modèles
try:
    response = requests.get(url, headers=headers)
    response.raise_for_status()

    print("✅ Liste des modèles disponibles :")
    print(response.json())

except requests.exceptions.RequestException as e:
    print("❌ Erreur lors de la récupération des modèles :")
    print(e)
