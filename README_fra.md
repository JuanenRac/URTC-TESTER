<p align="center">
  <img src="/images/URTC_TESTER_BANNER.svg" alt="URTC Tester Logo" width="100%">
</p>

# URTC Tester (Windows / Linux)

<p align="center">
  <a href="README.md">🇺🇸 English</a> |
  <a href="README_spa.md">🇪🇸 Español</a> |
  🇫🇷 <b>Français</b> |
  <a href="README_ita.md">🇮🇹 Italiano</a> |
  <a href="README_deu.md">🇩🇪 Deutsch</a> |
  <a href="README_zho.md">🇨🇳 简体中文</a> |
  <a href="README_jpn.md">🇯🇵 日本語</a> |
  <a href="README_por.md">🇵🇹 Português</a>
</p>


<p align="center">
  <img src="https://img.shields.io/badge/Licence-GPL%203.0-blue.svg" alt="GPL 3.0 or later">
  <img src="https://img.shields.io/badge/Langage-Python-3776AB.svg" alt="Python">
  <img src="https://img.shields.io/badge/UI-Qt%20Quick-38d4e6.svg" alt="Qt Quick">
  <img src="https://img.shields.io/badge/Protocole-CAN-yellow.svg" alt="CAN">
</p>


**Version :** 0.4.0 · **Auteur :** JuanenRac (Electro Hobby 3D) &lt;electrohobby3d@gmail.com&gt;

Licence : **GPL-3.0-or-later** pour le code source, **CC BY-SA 4.0** pour cette
documentation - voir `LICENSE` dans ce dépôt, ou la section « Licence
et Avis de Copyright » à la fin de ce document.

Un testeur de bus CAN en direct pour la carte URTC. Il se connecte via
le même adaptateur USB-CAN que celui utilisé par le flasher, demande à
la carte pour lequel de ses 25 profils d'outil elle est actuellement
configurée par cavaliers, et n'affiche que les contrôles et la
télémétrie propres à cet outil - pas une seule fenêtre essayant de
représenter les 25 à la fois. Tout ce qu'il fait est une commande
d'exécution ou une lecture de télémétrie contre l'application en cours
d'exécution ; il ne touche jamais la flash, donc il n'y a rien ici qui
puisse laisser la carte moins fonctionnelle qu'au départ.

**Vérification d'honnêteté - ce qui fonctionne réellement aujourd'hui :** les encodeurs de charge utile CAN pour les familles de contrôle migrées vers Qt Quick (`advanced_protocol.py`) sont réels et couverts par les tests de `tests/` (`python -m pytest -q`). La propre CI de ce dépôt (`.github/workflows/ci.yml`) les exécute aussi, avec `ruff check`, `tools/ci_validate.py`, une compilation de syntaxe de chaque fichier `.py` et les quatre scripts `verify_qt_*.py`, donc une régression là fait échouer le build. Les quatre scripts `verify_qt_*.py` à la racine du dépôt (`verify_qt_custom_frame.py`, `verify_qt_telemetry_watch.py`, `verify_qt_utility_panels.py`, `verify_qt_selftest.py`) sont de vraies vérifications de bout en bout, délibérément en dehors de `tests/`, contre un faux transport avec une vraie livraison de signaux entre threads - les quatre passent avec `QT_QPA_PLATFORM=offscreen python verify_qt_*.py`, que la CI exécute aussi. C'est le plafond honnête de ce qui est vérifié automatiquement : la couche de transport, la gestion ID/disposition des octets CAN, et la logique du pont Qt Quick sont réelles et exercées contre des trames simulées, pas du vrai matériel - comme le dit déjà "Known limitations" ci-dessous, ceci a été construit sans accès USB, donc rien ici n'a encore été vérifié contre une vraie carte. `qt_tester.py` et `assets/qml/TesterDeck.qml` sont l'implémentation réelle et substantielle (des milliers de lignes combinées), exercée par les tests avec des cartes simulées et par les scripts de vérification, jamais par une vraie carte.

> **État de la sûreté et de la cybersécurité :** cet écosystème n'est pas un système de sécurité certifié et aucune carte URTC assemblée n'existe encore. Les bootloaders contrôlent les images de firmware par CRC32 et un HMAC-SHA256 à clé partagée, pas par une signature asymétrique (prévue) ; les images d'application publiées sont signées avec la clé publique de développement (`signing_key_kind: dev`), si bien que n'importe qui peut produire une image acceptée par le bootloader ; rien n'a été transmis à une carte réelle. Lisez la [base de sécurité](https://github.com/JuanenRac/URTC-DOCS/blob/main/docs/SECURITY_BASELINE.md) et le [modèle de menaces](https://github.com/JuanenRac/URTC-DOCS/blob/main/docs/THREAT_MODEL.md) avant de vous fier à une affirmation d'ici pour la sécurité d'une personne.

## 📋 En un coup d'œil

| | |
|---|---|
| Version | `0.4.0` |
| Maturité | Fonctionnel |
| Technologie | Python / PySide6 / Qt Quick / live CAN bus diagnostics |
| Cible | Le PC de la personne qui l'utilise |
| Sur matériel réel | Simulé seulement : testé avec des émulateurs, des doubles de test ou des simulateurs ; aucune exécution sur du matériel réel n'est consignée pour cette version |

## 1. 🆚 Relation avec le flasher

