<p align="center">
  <img src="/images/URTC_TESTER_BANNER.svg" alt="URTC Tester Logo" width="100%">
</p>

# URTC Tester (Windows / Linux)

<p align="center">
  <a href="README.md">🇺🇸 English</a> |
  <a href="README_spa.md">🇪🇸 Español</a> |
  <a href="README_fra.md">🇫🇷 Français</a> |
  <a href="README_ita.md">🇮🇹 Italiano</a> |
  🇩🇪 <b>Deutsch</b> |
  <a href="README_zho.md">🇨🇳 简体中文</a> |
  <a href="README_jpn.md">🇯🇵 日本語</a> |
  <a href="README_por.md">🇵🇹 Português</a>
</p>

### Ein Live-CAN-Bus-Prüfer für die URTC-Platine: Er zeigt nur die Bedienelemente und die Telemetrie des angesteckten Werkzeugkopfs

<p align="center">
  <img src="https://img.shields.io/badge/Lizenz-GPL%203.0-blue.svg" alt="GPL 3.0 or later">
  <img src="https://img.shields.io/badge/Sprache-Python-3776AB.svg" alt="Python">
  <img src="https://img.shields.io/badge/UI-Qt%20Quick-38d4e6.svg" alt="Qt Quick">
  <img src="https://img.shields.io/badge/Protokoll-CAN-yellow.svg" alt="CAN">
</p>

---

**Ehrlichkeitscheck - was heute wirklich funktioniert:** die CAN-Payload-Encoder für die auf Qt Quick migrierten Steuerungsfamilien (`advanced_protocol.py`) sind real und durch die Tests in `tests/` abgedeckt (`python -m pytest -q`). Die eigene CI dieses Repos (`.github/workflows/ci.yml`) führt sie ebenfalls aus, zusammen mit `ruff check`, `python -m mypy`, `tools/ci_validate.py`, einer Syntaxkompilierung jeder `.py`-Datei und den vier `verify_qt_*.py`-Skripten, sodass eine Regression dort den Build fehlschlagen lässt. Die vier `verify_qt_*.py`-Skripte im Repo-Root (`verify_qt_custom_frame.py`, `verify_qt_telemetry_watch.py`, `verify_qt_utility_panels.py`, `verify_qt_selftest.py`) sind echte, bewusst außerhalb von `tests/` gehaltene End-to-End-Prüfungen gegen einen simulierten Transport mit echter Cross-Thread-Signal-Zustellung - alle vier bestehen mit `QT_QPA_PLATFORM=offscreen python verify_qt_*.py`, was die CI ebenfalls ausführt. Das ist die ehrliche Obergrenze dessen, was automatisch verifiziert wird: die Transportschicht, die CAN-ID-/Byte-Layout-Verarbeitung und die Qt-Quick-Brückenlogik sind real und werden gegen simulierte Frames geprüft, nicht gegen echte Hardware - wie "Known limitations" weiter unten bereits sagt, wurde dies ohne USB-Zugriff gebaut, sodass hier noch nichts gegen eine echte Platine geprüft wurde. `qt_tester.py` und `assets/qml/TesterDeck.qml` sind die reale, umfangreiche Implementierung (zusammen tausende Zeilen), geprüft durch die Tests mit simulierten Platinen und die Verify-Skripte, nie durch eine echte Platine.

---

