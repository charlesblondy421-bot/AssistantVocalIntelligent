"""
Assistant Vocal Intelligent
Version Professionnelle - Optimisée
"""
import webbrowser
import pyttsx3
import speech_recognition as sr
import threading
import customtkinter as ctk
import urllib.parse
from dataclasses import dataclass
from typing import Dict, Tuple, Callable, Optional, List
import logging
from enum import Enum
from datetime import datetime
import sys
import os

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('assistant_vocal.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Constantes
class Sites(Enum):
    """Sites web supportés par l'assistant"""
    YOUTUBE = "YouTube"
    WHATSAPP = "WhatsApp"
    TIKTOK = "TikTok"
    FACEBOOK = "Facebook"
    GOOGLE = "Google"
    GITHUB = "GitHub"

URLS = {
    Sites.YOUTUBE: "https://www.youtube.com",
    Sites.WHATSAPP: "https://web.whatsapp.com",
    Sites.TIKTOK: "https://www.tiktok.com",
    Sites.FACEBOOK: "https://www.facebook.com",
    Sites.GOOGLE: "https://www.google.com",
    Sites.GITHUB: "https://github.com"
}

MOTEUR_RECHERCHE = "https://www.google.com/search?q="

@dataclass
class Commande:
    """Représente une commande vocale"""
    action: Optional[Callable]
    description: str
    mots_cles: Tuple[str, ...]
    categorie: str = "general"

class ModeApparence(Enum):
    """Modes d'apparence de l'interface"""
    SOMBRE = "dark"
    CLAIR = "light"
    SYSTEME = "system"

class AssistantVocalApp:
    """Application principale de l'assistant vocal"""

    def __init__(self):
        """Initialise l'application avec toutes les configurations"""
        self._initialiser_parametres()
        self._configurer_interface()
        self._initialiser_moteur_vocal()
        self._initialiser_variables_etat()
        self._creer_widgets()
        self._demarrer_assistant()

    def _initialiser_parametres(self):
        """Initialise les paramètres de l'application"""
        self.mode_apparence = ModeApparence.SOMBRE
        self.langue = "fr-FR"
        self.vitesse_parole = 170
        self.volume_parole = 0.9

    def _configurer_interface(self):
        """Configure l'interface graphique"""
        ctk.set_appearance_mode(self.mode_apparence.value)
        ctk.set_default_color_theme("blue")

        self.root = ctk.CTk()
        self.root.title("DonCharlesAssistant")
        self.root.geometry("800x600")
        self.root.resizable(False, False)

        # Protection contre la fermeture brusque
        self.root.protocol("WM_DELETE_WINDOW", self.quitter)

        # Centre la fenêtre
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')

    def _initialiser_moteur_vocal(self):
        """Initialise et configure le moteur de synthèse vocale"""
        try:
            self.engine = pyttsx3.init()

            # Configuration des propriétés
            self.engine.setProperty('rate', self.vitesse_parole)
            self.engine.setProperty('volume', self.volume_parole)

            # Chercher une voix appropriée
            self._configurer_voix()

            logger.info("Moteur vocal initialisé avec succès")

        except Exception as e:
            logger.error(f"Erreur d'initialisation du moteur vocal: {e}")
            # Créer un moteur factice pour éviter les crashs
            self.engine = type('obj', (object,), {
                'say': lambda x: print(f"TTS: {x}"),
                'runAndWait': lambda: None,
                'setProperty': lambda x, y: None
            })()

    def _configurer_voix(self):
        """Configure la voix de synthèse"""
        try:
            voices = self.engine.getProperty('voices')

            # Priorité 1: Voix française
            french_voices = [
                v for v in voices
                if any(fr_indicator in v.name.lower() for fr_indicator in ['fr', 'french', 'français'])
            ]

            if french_voices:
                self.engine.setProperty('voice', french_voices[0].id)
                logger.info(f"Voix française sélectionnée: {french_voices[0].name}")
                return

            # Priorité 2: Voix anglaise féminine
            female_voices = [
                v for v in voices
                if 'female' in v.name.lower() or 'zira' in v.name.lower()
            ]

            if female_voices:
                self.engine.setProperty('voice', female_voices[0].id)
                logger.info(f"Voix féminine sélectionnée: {female_voices[0].name}")
                return

            # Priorité 3: Première voix disponible
            if voices:
                self.engine.setProperty('voice', voices[0].id)
                logger.info(f"Voix par défaut sélectionnée: {voices[0].name}")

        except Exception as e:
            logger.warning(f"Configuration de voix échouée: {e}")

    def _initialiser_variables_etat(self):
        """Initialise les variables d'état de l'application"""
        self.ecoute_active = False
        self.thread_ecoute = None
        self.reconnaissance_active = True
        self.commandes_executees = []

        # Initialisation des commandes
        self._initialiser_commandes()

    def _initialiser_commandes(self):
        """Initialise le dictionnaire des commandes"""
        self.commandes = {
            Sites.YOUTUBE: Commande(
                action=lambda: self._ouvrir_site(Sites.YOUTUBE),
                description="Ouverture de YouTube",
                mots_cles=("youtube", "ouverture youtube", "ouvre youtube", "lance youtube"),
                categorie="sites"
            ),
            Sites.WHATSAPP: Commande(
                action=lambda: self._ouvrir_site(Sites.WHATSAPP),
                description="Ouverture de WhatsApp Web",
                mots_cles=("whatsapp", "ouvrir whatsapp", "whatsapp web", "lance whatsapp"),
                categorie="sites"
            ),
            Sites.TIKTOK: Commande(
                action=lambda: self._ouvrir_site(Sites.TIKTOK),
                description="Ouverture de TikTok",
                mots_cles=("tiktok", "ouvre tiktok", "tiktok.com", "lance tiktok"),
                categorie="sites"
            ),
            Sites.FACEBOOK: Commande(
                action=lambda: self._ouvrir_site(Sites.FACEBOOK),
                description="Ouverture de Facebook",
                mots_cles=("facebook", "ouvre facebook", "fb", "lance facebook"),
                categorie="sites"
            ),
            Sites.GOOGLE: Commande(
                action=lambda: self._ouvrir_site(Sites.GOOGLE),
                description="Ouverture de Google",
                mots_cles=("google", "ouvre google", "lance google"),
                categorie="sites"
            ),
            Sites.GITHUB: Commande(
                action=lambda: self._ouvrir_site(Sites.GITHUB),
                description="Ouverture de GitHub",
                mots_cles=("github", "ouvre github", "git hub", "lance github"),
                categorie="sites"
            ),
            "recherche": Commande(
                action=None,
                description="Recherche sur internet",
                mots_cles=("rechercher", "chercher", "trouve", "search", "recherche", "cherche"),
                categorie="recherche"
            ),
            "quitter": Commande(
                action=lambda: self.root.after(100, self.quitter),
                description="Fermeture de l'application",
                mots_cles=("quitter", "arrêter", "stop", "ferme", "au revoir", "exit", "quitte"),
                categorie="systeme"
            ),
            "aide": Commande(
                action=lambda: self._afficher_aide(),
                description="Affiche l'aide",
                mots_cles=("aide", "help", "commandes", "que peux-tu faire", "comment utiliser"),
                categorie="systeme"
            )
        }

    def _creer_widgets(self):
        """Crée tous les widgets de l'interface"""
        # Configuration du grid principal
        self.root.grid_columnconfigure(0, weight=1)

        self._creer_en_tete()
        self._creer_panel_sites()
        self._creer_panel_recherche()
        self._creer_panel_controle()
        self._creer_console_statut()
        self._creer_pied_page()

    def _creer_en_tete(self):
        """Crée l'en-tête de l'application"""
        frame_titre = ctk.CTkFrame(self.root, corner_radius=10)
        frame_titre.grid(row=0, column=0, padx=15, pady=(15, 5), sticky="ew")
        frame_titre.grid_columnconfigure(0, weight=1)

        titre = ctk.CTkLabel(
            frame_titre,
            text="🎙️ Assistant Vocal Intelligent",
            font=("Arial", 26, "bold")
        )
        titre.grid(row=0, column=0, pady=15)

        sous_titre = ctk.CTkLabel(
            frame_titre,
            text="Contrôle vocal de votre navigation web",
            font=("Arial", 14),
            text_color="gray"
        )
        sous_titre.grid(row=1, column=0, pady=(0, 10))

    def _creer_panel_sites(self):
        """Crée le panel des sites rapides"""
        frame_sites = ctk.CTkFrame(self.root, corner_radius=10)
        frame_sites.grid(row=1, column=0, padx=15, pady=5, sticky="ew")

        label_sites = ctk.CTkLabel(
            frame_sites,
            text="📋 Sites Rapides",
            font=("Arial", 16, "bold")
        )
        label_sites.pack(pady=(10, 5))

        # Grille de boutons pour les sites
        frame_boutons = ctk.CTkFrame(frame_sites)
        frame_boutons.pack(pady=10, padx=10)

        sites_a_afficher = [
            (Sites.YOUTUBE, "🔴 YouTube", "#FF0000"),
            (Sites.WHATSAPP, "🟢 WhatsApp", "#25D366"),
            (Sites.TIKTOK, "⚫ TikTok", "#000000"),
            (Sites.FACEBOOK, "🔵 Facebook", "#1877F2"),
            (Sites.GOOGLE, "🔶 Google", "#4285F4"),
            (Sites.GITHUB, "📊 GitHub", "#333333")
        ]

        for i, (site, texte, couleur) in enumerate(sites_a_afficher):
            row = i // 3
            col = i % 3

            btn = ctk.CTkButton(
                frame_boutons,
                text=texte,
                command=lambda s=site: self._ouvrir_site(s),
                width=140,
                height=40,
                font=("Arial", 12),
                fg_color=couleur,
                hover_color=self._eclaircir_couleur(couleur),
                corner_radius=8
            )
            btn.grid(row=row, column=col, padx=8, pady=8)

    def _creer_panel_recherche(self):
        """Crée le panel de recherche"""
        frame_recherche = ctk.CTkFrame(self.root, corner_radius=10)
        frame_recherche.grid(row=2, column=0, padx=15, pady=5, sticky="ew")

        label_recherche = ctk.CTkLabel(
            frame_recherche,
            text="🔍 Recherche Web",
            font=("Arial", 16, "bold")
        )
        label_recherche.pack(pady=(10, 5))

        # Champ de recherche avec bouton
        self.entry_recherche = ctk.CTkEntry(
            frame_recherche,
            width=450,
            height=45,
            placeholder_text="Entrez votre recherche ou dites 'Rechercher [mot-clé]'...",
            font=("Arial", 13),
            corner_radius=10
        )
        self.entry_recherche.pack(pady=10, padx=20)
        self.entry_recherche.bind('<Return>', lambda e: self._effectuer_recherche())

        btn_frame = ctk.CTkFrame(frame_recherche, fg_color="transparent")
        btn_frame.pack(pady=(0, 10))

        btn_rechercher = ctk.CTkButton(
            btn_frame,
            text="🔎 Lancer la recherche",
            command=self._effectuer_recherche,
            width=200,
            height=40,
            font=("Arial", 13, "bold"),
            corner_radius=10
        )
        btn_rechercher.pack(side="left", padx=5)

        btn_effacer = ctk.CTkButton(
            btn_frame,
            text="🗑️ Effacer",
            command=lambda: self.entry_recherche.delete(0, 'end'),
            width=100,
            height=40,
            font=("Arial", 12),
            fg_color="gray",
            hover_color="dark gray",
            corner_radius=10
        )
        btn_effacer.pack(side="left", padx=5)

    def _creer_panel_controle(self):
        """Crée le panel de contrôle vocal"""
        frame_controle = ctk.CTkFrame(self.root, corner_radius=10)
        frame_controle.grid(row=3, column=0, padx=15, pady=5, sticky="ew")

        self.btn_ecouter = ctk.CTkButton(
            frame_controle,
            text="🎤 Démarrer l'écoute vocale",
            command=self._toggle_ecoute,
            width=280,
            height=50,
            font=("Arial", 15, "bold"),
            corner_radius=12
        )
        self.btn_ecouter.pack(pady=15)

        # Indicateur d'activité
        self.label_indicateur = ctk.CTkLabel(
            frame_controle,
            text="● Écoute inactive",
            text_color="gray",
            font=("Arial", 12)
        )
        self.label_indicateur.pack(pady=(0, 10))

    def _creer_console_statut(self):
        """Crée la console de statut"""
        frame_console = ctk.CTkFrame(self.root, corner_radius=10)
        frame_console.grid(row=4, column=0, padx=15, pady=5, sticky="nsew")

        # Configuration pour l'expansion
        self.root.grid_rowconfigure(4, weight=1)
        frame_console.grid_columnconfigure(0, weight=1)
        frame_console.grid_rowconfigure(0, weight=1)

        label_console = ctk.CTkLabel(
            frame_console,
            text="📝 Journal d'activité",
            font=("Arial", 14, "bold")
        )
        label_console.grid(row=0, column=0, padx=10, pady=5, sticky="w")

        # Zone de texte pour les logs
        self.text_console = ctk.CTkTextbox(
            frame_console,
            font=("Consolas", 11),
            corner_radius=8
        )
        self.text_console.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")
        self.text_console.configure(state="disabled")

    def _creer_pied_page(self):
        """Crée le pied de page"""
        frame_pied = ctk.CTkFrame(self.root, height=50, corner_radius=10)
        frame_pied.grid(row=5, column=0, padx=15, pady=(5, 15), sticky="ew")

        btn_quitter = ctk.CTkButton(
            frame_pied,
            text="🚪 Quitter l'application",
            command=self.quitter,
            width=200,
            height=40,
            font=("Arial", 13),
            fg_color="#D32F2F",
            hover_color="#B71C1C",
            corner_radius=10
        )
        btn_quitter.pack(pady=10)

        # Statut en bas
        self.label_statut = ctk.CTkLabel(
            frame_pied,
            text="Prêt",
            font=("Arial", 11),
            text_color="green"
        )
        self.label_statut.pack(pady=(0, 5))

    def _demarrer_assistant(self):
        """Démarre l'assistant avec un message de bienvenue"""
        message_accueil = (
            f"Assistant vocal initialisé à {datetime.now().strftime('%H:%M:%S')}. "
            "Prêt à recevoir vos commandes."
        )
        self._mettre_a_jour_console(message_accueil, "INFO")
        self._mettre_a_jour_statut("Prêt")
        self._parler("Assistant vocal initialisé. Je suis prêt à vous aider.")

    def _ouvrir_site(self, site: Sites):
        """Ouvre un site web spécifique"""
        try:
            if site in URLS:
                url = URLS[site]
                webbrowser.open(url)

                message = f"Ouverture de {site.value}"
                self._mettre_a_jour_console(message, "SUCCES")
                self._mettre_a_jour_statut(f"Ouvert: {site.value}")
                self._parler(message)

                # Historique
                self.commandes_executees.append({
                    'type': 'site',
                    'site': site.value,
                    'url': url,
                    'timestamp': datetime.now()
                })

                logger.info(f"Site ouvert: {site.value} ({url})")

        except Exception as e:
            erreur_msg = f"Erreur lors de l'ouverture de {site.value}: {str(e)}"
            self._mettre_a_jour_console(erreur_msg, "ERREUR")
            self._mettre_a_jour_statut("Erreur")
            logger.error(erreur_msg)

    def _effectuer_recherche(self, requete: Optional[str] = None):
        """Effectue une recherche web"""
        try:
            if not requete:
                requete = self.entry_recherche.get().strip()

            if not requete:
                self._mettre_a_jour_console("Requête vide", "AVERTISSEMENT")
                self._mettre_a_jour_statut("Requête vide")
                self._parler("Veuillez entrer une requête de recherche.")
                return

            requete_encodee = urllib.parse.quote(requete)
            url_recherche = MOTEUR_RECHERCHE + requete_encodee
            webbrowser.open(url_recherche)

            message = f"Recherche: '{requete}'"
            self._mettre_a_jour_console(message, "SUCCES")
            self._mettre_a_jour_statut(f"Recherche: {requete[:20]}...")
            self._parler(f"Recherche pour {requete}.")

            # Historique
            self.commandes_executees.append({
                'type': 'recherche',
                'requete': requete,
                'url': url_recherche,
                'timestamp': datetime.now()
            })

            logger.info(f"Recherche effectuée: {requete}")

        except Exception as e:
            erreur_msg = f"Erreur de recherche: {str(e)}"
            self._mettre_a_jour_console(erreur_msg, "ERREUR")
            self._mettre_a_jour_statut("Erreur recherche")
            logger.error(erreur_msg)

    def _toggle_ecoute(self):
        """Active ou désactive l'écoute vocale"""
        if self.ecoute_active:
            self._arreter_ecoute()
        else:
            self._demarrer_ecoute()

    def _demarrer_ecoute(self):
        """Démarre l'écoute vocale"""
        try:
            self.ecoute_active = True
            self.btn_ecouter.configure(
                text="⏸️ Arrêter l'écoute",
                fg_color="#D32F2F",
                hover_color="#B71C1C"
            )
            self.label_indicateur.configure(
                text="● Écoute active - Parlez maintenant",
                text_color="green"
            )

            self._mettre_a_jour_console("Écoute vocale activée", "INFO")
            self._mettre_a_jour_statut("Écoute active")
            self._parler("Écoute activée. Je vous écoute.")

            # Démarrer le thread d'écoute
            self.thread_ecoute = threading.Thread(
                target=self._boucle_ecoute,
                daemon=True
            )
            self.thread_ecoute.start()

        except Exception as e:
            self._mettre_a_jour_console(f"Erreur démarrage écoute: {e}", "ERREUR")
            self.ecoute_active = False

    def _arreter_ecoute(self):
        """Arrête l'écoute vocale"""
        self.ecoute_active = False
        self.btn_ecouter.configure(
            text="🎤 Démarrer l'écoute",
            fg_color=ctk.ThemeManager.theme["CTkButton"]["fg_color"],
            hover_color=ctk.ThemeManager.theme["CTkButton"]["hover_color"]
        )
        self.label_indicateur.configure(
            text="● Écoute inactive",
            text_color="gray"
        )

        self._mettre_a_jour_console("Écoute vocale désactivée", "INFO")
        self._mettre_a_jour_statut("Écoute inactive")

    def _boucle_ecoute(self):
        """Boucle principale d'écoute vocale"""
        recognizer = sr.Recognizer()

        with sr.Microphone() as source:
            # Ajustement au bruit ambiant
            recognizer.adjust_for_ambient_noise(source, duration=0.5)

            while self.ecoute_active:
                try:
                    self.label_indicateur.configure(text="● Écoute active - En attente...")

                    # Écoute avec timeout
                    audio = recognizer.listen(
                        source,
                        timeout=5,
                        phrase_time_limit=10
                    )

                    self.label_indicateur.configure(text="● Écoute active - Traitement...")

                    # Reconnaissance
                    texte = recognizer.recognize_google(
                        audio,
                        language=self.langue
                    ).lower()

                    self._mettre_a_jour_console(f"📢 Reconnu: {texte}", "COMMANDE")

                    if not self._traiter_commande(texte):
                        self._mettre_a_jour_console(
                            "Commande non reconnue. Dites 'aide' pour la liste.",
                            "AVERTISSEMENT"
                        )
                        self._parler("Je n'ai pas compris. Essayez une autre commande.")

                except sr.WaitTimeoutError:
                    continue
                except sr.UnknownValueError:
                    self._mettre_a_jour_console("Parole non reconnue", "AVERTISSEMENT")
                except sr.RequestError as e:
                    erreur_msg = f"Service reconnaissance: {e}"
                    self._mettre_a_jour_console(erreur_msg, "ERREUR")
                    self._parler("Problème de connexion internet.")
                    logger.error(erreur_msg)
                except Exception as e:
                    erreur_msg = f"Erreur écoute: {e}"
                    self._mettre_a_jour_console(erreur_msg, "ERREUR")
                    logger.error(erreur_msg)

    def _traiter_commande(self, texte: str) -> bool:
        """Traite une commande vocale reconnue"""
        texte_lower = texte.lower().strip()

        # Recherche dans toutes les commandes
        for cle, commande in self.commandes.items():
            for mot_cle in commande.mots_cles:
                if mot_cle in texte_lower:
                    if commande.action:
                        # Exécuter l'action
                        self.root.after(0, commande.action)
                        self._mettre_a_jour_console(
                            f"Commande exécutée: {commande.description}",
                            "SUCCES"
                        )
                        return True

        # Recherche spécifique
        if any(mot in texte_lower for mot in ["rechercher", "chercher", "recherche", "cherche"]):
            # Extraire la requête après le mot-clé
            mots = texte_lower.split()
            for i, mot in enumerate(mots):
                if mot in ["rechercher", "chercher", "recherche", "cherche"]:
                    if i + 1 < len(mots):
                        requete = " ".join(mots[i+1:])
                        if requete:
                            self.root.after(0, lambda r=requete: self._effectuer_recherche(r))
                            return True

        return False

    def _afficher_aide(self):
        """Affiche l'aide des commandes disponibles"""
        sites = [site.value for site in Sites]
        message = (
            f"Commandes disponibles:\n"
            f"- Sites: {', '.join(sites)}\n"
            f"- Recherche: 'rechercher [votre recherche]'\n"
            f"- Autres: 'aide', 'quitter'"
        )

        self._mettre_a_jour_console("Affichage de l'aide", "INFO")
        self._parler(f"Vous pouvez dire: ouvrir {', ou '.join(sites)}. Ou effectuer une recherche.")

    def _mettre_a_jour_console(self, message: str, niveau: str = "INFO"):
        """Ajoute un message à la console"""
        couleurs = {
            "INFO": "white",
            "SUCCES": "#4CAF50",
            "ERREUR": "#F44336",
            "AVERTISSEMENT": "#FF9800",
            "COMMANDE": "#2196F3"
        }

        couleur = couleurs.get(niveau, "white")
        timestamp = datetime.now().strftime("%H:%M:%S")

        self.text_console.configure(state="normal")
        self.text_console.insert(
            "end",
            f"[{timestamp}] {message}\n",
            niveau
        )
        self.text_console.tag_config(niveau, foreground=couleur)
        self.text_console.see("end")
        self.text_console.configure(state="disabled")

    def _mettre_a_jour_statut(self, message: str):
        """Met à jour le statut en bas de l'interface"""
        self.label_statut.configure(text=message)

    def _parler(self, message: str):
        """Prononce un message vocalement"""
        try:
            if self.reconnaissance_active:
                self.engine.say(message)
                self.engine.runAndWait()
        except Exception as e:
            logger.warning(f"Synthèse vocale échouée: {e}")
            # Fallback: afficher dans la console
            self._mettre_a_jour_console(f"(TTS) {message}", "INFO")

    def _eclaircir_couleur(self, couleur: str) -> str:
        """Éclaircit une couleur hexadécimale"""
        # Conversion simplifiée - retourne une couleur plus claire
        return couleur  # Pour l'instant, retourne la même couleur

    def quitter(self):
        """Ferme l'application proprement"""
        self._arreter_ecoute()
        self._mettre_a_jour_console("Fermeture de l'application...", "INFO")
        self._mettre_a_jour_statut("Fermeture...")

        logger.info("Application fermée proprement")

        # Petite pause pour laisser les messages s'afficher
        self.root.after(500, self.root.quit)
        self.root.after(600, self.root.destroy)


def main():
    """Point d'entrée principal de l'application"""
    try:
        logger.info("=" * 50)
        logger.info("Démarrage de l'Assistant Vocal")
        logger.info("=" * 50)

        app = AssistantVocalApp()
        app.root.mainloop()

    except KeyboardInterrupt:
        logger.info("Application interrompue par l'utilisateur")
    except Exception as e:
        logger.critical(f"Erreur critique: {e}", exc_info=True)
        # Message d'erreur utilisateur
        ctk.CTk().withdraw()
        ctk.CTkMessageBox(
            title="Erreur Critique",
            message=f"L'application a rencontré une erreur:\n{str(e)}",
            icon="cancel"
        )
    finally:
        logger.info("Application terminée")


if __name__ == "__main__":
    main()