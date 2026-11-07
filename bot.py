import os
import time
import requests
import re
from playwright.sync_api import sync_playwright

# --- CONFIGURATION INTERNE DE L'API MAIL JETABLE ---
def create_temp_email():
    """Génère une adresse email jetable via Mail.tm"""
    try:
        domains_res = requests.get("https://mail.tm").json()
        domain = domains_res["hydra:member"][0]["domain"]
        username = f"botvote{int(time.time())}"
        email = f"{username}@{domain}"
        password = "SuperPassword123!"
        
        account_res = requests.post("https://mail.tm", json={
            "address": email,
            "password": password
        })
        if account_res.status_code == 211:
            token_res = requests.post("https://mail.tm", json={
                "address": email,
                "password": password
            }).json()
            return email, token_res["token"]
    except Exception as e:
        print(f"Erreur Mail.tm : {e}")
    return None, None

def get_verification_code(token):
    """Attend et extrait le code de validation reçu dans la boîte mail"""
    headers = {"Authorization": f"Bearer {token}"}
    print("Attente du mail de confirmation (60 secondes max)...")
    for _ in range(12): # Boucle d'attente de 60 secondes max
        time.sleep(5)
        try:
            messages = requests.get("https://mail.tm", headers=headers).json()["hydra:member"]
            if messages:
                msg_id = messages[0]["id"]
                msg_detail = requests.get(f"https://mail.tm/{msg_id}", headers=headers).json()
                body = msg_detail.get("text", "")
                # Recherche d'une suite de 4 à 8 chiffres dans le texte du mail
                code_match = re.search(r'\b\d{4,8}\b', body)
                if code_match:
                    return code_match.group(0)
        except Exception as e:
            print(f"Erreur de lecture du mail : {e}")
    return None

# --- PROGRAMME PRINCIPAL DE VOTE ---
def executer_vote():
    pseudo_minecraft = "Usagi84" 
    url_site_vote = "https://serveur-prive.net"

    # 1. Génération du mail jetable pour la session
    print("Création d'une boîte mail jetable temporaire...")
    email, mail_token = create_temp_email()
    if not email:
        print("Impossible de créer l'e-mail jetable. Arrêt.")
        return

    print(f"Email temporaire généré : {email}")

    # 2. Automatisation du navigateur avec Playwright
    with sync_playwright() as p:
        print("Lancement du navigateur Chromium masqué...")
        browser = p.chromium.launch(headless=True)
        # Injection d'un profil humain standard pour éviter les blocages de base
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080}
        )
        page = context.new_page()
        
        print(f"Connexion au site : {url_site_vote}")
        page.goto(url_site_vote, wait_until="networkidle")
        time.sleep(5)

        try:
            # Étape 1 : Ouvrir la pop-up de vote
            print("Clic sur le bouton 'Je vote maintenant'...")
            page.get_by_role("link", name="Je vote maintenant").click()
            time.sleep(3)
            
            # Étape 2 : Entrer l'adresse e-mail générée
            print("Saisie de l'adresse e-mail dans le champ de vérification...")
            page.get_by_label("Adresse e-mail *").fill(email)
            
            # Étape 3 : Cliquer sur envoyer pour déclencher le mail
            print("Clic sur le bouton 'Envoyer'...")
            page.get_by_role("button", name="Envoyer").click()
            time.sleep(5)
            
            # Étape 4 : Récupérer le code reçu par l'API
            code_validation = get_verification_code(mail_token)
            if not code_validation:
                print("Erreur : Aucun code de validation reçu par mail.")
                page.screenshot(path="erreur_pas_de_code.png")
                return
            
            print(f"Code reçu trouvé : {code_validation}")
            
            # Étape 5 : Entrer le code dans le formulaire
            print("Saisie du code secret sur le site...")
            page.get_by_label("Code de vérification *").fill(code_validation)
            
            # Étape 6 : Validation finale du vote
            print("Validation finale du vote...")
            page.get_by_role("button", name="Valider").click()
            time.sleep(5)
            
            print("Opération terminée ! Capture d'écran finale de contrôle...")
            page.screenshot(path="confirmation_vote.png")
            
        except Exception as e:
            print(f"Erreur durant l'exécution : {e}")
            page.screenshot(path="erreur_execution.png")
            
        finally:
            browser.close()

if __name__ == "__main__":
    executer_vote()