Cet outil et [URTC Flasher](https://github.com/JuanenRac/URTC-FLASHER) partagent la même couche de transport
(les classes SLCAN et SocketCAN sont identiques) puisque les deux ont
finalement juste besoin de faire entrer et sortir des trames CAN du
même type d'adaptateur, mais ils font des travaux fondamentalement
différents :

| | Flasher | Tester |
|---|---|---|
| Touche la flash | Oui (c'est tout l'intérêt) | Jamais |
| Parle à | Le bootloader, principalement | L'application en cours d'exécution |
| But | Mettre à jour le firmware | Exercer/vérifier le matériel réel d'une tête d'outil |

Si vous n'êtes pas sûr de celui dont vous avez besoin : si la carte
exécute déjà le firmware et que vous voulez vérifier qu'un outil
fonctionne réellement (le chauffage chauffe, le moteur tourne, la LED
s'allume), vous voulez celui-ci.

## 2. 📦 Installation et exécution

Même schéma que le flasher :

```
pip install -r requirements.txt
python urtc_tester.py          # Windows
python3 urtc_tester.py         # Linux
```

Ou construisez un binaire autonome : `build_exe.bat` sous Windows,
`./build_exe.sh` sous Linux. Les deux nettoient d'abord `build/`/`dist/`
et empaquettent `assets/` (la bannière et l'icône) dans l'exécutable -
voir [docs/BUILD_AND_RUN.md](docs/BUILD_AND_RUN.md) pour le chemin de
validation sans gestion de version (`build-test.bat`/`build-test.sh`)
sur lequel s'appuient ces scripts d'empaquetage, et le propre README du
flasher pour le raisonnement complet derrière les scripts d'empaquetage
eux-mêmes, puisqu'il s'applique identiquement ici.

**Versionnage :** `TESTER_VERSION` (dans `tester_config.py`, affiché
dans la barre de titre, la boîte de dialogue À propos, les logs de
session et les paquets de débogage) suit le schéma
`MAJEUR.MINEUR.CORRECTIF`. Les deux scripts de build l'incrémentent
automatiquement juste avant chaque build réel via `bump_version.py`,
avec une règle « compteur kilométrique » en base 10 : CORRECTIF +1, et
au-delà de 9 il repasse à 0 et MINEUR monte de 1 (ex. `0.1.9` →
`0.2.0`). Exécuter depuis le code source (`python urtc_tester.py`) ne le
touche jamais - seule une exécution réelle de
`build_exe.bat`/`build_exe.sh` le fait. MAJEUR ne monte jamais
automatiquement, seulement à la main. Voir `CHANGELOG.md` pour
l'historique des versions.

### Console visuelle de contrôle

La console de commandes **Qt Quick** est désormais celle par défaut :
~~~
python urtc_tester.py
~~~
Elle utilise les transports SLCAN/SocketCAN et démarre en écoute
seule, elle ne peut donc pas émettre avant l'armement volontaire des contrôles
actifs. Chacune des commandes propres aux 25 profils d'outil y est couverte de
manière réelle et confirmée (mouvement, perceuse, AOI, électro-aimant,
impulsion de soudure par points/ultrasons, jet de pâte, flying probe,
inspection thermique, les 5 actionneurs à watchdog-keepalive, télémétrie
vide/scan-probe), chacune soumise à la même porte : une correspondance
d'identité, un mode actif armé explicitement et une confirmation de
l'utilisateur dans QML avant toute émission.
Rien de tout cela n'a encore été vérifié sur une vraie carte - voir « Limitations connues » ci-dessous.

La console affiche aussi les **valeurs en direct** de l'outil détecté (température avec un graphique défilant et export CSV, régime, fins de course ; elles ne font qu'écouter, donc elles fonctionnent en écoute seule et à côté d'une sortie en marche), exécute l'**autotest**, avertit dans l'en-tête quand le **contrôle de santé du bus** (une interrogation de l'outil actif toutes les 3 secondes tant que rien d'autre n'utilise le bus) voit un problème, et a une boîte **À propos d'URTC Tester** avec le Readme, la Licence et la page GitHub, à côté de **Enregistrer les journaux...**.

L'en-tête de la fenêtre Qt Quick a un sélecteur de langue ; le choix est enregistré et s'applique au prochain démarrage. Il interroge aussi la position de l'alimenteur de fil du fer à souder et la remet à zéro (estimation en boucle ouverte ; la remise à zéro demande une confirmation). La sonde d'identité affiche aussi le numéro de correctif du firmware lorsque la carte l'envoie (firmware URTC 0.3.5 et suivants) ; un firmware plus ancien n'affiche que majeur.mineur.

Le flux de diagnostic CAN en direct existant utilise désormais une surface de contrôle bleu nuit/cyan : en-tête produit, carte de connexion contrastée, onglets d'outils lisibles, journal de session sombre et progression visible. Ce changement visuel et d'accessibilité ne modifie ni la surveillance passive ni le routage des commandes, et rien de tout cela n'a été essayé sur une vraie carte.

### En-tête et outils

- **En-tête** - l'état de la connexion, l'avertissement de santé du bus, le sélecteur de langue (le choix est enregistré et s'applique au prochain démarrage) et la version.
- **Enregistrer les journaux...** et **EXPORTER LA SESSION (JOURNAL AVEC EMPREINTE)** - le journal affiché en texte brut, ou un zip avec le journal, un manifeste qui le désigne par son SHA-256 et les diagnostics système (voir « Journaux et paquets de débogage » plus bas).
- **À propos d'URTC Tester** - version et auteur, avec des boutons pour **Lisez-moi** (dans la langue de l'interface si une traduction existe), **Licence** et la page **GitHub d'URTC** du projet.

### Structure des fichiers

Cet outil est organisé en modules par responsabilité, purement pour la lisibilité - il n'y a aucune différence fonctionnelle entre les avoir comme fichiers séparés ou comme un seul gros fichier. `tester_config.py` contient les constantes de configuration/langue/protocole, `tester_transports.py` contient SLCAN/SocketCAN, `tester_bus_monitor.py` contient le filtre de trames et les statistiques du bus, `qt_tester.py` est le pont Qt Quick (avec `assets/qml/TesterDeck.qml`), `tester_selftest.py`, `tester_telemetry.py` et `tester_autodetect.py` sont la logique sans fenêtre de l'autotest, des valeurs en direct et de la recherche du débit, et `urtc_tester.py` est juste le point d'entrée.

**Langue** : anglais par défaut. Se change avec le sélecteur de langue de l'en-tête de la fenêtre - change l'interface (étiquettes, boutons, dialogues, et messages de journal) vers l'une des 8 langues disponibles,
enregistre immédiatement dans `config.json` à côté de cet outil,
appliqué au prochain démarrage. Les traductions vivent dans des fichiers
texte brut sous `language/` (`english.lng`, `spanish.lng`, `italian.lng`,
`french.lng`, `german.lng`, `chinese.lng`, `japanese.lng`, `portuguese.lng`) sous forme de
paires simples `CLE=Valeur`, une par ligne - les lignes commençant par `#` et les lignes vides sont
ignorées, et un `\n` littéral dans une valeur devient un vrai saut de
ligne (utilisé par la poignée de messages de dialogue multi-lignes).
Modifiable directement si une traduction nécessite une correction, ou
comme point de départ pour une autre langue (ajoutez
`language/<nom>.lng`, ajoutez `("<nom>", "Nom Natif")` à
`AVAILABLE_LANGUAGES` près du début de `tester_config.py`, et définissez
`"language": "<nom>"` dans `config.json`). Une clé manquante d'un
fichier de langue retombe sur l'affichage du nom de cette clé même
plutôt que de planter, et un fichier de langue manquant ou illisible
(mauvaise modification, mauvais nom de fichier) retombe sur l'anglais
pour toute l'interface - dans les deux cas l'outil reste utilisable
pendant que le décalage se règle.

**Configuration SLCAN/SocketCAN sous Linux** (reflash de l'adaptateur,
permissions série, activation avec `ip link`) est exactement la même
que la section 1 du flasher - voir le
[README d'URTC Flasher](https://github.com/JuanenRac/URTC-FLASHER)
sections 1 et 2 plutôt que de la dupliquer ici.

## 3. ⚙️ Comment ça fonctionne

La fenêtre est disposée en 3 colonnes : gauche et centre contiennent les
sections toujours visibles ci-dessous (1-4, puis 6), droite contient le
panneau par outil de la section 5, qui est la seule partie de la
fenêtre qui change réellement selon ce qui est détecté. Diviser les
sections toujours visibles sur 2 colonnes plutôt que de les empiler
toutes en une seule empêche la fenêtre de devenir assez haute pour ne
plus tenir sur un écran ordinaire, à mesure que davantage de ces
sections ont été ajoutées au fil du temps. Le panneau propre de
l'imprimante 3D (le plus haut des 25) va un pas plus loin et divise ses
propres contrôles en 2 sous-colonnes en interne, pour la même raison.
Voir [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) pour le guide
d'architecture au niveau des modules que cette section résume.

**Connecter** (section 1, identique au flasher) : choisissez
Série/SLCAN ou SocketCAN, le port/interface, détectez éventuellement
automatiquement le débit binaire, puis Connecter.

**La détection se produit automatiquement à la connexion** (ou cliquez
sur **Détecter** pour la refaire) : l'outil envoie `0x110` (interroger
l'outil actif) et `0x7F8` (interroger la version), et utilise la
réponse pour :
- Montrer lequel des 25 profils d'outil est actif, et l'état général de
  la carte (toute erreur déclarée, défaut de bus CAN, encore dans
  l'écran de démarrage).
- Montrer le HardwareID et la version de firmware rapportés, signalant
  une discordance si cela ne correspond pas au propre
  `THIS_HARDWARE_ID` de ce projet.
- Construire le panneau **Contrôles d'Outil** à droite pour cet outil
  spécifique - et seulement cet outil. Changer quel outil est
  cavalié et détecter à nouveau démonte l'ancien panneau et en
  construit un nouveau depuis zéro.

**Contrôles Globaux** (section 2, toujours visible quel que soit l'outil
actif) : le remplacement de couleur de la LED de statut, la couleur et
l'allumage/extinction de l'anneau LED, et le mode d'affichage OLED
(`0x100`) - ceux-ci s'appliquent à chaque outil, donc ils ne se
déplacent pas vers le panneau dynamique. En mode Inspection AOI
spécifiquement, l'allumage/extinction de l'anneau ici est ignoré en
faveur du propre contrôle de stroboscope de cet outil (selon
[docs/CANBUS.md](docs/CANBUS.md)) - la couleur s'applique quand même dans les deux cas.

**Carte d'Extension** (section 3, toujours visible) : le propre bus SPI
générique et la ligne DIAG0 de `CONN_EXPANSION` - le passage brut
partagé par toutes les variantes de carte d'extension avec driver.
L'ADS1115 et les capteurs MLX9064x, ainsi que le driver propre de
l'actionneur de sertissage, ne se contrôlent pas depuis ici - ils vivent
dans le panneau de leur propre outil à la place (Sonde Volante,
Inspection Avancée PCB, Actionneur de Sertissage - voir section 4
ci-dessous), puisque celui qui s'applique réellement dépend du profil
d'outil configuré par cavaliers.

**F-RAM de Persistance** (section 4, également toujours visible, mais
délibérément séparée de Carte d'Extension ci-dessus) : la FM24CL64B
partage le propre bus I2C2 matériel de l'OLED - un composant central de
la carte, pas quelque chose de câblé à `CONN_EXPANSION` du tout.
Regrouper les deux ensemble impliquerait une connexion entre eux qui
n'est pas réelle - le connecteur d'extension lui-même n'a pas de F-RAM,
pas d'EEPROM, rien de non volatile dessus.
- **Passage direct SPI** : tapez des octets hexadécimaux séparés par des
  espaces (1 à 7 d'entre eux, p. ex. `01 02 03`), appuyez sur Envoyer,
  et voyez exactement ce qui est revenu sur MISO pendant ce même
  transfert (`0x180`/`0x181`) - un transport d'octets brut, pas
  conscient des registres TMC5160, correspondant à la propre approche
  du firmware. Utile pour exercer le bus lui-même avant qu'il ne vaille
  la peine de construire un panneau dédié pour le protocole de
  registres d'une carte d'extension spécifique.
- **Niveau DIAG0** : **Interroger DIAG0** lit l'état actuel de la ligne
  de diagnostic de blocage/défaut d'un TMC5160 (`0x182`/`0x183`) - HIGH
  (inactif) ou LOW (affirmé). Une simple lecture interrogée, pas une
  valeur en direct/poussée - appuyez à nouveau sur le bouton pour
  l'actualiser.
- **F-RAM de Persistance** : **Interroger l'État** relit ce que la
  carte a sauvegardé la dernière fois avant une perte d'alimentation
  (`0x190`/`0x191`) - quel outil c'était, le point de consigne, si une
  erreur critique était active à ce moment-là. **Effacer la F-RAM...**
  l'efface (`0x192`, avec une boîte de dialogue de confirmation
  d'abord - ceci ne peut pas être annulé).
- **Type de carte d'extension** : **Interroger** montre laquelle des 7
  configurations possibles de `CONN_EXPANSION` est actuellement définie
  (`0x1A1` - voir `EXPANSION.TXT`). Lecture seule ici - définissez-la
  depuis la propre section CAN OTA de `URTC Flasher` à la place,
  puisque c'est une étape de configuration matérielle ponctuelle, pas
  quelque chose à changer avec désinvolture depuis un outil de
  diagnostic en direct.
- **Variante de capteur MLX9064x** : **Interroger** montre lequel des 3
  capteurs thermiques de la famille MLX9064x (ou aucun) est
  actuellement configuré (`0x1A7` - voir `CANBUS.md`) - pertinent
  uniquement lorsque le type de carte d'extension ci-dessus est une
  variante Advanced ou Basic+MLX9064x. Lecture seule ici, même
  raisonnement que le type de carte d'extension ci-dessus.
- **Configuration libre de l'outil** : **Interroger** montre la lecture
  brute des cavaliers ID (0-31) à côté de ce que dit actuellement le
  registre `free_tool_selection` de la F-RAM (`0x1A3` - voir
  `EEPROM.TXT` section 5) - seulement réellement consulté par une carte
  dont les cavaliers lisent 0x1F/11111b. Lecture seule ici, même
  raisonnement que le type de carte d'extension ci-dessus - `URTC
  Flasher` est le seul outil qui l'écrit.
- **Type de périphérique et numéro de série** : **Interroger** montre le
  type de périphérique fixe (toujours URTC/0x03) à côté du numéro de
  série de l'appareil actuellement défini (`0x1A5` - voir `EEPROM.TXT`
  section 6), une étiquette attribuée par l'hôte pour distinguer
  plusieurs cartes par ailleurs identiques sur le même bus CAN. Lecture
  seule ici aussi - `URTC Flasher` écrit le numéro de série, cet outil
  ne fait que le relire.

**Trame CAN Personnalisée** (section 6, également toujours visible) :
une entrée d'ID brut + octets hexadécimaux avec envoi unique et
périodique - pour une commande qui n'a pas encore son propre contrôle
ici, ou pour tester quelque chose non (ou pas encore) documenté dans
`docs/CANBUS.md`. Aucune validation au-delà de la plage d'ID et
DLC≤8 ; quoi que ceci envoie est exactement ce qui va sur le bus. La
même section ouvre aussi le **Moniteur de Bus Brut** (voir ci-dessous).

**Exécuter Auto-test** (à côté de Détecter) : exécute un petit ensemble
de vérifications de communication sûres et au repos pour l'outil
actuellement détecté - confirme que l'interrogation de l'outil actif et
celle de la version répondent toutes les deux, puis (pour les outils
avec télémétrie) envoie un point de consigne/vitesse/puissance sûr de 0
et vérifie que la télémétrie attendue arrive. N'envoie délibérément
jamais rien qui chaufferait, tirerait, ou tournerait réellement à
puissance significative - ceci vérifie que l'aller-retour de
communication fonctionne, pas qu'un actionneur répond physiquement,
puisque confirmer cela nécessite de toute façon un humain qui observe.
Demande confirmation avant d'envoyer quoi que ce soit. Les outils sans
télémétrie (mouvement simple) ou qui sont purement pilotés par
événements (sonde de balayage) reçoivent une note informative
seulement au lieu d'un vrai succès/échec. **La couverture est
partielle** : seuls 7 des 25 outils ont une étape d'auto-test définie
(fer à souder, perceuse, laser, imprimante 3D, AOI, vide, sonde de
balayage) - les 18 autres outils n'exécutent aucune vérification quand
ce bouton est actionné.

**Graphiques de température en direct** : les panneaux du fer à souder
et de la buse de l'imprimante 3D montrent tous deux un petit graphique
linéaire défilant à côté de leur lecture de température en direct - un
simple Canvas Qt Quick, pas une nouvelle dépendance
(matplotlib/pyqtgraph casseraient la politique de zéro dépendance de
cet outil au-delà de pyserial). Échelle d'axe Y fixe (0 jusqu'au
plafond de point de consigne propre à cet outil) plutôt qu'auto-échelle,
donc la tendance est facile à lire d'un coup d'œil plutôt que l'échelle
se décale en dessous.

**Moniteur de Bus Brut** (ouvert depuis la section Trame CAN
Personnalisée) : une fenêtre séparée montrant chaque trame vue,
n'importe quel ID, indépendante du panneau d'outil actif - un tableau à
défilement en direct (Temps/ID/DLC/Données/Δt), Pause/Effacer, et une
lecture approximative de charge de bus/taux de trames (mise à jour une
fois par seconde ; le chiffre de charge ne modélise pas la surcharge de
bit-stuffing, donc traitez-le comme un chiffre diagnostique approximatif,
pas une mesure certifiée). **Exporter .trc...**/**Exporter .asc...**
enregistrent le tableau actuellement affiché comme un fichier de trace
simplifié au style PEAK PCAN-View / Vector CANalyzer respectivement -
assez proche pour être lisible par la plupart des outils qui attendent
ces formats, pas garanti identique octet par octet à ce que produisent
les applications réelles. Si `urtc_custom_ids.json` existe à côté de ce
script (optionnel, non inclus par défaut - `{"0x199": "My Sensor"}`),
la colonne ID montre ce nom convivial à côté de l'ID hexadécimal brut -
utile pour quiconque teste le propre trafic d'une carte d'extension
personnalisée sans avoir besoin de modifier le code source de cet
outil.

## 4. 🧰 Couverture des outils

Chacun des 25 profils a son propre panneau, construit directement à
partir de `docs/CANBUS.md` :

| Outil | Contrôles | Télémétrie en direct |
|---|---|---|
| Fer à souder | Température de consigne, marche/arrêt ; alimentateur de fil direction + nombre de pas (mouvement unique) ; interrogation et réinitialisation à 0 de la position de l'alimentateur | Température réelle ; position de l'alimentateur (estimation en boucle ouverte) |
| Distributeur Pâte/Liquide, Tournevis, les deux Pinces, SMT Pick & Place, Vacuum Gripper (LG) | Direction + nombre de pas (mouvement unique) | aucune (0x120 partagé, aucune télémétrie pour aucun de ces 7) |
| Prélèvement par Aspiration | aucun | Lecture analogique, pièce détectée |
| Perceuse | Vitesse + direction | RPM réel, fin de course |
| Inspection AOI | Mode anneau (éteint/stroboscope/continu) + période de stroboscope | Fin de course |
| Graveur Laser | Puissance + armement/sécurité du verrou laser (une sortie du firmware, pas un verrouillage matériel) | Fin de course |
| Imprimante 3D | Consigne de buse, direction/pas de l'extrudeur, puissance ventilateur de couche, puissance ventilateur hotend | Température hotend, RPM ventilateur de couche, RPM ventilateur hotend |
| Sonde de Balayage | aucun | Nombre d'événements d'impact + horodatage (`0x095` priorité maximale) |
| Électroaimant | Case à cocher activer/relâcher bobine | aucune |
| Soudeuse par Points | Durée d'impulsion + Déclencher | aucune (ne se déclenche que si le capteur de contact lit HIGH d'abord - voir le propre `0x1C0` de `docs/CANBUS.md`) |
| Revêtement Conforme, Insertion par Pression | aucun - panneau purement informatif | aucune - les deux ID d'outil n'ont aucun gestionnaire CAN, leur propre actionneur et capteur vivent sur la carte mère du robot lui-même, voir `docs/TOOLS.TXT` |
| Sonde Volante | La lecture basique est automatique ; la lecture avancée nécessite un mot de config ADS1115 brut (hex) + Déclencher Conversion + Lire Résultat | Lecture basique ADC intégré (automatique, `0x243`) |
| Durcissement UV | Curseur de puissance (0-255) + Envoyer/Éteindre | aucune |
| Air Chaud pour Retouche | Température de consigne, puissance ventilateur, marche/arrêt | Température en direct (partage la propre télémétrie `0x135` et le graphique en direct du fer à souder - même boucle thermique physique) |
| Actionneur de Sertissage | Direction + nombre de pas (mouvement unique, même forme que les outils de mouvement partagés ci-dessus, mais atteint le driver d'une carte d'extension via `0x1F0` au lieu du `0x120` intégré) | aucune |
| Inspection Avancée PCB | Déclencher Capture, Vérifier Statut, Lire Image Thermique | Toile de carte thermique 32x24 pixels (dégradé bleu-rouge), extraite morceau par morceau via CAN à la demande - pas un flux vidéo en direct, voir section 6 ci-dessous |
| Jetting de Pâte à Souder | Canal PWM + fréquence (Configurer), puis cycle + durée (Déclencher Impulsion) | aucune |
| Soudeuse Ultrasonique | Durée d'impulsion + Déclencher | aucune (même forme que la Soudeuse par Points, mais sans verrou du capteur de contact) |

**Les watchdogs de communication sont gérés pour vous.** Le fer à
souder, l'Air Chaud pour Retouche (partage la même boucle thermique et
le même watchdog que le fer à souder), le laser, et la buse de
l'imprimante 3D ont chacun un watchdog de 250ms dans le firmware ; le
ventilateur de couche en a un de 1000ms. Cocher la case "Actif"
correspondante n'envoie pas seulement la commande une fois - elle la
renvoie automatiquement (150ms pour les outils avec watchdog 250ms,
400ms pour le ventilateur de couche) tant que la case reste cochée, de
la même manière qu'un vrai contrôleur maître doit le faire. La décocher
envoie une seule trame zéro/arrêt et s'arrête. Le ventilateur hotend
n'a pas de watchdog (un détecteur de blocage à la place - voir
`docs/CANBUS.md`), donc c'est un simple envoi unique.

**Notes de confort (commodités logicielles, pas des fonctions de sécurité).**

- **ARRÊTER TOUTES LES SORTIES** (dans les deux fenêtres, disponible une fois connecté avec les vérifications actives armées) envoie toutes les commandes d'arrêt connues - chauffages, laser, perceuse, lampe UV, ventilateur de couche, relâchement de l'électroaimant, moteurs pas à pas simples et sertisseuse - quel que soit l'outil monté, et arrête tous les rafraîchissements. Le ventilateur du hotend est laissé en marche volontairement, car la buse peut être encore chaude. C'est une commande logicielle envoyée sur le bus CAN, pas un arrêt d'urgence : elle ne peut pas agir si le bus, l'adaptateur, le PC ou la carte tombe en panne.
- Les impulsions de soudure ponctuelles, l'impulsion de pâte et le sertissage demandent aussi une confirmation dans la fenêtre classique, comme le fait toujours le deck Qt Quick.
- La perceuse et la lampe UV sont rafraîchies comme le laser et les chauffages. Tant que le chauffage de l'imprimante 3D est maintenu, son rafraîchissement de 150 ms porte 0 pas d'extrudeur, que le firmware lit comme un ordre d'arrêt : un mouvement d'extrudeur lancé dans cet état est annulé en 150 ms, donc déplacez l'extrudeur chauffage éteint jusqu'à ce que le firmware offre un mode qui le laisse tranquille.
- Le port et le débit sont mémorisés pour la prochaine session (`config.json`) et le deck Qt Quick a son propre sélecteur de débit. La **détection automatique** commence par écouter à chaque débit (rien n'est émis sur un bus actif) et n'interroge à chaque débit que si le bus est complètement silencieux.
- Le Moniteur de bus brut peut être limité à certains ID CAN (**Filtre d'ID**) et aux trames dont les données ont changé (**Changements seulement**).

### 🔥 Test de banc d'emballement thermique (firmware URTC 0.3.2+ / 0.3.3+)

Detect affiche désormais *pourquoi* une carte a verrouillé une erreur :
l'octet 4 de `0x111` (protection contre l'emballement thermique : MAXTEMP,
HEATING_NO_RISE ou DROPPED_AT_TARGET) apparaît dans l'état de la carte, et un
redémarrage causé par le watchdog matériel (octet 5 de `0x111`) est
journalisé. **Compteurs thermiques** (panneau F-RAM dans les deux
interfaces) lit `0x1AA`/`0x1AB` : défauts thermiques cumulés, heures totales
de chauffe et dernier défaut. Les réponses d'un ancien firmware (`0x111` sur
4 octets, pas de `0x1AB`) sont affichées comme « non renseigné », jamais
comme zéro. La procédure pas à pas pour valider la protection sur une vraie
carte est dans [`docs/THERMAL_RUNAWAY_BENCH_TEST.md`](docs/THERMAL_RUNAWAY_BENCH_TEST.md).

## 5. 📋 Journaux et paquets de débogage

Comme le flasher : un journal de session horodaté est écrit
automatiquement dans `logs/` (sûr à supprimer), et
**Exporter le Paquet de Débogage** enregistre un `.zip` avec le journal
actuel à l'écran plus des diagnostics système de base (OS, version
Python, transport/port/débit binaire actuel, outil détecté) pour
remettre à quiconque déboguant un problème de tête d'outil.

### 🤖 Sans fenêtre : plans de test

`python urtc_tester.py --headless COMMANDE` exécute le testeur sans fenêtre, pour une ligne de production, un script de banc ou une tâche de CI : `info` (qui répond : outil, firmware, état rapide), `selftest`, `run-plan FICHIER` et `validate-plan FICHIER`. Un plan est un court fichier JSON d'étapes rangé dans `plans/` (attendre un outil, aucun défaut, une version minimale du firmware, l'autotest, une trame dont la valeur est dans une plage, une attente, une question à la personne au banc). La commande écrit un journal de chaque trame et un enregistrement de résultat qui nomme le journal par son SHA-256, le même que celui du pupitre. Un plan n'envoie que des requêtes, sauf s'il dit `"actuation": true` et que l'opérateur ajoute `--allow-actuation` ; les trames du bootloader, de mise à jour, de configuration et d'effacement ne sont jamais envoyées, et après un plan qui a commandé quelque chose toutes les sorties sont de nouveau coupées. `--transport simulate` joue une tête d'outil simulée et `--transport replay --port FICHIER` une trace `.trc` ou `.asc` enregistrée, de sorte qu'un plan peut être essayé sans carte. Code de sortie : 0 réussi, 1 une vérification a échoué, 2 le plan ou les arguments sont faux, 3 le test n'a pas pu être mené. Le texte affiché est en anglais, comme la ligne de commande du flasher. Détails dans [`docs/HEADLESS.md`](docs/HEADLESS.md). Rien de cela n'a tourné contre une vraie carte.

## 6. ⚠️ Limitations connues

Le contrat de preuve de cet outil - ce qui compte comme pass/fail/unknown,
pourquoi l'absence de preuve est toujours unknown et jamais pass, et
pourquoi il n'accorde par lui-même aucune autorité de flashage de
firmware - est documenté dans
[docs/INTEGRATION_CONTRACT.md](docs/INTEGRATION_CONTRACT.md).

- **Non testé contre du matériel réel.** Chaque pièce ici - la couche
  de transport, la gestion ID CAN/disposition d'octets, la
  synchronisation keepalive du watchdog - a été vérifiée isolément
  (trames simulées, un vrai sous-processus pour la synchronisation où
  pertinent) mais l'environnement qui a construit ceci n'a pas d'accès
  USB. Traitez une première session réelle avec la même prudence que
  demande le propre README du flasher.
- **Un panneau d'outil à la fois, par conception**, pas une limitation
  actuelle à supprimer plus tard - voir l'introduction ci-dessus pour
  la raison.
- **Les couleurs LED globales sont un remplacement direct**, pas une
  relecture en direct - il n'y a pas de télémétrie de ce que les LED
  de statut/anneau montrent réellement actuellement, seulement ce qui a
  été commandé en dernier.
- **La propre image thermique de l'Inspection Avancée PCB est basée sur
  extraction, pas un flux en direct.** Lire une image complète signifie
  demander les 48 morceaux séquentiellement via CAN (pire cas, la
  propre résolution de MLX90640/MLX90642) - cela peut prendre plusieurs
  secondes, et il n'existe aucun mode d'envoi en streaming dans le
  propre protocole CAN de cet outil pour accélérer cela. Il faut d'abord déclencher une capture ; Lire Image Thermique attend alors jusqu'à deux secondes que le capteur signale qu'il est prêt et, s'il ne le fait pas, ne lit rien, car le firmware ne répond pas aux demandes de morceau avant cela. Le capteur installé est interrogé en premier (48 morceaux pour MLX90640/MLX90642, 12 pour MLX90641), et un morceau perdu laisse ses pixels vides au lieu de décaler le reste de l'image.
- **Exécuter Self-Test ne couvre que 7 des 25 outils** (fer à souder,
  perceuse, laser, imprimante 3D, AOI, aspiration, sonde de balayage)
  - voir « Comment ça fonctionne » ci-dessus pour l'explication
  complète. Les 18 autres outils ne reçoivent aucune vérification
  automatisée de ce bouton ; les vérifier signifie toujours observer
  le matériel réel répondre aux commandes de son propre panneau.

## 📂 Structure du Dépôt

```
/
├── urtc_tester.py             Point d'entrée - démarre la console Qt Quick
├── qt_tester.py                Front end Qt Quick - command deck réel par défaut, en lecture seule par défaut
│                                limité, en lecture seule par défaut
├── tester_config.py            Constantes de config/langue/protocole (ID CAN,
│                                noms d'outils, MOTION_TOOL_IDS,
│                                AVAILABLE_LANGUAGES, EXPANSION_BOARD_TYPES)
├── tester_transports.py        Classes de transport SLCAN et SocketCAN
├── tester_bus_monitor.py       Thread de lecture CAN en arrière-plan
│                                (CANBusMonitor)
├── tester_autodetect.py        Recherche du débit d'un adaptateur SLCAN
├── tester_selftest.py          Étapes et exécution de l'autotest (sans code de fenêtre)
├── tester_plan.py              Plans de test : validation, exécution et le « tout éteint » qui suit
├── tester_cli.py               Le testeur sans fenêtre (--headless) : info, selftest, run-plan
├── tester_simulator.py         Tête d'outil simulée et lecteur de traces enregistrées
├── plans/                      Exemples de plans de test (JSON)
├── tester_telemetry.py         Valeurs en direct de chaque outil et série enregistrée
├── tester_trace_export.py      Écriture des exports de trames .trc / .asc
├── urtc_ui/                    Aides d'interface partagées (copie d'URTC-COMMON)
├── advanced_protocol.py        Encodeurs purs de payload CAN pour les familles de
│                                contrôles migrées vers Qt Quick - tests sans matériel
├── verify_qt_custom_frame.py        Vraie vérification de bout en bout, hors tests/, du panneau Qt Quick Custom CAN Frame (a besoin d'une vraie boucle d'événements Qt)
├── verify_qt_telemetry_watch.py     Vraie vérification de bout en bout, hors tests/, de la télémétrie Qt Quick (Vacuum Pickup / Scan Probe)
├── verify_qt_utility_panels.py      Vraie vérification de bout en bout, hors tests/, des panneaux utilitaires Qt Quick (Global Controls / Expansion Board / F-RAM)
├── verify_qt_selftest.py            Vraie vérification de bout en bout, hors tests/, de l'autotest Qt Quick
├── tests/
│   └── test_advanced_protocol.py   Tests sans matériel pour les encodeurs de advanced_protocol.py - exécutés par la CI, voir Vérification d'honnêteté ci-dessus
├── requirements.txt            pyserial>=3.5 + PySide6>=6.8,<7
├── build_exe.bat               Script de build du binaire Windows autonome
│                                (PyInstaller)
├── build_exe.sh                Le même, pour Linux
├── build-test.bat              Contrôle build/compilation sans gestion de version
├── build-test.sh                Le même, pour Linux
├── bump.py                     Commande explicite pour monter la version (compiler ne la monte jamais)
├── bump_version.py             Incrément de version type compteur kilométrique, exécuté par les scripts de build
├── bump_manifest_version.py    Synchronise la version de urtc.project.json avec la version native (--sync)
├── URTC_Tester.spec            Spec PyInstaller utilisée par les deux scripts de
│                                build
├── assets/
│   ├── URTC_APP_ICON.svg       Source de l'icône fenêtre/barre des tâches (petit
│                                design autonome)
│   ├── URTC_LOGO_TESTER.svg    Source de la bannière (vectorielle)
│   ├── HYDRA_UMC_ICON.svg      Source vectorielle animée HYDRA-UMC maintenue
│   ├── qml/
│   │   └── TesterDeck.qml      UI Qt Quick du command deck par défaut
│   ├── urtc_icon.ico           Icône Windows, générée depuis URTC_APP_ICON.svg
│   └── urtc_icon.png           La même, en PNG (Linux)
├── images/
│   ├── URTC_LOGO_TESTER.svg    Bannière du logo affichée en haut de ce README
│   └── URTC_TESTER_V1_1.png    Capture d'écran de la fenêtre principale de l'outil
│                                (voir Photos ci-dessous)
├── language/
│   ├── english.lng             Langue par défaut, chaînes KEY=Value en texte brut
│   ├── spanish.lng
│   ├── italian.lng
│   ├── french.lng
│   ├── german.lng
│   ├── japanese.lng
│   ├── chinese.lng
│   └── portuguese.lng
├── logs/                       Journaux de session écrits ici à l'exécution (sans
│                                risque à supprimer)
├── LICENSE                     Texte complet de la licence - voir Licence et Avis
│                                de Copyright ci-dessous
├── NOTICE                      Mention de copyright et licence de la documentation
├── README.md                   Version anglaise
├── README_spa.md               Traduction espagnole
├── README_ita.md               Traduction italienne
├── README_fra.md               Ce fichier
├── README_deu.md               Traduction allemande
├── README_zho.md               Traduction chinoise
├── docs/
│   ├── ARCHITECTURE.md
│   ├── BUILD_AND_RUN.md
│   ├── INTEGRATION_CONTRACT.md
│   ├── CANBUS.md
│   └── THERMAL_RUNAWAY_BENCH_TEST.md
├── tools/
│   ├── build_test.py                     Contrôle de compilation sans gestion de version + validation des sources du deck Qt Quick
│   └── ci_validate.py                    Validation manifest/CHANGELOG/docs utilisée par la CI
└── README_jpn.md               Traduction japonaise
```

## 📸 Photos

<p align="center">
  <img src="images/URTC_TESTER_V1_1.png" alt="Fenêtre URTC Tester" width="700">
</p>

**Enregistreur de défauts, fonctions optionnelles, banc du rack et vue thermique (nouveau, vérifié avec des simulations seulement) :** le tableau lit la boîte noire de la carte (`0x1A8` / `0x1A9`) et l'enregistre en CSV et JSON, automatiquement une fois pour chaque erreur signalée par la carte quand cette option est activée ; il active les fonctions optionnelles du firmware (`0x1AE` / `0x1AF`, désactivées par défaut, effet au prochain démarrage) ; il propose un rack d'outils simulé avec le protocole série d'URTC-SMART-RACK, l'identité de chaque tête (type et numéro de série) et l'export d'une page d'état ; et il affiche l'image d'inspection thermique en fausses couleurs (une image simulée l'indique). Les noms et types d'outils viennent désormais des profils d'outil partagés d'URTC-COMMON. Rien de cela n'a été utilisé avec une vraie carte.

**PID du chauffage (nouveau, vérifié avec des simulations seulement) :** le pupitre lit l'état du PID du chauffage du firmware (`0x1B9` / `0x1BA` : les gains en vigueur, l'état et la sortie du dernier cycle de régulation), enregistre des gains (de 0 à 600) et lance ou annule l'autoréglage par relais, qui chauffe la panne autour de la consigne actuelle du fer à souder (100 à 445 C) et enregistre les gains trouvés. Enregistrer des gains et lancer l'autoréglage demandent la confirmation habituelle ; annuler non. La tête simulée de la ligne de commande (`--transport simulate`) répond aussi à ces trames. La fonction doit d'abord être activée parmi les fonctions optionnelles ; rien de cela n'a été utilisé avec une vraie carte.

## 🔗 Projets Liés

Ce projet fait partie de l'écosystème robotique HYDRA-UMC du même auteur (JuanenRac / Electro Hobby 3D). Bon à savoir, car une demande pourrait en réalité concerner l'un de ceux-ci plutôt que ce dépôt.

**Projet Parent**
- **[URTC](https://github.com/JuanenRac/URTC)** — firmware pour la carte physique Universal Robot Tool Controller, plus de 25 profils d'outil sur bus CAN ; le parent dont ce dépôt est un outil spécifique, au sein de sa propre famille d'outils CAN-bus.

**Projets Frères** — les autres outils de la propre famille d'outils CAN-bus d'URTC
- **[URTC-FLASHER](https://github.com/JuanenRac/URTC-FLASHER)** — outil de bureau à interface graphique pour flasher les cartes URTC, CAN-OTA plus SWD/JTAG puce complète.
- **[URTC-GATEWAY](https://github.com/JuanenRac/URTC-GATEWAY)** — une passerelle devant le bus CAN qui ne laisse passer que les identifiants d'une liste, limite leur débit et exige une clé de session.
- **[URTC-WEB-STUDIO](https://github.com/JuanenRac/URTC-WEB-STUDIO)** — alternative basée navigateur à URTC-TESTER via la Web Serial API, sans installation locale.

**Directement Liés**
- **[HYDRA-UMC-TOOL-CLI](https://github.com/JuanenRac/HYDRA-UMC-TOOL-CLI)** — CLI de flotte avec un vrai contrat de codes de sortie stable, un vrai client en direct de la propre API de HYDRA-UMC-SERVER — exécute des audits à l'échelle de la flotte (la commande `audit`) sur toutes les têtes d'outil à la fois, au-delà de la portée mono-carte couverte par ce testeur.
- **[URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL)** — firmware plus un vrai compagnon de vision Python pour une tête d'outil d'inspection thermique/RGB — complète le diagnostic CAN-bus en direct de ce projet avec ses propres contrôles visuels d'assurance qualité sur la tête d'outil.
- **[URTC-UPDATER](https://github.com/JuanenRac/URTC-UPDATER)** — outil de bureau qui détecte, installe et met à jour les dépôts de la famille URTC, une action explicite à la fois.

**Fait Également Partie de l'Écosystème**

*Matériel & Plateforme de Base*
- **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** — la conception de la carte mère du bras robotique : hôte CM5 + coprocesseur STM32H745 double cœur, destinée à coordonner jusqu'à 8 bras-outils via CAN-OTA/SPI-OTA (firmware à un stade précoce ; aucune carte assemblée pour l'instant).
- **[HYDRA-UMC-OS](https://github.com/JuanenRac/HYDRA-UMC-OS)** — couche produit reproductible sur Raspberry Pi OS pour le CM5 : agent en lecture seule, config/profils validés, provisionnement WiFi de premier contact.
- **[HYDRA-UMC-SDK](https://github.com/JuanenRac/HYDRA-UMC-SDK)** — le contrat JSON-Schema partagé et la barrière logicielle de contrôle des jobs contre laquelle chaque bridge valide ses commandes (pas une fonction de sécurité certifiée).
- **[HYDRA-UMC-CONNECTOR-HUB](https://github.com/JuanenRac/HYDRA-UMC-CONNECTOR-HUB)** — registre déclaratif et validateur de manifestes d'adaptateur pour les connecteurs de machines externes ; étend la propre idée de contrat du SDK aux machines externes sans remplacer les projets de passerelle industrielle.

*Backend Central & Clients*
- **[HYDRA-UMC-SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER)** — le vrai backend headless (REST/WebSocket) auquel parle réellement chaque client de contrôle.
- **[HYDRA-UMC-STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)** — tableau de bord de contrôle web avec visualisation 3D multi-robot en temps réel.
- **[HYDRA-UMC-SUITE](https://github.com/JuanenRac/HYDRA-UMC-SUITE)** — centre de commande d'essaim de bureau (PySide6) pour plusieurs serveurs à la fois, empaqueté en exécutable autonome.
- **[HYDRA-UMC-ANDROID-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-ANDROID-CONTROL)** — application de contrôle Android native avec connexion biométrique et un compagnon Wear OS jumelé.
- **[HYDRA-UMC-IOS-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-IOS-CONTROL)** — application de contrôle iOS/iPadOS (Flutter) avec synchronisation WebSocket en temps réel.
- **[HYDRA-UMC-DSI](https://github.com/JuanenRac/HYDRA-UMC-DSI)** — interface tactile native pour l'écran tactile DSI 7" embarqué, intégrée directement sur le CM5.
- **[HYDRA-UMC-EDITOR-URDF](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-URDF)** — créateur/éditeur graphique de bureau pour URDF qui envoie les modèles terminés vers le propre catalogue de STUDIO.
- **[HYDRA-UMC-EDITOR-STL](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-STL)** — éditeur de bureau de modèles STL, transformant/remplaçant/retirant/ajoutant de vraies pièces dans le même catalogue de modèles qu'édite aussi HYDRA-UMC-EDITOR-URDF.
- **[HYDRA-UMC-BRIDGE-AMR](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-AMR)** — frontière de coordination pour les flottes AGV/AMR via un éditeur MQTT VDA 5050 (testé uniquement contre une flotte émulée).
- **[HYDRA-UMC-BRIDGE-CNC](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-CNC)** — coordinateur haut niveau pour cellules CNC avec accès au statut/octets de contrôle GRBL (testé uniquement contre un émulateur).
- **[HYDRA-UMC-BRIDGE-DROIDS](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-DROIDS)** — frontière de coordination pour droïdes à pattes/humanoïdes, avec un émetteur de commandes Boston Dynamics Spot (testé uniquement contre un émulateur).
- **[HYDRA-UMC-BRIDGE-LASER](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-LASER)** — coordinateur de cellules laser lisant 3 signaux GPIO de clé/enceinte/verrouillage (testé uniquement contre une puce simulée ; il ne peut ni armer ni tirer un laser).
- **[HYDRA-UMC-BRIDGE-OPENPNP](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-OPENPNP)** — coordinateur haut niveau sûr pour le flux de cartes du pick-and-place OpenPnP.
- **[HYDRA-UMC-BRIDGE-PRINTER3D](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-PRINTER3D)** — frontière de coordination sûre pour imprimantes 3D Moonraker/Klipper, avec de vraies commandes de tâche contrôlées.
- **[HYDRA-UMC-BRIDGE-ROS2](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-ROS2)** — coordinateur avec un transport ROS 2 rclpy à importation paresseuse (pas encore exécuté contre une installation ROS 2).
- **[HYDRA-UMC-BRIDGE-UAV](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-UAV)** — frontière de coordination pour UAV équipés de caméra, avec un émetteur de commandes MAVLink (testé uniquement contre un émulateur).

*Nœud IA de Vision (Hailo-8)*
- **[HYDRA-UMC-VISION-NODE](https://github.com/JuanenRac/HYDRA-UMC-VISION-NODE)** — hub d'intégration pour le pipeline de vision Hailo-8, avec une vraie vérification de disponibilité matérielle par étape.
- **[HYDRA-UMC-DETECTION-HEF](https://github.com/JuanenRac/HYDRA-UMC-DETECTION-HEF)** — registre réel de modèles compilés avec vérification de chargement sécurisé par architecture Hailo/checksum.
- **[HYDRA-UMC-VISION-STREAMER](https://github.com/JuanenRac/HYDRA-UMC-VISION-STREAMER)** — générateur réel de pipeline GStreamer + config MediaMTX, avec une vraie frontière d'intégration HailoRT.
- **[HYDRA-UMC-VISUAL-SERVOING-API](https://github.com/JuanenRac/HYDRA-UMC-VISUAL-SERVOING-API)** — loi de correction Position-Based Visual Servoing avec autorisation conditionnée à l'état de zone ; pas encore d'estimation de pose par caméra.
- **[HYDRA-UMC-SAFETY-ZONES](https://github.com/JuanenRac/HYDRA-UMC-SAFETY-ZONES)** — logique v0 de violation de zone, de fraîcheur de calibration et de demande d'E-STOP qui lit les positions d'objets dans un fichier ; aucun détecteur ne l'alimente et aucun E-STOP physique n'y est encore relié.

*Nœud IA Cognitif (Hailo-10)*
- **[HYDRA-UMC-COGNITIVE-NODE](https://github.com/JuanenRac/HYDRA-UMC-COGNITIVE-NODE)** — hub d'intégration pour le pipeline cognitif Hailo-10 (orchestration LLM/VLA/voix).
- **[HYDRA-UMC-VLA-ENGINE](https://github.com/JuanenRac/HYDRA-UMC-VLA-ENGINE)** — vrai encodage/décodage de jetons d'action et génération de trajectoire pour un modèle Vision-Language-Action.
- **[HYDRA-UMC-VOICE-UI](https://github.com/JuanenRac/HYDRA-UMC-VOICE-UI)** — vrai front-end vocal (VAD + analyseur d'intention) avec un relais Watch borné et soumis à confirmation.
- **[HYDRA-UMC-SEMANTIC-PLANNER](https://github.com/JuanenRac/HYDRA-UMC-SEMANTIC-PLANNER)** — vraie décomposition de tâches basée sur des règles et récupération sémantique d'erreurs sur les codes d'erreur MCU.
- **[HYDRA-UMC-DOCS-QA](https://github.com/JuanenRac/HYDRA-UMC-DOCS-QA)** — vraie recherche documentaire TF-IDF (bibliothèque standard uniquement) sur les propres documents Markdown de cet écosystème.
- **[HYDRA-UMC-LOCAL-TECHNICIAN](https://github.com/JuanenRac/HYDRA-UMC-LOCAL-TECHNICIAN)** — technicien de maintenance IA local et à portes de politique pour l'écosystème lui-même - observe, diagnostique et propose des corrections ; les deux niveaux de risque les plus élevés ne sont délibérément pas encore implémentés.

*Orchestration & Essaim*
- **[HYDRA-UMC-ORCHESTRATOR](https://github.com/JuanenRac/HYDRA-UMC-ORCHESTRATOR)** — hub d'intégration avec un vrai contrat de rapport de santé gRPC/Protobuf et une machine à états de mission.
- **[HYDRA-UMC-JOB-DISPATCHER](https://github.com/JuanenRac/HYDRA-UMC-JOB-DISPATCHER)** — vraie file de tâches basée sur la priorité avec déduplication, via une vraie API HTTP.
- **[HYDRA-UMC-NODE-HEALING](https://github.com/JuanenRac/HYDRA-UMC-NODE-HEALING)** — vrai chien de garde de santé de flotte basé sur gRPC, avec retry/backoff et détection d'incohérence d'identité.
- **[HYDRA-UMC-PATH-PLANNER-3D](https://github.com/JuanenRac/HYDRA-UMC-PATH-PLANNER-3D)** — vrai planificateur de trajectoire 3D basé sur RRT, avec vraie validation des collisions obstacle/espace de travail.
- **[HYDRA-UMC-SWARM-SYNC](https://github.com/JuanenRac/HYDRA-UMC-SWARM-SYNC)** — vraie synchronisation d'état CRDT LWW-Element-Map, testée par propriétés pour la convergence multi-cellule.

*Jumeau Numérique & Simulation*
- **[HYDRA-UMC-TWIN](https://github.com/JuanenRac/HYDRA-UMC-TWIN)** — hub d'intégration pour le moteur de jumeau numérique, avec un vrai contrat de synchronisation par compatibilité de version.
- **[HYDRA-UMC-HIL-BRIDGE](https://github.com/JuanenRac/HYDRA-UMC-HIL-BRIDGE)** — routeur hardware-in-the-loop avec un verrouillage logiciel de collision entre simulation et matériel réel (testé sans matériel réel).
- **[HYDRA-UMC-PHYSICS-REPLICA](https://github.com/JuanenRac/HYDRA-UMC-PHYSICS-REPLICA)** — vraie cinématique directe et validation des limites articulaires sur un vrai sous-ensemble URDF.
- **[HYDRA-UMC-SYNTHETIC-DATA-GEN](https://github.com/JuanenRac/HYDRA-UMC-SYNTHETIC-DATA-GEN)** — vrai générateur procédural de scènes 2D avec export d'annotations YOLO/COCO.

*Données & Analytique*
- **[HYDRA-UMC-DATALAKE](https://github.com/JuanenRac/HYDRA-UMC-DATALAKE)** — vrai magasin de séries temporelles basé sur sqlite3, avec une vraie API HTTP d'ingestion/requête.
- **[HYDRA-UMC-ANOMALY-DETECTOR](https://github.com/JuanenRac/HYDRA-UMC-ANOMALY-DETECTOR)** — vrai détecteur d'anomalies FFT + ligne de base statistique, avec surveillance de dérive.
- **[HYDRA-UMC-PRODUCTION-REPORTS](https://github.com/JuanenRac/HYDRA-UMC-PRODUCTION-REPORTS)** — vrai calcul OEE/disponibilité sur l'historique de DATALAKE, avec export CSV reproductible.
- **[HYDRA-UMC-TELEMETRY-COLLECTOR](https://github.com/JuanenRac/HYDRA-UMC-TELEMETRY-COLLECTOR)** — vrai pipeline d'ingestion CAN/WebSocket vers DATALAKE, avec déduplication par séquence.

*Passerelle Industrielle*
- **[HYDRA-UMC-GATEWAY-INDUSTRIAL](https://github.com/JuanenRac/HYDRA-UMC-GATEWAY-INDUSTRIAL)** — hub d'intégration relayant vers les protocoles industriels, avec une vraie couche de liste blanche de commandes/contre-pression.
- **[HYDRA-UMC-OPCUA-SERVER](https://github.com/JuanenRac/HYDRA-UMC-OPCUA-SERVER)** — vrai espace d'adressage OPC-UA, vérifié avec une vraie session client du protocole binaire.
- **[HYDRA-UMC-MQTT-BROKER](https://github.com/JuanenRac/HYDRA-UMC-MQTT-BROKER)** — vrai broker MQTT avec authentification par client optionnelle et ACL de sujets.
- **[HYDRA-UMC-MTCONNECT-ADAPTER](https://github.com/JuanenRac/HYDRA-UMC-MTCONNECT-ADAPTER)** — vrais points de terminaison XML MTConnect `/probe` et `/current`, avec sortie en mode dégradé.

*Outils Complémentaires & Opérations de l'Écosystème*
- **[HYDRA-UMC-DASHBOARD-AI](https://github.com/JuanenRac/HYDRA-UMC-DASHBOARD-AI)** — panneaux Smart Summaries et Anomaly Highlighting sur DATALAKE/ANOMALY-DETECTOR, avec un repli statistique honnête.
- **[HYDRA-UMC-WATCH](https://github.com/JuanenRac/HYDRA-UMC-WATCH)** — application compagnon WearOS avec des motifs d'alerte haptique et un relais vocal vers le téléphone jumelé (pas encore exécutée sur une montre physique).
- **[URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK)** — firmware pour un rack de montage de cartes avec décodage réel d'ID d'outil et logique de préchauffage Smart Idle.
- **[HYDRA-UMC-UPDATER](https://github.com/JuanenRac/HYDRA-UMC-UPDATER)** — outil administratif de bureau qui découvre, clone et met à jour chaque dépôt de cet écosystème.
- **[HYDRA-UMC-OS-REBUILDER](https://github.com/JuanenRac/HYDRA-UMC-OS-REBUILDER)** — outil de bureau Windows/Linux qui construit une image de la CM5 prête à graver, préchargée avec les versions les plus actuelles de l'écosystème, avec une configuration de premier démarrage Wi-Fi/utilisateur/SSH façon Raspberry Pi Imager.
- **[HYDRA-UMC-OPS-AGENT](https://github.com/JuanenRac/HYDRA-UMC-OPS-AGENT)** — coordinateur d'incidents de maintenance : un rôle edge à faible privilège collecte un instantané d'inventaire/santé assaini, un rôle control-plane le rend en lecture seule et demande à un fournisseur d'IA de suggérer un diagnostic - n'applique jamais de correctif ni ne déploie rien.
- **[HYDRA-UMC-DEV-SERVER](https://github.com/JuanenRac/HYDRA-UMC-DEV-SERVER)** — hôte de développement reproductible (Raspberry Pi 5 / CM5) qui héberge le code source de l'écosystème et exécute des tâches de compilation/test délimitées via une file d'attente durable ; un rôle de développement dédié, explicitement distinct d'un CM5 opérationnel.

## 📜 LICENCE

URTC Tester est (c) 2026 JuanenRac (Electro Hobby 3D). Cet avis doit
être inclus dans toute distribution de ce projet ou de ses travaux
dérivés.

Ce projet consiste en du code source et sa propre documentation,
disponibles sous des licences différentes - chacune adaptée à ce
qu'elle couvre réellement :

1. Le code source (`urtc_tester.py` et chaque module `tester_*.py`) et
   tout binaire construit à partir de celui-ci via
   `build_exe.bat`/`build_exe.sh` sont disponibles sous la
   **GNU General Public License v3.0 or later (GPL-3.0-or-later)**. Texte complet sur
   https://www.gnu.org/licenses/gpl-3.0.html.

2. La documentation (ce README et ses propres traductions -
   `README_spa.md`, `README_ita.md`, `README_fra.md`, `README_deu.md`,
   `README_zho.md`, `README_jpn.md`, `README_por.md` et les guides de `docs/`)
   est disponible sous **Creative Commons Attribution-ShareAlike 4.0
   International (CC BY-SA 4.0)**. Texte complet sur
   https://creativecommons.org/licenses/by-sa/4.0/.

Cet outil est le compagnon de diagnostic live du bus CAN du projet
[URTC (Universal Robot Tool Controller)](https://github.com/JuanenRac/URTC)
- voir le propre dépôt de ce projet pour le firmware de la carte, les
conceptions matérielles, et la documentation complète du protocole que
cet outil exerce. Le propre firmware d'URTC est GPL-3.0-or-later et ses
conceptions matérielles sont CERN-OHL-S v2 ; la propre licence de cet
outil ici ne s'étend pas à ce projet séparé, et vice-versa. Une
alternative basée sur le web couvrant un terrain similaire existe aussi
sur
[URTC Web Studio](https://github.com/JuanenRac/URTC-WEB-STUDIO).

Si vous construisez sur ce projet, gardez la séparation des licences à
l'esprit : les modifications de code devraient rester GPL-3.0-or-later, les
dérivés de documentation devraient rester CC BY-SA - chacun avec une
attribution à ce projet et son auteur.

---

## 📚 Documentation & Communauté

- **[CONTRIBUTING.md](CONTRIBUTING.md)** — pile technologique et lignes directrices de codage pour une pull request.
- **[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)** — les normes de comportement attendues dans cette communauté.
- **[SECURITY.md](SECURITY.md)** — comment signaler une vulnérabilité, et les véritables axes de sécurité de ce projet.
- **[SUPPORT.md](SUPPORT.md)** — où poser des questions et signaler des bugs.
- **[LICENSE.md](LICENSE.md)** — la licence propre de ce projet.

## 👤 AUTEUR

**JuanenRac** (Electro Hobby 3D)
📧 electrohobby3d@gmail.com
📺 [youtube.com/@electrohobby3d](https://youtube.com/@electrohobby3d)