> **Stand von Sicherheit (Safety) und Security:** Dieses Ökosystem ist kein zertifiziertes Sicherheitssystem, und es existiert noch keine bestückte URTC-Platine. Die Bootloader prüfen Firmware-Images mit CRC32 und einem HMAC-SHA256 mit gemeinsamem Schlüssel, nicht mit einer asymmetrischen Signatur (geplant); die veröffentlichten Anwendungs-Images sind mit dem öffentlichen Entwicklungsschlüssel signiert (`signing_key_kind: dev`), sodass jeder ein vom Bootloader akzeptiertes Image erzeugen kann; an eine echte Platine wurde noch nichts gesendet. Lesen Sie die [Sicherheitsbasis](https://github.com/JuanenRac/URTC-DOCS/blob/main/docs/SECURITY_BASELINE.md) und das [Bedrohungsmodell](https://github.com/JuanenRac/URTC-DOCS/blob/main/docs/THREAT_MODEL.md), bevor Sie sich für die Sicherheit einer Person auf eine Aussage hier verlassen.

## 📋 Auf einen Blick

| | |
|---|---|
| Version | `0.4.3` |
| Reifegrad | Funktionsfähig |
| Tests | 578 (`python -m pytest -q`) |
| Technik | Python / PySide6 / Qt Quick / live CAN bus diagnostics |
| Ziel | Der PC der Person, die es benutzt |
| Auf echter Hardware | Nur simuliert: gegen Emulatoren, Attrappen oder Simulatoren getestet; für diese Version ist kein Lauf auf echter Hardware vermerkt |

**Springe zu:** [Überblick](#-überblick) · [Architektur](#-architektur) · [Funktionen](#-funktionen) · [Sicherheit](#-sicherheit-und-schutz) · [Schnittstellen](#-schnittstellen) · [Schnellstart](#-schnellstart) · [Tests](#-tests) · [Struktur](#-struktur-des-repositorys) · [Verwandte](#-verwandte-projekte)

<!-- urtc-section:status_tester -->
## 🚦 Projektstatus

🟢 fertig und überprüft · 🟡 funktioniert, mit bekannten Grenzen · 🟠 halb fertig oder nicht überprüft · 🔴 nicht gemacht oder funktioniert nicht. Nichts ist grün, wenn es nie auf echter Hardware lief.

| Teil | Status | Was das Repository belegen kann |
| --- | :---: | --- |
| Software | 🟡 | Läuft am PC und gegen den Simulator; nie an einer echten Platine ausgeführt. |
| Oberfläche | 🟡 | Das Fenster läuft und wird gegen eine simulierte Platine geprüft; nicht mit einem echten Adapter probiert. |
| Tests | 🟢 | Die Testsuite besteht bei jedem Push in der CI. |
| Echte Hardware | 🟠 | Noch kein Lauf an einer echten Platine: der Bankversuch steht noch aus. |
| Dokumentation | 🟡 | README in acht Sprachen und Referenzdokumente; die Übersetzungen wurden nicht von Muttersprachlern geprüft. |

<!-- /urtc-section:status_tester -->

## 🎯 Überblick

Ein Live-CAN-Bus-Testwerkzeug für die URTC-Platine. Es verbindet sich
über denselben USB-CAN-Adapter, den auch der Flasher verwendet, fragt
die Platine, für welches ihrer 25 Werkzeugprofile sie aktuell per Jumper
konfiguriert ist, und zeigt nur die eigenen Steuerelemente und die
Telemetrie dieses Werkzeugs - nicht ein einziges Fenster, das versucht,
alle 25 gleichzeitig darzustellen. Alles, was es tut, ist ein
Laufzeitbefehl oder ein Telemetrie-Lesevorgang gegen die laufende
Anwendung; es berührt niemals die Flash, sodass es hier nichts gibt, das
die Platine weniger funktionsfähig zurücklassen könnte, als sie
begonnen hat.

### Beziehung zum Flasher

Dieses Tool und [URTC Flasher](https://github.com/JuanenRac/URTC-FLASHER) teilen sich denselben
Transport-Layer (die SLCAN- und SocketCAN-Klassen sind identisch), da
beide letztlich nur CAN-Frames auf denselben Adaptertyp bringen und von
ihm holen müssen, aber sie erledigen grundlegend unterschiedliche
Aufgaben:

| | Flasher | Tester |
|---|---|---|
| Berührt die Flash | Ja (das ist der ganze Sinn) | Nie |
| Spricht mit | Hauptsächlich dem Bootloader | Der laufenden Anwendung |
| Zweck | Firmware aktualisieren | Die tatsächliche Hardware eines Werkzeugkopfs testen/verifizieren |

Wenn Sie nicht sicher sind, welches Sie brauchen: wenn die Platine
bereits Firmware ausführt und Sie prüfen wollen, ob ein Werkzeug
tatsächlich funktioniert (die Heizung heizt, der Motor dreht sich, die
LED leuchtet), wollen Sie dieses.

## 🧩 Rolle in URTC

URTC-TESTER ist das Programm, das prüft, was ein URTC-Werkzeugkopf tatsächlich tut, während er seine Anwendung ausführt: Es verbindet sich über denselben USB-CAN-Adapter wie URTC-FLASHER, fragt die Platine, für welches ihrer 25 Werkzeugprofile sie gebrückt ist, und zeigt nur die Bedienelemente und die Telemetrie dieses Werkzeugs, nie ein Fenster, das alle 25 darstellen will. Alles, was es tut, ist ein Befehl zur Laufzeit oder ein Telemetrie-Lesezugriff; es berührt nie den Flash und kann eine Platine daher nicht schlechter zurücklassen, als es sie vorgefunden hat. Das Protokoll ist das von URTC-COMMON, und URTC-WEB-STUDIO bietet dieselben Abläufe im Browser.

## 🏛️ Architektur

<p align="center">
  <img src="images/architecture.svg" alt="Architektur von URTC-TESTER: wer es nutzt, was es enthält und wovon es abhängt" width="100%">
</p>

Wie die Teile dieses Repositorys zusammenpassen: wer es nutzt, was es enthält und wovon es abhängt. Das Bild wird aus `docs/architecture.json` gezeichnet und gegen den Code geprüft.

<!-- urtc-section:updates -->
### So wird aktualisiert

Dieses Programm kann nach einer neueren Version seiner selbst suchen: Die Schaltfläche „Nach Updates suchen“ fragt GitHub einmal und bietet ein signiertes Paket nur an, wenn es für Ihr System ist und neuer. Nichts wird von selbst geprüft oder installiert, solange Sie die Prüfung nicht einschalten, und ein Update braucht Ihre Bestätigung. Das Paket muss zu seinem SHA-256 und zur Signatur des im Programm angehefteten Release-Schlüssels passen; die vorherige Version bleibt erhalten und wird von selbst wiederhergestellt, wenn die neue nicht startet. `urtc-updater --cli package list|check|install|rollback` macht dasselbe auf der Kommandozeile für Flasher und Tester, und `install --file` funktioniert ohne Netzwerk.
<!-- /urtc-section:updates -->

## 🖼️ Screenshots

<!-- urtc-shots -->
Aufgenommen mit 1920×1080 auf einem Prüfstand, mit Beispieldaten und ohne eine echte Anlage dahinter.

<table>
<tr>
<td width="50%" valign="top"><img src="images/screenshots/deck.png" alt="Das Fenster beim Öffnen: das Transport-Tor, der Sicherheitsmodus „nur lauschen“, die Werkzeugprofile und die Kontrollpunkte für Identität und Zustand." width="100%"><br><sub>Das Fenster beim Öffnen: das Transport-Tor, der Sicherheitsmodus „nur lauschen“, die Werkzeugprofile und die Kontrollpunkte für Identität und Zustand.</sub></td>
<td width="50%" valign="top"><img src="images/screenshots/heads.png" alt="Werkzeugköpfe am Bus: ein modellierter Bus mit sechs Köpfen, jeder in einem anderen möglichen Zustand (gewählt, Adresskonflikt, Fehler gehalten, im Bootloader, verloren und bereit)." width="100%"><br><sub>Werkzeugköpfe am Bus: ein modellierter Bus mit sechs Köpfen, jeder in einem anderen möglichen Zustand (gewählt, Adresskonflikt, Fehler gehalten, im Bootloader, verloren und bereit).</sub></td>
</tr>
<tr>
<td width="50%" valign="top"><img src="images/screenshots/help.png" alt="Das Hilfefenster: die Schritte zur Benutzung des Programms, in der Sprache des Fensters." width="100%"><br><sub>Das Hilfefenster: die Schritte zur Benutzung des Programms, in der Sprache des Fensters.</sub></td>
<td width="50%" valign="top"><img src="images/screenshots/updates.png" alt="Das Update-Fenster: ein neueres signiertes Paket wird erst nach deiner Bestätigung installiert." width="100%"><br><sub>Das Update-Fenster: ein neueres signiertes Paket wird erst nach deiner Bestätigung installiert.</sub></td>
</tr>
</table>
<!-- /urtc-shots -->

**Fehlerrekorder, optionale Funktionen, Rack-Prüfstand und Wärmebild (neu, nur mit Attrappen geprüft):** Das Deck liest die Blackbox der Platine (`0x1A8` / `0x1A9`) und speichert sie als CSV und JSON, bei eingeschalteter Option automatisch einmal für jeden gemeldeten Fehler; es schaltet die optionalen Firmware-Funktionen (`0x1AE` / `0x1AF`, standardmäßig aus, wirksam nach dem nächsten Einschalten); es hat ein simuliertes Werkzeug-Rack mit dem seriellen Protokoll von URTC-SMART-RACK, der Identität jedes Kopfes (Typ und Seriennummer) und dem Export einer Statusseite; und es zeigt das Wärmebild der thermischen Inspektion in Falschfarben (ein simuliertes Bild sagt das). Die Werkzeugnamen und -arten stammen jetzt aus den gemeinsamen Werkzeugprofilen von URTC-COMMON. Nichts davon wurde mit einer echten Platine benutzt.

**Heizer-PID (neu, nur mit Attrappen geprüft):** das Deck liest den Zustand des Heizer-PID der Firmware (`0x1B9` / `0x1BA`: die gültigen Verstärkungen, den Zustand und den Ausgang des letzten Regelzyklus), speichert Verstärkungen (0 bis 600) und startet oder bricht den Relais-Autotune ab, der die Spitze um den aktuellen Sollwert des Lötkolbens (100 bis 445 C) heizt und die gefundenen Verstärkungen speichert. Verstärkungen speichern und den Autotune starten verlangen die übliche Bestätigung, das Abbrechen nicht. Der simulierte Kopf der Kommandozeile (`--transport simulate`) beantwortet diese Frames ebenfalls. Die Funktion muss vorher bei den optionalen Funktionen eingeschaltet werden; nichts davon wurde mit einer echten Platine benutzt.

Diese Bilder zeigen das echte Fenster, ohne Bildschirm gezeichnet, so wie es sich öffnet (nichts verbunden, nichts gesendet). Die Anleitung führt durch das Deck, das Hilfefenster und das Update-Fenster.

[Anleitung mit Bildern](docs/WINDOW_GUIDE.md)

## ✨ Funktionen

### Wie es funktioniert

Das Fenster ist in 3 Spalten angeordnet: links und mittig enthalten die
immer sichtbaren Abschnitte unten (1-4, dann 6), rechts enthält das
Panel pro Werkzeug aus Abschnitt 5, das der einzige Teil des Fensters
ist, der sich tatsächlich basierend darauf ändert, was erkannt wird.
Die immer sichtbaren Abschnitte auf 2 Spalten statt alle in einer zu
stapeln, hält das Fenster davon ab, so hoch zu wachsen, dass es nicht
mehr auf einen normalen Bildschirm passt, während im Laufe der Zeit
mehr dieser Abschnitte hinzugefügt wurden. Das eigene Panel des
3D-Druckers (das höchste der 25) geht noch einen Schritt weiter und
teilt seine eigenen Steuerelemente intern in 2 Unterspalten, aus
demselben Grund. Siehe [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) für
den Architektur-Leitfaden auf Modulebene, den dieser Abschnitt
zusammenfasst.

**Verbinden** (Abschnitt 1, identisch zum Flasher): wählen Sie
Seriell/SLCAN oder SocketCAN, den Port/die Schnittstelle, erkennen Sie
optional die Bitrate automatisch, dann Verbinden.

**Die Erkennung erfolgt automatisch beim Verbinden** (oder klicken Sie
auf **Erkennen**, um sie zu wiederholen): das Tool sendet `0x110`
(aktives Werkzeug abfragen) und `0x7F8` (Version abfragen), und
verwendet die Antwort, um:
- Zu zeigen, welches der 25 Werkzeugprofile aktiv ist, und den
  Gesamtstatus der Platine (jeder deklarierte Fehler, CAN-Busfehler,
  noch im Start-Splashscreen).
- Die gemeldete HardwareID und Firmware-Version anzuzeigen und eine
  Abweichung zu kennzeichnen, falls sie nicht mit der eigenen
  `THIS_HARDWARE_ID` dieses Projekts übereinstimmt.
- Das Panel **Werkzeugsteuerung** rechts für dieses spezifische
  Werkzeug zu erstellen - und nur dieses Werkzeug. Das Wechseln, welches
  Werkzeug gejumpert ist, und erneutes Erkennen baut das alte Panel ab
  und erstellt das neue von Grund auf neu.

**Globale Steuerung** (Abschnitt 2, immer sichtbar unabhängig davon,
welches Werkzeug aktiv ist): die Übersteuerung der Status-LED-Farbe,
die Ring-LED-Farbe und Ein/Aus, und der OLED-Anzeigemodus (`0x100`) -
diese gelten für jedes Werkzeug, sodass sie nicht in das dynamische
Panel wandern. Im AOI-Inspektionsmodus speziell wird das Ein/Aus des
Rings hier zugunsten der eigenen Stroboskopsteuerung dieses Werkzeugs
ignoriert (gemäß [docs/CANBUS.md](docs/CANBUS.md)) - die Farbe gilt in beiden Fällen
trotzdem.

**Erweiterungsplatine** (Abschnitt 3, immer sichtbar): der eigene
generische SPI-Bus und die DIAG0-Leitung von `CONN_EXPANSION` - der
rohe Durchgang, den sich alle Erweiterungsplatinen-Varianten mit
Treiber teilen. Der ADS1115 und die MLX9064x-Sensoren sowie der eigene
Treiber des Crimp-Aktuators werden nicht von hier gesteuert - sie leben
stattdessen im Panel des jeweiligen Werkzeugs (Flying Probe, PCB
Advanced Inspection, Crimping Actuator - siehe Abschnitt 4 unten), da
davon abhängt, welches davon tatsächlich zutrifft, welches
Werkzeugprofil per Jumper konfiguriert ist.

**Persistenz-F-RAM** (Abschnitt 4, ebenfalls immer sichtbar, aber
absichtlich getrennt von Erweiterungsplatine oben): die FM24CL64B teilt
sich den eigenen Hardware-I2C2-Bus mit dem OLED - eine Kernkomponente
der Platine, überhaupt nicht etwas, das mit `CONN_EXPANSION` verdrahtet
ist. Die beiden zusammen zu gruppieren würde eine Verbindung zwischen
ihnen implizieren, die nicht real ist - der Erweiterungssteckverbinder
selbst hat kein F-RAM, kein EEPROM, nichts nichtflüchtiges darauf.
- **SPI-Durchleitung**: geben Sie durch Leerzeichen getrennte Hex-Bytes
  ein (1-7 davon, z. B. `01 02 03`), drücken Sie Senden, und sehen Sie
  genau, was während dieser selben Übertragung auf MISO zurückkam
  (`0x180`/`0x181`) - ein roher Byte-Transport, nicht
  TMC5160-Register-bewusst, entsprechend dem eigenen Ansatz der
  Firmware. Nützlich, um den Bus selbst zu testen, bevor sich der Bau
  eines dedizierten Panels für das Registerprotokoll einer bestimmten
  Erweiterungsplatine lohnt.
- **DIAG0-Pegel**: **DIAG0 abfragen** liest den aktuellen Zustand der
  Stall-/Fehler-Diagnoseleitung eines TMC5160 (`0x182`/`0x183`) - HIGH
  (inaktiv) oder LOW (ausgelöst). Ein einfacher abgefragter
  Lesevorgang, kein Live-/gepushter Wert - drücken Sie die
  Schaltfläche erneut, um ihn zu aktualisieren.
- **Persistenz-F-RAM**: **Zustand abfragen** liest zurück, was die
  Platine zuletzt vor einem Stromausfall gespeichert hat
  (`0x190`/`0x191`) - welches Werkzeug es war, den Sollwert, ob zu
  diesem Zeitpunkt ein kritischer Fehler aktiv war. **F-RAM löschen...**
  löscht es (`0x192`, zuerst mit einem Bestätigungsdialog - dies kann
  nicht rückgängig gemacht werden).
- **Erweiterungsplatinentyp**: **Abfragen** zeigt, welche der 7
  möglichen `CONN_EXPANSION`-Konfigurationen aktuell eingestellt ist
  (`0x1A1` - siehe `EXPANSION.TXT`). Hier schreibgeschützt - stellen
  Sie es stattdessen über den eigenen CAN-OTA-Abschnitt von `URTC
  Flasher` ein, da es sich um einen einmaligen
  Hardware-Konfigurationsschritt handelt, nichts, das beiläufig von
  einem Live-Diagnosetool geändert werden sollte.
- **MLX9064x-Sensorvariante**: **Abfragen** zeigt, welcher der 3
  Wärmesensoren der MLX9064x-Familie (oder keiner) aktuell konfiguriert
  ist (`0x1A7` - siehe `CANBUS.md`) - nur relevant, wenn der obige
  Erweiterungsplatinentyp eine Advanced-Variante oder Basic+MLX9064x
  ist. Hier schreibgeschützt, gleiche Begründung wie beim
  Erweiterungsplatinentyp oben.
- **Freie Werkzeugkonfiguration**: **Abfragen** zeigt die rohe
  ID-Jumper-Ablesung (0-31) neben dem, was das
  `free_tool_selection`-Register des F-RAM aktuell sagt (`0x1A3` -
  siehe `EEPROM.TXT` Abschnitt 5) - tatsächlich nur konsultiert von
  einer Platine, deren Jumper 0x1F/11111b lesen. Hier ebenfalls
  schreibgeschützt, dieselbe Begründung wie beim
  Erweiterungsplatinentyp oben - `URTC Flasher` ist das einzige Tool,
  das es schreibt.
- **Peripherietyp und Seriennummer**: **Abfragen** zeigt den festen
  Peripherietyp (immer URTC/0x03) neben der aktuell eingestellten
  Geräteseriennummer (`0x1A5` - siehe `EEPROM.TXT` Abschnitt 6), eine
  vom Host zugewiesene Kennung, um mehrere ansonsten identische
  Platinen auf demselben CAN-Bus zu unterscheiden. Hier ebenfalls
  schreibgeschützt - `URTC Flasher` schreibt die Seriennummer, dieses
  Tool liest sie nur zurück.

**Benutzerdefinierter CAN-Frame** (Abschnitt 6, ebenfalls immer
sichtbar): eine rohe ID-Eingabe + Hex-Bytes mit Einmal- und periodischem
Senden - für einen Befehl, der hier noch keine eigene Steuerung hat,
oder um etwas zu testen, das nicht (oder noch nicht) in
`docs/CANBUS.md` dokumentiert ist. Keine Validierung über den
ID-Bereich und DLC≤8 hinaus; was auch immer dies sendet, ist genau das,
was auf den Bus geht. Derselbe Abschnitt öffnet auch den **Rohen
Bus-Monitor** (siehe unten).

**Selbsttest ausführen** (neben Erkennen): führt einen kleinen Satz
sicherer, ruhender Kommunikationsprüfungen für das aktuell erkannte
Werkzeug aus - bestätigt, dass sowohl die Abfrage des aktiven Werkzeugs
als auch die Versionsabfrage antworten, dann (für Werkzeuge mit
Telemetrie) sendet einen sicheren Sollwert/Geschwindigkeit/Leistung von
0 und prüft, ob die erwartete Telemetrie ankommt. Sendet absichtlich
nie etwas, das tatsächlich mit bedeutsamer Leistung heizen, feuern oder
drehen würde - dies verifiziert, dass der Kommunikations-Roundtrip
funktioniert, nicht, dass ein Aktuator physisch reagiert, da die
Bestätigung dessen sowieso einen zusehenden Menschen erfordert. Fragt
vor dem Senden von irgendetwas nach Bestätigung. Werkzeuge ohne
Telemetrie (einfache Bewegung) oder die rein ereignisgesteuert sind
(Scan-Sonde) erhalten stattdessen einen reinen Informationshinweis statt
eines echten Bestanden/Fehlgeschlagen. **Die Abdeckung ist
unvollständig**: nur 7 der 25 Werkzeuge haben einen definierten
Selbsttest-Schritt (Lötkolben, Bohrer, Laser, 3D-Drucker, AOI, Vakuum,
Scan-Sonde) - die anderen 18 Werkzeuge führen bei Betätigung dieser
Schaltfläche keine Prüfung aus.

**Live-Temperaturgraphen**: sowohl die Panels des Lötkolbens als auch
der 3D-Drucker-Düse zeigen jeweils ein kleines rollendes Liniendiagramm
neben ihrer Live-Temperaturmessung - eine einfache Qt-Quick-Canvas-Fläche,
keine neue Abhängigkeit (matplotlib/pyqtgraph würden die
Null-Abhängigkeits-Richtlinie dieses Tools über pyserial hinaus
brechen). Feste Y-Achsen-Skala (0 bis zur eigenen Sollwertobergrenze
dieses Werkzeugs) statt automatischer Skalierung, sodass der Trend auf
einen Blick leicht zu lesen ist, statt dass sich die Skala darunter
verschiebt.

**Roher Bus-Monitor** (geöffnet aus dem Abschnitt Benutzerdefinierter
CAN-Frame): ein separates Fenster, das jeden gesehenen Frame zeigt,
jede ID, unabhängig vom aktiven Werkzeugpanel - eine live-scrollende
Tabelle (Zeit/ID/DLC/Daten/Δt), Pause/Löschen, und eine ungefähre
Busauslastungs-/Frame-Rate-Anzeige (einmal pro Sekunde aktualisiert;
die Auslastungszahl modelliert nicht den Bit-Stuffing-Overhead, also
behandeln Sie sie als ungefähre Diagnosezahl, keine zertifizierte
Messung). **Exportieren .trc...**/**Exportieren .asc...** speichern die
aktuell angezeigte Tabelle als vereinfachte Trace-Datei im Stil von
PEAK PCAN-View bzw. Vector CANalyzer - nah genug, um von den meisten
Tools, die diese Formate erwarten, lesbar zu sein, nicht garantiert
byte-identisch zu dem, was die echten Anwendungen produzieren. Wenn
`urtc_custom_ids.json` neben diesem Skript existiert (optional,
standardmäßig nicht enthalten - `{"0x199": "My Sensor"}`), zeigt die
ID-Spalte diesen freundlichen Namen neben der rohen Hex-ID - nützlich
für jeden, der den eigenen Verkehr einer benutzerdefinierten
Erweiterungsplatine testet, ohne den Quellcode dieses Tools ändern zu
müssen.

### Werkzeugabdeckung

Jedes der 25 Profile hat sein eigenes Panel, direkt aus
`docs/CANBUS.md` aufgebaut:

| Werkzeug | Steuerelemente | Live-Telemetrie |
|---|---|---|
| Lötkolben | Solltemperatur, Ein/Aus; Lötzinnvorschub Richtung + Schrittzahl (Einmalbewegung); Abfrage und Zurücksetzen der Vorschubposition auf 0 | Ist-Temperatur; Vorschubposition (Schätzung im offenen Regelkreis) |
| Pasten-/Flüssigkeitsspender, Schraubendreher, beide Greifer, SMT Pick & Place, Vacuum Gripper (LG) | Richtung + Schrittzahl (Einmalbewegung) | keine (gemeinsames 0x120, keine Telemetrie für keines dieser 7) |
| Vakuum-Aufnahme | keine | Analogmessung, Teil erkannt |
| Bohrer | Geschwindigkeit + Richtung | Ist-Drehzahl, Endanschlag |
| AOI-Inspektion | Ringmodus (aus/Stroboskop/kontinuierlich) + Stroboskopperiode | Endanschlag |
| Lasergravierer | Leistung + Laser-Sperre scharf/sicher (ein Firmware-Ausgang, keine Hardware-Verriegelung) | Endanschlag |
| 3D-Drucker | Düsensollwert, Extruderrichtung/-schritte, Schichtlüfterleistung, Hotend-Lüfterleistung | Hotend-Temperatur, Schichtlüfter-Drehzahl, Hotend-Lüfter-Drehzahl |
| Scan-Sonde | keine | Anzahl Aufprallereignisse + Zeitstempel (`0x095` mit höchster Priorität) |
| Elektromagnet | Kontrollkästchen Spule erregen/lösen | keine |
| Punktschweißgerät | Impulsdauer + Auslösen | keine (löst nur aus, wenn der Kontaktsensor zuvor HIGH liest - siehe das eigene `0x1C0` in `docs/CANBUS.md`) |
| Konforme Beschichtung, Einpress-Zylinder | keine - rein informatives Panel | keine - beide Werkzeug-IDs haben keinen eigenen CAN-Handler, ihr eigener Aktuator und Sensor befinden sich auf der Hauptplatine des Roboters selbst, siehe `docs/TOOLS.TXT` |
| Flying Probe | Die Basismessung erfolgt automatisch; die erweiterte Messung benötigt ein rohes ADS1115-Konfigurationswort (hex) + Konvertierung Auslösen + Ergebnis Lesen | Basismessung integrierter ADC (automatisch, `0x243`) |
| UV-Härtung | Leistungsregler (0-255) + Senden/Aus | keine |
| Heißluft für Nacharbeit | Solltemperatur, Gebläseleistung, Ein/Aus | Live-Temperatur (teilt sich die eigene `0x135`-Telemetrie und das Live-Diagramm des Lötkolbens - derselbe physische Thermoregelkreis) |
| Crimp-Aktuator | Richtung + Schrittzahl (Einmalbewegung, gleiche Form wie die oben gemeinsam genutzten Bewegungswerkzeuge, erreicht aber den Treiber einer Erweiterungsplatine über `0x1F0` statt des integrierten `0x120`) | keine |
| Thermal Inspection | Erfassung Auslösen, Status Prüfen, Wärmebild Lesen | 32x24-Pixel-Wärmebild-Leinwand (Blau-Rot-Verlauf), Chunk für Chunk über CAN auf Anfrage abgerufen - kein Live-Videofeed, siehe Abschnitt 6 unten |
| Lötpasten-Jetting | PWM-Kanal + Frequenz (Konfigurieren), dann Tastverhältnis + Dauer (Impuls Auslösen) | keine |
| Ultraschallschweißgerät | Impulsdauer + Auslösen | keine (gleiche Form wie Punktschweißgerät, aber ohne Kontaktsensor-Sperre) |

**Kommunikations-Watchdogs werden für Sie gehandhabt.** Der Lötkolben,
die Heißluft für Nacharbeit (teilt sich denselben Thermoregelkreis und
Watchdog wie der Lötkolben), der Laser, und die 3D-Drucker-Düse haben
jeweils einen 250ms-Watchdog in der Firmware; der Schichtlüfter hat
einen 1000ms-Watchdog. Das Markieren des entsprechenden
"Aktiv"-Kästchens sendet den Befehl nicht nur einmal - es sendet ihn
automatisch erneut (150ms für die Werkzeuge mit 250ms-Watchdog, 400ms
für den Schichtlüfter), solange das Kästchen markiert bleibt, genauso
wie es ein echter Master-Controller tun muss. Das Deaktivieren sendet
einen einzelnen Null-/Aus-Frame und stoppt. Der Hotend-Lüfter hat
keinen Watchdog (stattdessen einen Stillstandsdetektor - siehe
`docs/CANBUS.md`), also ist es ein einfaches einmaliges Senden.

**Hinweise zur Bedienung (Software-Komfort, keine Sicherheitsfunktionen).**

- **ALLE AUSGÄNGE STOPPEN** (in beiden Fenstern, verfügbar bei bestehender Verbindung und scharfgeschalteten aktiven Prüfungen) sendet jeden bekannten Aus-Befehl - Heizungen, Laser, Bohrmaschine, UV-Lampe, Schichtlüfter, Freigabe des Elektromagneten, einfache Schrittmotoren und Crimper - egal welches Werkzeug eingebaut ist, und stoppt jede Auffrischung. Der Hotend-Lüfter bleibt absichtlich an, weil die Düse noch heiß sein kann. Das ist ein Software-Befehl über den CAN-Bus, kein Notaus: Er wirkt nicht, wenn Bus, Adapter, PC oder Platine ausfallen.
- Die einmaligen Schweißimpulse, der Pasteimpuls und das Crimpen verlangen auch im klassischen Fenster eine Bestätigung, wie es das Qt-Quick-Deck immer tut.
- Die Bohrmaschine und die UV-Lampe werden wie der Laser und die Heizungen aufgefrischt. Solange die Heizung des 3D-Druckers gehalten wird, enthält ihre 150-ms-Auffrischung 0 Extruderschritte, die die Firmware als Stoppbefehl liest: Eine in diesem Zustand gestartete Extruderbewegung wird innerhalb von 150 ms abgebrochen. Den Extruder daher bei ausgeschalteter Heizung bewegen, bis die Firmware einen Modus bietet, der den Extruder in Ruhe lässt.
- Port und Bitrate werden für die nächste Sitzung gemerkt (`config.json`), und das Qt-Quick-Deck hat eine eigene Bitraten-Auswahl. Die **automatische Erkennung** hört zuerst nur bei jeder Bitrate zu (auf einem aktiven Bus wird nichts gesendet) und fragt nur dann bei jeder Bitrate nach, wenn der Bus völlig still ist.
- Der Rohdaten-Busmonitor lässt sich auf einige CAN-IDs (**ID-Filter**) und auf Frames mit geänderten Daten (**Nur Änderungen**) beschränken.

#### 🔥 Prüfstandstest für thermisches Durchgehen (URTC-Firmware 0.3.2+ / 0.3.3+)

Detect zeigt jetzt, *warum* eine Platine einen Fehler verriegelt hat: Byte 4
von `0x111` (Schutz vor thermischem Durchgehen: MAXTEMP, HEATING_NO_RISE oder
DROPPED_AT_TARGET) erscheint im Platinenstatus, und ein vom
Hardware-Watchdog ausgelöster Reset (Byte 5 von `0x111`) wird protokolliert.
**Thermik-Zähler** (F-RAM-Bereich in beiden Oberflächen) liest
`0x1AA`/`0x1AB`: thermische Fehler insgesamt, gesamte Heizstunden und den
letzten Fehler. Antworten älterer Firmware (`0x111` mit 4 Bytes, kein
`0x1AB`) werden als "nicht gemeldet" angezeigt, nie als null. Die
Schritt-für-Schritt-Anleitung zur Prüfung an einer echten Platine steht in
[`docs/THERMAL_RUNAWAY_BENCH_TEST.md`](docs/THERMAL_RUNAWAY_BENCH_TEST.md).

<!-- urtc-section:heads -->
### Mehrere Werkzeugköpfe an einem Bus

Die Firmware kann mehrere Werkzeugköpfe an einem CAN-Bus betreiben (die Multinode-Erweiterung). Sie ist **standardmäßig aus**, und ein Bus mit einem Kopf arbeitet genau wie bisher. Das Fenster **Köpfe** findet die Köpfe, listet jeden mit Adresse, Werkzeug und Seriennummer und zeigt seinen Zustand: bereit, ausgewählt, Adresskonflikt, Fehler gespeichert, im Bootloader oder verloren. Sie wählen einen aus, das Programm fragt nach einer Bestätigung und sendet erst danach etwas an diesen Kopf; solange mehrere Köpfe am Bus hängen, wird ein Befehl abgelehnt, bis einer ausgewählt ist und es bestätigt hat. Geht der ausgewählte Kopf verloren, wechseln alle Köpfe in ihren sicheren Zustand (ein Kontrollkästchen des Fensters schaltet das ab). Getestet wurde nur gegen ein Modell des Busses, nicht mit Platinen. Siehe `docs/MULTINODE.md` in URTC-COMMON.
<!-- /urtc-section:heads -->

## 🔒 Sicherheit und Schutz

| Risiko | Abwehr |
|---|---|
| Ein Befehl an eine Platine, die nicht das Werkzeug ist, das das Fenster zeigt | Das Panel eines Werkzeugs wird nur für das Werkzeug gezeigt, das die Platine selbst gemeldet hat, und jeder Befehl ist an eine Identitätsübereinstimmung gebunden |
| Unbeabsichtigtes Senden | Das Fenster startet im reinen Hörmodus: Es kann nicht senden, bis aktive Prüfungen bewusst scharf geschaltet werden, und jede Aktion, die auf die Platine wirkt, verlangt vorher eine Bestätigung im Fenster |
| Die Platine beschädigen | Der Tester berührt nie den Flash: Alles, was er tut, ist ein Befehl zur Laufzeit oder ein Telemetrie-Lesezugriff auf die laufende Anwendung |
| Ein Protokoll, das jemand verändern könnte | Der Sitzungsexport ist ein Zip mit dem Protokoll, einem Manifest, das es über seinen SHA-256 benennt, und den Diagnosedaten des Systems |

Nichts davon wurde an einer echten Platine erprobt, und nichts davon ist eine zertifizierte Sicherheitsfunktion; siehe die Einschränkungen unten.

## 🔌 Schnittstellen

Wie beim Flasher: ein zeitgestempeltes Sitzungsprotokoll wird
automatisch nach `logs/` geschrieben (sicher zu
löschen), und **Debug-Paket exportieren** speichert eine `.zip`-Datei
mit dem aktuellen Bildschirmprotokoll plus grundlegender Systemdiagnose
(Betriebssystem, Python-Version, aktueller Transport/Port/Bitrate,
erkanntes Werkzeug) zur Weitergabe an denjenigen, der ein
Werkzeugkopfproblem debuggt.

### 🤖 Ohne Fenster: Prüfpläne

`python urtc_tester.py --headless BEFEHL` führt den Tester ohne Fenster aus, für eine Fertigungslinie, ein Prüfstandsskript oder einen CI-Job: `info` (wer antwortet: Werkzeug, Firmware, Schnellstatus), `selftest`, `run-plan DATEI` und `validate-plan DATEI`. Ein Plan ist eine kurze JSON-Datei mit Schritten in `plans/` (ein Werkzeug erwarten, keine Fehler, eine Mindest-Firmwareversion, der Selbsttest, ein Frame, dessen Wert in einem Bereich liegt, eine Wartezeit, eine Frage an die Person am Prüfplatz). Der Befehl schreibt ein Protokoll jedes Frames und einen Ergebnisdatensatz, der das Protokoll über seinen SHA-256 benennt, derselbe Datensatz wie im Deck. Ein Plan sendet nur Abfragen, es sei denn, er sagt `"actuation": true` und die Bedienperson fügt `--allow-actuation` hinzu; Bootloader-, Update-, Konfigurations- und Löschframes werden nie gesendet, ein Befehl, den die Firmware ohne Auffrischung wieder fallen lässt (Heizer, Bohrer, Laser), kann während des Wartens des Plans wiederholt werden (`keepalive_ms`), und nach einem Plan, der etwas angesteuert hat, werden alle Ausgänge wieder abgeschaltet. `--transport simulate` spielt einen simulierten Werkzeugkopf ab und `--transport replay --port DATEI` einen aufgezeichneten `.trc`- oder `.asc`-Mitschnitt, sodass ein Plan ohne Platine erprobt werden kann. Exit-Status: 0 bestanden, 1 eine Prüfung ist fehlgeschlagen, 2 Plan oder Argumente sind falsch, 3 die Prüfung konnte nicht durchgeführt werden. Die Ausgabe ist englisch, wie die Kommandozeile des Flashers. Einzelheiten in [`docs/HEADLESS.md`](docs/HEADLESS.md). Nichts davon ist gegen eine echte Platine gelaufen.

**Pläne im Fenster (neu, nur mit Tests und dem simulierten Kopf geprüft):** der Abschnitt TESTPLÄNE am Ende der rechten Spalte des Decks listet die Pläne aus `plans/`, führt den gewählten mit demselben Motor gegen die verbundene Platine aus (nicht im Nur-Hören-Modus und nur, solange nichts anderes den Bus liest), zeigt jeden Schritt, sobald er endet, stellt die Fragen eines Bestätigungsschritts in einem Dialog und speichert das Log und den Ergebnisdatensatz. Ein Plan, der Ausgänge ansteuert, fragt zuerst nach einer Bestätigung und am Ende werden alle Ausgänge abgeschaltet; Abbrechen stoppt ihn nach dem laufenden Schritt.

**Nach Updates suchen.** Die Schaltfläche „Nach Updates suchen“ fragt GitHub einmal nach dem neuesten Release und bietet den Download nur an, wenn es ein Paket für dieses System enthält, das neuer als die installierte Version ist. Das Paket wird nur akzeptiert, wenn SHA-256 und Ed25519-Signatur (der im Programm angeheftete Schlüssel der Releases) gültig sind; es wird erst nach Ihrer Bestätigung installiert, nie, solange ein Ausgang eingeschaltet ist, und die vorherige Version bleibt zum Zurückgehen erhalten (und wird von selbst wiederhergestellt, wenn die neue nicht startet). Nichts wird von selbst geprüft oder installiert: die Prüfung beim Start ist eine Option, standardmäßig aus, und die Bestätigung lässt sich nur im selben Fenster nach einer Warnung abschalten.

**Aufgezeichneten Trace abspielen.** „Trace öffnen“ lädt einen `.trc`- oder `.asc`-Trace (die des Bus-Monitors oder von PCAN-View und CANalyzer) und spielt seine empfangenen Frames in eine eigene Liste ein, markiert als REPLAY, mit 0,25x bis 10x, Pause, Stopp und Wiederholen; eine Stille von mehr als zwei Sekunden wird verkürzt. Eine Wiedergabe sendet nie, beantwortet nie eine Anfrage, vermischt sich nie mit dem Bus-Monitor oder dessen Export und läuft nicht, solange eine Platine verbunden ist (sie pausiert von selbst, wenn eine verbunden wird). Eine Datei über 50 MB oder ohne empfangenen Frame wird abgelehnt und das wird gesagt.

**Blackbox-Betrachter.** Der von der Platine gelesene Datensatz und jeder früher gespeicherte (`.json` oder `.csv`, von diesem Programm geschrieben, geöffnet mit „Gespeicherten Datensatz öffnen“, ohne Platine) wird als gemessene Temperatur und Sollwert über der Zeit gezeichnet, mit einer Marke, wo das Fehlerflag zuerst gesetzt wurde, und Messwert für Messwert mit den Flags in Worten aufgelistet. Jedes Feld muss eine ganze Zahl im Bereich sein, und ein Datensatz hat höchstens 67 Messwerte; eine Datei, die kein Datensatz ist, wird mit Grund abgelehnt, und die vorherige Zeichnung bleibt.

**Ohne Hardware:** Eine virtuelle Platine ersetzt Adapter und Platine. Starte `python -m urtc_can.virtual_board` und gib ihre serielle URL als Port an (`--transport serial --port socket://127.0.0.1:7777`); die Platine beantwortet die Versionsabfrage und den Schnellstatus wie eine Anwendung, sodass `info` und Pläne aus Abfragen ohne angeschlossene Geräte vollständig durchlaufen. Sie ist ein Modell nach der Protokollbeschreibung, kein Werkzeugkopf: Der Selbsttest eines Werkzeugs meldet, was er nicht lesen kann.

## 🚀 Schnellstart

Dasselbe Schema wie der Flasher:

```
pip install -r requirements.txt
python urtc_tester.py          # Windows
python3 urtc_tester.py         # Linux
```

### Visuelles Steuerpult

Das **Qt-Quick**-Kommandopult ist jetzt der echte Standard:
~~~
python urtc_tester.py
~~~
Es nutzt die Transporte SLCAN/SocketCAN und startet im
Nur-Lese-Modus, kann also erst senden, wenn aktive Prüfungen bewusst aktiviert
werden. Jeder der Befehle der 25 Werkzeugprofile ist hier real und bestätigt
abgedeckt (Bewegung, Bohrer, AOI, Elektromagnet, Punkt-/Ultraschall-
Schweißpuls, Pastendosierung, Flying Probe, Thermoinspektion, die 5 Aktoren
mit Watchdog-Keepalive, Vakuum-/Scan-Probe-Telemetrie), jeweils gleich
abgesichert: eine Identitätsübereinstimmung, ein ausdrücklich aktivierter
aktiver Modus und eine Benutzerbestätigung in QML, bevor etwas gesendet wird.
Bisher wurde nichts davon an einer echten Platine geprüft - siehe „Bekannte Einschränkungen“ unten.

Das Pult zeigt außerdem die **Live-Werte** des erkannten Werkzeugs (Temperatur mit rollendem Diagramm und CSV-Export, Drehzahl, Endschalter; sie hören nur zu und funktionieren daher im Nur-Hören-Modus und neben einem laufenden Ausgang), führt den **Selbsttest** aus, warnt in der Kopfzeile, wenn die **Busgesundheitsprüfung** (alle 3 Sekunden eine Abfrage des aktiven Werkzeugs, solange nichts anderes den Bus nutzt) ein Problem sieht, und hat einen **Über URTC Tester**-Dialog mit Readme, Lizenz und GitHub-Seite neben **Protokolle speichern...**.

Der Kopf des Qt-Quick-Fensters hat eine Sprachauswahl; die Auswahl wird gespeichert und gilt beim nächsten Start. Außerdem fragt es die Position des Drahtvorschubs des Lötkolbens ab und setzt sie zurück (Schätzung im offenen Regelkreis; das Zurücksetzen verlangt eine Bestätigung). Die Identitätsabfrage zeigt auch die Patch-Nummer der Firmware, wenn die Platine sie sendet (URTC-Firmware 0.3.5 und neuer); ältere Firmware zeigt nur Major.Minor.

Der bestehende Live-CAN-Diagnoseablauf verwendet jetzt eine dunkelblau-cyanfarbene Steueroberfläche: Produktkopf, kontrastreiche Verbindungskarte, klare Werkzeug-Tabs, dunkles Sitzungsprotokoll und sichtbarer Fortschritt. Diese Änderung von Darstellung und Zugänglichkeit verändert weder passives Monitoring noch Befehlsrouting, und nichts davon wurde auf einer echten Platine ausprobiert.

### Kopfzeile und Werkzeuge

- **Kopfzeile** - der Verbindungsstatus, die Busgesundheitswarnung, die Sprachauswahl (die Wahl wird gespeichert und gilt ab dem nächsten Start) und die Version.
- **Protokolle speichern...** und **SITZUNG EXPORTIEREN (LOG MIT HASH)** - das Bildschirmprotokoll als reiner Text bzw. ein Zip mit dem Protokoll, einem Manifest, das es über seinen SHA-256 benennt, und der Systemdiagnose (siehe „Protokolle und Debug-Pakete“ unten).
- **Über URTC Tester** - Version und Autor, mit Schaltflächen für **Readme** (in der Sprache der Oberfläche, wenn eine Übersetzung existiert), **Lizenz** und die **URTC GitHub**-Seite des Projekts.

### Dateistruktur

Dieses Tool ist aus Gründen der Lesbarkeit in Module nach Zuständigkeit organisiert - es gibt keinen funktionalen Unterschied zwischen separaten Dateien und einer großen Datei. `tester_config.py` enthält die Konfigurations-/Sprach-/Protokollkonstanten, `tester_transports.py` enthält SLCAN/SocketCAN, `tester_bus_monitor.py` enthält den Frame-Filter und die Busstatistik, `qt_tester.py` ist die Qt-Quick-Brücke (mit `assets/qml/TesterDeck.qml`), `tester_selftest.py`, `tester_telemetry.py` und `tester_autodetect.py` sind die fensterlose Logik von Selbsttest, Live-Werten und Bitratensuche, und `urtc_tester.py` ist nur der Einstiegspunkt.

**Sprache**: Englisch als Standard. Wird mit der Sprachauswahl in der Kopfzeile des Fensters gewechselt - wechselt die Oberfläche (Beschriftungen, Schaltflächen, Dialoge, und Protokollnachrichten) zu einer der 8 verfügbaren Sprachen,
speichert sofort in `config.json` neben diesem Tool, angewendet beim
nächsten Start. Übersetzungen leben in reinen Textdateien unter
`language/` (`english.lng`, `spanish.lng`, `italian.lng`, `french.lng`,
`german.lng`, `chinese.lng`, `japanese.lng`, `portuguese.lng`) als einfache
`SCHLÜSSEL=Wert`-Paare, eines pro Zeile -
Zeilen, die mit `#` beginnen, und leere Zeilen werden ignoriert, und ein
wörtliches `\n` innerhalb eines Werts wird zu einem echten Zeilenumbruch
(verwendet von der Handvoll mehrzeiliger Dialognachrichten). Aus dem Katalog von URTC-COMMON erzeugt (eine Übersetzung wird dort korrigiert und die Dateien werden neu geschrieben, nie von Hand bearbeitet), oder als Ausgangspunkt für eine andere Sprache (fügen Sie `language/<name>.lng`
hinzu, fügen Sie `("<name>", "Eigener Name")` zu `AVAILABLE_LANGUAGES`
nahe dem Anfang von `tester_config.py` hinzu, und setzen Sie
`"language": "<name>"` in `config.json`). Ein fehlender Schlüssel aus
einer Sprachdatei fällt darauf zurück, den Namen dieses Schlüssels
selbst anzuzeigen, statt abzustürzen, und eine fehlende oder unlesbare
Sprachdatei (fehlerhafte Bearbeitung, falscher Dateiname) fällt für die
gesamte Oberfläche auf Englisch zurück - so oder so bleibt das Tool
nutzbar, während die Unstimmigkeit behoben wird.

**SLCAN/SocketCAN-Einrichtung unter Linux** (Adapter-Reflash, serielle
Berechtigungen, Aktivierung mit `ip link`) ist genau dieselbe wie
Abschnitt 1 des Flashers - siehe die eigene
[README von URTC Flasher](https://github.com/JuanenRac/URTC-FLASHER)
Abschnitte 1 und 2, statt es hier zu duplizieren.

<!-- urtc-section:compatibility -->
### Voraussetzungen und Kompatibilität

Welche Versionen der URTC-Programme zusammenarbeiten und welche Protokollversion jede spricht, steht in der Kompatibilitätstabelle, die URTC-COMMON erzeugt: [docs/COMPATIBILITY.md](https://github.com/JuanenRac/URTC/blob/main/docs/COMPATIBILITY.md).
<!-- /urtc-section:compatibility -->

## 🧪 Tests

Die Suite hat 578 Tests (`python -m pytest -q`; mit Qt auf einem Rechner ohne Bildschirm `QT_QPA_PLATFORM=offscreen`; die, die PySide6 brauchen, werden ohne übersprungen): die CAN-Nutzdaten-Kodierer und -Dekodierer jeder Werkzeugfamilie, die SLCAN- und SocketCAN-Transporte gegen Attrappen, die Identitätsabfrage, der Selbsttest, die Watchdog-Keepalives, die Busgesundheitsprüfung, die Testpläne und der Modus ohne Fenster, der Sitzungsexport mit seinem Hash, die Sprachdateien und die Qt-Quick-Panels. Vier Skripte im Wurzelverzeichnis (`verify_qt_*.py`) steuern die Qt-Quick-Panels mit einer echten Qt-Ereignisschleife durchgängig an. Die CI führt außerdem `ruff check`, `python -m mypy` und `tools/ci_validate.py` aus. Nichts davon lief gegen eine echte Platine.

## 🏗️ Build und Veröffentlichung

Oder erstellen Sie ein eigenständiges Binary: `build_exe.bat` unter
Windows, `./build_exe.sh` unter Linux. Beide bereinigen zuerst
`build/`/`dist/` und bündeln `assets/` (das Banner und das Symbol) in
das Executable - siehe [docs/BUILD_AND_RUN.md](docs/BUILD_AND_RUN.md)
für den versionsneutralen Validierungspfad
(`build-test.bat`/`build-test.sh`), auf dem diese Paketierungsskripte
aufbauen, und das eigene README des Flashers für die vollständige
Begründung hinter den Paketierungsskripten selbst, da sie hier identisch
gilt.

**Version:** `TESTER_VERSION` (in `tester_config.py`, sichtbar in der Titelleiste, im Über-Dialog, in den Sitzungsprotokollen und in den Debug-Paketen) folgt `MAJOR.MINOR.PATCH` und wird nur durch den ausdrücklichen Schritt `python bump.py` erhöht. Das Ausführen aus dem Quelltext (`python urtc_tester.py`) und das Bauen (`build_exe.bat` / `build_exe.sh`) berühren sie nie. Den Versionsverlauf siehe `CHANGELOG.md`.

## 📂 Struktur des Repositorys

<p align="center">
  <img src="images/repository-structure.svg" alt="Struktur des Repositorys URTC-TESTER" width="100%">
</p>

<details>
<summary>Textversion des Baums</summary>

```text
URTC-TESTER/
├── urtc_tester.py                                     Einstiegspunkt
├── qt_tester.py                                       das Qt-Quick-Deck
├── tester_*.py                                        Transporte, Monitor, Selbsttest, Pläne, Telemetrie
├── advanced_protocol.py                               reine CAN-Nutzdaten-Kodierer
├── verify_qt_*.py                                     End-to-End-Prüfungen der Qt-Panels
├── urtc_can/                                          Protokoll, Transporte und Updates (Kopie)
├── urtc_ui/                                           Oberflächen-Helfer (Kopie)
├── tests/                                             eine Testdatei je Bereich
├── plans/                                             Beispiel-Testpläne (JSON)
├── language/                                          die acht .lng-Sprachdateien
├── assets/                                            QML, Banner und Symbol
├── docs/                                              Architektur, Build und Betrieb
├── logs/                                              Sitzungsprotokolle (nicht in Git)
├── tools/                                             Build-Prüfung und gemeinsame Werkzeuge
├── images/                                            Banner und Bilder dieses READMEs
├── .github/                                           CI-Workflow sowie Vorlagen für Issues und Pull Requests
├── test.sh test.bat                                   führen die Tests aus
├── run.sh run.bat                                     starten das Programm
├── build-test.sh build-test.bat                       Build- und Testskripte, die im Repository nichts ändern
├── urtc.project.json                                  Manifest: Version, Rolle, Reifegrad und Build-Befehl
├── CHANGELOG.md                                       was sich in jeder Version geändert hat
├── SECURITY.md SUPPORT.md LICENSE                     Sicherheitsrichtlinie, Support und Lizenz
├── CONTRIBUTING.md CODE_OF_CONDUCT.md                 wie man mitwirkt, und der Verhaltenskodex
├── .gitattributes .gitignore                          Git-Einstellungen
├── build_exe.sh build_exe.bat                         eigenständiges Programm (PyInstaller)
├── bump.py bump_version.py bump_manifest_version.py   Skripte, die die Version erhöhen
├── requirements*.txt requirements*.lock               Abhängigkeiten, mit ihren Sperren
├── mypy.ini ruff.toml .coveragerc                     Einstellungen für Typen, Lint und Abdeckung
├── urtc_i18n.lock.json                                Sperre der erzeugten Sprachdateien
└── NOTICE LICENSE.md                                  Urheberrechtshinweis und Dokumentationslizenz
```

</details>

Die kommentierte Liste jeder Quelldatei, eine Zeile je Datei, steht in [docs/SOURCE_MAP.md](docs/SOURCE_MAP.md).

## 🗺️ Roadmap und bekannte Grenzen

Der Evidenz-Vertrag dieses Tools - was als pass/fail/unknown zählt,
warum fehlende Evidenz immer unknown und nie pass bedeutet, und warum es
selbst keine Firmware-Flash-Berechtigung erteilt - ist in
[docs/INTEGRATION_CONTRACT.md](docs/INTEGRATION_CONTRACT.md)
dokumentiert.

- **Nicht gegen echte Hardware getestet.** Jedes Teil hier - der
  Transport-Layer, die CAN-ID-/Byte-Layout-Handhabung, das
  Watchdog-Keepalive-Timing - wurde isoliert geprüft (simulierte
  Frames, ein echter Subprozess für das Timing, wo relevant), aber die
  Umgebung, die dies gebaut hat, hat keinen USB-Zugriff. Behandeln Sie
  eine erste echte Sitzung mit derselben Vorsicht, die das eigene
  README des Flashers verlangt.
- **Ein Werkzeugpanel zur Zeit, per Design**, keine aktuelle
  Einschränkung, die später entfernt werden soll - siehe die
  Einleitung oben für den Grund.
- **Globale LED-Farben sind eine direkte Übersteuerung**, kein
  Live-Rücklesen - es gibt keine Telemetrie dafür, was die
  Status-/Ring-LEDs aktuell tatsächlich anzeigen, nur was zuletzt
  befohlen wurde.
- **Das eigene Wärmebild von Thermal Inspection basiert auf
  Abruf, nicht auf einem Live-Feed.** Ein vollständiges Bild zu lesen
  bedeutet, alle 48 Chunks nacheinander über CAN abzufragen
  (schlimmster Fall, die eigene Auflösung von MLX90640/MLX90642) - dies
  kann einige Sekunden dauern, und es gibt keinen Streaming-Sendemodus
  im eigenen CAN-Protokoll dieses Werkzeugs, um es schneller zu machen.
  Zuerst muss eine Erfassung ausgelöst werden; Wärmebild Lesen wartet dann bis zu zwei Sekunden darauf, dass der Sensor „bereit“ meldet, und liest andernfalls nichts, weil die Firmware Chunk-Anfragen vorher nicht beantwortet. Zuerst wird abgefragt, welcher Sensor verbaut ist (48 Chunks für MLX90640/MLX90642, 12 für MLX90641), und ein verlorener Chunk lässt seine Pixel leer, statt den Rest des Bildes zu verschieben.
- **Self-Test ausführen deckt nur 7 der 25 Werkzeuge ab** (Lötkolben,
  Bohrer, Laser, 3D-Drucker, AOI, Vakuum, Scan-Sonde) - siehe „Wie es
  funktioniert" oben für die vollständige Erklärung. Die anderen 18
  Werkzeuge erhalten von diesem Button keine automatisierte Prüfung;
  sie zu verifizieren bedeutet weiterhin, die tatsächliche Hardware bei
  der Reaktion auf die Bedienelemente ihres eigenen Panels zu
  beobachten.

## 🌍 Sprachen

README und Texte gibt es auf Englisch, Spanisch, Französisch, Italienisch, Deutsch, Chinesisch, Japanisch und europäischem Portugiesisch.

## 🔗 Verwandte Projekte

URTC besteht aus unabhängigen Repositories mit jeweils eigener Version, eigenen Tests und eigenem README. Das ist die Familie, nach Gruppen:

* **URTC Tool Platform:**
  * [URTC](https://github.com/JuanenRac/URTC) - Firmware der Werkzeugkopf-Platine (25 Werkzeugprofile, CAN-Bootloader) und die Referenz des CAN-Protokolls.
  * [URTC-COMMON](https://github.com/JuanenRac/URTC-COMMON) - das CAN-Protokoll einmal als Daten geschrieben (Spezifikation, erzeugte Tabellen, Konformitätsvektoren) und der Code, den die Programme teilen.
  * [URTC-FLASHER](https://github.com/JuanenRac/URTC-FLASHER) - Desktop-Werkzeug, das die Platinen-Firmware über CAN oder über SWD/JTAG aktualisiert.
  * [URTC-GATEWAY](https://github.com/JuanenRac/URTC-GATEWAY) - Gateway vor dem CAN-Bus: lässt nur gelistete Kennungen durch, begrenzt ihre Rate und verlangt einen Sitzungsschlüssel.
  * [URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK) - hardwareunabhängige C-Logik und Befehlsprotokoll für eine Werkzeugablage mit Vorheizen und Lebenszyklusverfolgung.
  * **URTC-TESTER** (dieses Repository) - Desktop-Live-Tester für den CAN-Bus, der die Bedienelemente und die Telemetrie des von einer Platine gemeldeten Werkzeugprofils zeigt.
  * [URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL) - Sensorrahmen-Protokoll in C und ein Python-Thermo-/RGB-Begleiter für einen Inspektions-Werkzeugkopf.
  * [URTC-WEB-STUDIO](https://github.com/JuanenRac/URTC-WEB-STUDIO) - Browser-App, die die Platine über Web Serial und SLCAN flasht und testet, ohne Installation.
* **Ecosystem Operations:**
  * [URTC-DEVTOOLS](https://github.com/JuanenRac/URTC-DEVTOOLS) - die gemeinsamen Repository-Werkzeuge der Familie als versionierter Satz, mit einer Sperrdatei, die eine bearbeitete von einer veralteten Kopie unterscheidet.
  * [URTC-DOCS](https://github.com/JuanenRac/URTC-DOCS) - Architektur, Schnittstellen, Sicherheitsbasis und erzeugter Katalog des Ökosystems sowie die Werkzeuge, die alle Repositories vergleichen.
  * [URTC-UPDATER](https://github.com/JuanenRac/URTC-UPDATER) - Desktop-Werkzeug, das die Repositories der URTC-Familie erkennt, installiert und aktualisiert, jeweils eine ausdrückliche Aktion.

**Schwesterprojekte (unabhängig, mit derselben Basis und denselben Werkzeugen):**

* **[HYDRA-UMC-DOCS](https://github.com/JuanenRac/HYDRA-UMC-DOCS)** - Schwesterprojekt: das Dokumentationszentrum von HYDRA-UMC, einem unabhängigen Ökosystem, das Basis und Werkzeuge mit diesem teilt
* **[ARMOR-DOCS](https://github.com/JuanenRac/ARMOR-DOCS)** - Schwesterprojekt: das Dokumentationszentrum von A.R.M.O.R., dem Sicherheits-Ökosystem, ebenfalls unabhängig und auf derselben Basis
* **[JuanenRac](https://github.com/JuanenRac/JuanenRac)** - das Profil und das Status-Dashboard aller Ökosysteme

## 📚 Dokumentation

- **[CONTRIBUTING.md](CONTRIBUTING.md)** — Technologie-Stack und Coding-Richtlinien für einen Pull Request.
- **[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)** — die in dieser Community erwarteten Verhaltensstandards.
- **[SECURITY.md](SECURITY.md)** — wie man eine Schwachstelle meldet, und die echten Sicherheitsschwerpunkte dieses Projekts.
- **[SUPPORT.md](SUPPORT.md)** — wo man Fragen stellt und Fehler meldet.
- **[LICENSE.md](LICENSE.md)** — die eigene Lizenz dieses Projekts.

## 🤝 Mitwirken und Community

* Führe vor einem Pull Request `URTC_CI=1 python tools/ci_validate.py` aus: es muss bestehen. Siehe [CONTRIBUTING.md](CONTRIBUTING.md) und den [Verhaltenskodex](CODE_OF_CONDUCT.md).
* Das README gibt es in acht Sprachen: Eine Textänderung wird in allen acht Dateien vorgenommen, und die mit anderen Repositorys geteilten Abschnitte schreibt `tools/readme_sections.py` von URTC-COMMON.
* Eine Änderung am CAN-Protokoll beginnt in URTC-COMMON (`spec/can_protocol.json`) und gelangt über die geprüfte Kopie in dieses Repository.
* Beschreibe nichts als auf einer Platine funktionierend, was nur gebaut wurde.
* Melde eine Schwachstelle privat: [SECURITY.md](SECURITY.md). Fragen, Ideen und Meldungen: electrohobby3d@gmail.com ([SUPPORT.md](SUPPORT.md)).

## 👤 AUTOR

**JuanenRac** (Electro Hobby 3D)
📧 electrohobby3d@gmail.com
📺 [youtube.com/@electrohobby3d](https://youtube.com/@electrohobby3d)

## 📜 LIZENZ

Lizenz: **GPL-3.0-or-later** für den Quellcode, **CC BY-SA 4.0** für diese
Dokumentation - siehe `LICENSE` in diesem Repository, oder den
Abschnitt „Lizenz und Urheberrechtshinweise" am Ende dieses Dokuments.

URTC Tester ist (c) 2026 JuanenRac (Electro Hobby 3D). Dieser Hinweis
muss in jeder Verteilung dieses Projekts oder abgeleiteter Werke
enthalten sein.

Dieses Projekt besteht aus Quellcode und seiner eigenen Dokumentation,
die unter verschiedenen Lizenzen verfügbar gemacht werden - jede
passend zu dem, was sie tatsächlich abdeckt:

1. Der Quellcode (`urtc_tester.py` und jedes `tester_*.py`-Modul) und
   jedes daraus über `build_exe.bat`/`build_exe.sh` erstellte Binary
   sind unter der **GNU General Public License v3.0 or later (GPL-3.0-or-later)**
   verfügbar. Vollständiger Text unter
   https://www.gnu.org/licenses/gpl-3.0.html.

2. Die Dokumentation (dieses README und seine eigenen Übersetzungen -
   `README_spa.md`, `README_ita.md`, `README_fra.md`, `README_deu.md`,
   `README_zho.md`, `README_jpn.md`, `README_por.md` und die Anleitungen in `docs/`)
   ist unter **Creative Commons Attribution-ShareAlike 4.0
   International (CC BY-SA 4.0)** verfügbar. Vollständiger Text unter
   https://creativecommons.org/licenses/by-sa/4.0/.

Dieses Tool ist der Live-CAN-Bus-Diagnose-Begleiter des
[URTC (Universal Robot Tool Controller)](https://github.com/JuanenRac/URTC)
-Projekts - siehe das eigene Repository dieses Projekts für die
Platinen-Firmware, Hardware-Designs und die vollständige
Protokolldokumentation, die dieses Tool ausübt. Die eigene Firmware von
URTC ist GPL-3.0-or-later und ihre Hardware-Designs sind CERN-OHL-S v2; die
eigene Lizenz dieses Tools erstreckt sich hier nicht auf dieses
separate Projekt, und umgekehrt. Eine webbasierte Alternative, die
ähnliches Terrain abdeckt, existiert ebenfalls unter
[URTC Web Studio](https://github.com/JuanenRac/URTC-WEB-STUDIO).

Wenn Sie auf diesem Projekt aufbauen, denken Sie an die Lizenztrennung:
Codeänderungen sollten GPL-3.0-or-later bleiben, Dokumentationsableitungen
sollten CC BY-SA bleiben - jeweils mit Zuschreibung zurück an dieses
Projekt und seinen Autor.
