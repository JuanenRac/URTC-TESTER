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


<p align="center">
  <img src="https://img.shields.io/badge/Lizenz-GPL%203.0-blue.svg" alt="GPL 3.0 or later">
  <img src="https://img.shields.io/badge/Sprache-Python-3776AB.svg" alt="Python">
  <img src="https://img.shields.io/badge/UI-Qt%20Quick-38d4e6.svg" alt="Qt Quick">
  <img src="https://img.shields.io/badge/Protokoll-CAN-yellow.svg" alt="CAN">
</p>


**Version:** 0.4.1 · **Autor:** JuanenRac (Electro Hobby 3D) &lt;electrohobby3d@gmail.com&gt;

Lizenz: **GPL-3.0-or-later** für den Quellcode, **CC BY-SA 4.0** für diese
Dokumentation - siehe `LICENSE` in diesem Repository, oder den
Abschnitt „Lizenz und Urheberrechtshinweise" am Ende dieses Dokuments.

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

**Ehrlichkeitscheck - was heute wirklich funktioniert:** die CAN-Payload-Encoder für die auf Qt Quick migrierten Steuerungsfamilien (`advanced_protocol.py`) sind real und durch die Tests in `tests/` abgedeckt (`python -m pytest -q`). Die eigene CI dieses Repos (`.github/workflows/ci.yml`) führt sie ebenfalls aus, zusammen mit `ruff check`, `tools/ci_validate.py`, einer Syntaxkompilierung jeder `.py`-Datei und den vier `verify_qt_*.py`-Skripten, sodass eine Regression dort den Build fehlschlagen lässt. Die vier `verify_qt_*.py`-Skripte im Repo-Root (`verify_qt_custom_frame.py`, `verify_qt_telemetry_watch.py`, `verify_qt_utility_panels.py`, `verify_qt_selftest.py`) sind echte, bewusst außerhalb von `tests/` gehaltene End-to-End-Prüfungen gegen einen simulierten Transport mit echter Cross-Thread-Signal-Zustellung - alle vier bestehen mit `QT_QPA_PLATFORM=offscreen python verify_qt_*.py`, was die CI ebenfalls ausführt. Das ist die ehrliche Obergrenze dessen, was automatisch verifiziert wird: die Transportschicht, die CAN-ID-/Byte-Layout-Verarbeitung und die Qt-Quick-Brückenlogik sind real und werden gegen simulierte Frames geprüft, nicht gegen echte Hardware - wie "Known limitations" weiter unten bereits sagt, wurde dies ohne USB-Zugriff gebaut, sodass hier noch nichts gegen eine echte Platine geprüft wurde. `qt_tester.py` und `assets/qml/TesterDeck.qml` sind die reale, umfangreiche Implementierung (zusammen tausende Zeilen), geprüft durch die Tests mit simulierten Platinen und die Verify-Skripte, nie durch eine echte Platine.

> **Stand von Sicherheit (Safety) und Security:** Dieses Ökosystem ist kein zertifiziertes Sicherheitssystem, und es existiert noch keine bestückte URTC-Platine. Die Bootloader prüfen Firmware-Images mit CRC32 und einem HMAC-SHA256 mit gemeinsamem Schlüssel, nicht mit einer asymmetrischen Signatur (geplant); die veröffentlichten Anwendungs-Images sind mit dem öffentlichen Entwicklungsschlüssel signiert (`signing_key_kind: dev`), sodass jeder ein vom Bootloader akzeptiertes Image erzeugen kann; an eine echte Platine wurde noch nichts gesendet. Lesen Sie die [Sicherheitsbasis](https://github.com/JuanenRac/URTC-DOCS/blob/main/docs/SECURITY_BASELINE.md) und das [Bedrohungsmodell](https://github.com/JuanenRac/URTC-DOCS/blob/main/docs/THREAT_MODEL.md), bevor Sie sich für die Sicherheit einer Person auf eine Aussage hier verlassen.

## 📋 Auf einen Blick

| | |
|---|---|
| Version | `0.4.1` |
| Reifegrad | Funktionsfähig |
| Technik | Python / PySide6 / Qt Quick / live CAN bus diagnostics |
| Ziel | Der PC der Person, die es benutzt |
| Auf echter Hardware | Nur simuliert: gegen Emulatoren, Attrappen oder Simulatoren getestet; für diese Version ist kein Lauf auf echter Hardware vermerkt |

## 1. 🆚 Beziehung zum Flasher

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

## 2. 📦 Installation und Ausführung

Dasselbe Schema wie der Flasher:

```
pip install -r requirements.txt
python urtc_tester.py          # Windows
python3 urtc_tester.py         # Linux
```

Oder erstellen Sie ein eigenständiges Binary: `build_exe.bat` unter
Windows, `./build_exe.sh` unter Linux. Beide bereinigen zuerst
`build/`/`dist/` und bündeln `assets/` (das Banner und das Symbol) in
das Executable - siehe [docs/BUILD_AND_RUN.md](docs/BUILD_AND_RUN.md)
für den versionsneutralen Validierungspfad
(`build-test.bat`/`build-test.sh`), auf dem diese Paketierungsskripte
aufbauen, und das eigene README des Flashers für die vollständige
Begründung hinter den Paketierungsskripten selbst, da sie hier identisch
gilt.

**Versionierung:** `TESTER_VERSION` (in `tester_config.py`, angezeigt in
der Titelleiste, im Über-Dialog, in Sitzungsprotokollen und in
Debug-Paketen) folgt dem Schema `MAJOR.MINOR.PATCH`. Beide Build-Skripte
erhöhen sie automatisch unmittelbar vor jedem echten Build über
`bump_version.py`, nach einer "Kilometerzähler"-Regel im Zehnersystem:
PATCH +1, und sobald PATCH 9 überschreitet, wird es auf 0 zurückgesetzt
und MINOR steigt um 1 (z. B. `0.1.9` → `0.2.0`). Das Ausführen aus dem
Quellcode (`python urtc_tester.py`) verändert sie nie - nur ein echter
Lauf von `build_exe.bat`/`build_exe.sh` tut dies. MAJOR wird nie
automatisch erhöht, nur von Hand. Siehe `CHANGELOG.md` für die
Versionshistorie.

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

## 3. ⚙️ Wie es funktioniert

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

## 4. 🧰 Werkzeugabdeckung

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

### 🔥 Prüfstandstest für thermisches Durchgehen (URTC-Firmware 0.3.2+ / 0.3.3+)

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

## 5. 📋 Protokolle und Debug-Pakete

Wie beim Flasher: ein zeitgestempeltes Sitzungsprotokoll wird
automatisch nach `logs/` geschrieben (sicher zu
löschen), und **Debug-Paket exportieren** speichert eine `.zip`-Datei
mit dem aktuellen Bildschirmprotokoll plus grundlegender Systemdiagnose
(Betriebssystem, Python-Version, aktueller Transport/Port/Bitrate,
erkanntes Werkzeug) zur Weitergabe an denjenigen, der ein
Werkzeugkopfproblem debuggt.

### 🤖 Ohne Fenster: Prüfpläne

`python urtc_tester.py --headless BEFEHL` führt den Tester ohne Fenster aus, für eine Fertigungslinie, ein Prüfstandsskript oder einen CI-Job: `info` (wer antwortet: Werkzeug, Firmware, Schnellstatus), `selftest`, `run-plan DATEI` und `validate-plan DATEI`. Ein Plan ist eine kurze JSON-Datei mit Schritten in `plans/` (ein Werkzeug erwarten, keine Fehler, eine Mindest-Firmwareversion, der Selbsttest, ein Frame, dessen Wert in einem Bereich liegt, eine Wartezeit, eine Frage an die Person am Prüfplatz). Der Befehl schreibt ein Protokoll jedes Frames und einen Ergebnisdatensatz, der das Protokoll über seinen SHA-256 benennt, derselbe Datensatz wie im Deck. Ein Plan sendet nur Abfragen, es sei denn, er sagt `"actuation": true` und die Bedienperson fügt `--allow-actuation` hinzu; Bootloader-, Update-, Konfigurations- und Löschframes werden nie gesendet, ein Befehl, den die Firmware ohne Auffrischung wieder fallen lässt (Heizer, Bohrer, Laser), kann während des Wartens des Plans wiederholt werden (`keepalive_ms`), und nach einem Plan, der etwas angesteuert hat, werden alle Ausgänge wieder abgeschaltet. `--transport simulate` spielt einen simulierten Werkzeugkopf ab und `--transport replay --port DATEI` einen aufgezeichneten `.trc`- oder `.asc`-Mitschnitt, sodass ein Plan ohne Platine erprobt werden kann. Exit-Status: 0 bestanden, 1 eine Prüfung ist fehlgeschlagen, 2 Plan oder Argumente sind falsch, 3 die Prüfung konnte nicht durchgeführt werden. Die Ausgabe ist englisch, wie die Kommandozeile des Flashers. Einzelheiten in [`docs/HEADLESS.md`](docs/HEADLESS.md). Nichts davon ist gegen eine echte Platine gelaufen.

**Nach Updates suchen.** Die Schaltfläche „Nach Updates suchen“ fragt GitHub einmal nach dem neuesten Release und bietet den Download nur an, wenn es ein Paket für dieses System enthält, das neuer als die installierte Version ist. Das Paket wird nur akzeptiert, wenn SHA-256 und Ed25519-Signatur (der im Programm angeheftete Schlüssel der Releases) gültig sind; es wird erst nach Ihrer Bestätigung installiert, nie, solange ein Ausgang eingeschaltet ist, und die vorherige Version bleibt zum Zurückgehen erhalten (und wird von selbst wiederhergestellt, wenn die neue nicht startet). Nichts wird von selbst geprüft oder installiert: die Prüfung beim Start ist eine Option, standardmäßig aus, und die Bestätigung lässt sich nur im selben Fenster nach einer Warnung abschalten.

**Aufgezeichneten Trace abspielen.** „Trace öffnen“ lädt einen `.trc`- oder `.asc`-Trace (die des Bus-Monitors oder von PCAN-View und CANalyzer) und spielt seine empfangenen Frames in eine eigene Liste ein, markiert als REPLAY, mit 0,25x bis 10x, Pause, Stopp und Wiederholen; eine Stille von mehr als zwei Sekunden wird verkürzt. Eine Wiedergabe sendet nie, beantwortet nie eine Anfrage, vermischt sich nie mit dem Bus-Monitor oder dessen Export und läuft nicht, solange eine Platine verbunden ist (sie pausiert von selbst, wenn eine verbunden wird). Eine Datei über 50 MB oder ohne empfangenen Frame wird abgelehnt und das wird gesagt.

**Blackbox-Betrachter.** Der von der Platine gelesene Datensatz und jeder früher gespeicherte (`.json` oder `.csv`, von diesem Programm geschrieben, geöffnet mit „Gespeicherten Datensatz öffnen“, ohne Platine) wird als gemessene Temperatur und Sollwert über der Zeit gezeichnet, mit einer Marke, wo das Fehlerflag zuerst gesetzt wurde, und Messwert für Messwert mit den Flags in Worten aufgelistet. Jedes Feld muss eine ganze Zahl im Bereich sein, und ein Datensatz hat höchstens 67 Messwerte; eine Datei, die kein Datensatz ist, wird mit Grund abgelehnt, und die vorherige Zeichnung bleibt.

**Ohne Hardware:** Eine virtuelle Platine ersetzt Adapter und Platine. Starte `python -m urtc_can.virtual_board` und gib ihre serielle URL als Port an (`--transport serial --port socket://127.0.0.1:7777`); die Platine beantwortet die Versionsabfrage und den Schnellstatus wie eine Anwendung, sodass `info` und Pläne aus Abfragen ohne angeschlossene Geräte vollständig durchlaufen. Sie ist ein Modell nach der Protokollbeschreibung, kein Werkzeugkopf: Der Selbsttest eines Werkzeugs meldet, was er nicht lesen kann.

## 6. ⚠️ Bekannte Einschränkungen

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

## 📂 Repository-Struktur

```
/
├── urtc_tester.py             Einstiegspunkt - startet das Qt-Quick-Pult
├── qt_tester.py                Qt-Quick-Frontend - echtes Standard-Command-Deck, standardmäßig
│                                schreibgeschützt
├── tester_config.py            Konfigurations-/Sprach-/Protokollkonstanten
│                                (CAN-IDs, Werkzeugnamen, MOTION_TOOL_IDS,
│                                AVAILABLE_LANGUAGES, EXPANSION_BOARD_TYPES)
├── tester_transports.py        SLCAN- und SocketCAN-Transportklassen
├── tester_bus_monitor.py       Hintergrund-Thread für CAN-Lesevorgänge
│                                (CANBusMonitor)
├── tester_autodetect.py        Bitratensuche für einen SLCAN-Adapter
├── tester_selftest.py          Selbsttest-Schritte und -Ablauf (ohne Fenstercode)
├── tester_plan.py              Prüfpläne: Validierung, Ablauf und das anschließende „Alles aus“
├── tester_cli.py               Der Tester ohne Fenster (--headless): info, selftest, run-plan
├── tester_simulator.py         Simulierter Werkzeugkopf und Player für aufgezeichnete Mitschnitte
├── plans/                      Beispiel-Prüfpläne (JSON)
├── tester_telemetry.py         Live-Werte jedes Werkzeugs und die aufgezeichnete Reihe
├── tester_trace_export.py      Schreiber der .trc-/.asc-Frame-Exporte
├── urtc_ui/                    Gemeinsame Oberflächen-Hilfen (Kopie aus URTC-COMMON)
├── advanced_protocol.py        Reine CAN-Payload-Encoder für die auf Qt Quick
│                                migrierten Steuerungsfamilien - hardwarefreie Tests
├── verify_qt_custom_frame.py        Echte End-to-End-Prüfung außerhalb von tests/ des Qt-Quick-Panels Custom CAN Frame (braucht eine echte Qt-Ereignisschleife)
├── verify_qt_telemetry_watch.py     Echte End-to-End-Prüfung außerhalb von tests/ der Qt-Quick-Telemetrie (Vacuum Pickup / Scan Probe)
├── verify_qt_utility_panels.py      Echte End-to-End-Prüfung außerhalb von tests/ der Qt-Quick-Utility-Panels (Global Controls / Expansion Board / F-RAM)
├── verify_qt_selftest.py            Echte End-to-End-Prüfung außerhalb von tests/ des Qt-Quick-Selbsttests
├── tests/
│   └── test_advanced_protocol.py   Hardwarefreie Tests für die Encoder von advanced_protocol.py - von der CI ausgeführt, siehe Ehrlichkeitscheck oben
├── requirements.txt            pyserial>=3.5 + PySide6>=6.8,<7
├── build_exe.bat               Build-Skript für die eigenständige Windows-Binary
│                                (PyInstaller)
├── build_exe.sh                Dasselbe, für Linux
├── build-test.bat              Build-/Kompilierprüfung ohne Versionserhöhung
├── build-test.sh                Dasselbe, für Linux
├── bump.py                     Ausdrücklicher Befehl zum Erhöhen der Version (Kompilieren erhöht nie)
├── bump_version.py             Versionserhöhung im Kilometerzähler-Stil, von den Build-Skripten ausgeführt
├── bump_manifest_version.py    Synchronisiert die Version von urtc.project.json mit der nativen (--sync)
├── URTC_Tester.spec            PyInstaller-Spec, die von beiden Build-Skripten
│                                verwendet wird
├── assets/
│   ├── URTC_APP_ICON.svg       Quelle des Fenster-/Taskleisten-Icons (kleines
│                                eigenständiges Design)
│   ├── URTC_LOGO_TESTER.svg    Banner-Quelle (Vektor)
│   ├── qml/
│   │   └── TesterDeck.qml      Qt-Quick-UI des Standard-Command-Decks
│   ├── urtc_icon.ico           Windows-Icon, erzeugt aus URTC_APP_ICON.svg
│   └── urtc_icon.png           Dasselbe, als PNG (Linux)
├── images/
│   ├── URTC_LOGO_TESTER.svg    Logo-Banner, das oben in diesem README gezeigt
│                                wird
│   └── URTC_TESTER_V1_1.png    Screenshot des Hauptfensters des Tools (siehe
│                                Fotos unten)
├── language/
│   ├── english.lng             Standardsprache, reine Text-KEY=Value-Zeichenketten
│   ├── spanish.lng
│   ├── italian.lng
│   ├── french.lng
│   ├── german.lng
│   ├── japanese.lng
│   ├── chinese.lng
│   └── portuguese.lng
├── logs/                       Sitzungsprotokolle, die hier zur Laufzeit
│                                geschrieben werden (gefahrlos löschbar)
├── LICENSE                     Vollständiger Lizenztext - siehe Lizenz und
│                                Urheberrechtshinweise unten
├── NOTICE                      Copyright-Hinweis und Lizenz der Dokumentation
├── README.md                   Englische Version
├── README_spa.md               Spanische Übersetzung
├── README_ita.md               Italienische Übersetzung
├── README_fra.md               Französische Übersetzung
├── README_deu.md               Diese Datei
├── README_zho.md               Chinesische Übersetzung
├── docs/
│   ├── ARCHITECTURE.md
│   ├── BUILD_AND_RUN.md
│   ├── INTEGRATION_CONTRACT.md
│   ├── CANBUS.md
│   └── THERMAL_RUNAWAY_BENCH_TEST.md
├── tools/
│   ├── build_test.py                     Kompilierprüfung ohne Versionserhöhung + Validierung der Qt-Quick-Deck-Quellen
│   └── ci_validate.py                    Manifest-/CHANGELOG-/Doku-Validierung, von der CI genutzt
└── README_jpn.md               Japanische Übersetzung
```

## 📸 Fotos

<p align="center">
  <img src="images/URTC_TESTER_V1_1.png" alt="URTC Tester Fenster" width="700">
</p>

**Fehlerrekorder, optionale Funktionen, Rack-Prüfstand und Wärmebild (neu, nur mit Attrappen geprüft):** Das Deck liest die Blackbox der Platine (`0x1A8` / `0x1A9`) und speichert sie als CSV und JSON, bei eingeschalteter Option automatisch einmal für jeden gemeldeten Fehler; es schaltet die optionalen Firmware-Funktionen (`0x1AE` / `0x1AF`, standardmäßig aus, wirksam nach dem nächsten Einschalten); es hat ein simuliertes Werkzeug-Rack mit dem seriellen Protokoll von URTC-SMART-RACK, der Identität jedes Kopfes (Typ und Seriennummer) und dem Export einer Statusseite; und es zeigt das Wärmebild der thermischen Inspektion in Falschfarben (ein simuliertes Bild sagt das). Die Werkzeugnamen und -arten stammen jetzt aus den gemeinsamen Werkzeugprofilen von URTC-COMMON. Nichts davon wurde mit einer echten Platine benutzt.

**Heizer-PID (neu, nur mit Attrappen geprüft):** das Deck liest den Zustand des Heizer-PID der Firmware (`0x1B9` / `0x1BA`: die gültigen Verstärkungen, den Zustand und den Ausgang des letzten Regelzyklus), speichert Verstärkungen (0 bis 600) und startet oder bricht den Relais-Autotune ab, der die Spitze um den aktuellen Sollwert des Lötkolbens (100 bis 445 C) heizt und die gefundenen Verstärkungen speichert. Verstärkungen speichern und den Autotune starten verlangen die übliche Bestätigung, das Abbrechen nicht. Der simulierte Kopf der Kommandozeile (`--transport simulate`) beantwortet diese Frames ebenfalls. Die Funktion muss vorher bei den optionalen Funktionen eingeschaltet werden; nichts davon wurde mit einer echten Platine benutzt.

## 🔗 Verwandte Projekte

Dieses Projekt ist Teil des HYDRA-UMC-Robotik-Ökosystems desselben Autors (JuanenRac / Electro Hobby 3D). Gut zu wissen, da eine Anfrage eigentlich eines dieser Projekte betreffen könnte statt dieses Repositorys.

**Übergeordnetes Projekt**
- **[URTC](https://github.com/JuanenRac/URTC)** — Firmware für die physische Universal-Robot-Tool-Controller-Platine, 25+ Werkzeugprofile über CAN-Bus; das übergeordnete Projekt, dessen spezifisches Werkzeug dieses Repository innerhalb seiner eigenen CAN-Bus-Tooling-Familie ist.

**Geschwisterprojekte** — die übrigen Werkzeuge der eigenen CAN-Bus-Tooling-Familie von URTC
- **[URTC-FLASHER](https://github.com/JuanenRac/URTC-FLASHER)** — Desktop-GUI-Flash-Tool für URTC-Platinen, CAN-OTA plus Full-Chip-SWD/JTAG.
- **[URTC-GATEWAY](https://github.com/JuanenRac/URTC-GATEWAY)** — ein Gateway vor dem CAN-Bus, das nur Kennungen einer Liste durchlässt, ihre Rate begrenzt und einen Sitzungsschlüssel verlangt.
- **[URTC-WEB-STUDIO](https://github.com/JuanenRac/URTC-WEB-STUDIO)** — browserbasierte Alternative zu URTC-TESTER über die Web-Serial-API, ohne lokale Installation.

**Direkt verwandt**
- **[HYDRA-UMC-TOOL-CLI](https://github.com/JuanenRac/HYDRA-UMC-TOOL-CLI)** — Flotten-CLI mit einem echten, stabilen Exit-Code-Vertrag, ein echter Live-Client der eigenen API von HYDRA-UMC-SERVER — führt flottenweite Audits (der Befehl `audit`) über alle Werkzeugköpfe gleichzeitig durch, über den Einzelplatinen-Umfang dieses Testers hinaus.
- **[URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL)** — Firmware plus ein echter Python-Vision-Begleiter für einen Thermal-/RGB-Inspektionswerkzeugkopf — ergänzt die Live-CAN-Bus-Diagnose dieses Projekts mit den eigenen visuellen Qualitätssicherungsprüfungen am Werkzeugkopf.
- **[URTC-UPDATER](https://github.com/JuanenRac/URTC-UPDATER)** — Desktop-Werkzeug, das die Repositories der URTC-Familie erkennt, installiert und aktualisiert, jeweils mit einer ausdrücklichen Aktion.

**Ebenfalls Teil des Ökosystems**

*Kern-Hardware & Plattform*
- **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** — der Entwurf des Motherboards des Roboterarms: CM5-Host + Dual-Core-STM32H745, gedacht zur Koordination von bis zu 8 Werkzeugarmen über CAN-OTA/SPI-OTA (Firmware in einer frühen Phase; noch keine bestückte Platine).
- **[HYDRA-UMC-OS](https://github.com/JuanenRac/HYDRA-UMC-OS)** — reproduzierbare Raspberry-Pi-OS-Produktschicht für den CM5: schreibgeschützter Agent, validierte Konfiguration/Profile, WiFi-Ersteinrichtung.
- **[HYDRA-UMC-SDK](https://github.com/JuanenRac/HYDRA-UMC-SDK)** — der gemeinsame JSON-Schema-Vertrag und die Software-Auftragsschranke, gegen die jede Bridge ihre Befehle validiert (keine zertifizierte Sicherheitsfunktion).
- **[HYDRA-UMC-CONNECTOR-HUB](https://github.com/JuanenRac/HYDRA-UMC-CONNECTOR-HUB)** — deklaratives Adapter-Manifest-Register und Validator für Konnektoren externer Maschinen; erweitert die eigene Vertragsidee des SDK auf externe Maschinen, ohne die Industrie-Gateway-Projekte zu ersetzen.

*Kern-Backend & Clients*
- **[HYDRA-UMC-SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER)** — das reale Headless-Backend (REST/WebSocket), mit dem jeder Steuerungsclient tatsächlich spricht.
- **[HYDRA-UMC-STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)** — Web-Steuerungs-Dashboard mit Echtzeit-3D-Visualisierung mehrerer Roboter.
- **[HYDRA-UMC-SUITE](https://github.com/JuanenRac/HYDRA-UMC-SUITE)** — Desktop-Schwarmleitstand (PySide6) für mehrere Server gleichzeitig, verpackt als eigenständige ausführbare Datei.
- **[HYDRA-UMC-ANDROID-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-ANDROID-CONTROL)** — native Android-Steuerungs-App mit biometrischem Login und einer gekoppelten Wear-OS-Begleit-App.
- **[HYDRA-UMC-IOS-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-IOS-CONTROL)** — iOS/iPadOS-Steuerungs-App (Flutter) mit Echtzeit-WebSocket-Synchronisierung.
- **[HYDRA-UMC-DSI](https://github.com/JuanenRac/HYDRA-UMC-DSI)** — native Touch-UI für das eingebaute 7"-DSI-Touchscreen, direkt auf dem CM5 eingebettet.
- **[HYDRA-UMC-EDITOR-URDF](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-URDF)** — grafischer Desktop-URDF-Ersteller/-Editor, der fertige Modelle in STUDIOs eigenen Katalog überträgt.
- **[HYDRA-UMC-EDITOR-STL](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-STL)** — Desktop-STL-Modelleditor, der echte Teile im selben Modellkatalog transformiert/ersetzt/entfernt/hinzufügt, den auch HYDRA-UMC-EDITOR-URDF bearbeitet.
- **[HYDRA-UMC-BRIDGE-AMR](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-AMR)** — Koordinationsschranke für AGV-/AMR-Flotten über einen VDA-5050-MQTT-Publisher (nur gegen eine emulierte Flotte getestet).
- **[HYDRA-UMC-BRIDGE-CNC](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-CNC)** — High-Level-Koordinator für CNC-Zellen mit GRBL-Status-/Steuerbyte-Zugriff (nur gegen einen Emulator getestet).
- **[HYDRA-UMC-BRIDGE-DROIDS](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-DROIDS)** — Koordinationsschranke für laufende/humanoide Droiden, mit einem Boston-Dynamics-Spot-Befehlssender (nur gegen einen Emulator getestet).
- **[HYDRA-UMC-BRIDGE-LASER](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-LASER)** — Koordinator für Laserzellen, liest 3 Schlüssel-/Gehäuse-/Verriegelungs-GPIO-Signale (nur gegen einen simulierten Chip getestet; kann keinen Laser scharfschalten oder auslösen).
- **[HYDRA-UMC-BRIDGE-OPENPNP](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-OPENPNP)** — sicherer High-Level-Koordinator für den Leiterplattenfluss von OpenPnP Pick-and-Place.
- **[HYDRA-UMC-BRIDGE-PRINTER3D](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-PRINTER3D)** — sichere Koordinationsschranke für Moonraker/Klipper-3D-Drucker, mit echten gesicherten Job-Befehlen.
- **[HYDRA-UMC-BRIDGE-ROS2](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-ROS2)** — Koordinator mit einem träge importierten rclpy-ROS-2-Transport (noch nicht gegen eine ROS-2-Installation ausgeführt).
- **[HYDRA-UMC-BRIDGE-UAV](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-UAV)** — Koordinationsschranke für kameraausgestattete UAVs, mit einem MAVLink-Befehlssender (nur gegen einen Emulator getestet).

*Vision-KI-Knoten (Hailo-8)*
- **[HYDRA-UMC-VISION-NODE](https://github.com/JuanenRac/HYDRA-UMC-VISION-NODE)** — Integrationsknoten für die Hailo-8-Vision-Pipeline, mit einer echten stufenweisen Hardware-Bereitschaftsprüfung.
- **[HYDRA-UMC-DETECTION-HEF](https://github.com/JuanenRac/HYDRA-UMC-DETECTION-HEF)** — echte Registry für kompilierte Modelle mit Hailo-Architektur-/Prüfsummen-Safe-Load-Verifizierung.
- **[HYDRA-UMC-VISION-STREAMER](https://github.com/JuanenRac/HYDRA-UMC-VISION-STREAMER)** — echter GStreamer-Pipeline- + MediaMTX-Konfigurationsgenerator mit einer echten HailoRT-Integrationsschranke.
- **[HYDRA-UMC-VISUAL-SERVOING-API](https://github.com/JuanenRac/HYDRA-UMC-VISUAL-SERVOING-API)** — Position-Based-Visual-Servoing-Korrekturgesetz mit Freigabe abhängig vom Zonenstatus; noch keine Posenschätzung per Kamera.
- **[HYDRA-UMC-SAFETY-ZONES](https://github.com/JuanenRac/HYDRA-UMC-SAFETY-ZONES)** — v0-Logik für Zonenverletzung, Kalibrierungsaktualität und E-STOP-Anforderung, die Objektpositionen aus einer Datei nimmt; kein Detektor speist sie, und noch kein physischer E-STOP ist angeschlossen.

*Kognitiver KI-Knoten (Hailo-10)*
- **[HYDRA-UMC-COGNITIVE-NODE](https://github.com/JuanenRac/HYDRA-UMC-COGNITIVE-NODE)** — Integrationsknoten für die Hailo-10-Cognitive-Pipeline (LLM-/VLA-/Sprach-Orchestrierung).
- **[HYDRA-UMC-VLA-ENGINE](https://github.com/JuanenRac/HYDRA-UMC-VLA-ENGINE)** — echte Aktions-Token-Kodierung/-Dekodierung und Trajektoriengenerierung für ein Vision-Language-Action-Modell.
- **[HYDRA-UMC-VOICE-UI](https://github.com/JuanenRac/HYDRA-UMC-VOICE-UI)** — echtes Sprach-Frontend (VAD + Intent-Parser) mit einem begrenzten, bestätigungsgesicherten Watch-Relay.
- **[HYDRA-UMC-SEMANTIC-PLANNER](https://github.com/JuanenRac/HYDRA-UMC-SEMANTIC-PLANNER)** — echte regelbasierte Aufgabenzerlegung und semantische Fehlerbehebung über MCU-Fehlercodes.
- **[HYDRA-UMC-DOCS-QA](https://github.com/JuanenRac/HYDRA-UMC-DOCS-QA)** — echte, nur auf der Standardbibliothek basierende TF-IDF-Dokumentensuche über die eigenen Markdown-Dokumente dieses Ökosystems.
- **[HYDRA-UMC-LOCAL-TECHNICIAN](https://github.com/JuanenRac/HYDRA-UMC-LOCAL-TECHNICIAN)** — lokaler, richtlinien-gesteuerter KI-Wartungstechniker für das Ökosystem selbst - beobachtet, diagnostiziert und schlägt Korrekturen vor; die zwei höchsten Risikostufen sind absichtlich noch nicht implementiert.

*Orchestrierung & Schwarm*
- **[HYDRA-UMC-ORCHESTRATOR](https://github.com/JuanenRac/HYDRA-UMC-ORCHESTRATOR)** — Integrationsknoten mit einem echten gRPC/Protobuf-Health-Report-Vertrag und einer Missions-Zustandsmaschine.
- **[HYDRA-UMC-JOB-DISPATCHER](https://github.com/JuanenRac/HYDRA-UMC-JOB-DISPATCHER)** — echte prioritätsbasierte Job-Queue mit Deduplizierung, über eine echte HTTP-API.
- **[HYDRA-UMC-NODE-HEALING](https://github.com/JuanenRac/HYDRA-UMC-NODE-HEALING)** — echter gRPC-basierter Flotten-Health-Watchdog mit Retry/Backoff und Identitäts-Mismatch-Erkennung.
- **[HYDRA-UMC-PATH-PLANNER-3D](https://github.com/JuanenRac/HYDRA-UMC-PATH-PLANNER-3D)** — echter RRT-basierter 3D-Pfadplaner mit echter Hindernis-/Arbeitsraum-Kollisionsvalidierung.
- **[HYDRA-UMC-SWARM-SYNC](https://github.com/JuanenRac/HYDRA-UMC-SWARM-SYNC)** — echte CRDT-LWW-Element-Map-Zustandssynchronisation, eigenschaftsgetestet auf Multi-Zellen-Konvergenz.

*Digitaler Zwilling & Simulation*
- **[HYDRA-UMC-TWIN](https://github.com/JuanenRac/HYDRA-UMC-TWIN)** — Integrationsknoten für die Digital-Twin-Engine, mit einem echten Versionskompatibilitäts-Sync-Vertrag.
- **[HYDRA-UMC-HIL-BRIDGE](https://github.com/JuanenRac/HYDRA-UMC-HIL-BRIDGE)** — Hardware-in-the-Loop-Router mit einer Software-Kollisionsverriegelung zwischen Simulation und echter Hardware (ohne echte Hardware getestet).
- **[HYDRA-UMC-PHYSICS-REPLICA](https://github.com/JuanenRac/HYDRA-UMC-PHYSICS-REPLICA)** — echte Vorwärtskinematik und Gelenkgrenzenvalidierung über eine echte URDF-Teilmenge.
- **[HYDRA-UMC-SYNTHETIC-DATA-GEN](https://github.com/JuanenRac/HYDRA-UMC-SYNTHETIC-DATA-GEN)** — echter prozeduraler 2D-Szenengenerator mit YOLO/COCO-Annotationsexport.

*Daten & Analytik*
- **[HYDRA-UMC-DATALAKE](https://github.com/JuanenRac/HYDRA-UMC-DATALAKE)** — echter sqlite3-gestützter Zeitreihenspeicher mit einer echten Ingest-/Abfrage-HTTP-API.
- **[HYDRA-UMC-ANOMALY-DETECTOR](https://github.com/JuanenRac/HYDRA-UMC-ANOMALY-DETECTOR)** — echter FFT- + statistischer Basislinien-Anomaliedetektor mit Drift-Überwachung.
- **[HYDRA-UMC-PRODUCTION-REPORTS](https://github.com/JuanenRac/HYDRA-UMC-PRODUCTION-REPORTS)** — echte OEE-/Verfügbarkeitsberechnung über den DATALAKE-Verlauf, mit reproduzierbarem CSV-Export.
- **[HYDRA-UMC-TELEMETRY-COLLECTOR](https://github.com/JuanenRac/HYDRA-UMC-TELEMETRY-COLLECTOR)** — echte CAN/WebSocket-Ingestion-Pipeline in DATALAKE, mit Sequenz-Deduplizierung.

*Industrie-Gateway*
- **[HYDRA-UMC-GATEWAY-INDUSTRIAL](https://github.com/JuanenRac/HYDRA-UMC-GATEWAY-INDUSTRIAL)** — Integrationsknoten, der zu Industrieprotokollen weiterleitet, mit einer echten Befehls-Allowlist-/Backpressure-Schicht.
- **[HYDRA-UMC-OPCUA-SERVER](https://github.com/JuanenRac/HYDRA-UMC-OPCUA-SERVER)** — echter OPC-UA-Adressraum, verifiziert mit einer echten Binärprotokoll-Client-Session.
- **[HYDRA-UMC-MQTT-BROKER](https://github.com/JuanenRac/HYDRA-UMC-MQTT-BROKER)** — echter MQTT-Broker mit optionaler Pro-Client-Authentifizierung und Topic-ACLs.
- **[HYDRA-UMC-MTCONNECT-ADAPTER](https://github.com/JuanenRac/HYDRA-UMC-MTCONNECT-ADAPTER)** — echte MTConnect-`/probe`- und `/current`-XML-Endpunkte mit Degraded-Mode-Ausgabe.

*Ergänzende Tools & Ökosystembetrieb*
- **[HYDRA-UMC-DASHBOARD-AI](https://github.com/JuanenRac/HYDRA-UMC-DASHBOARD-AI)** — Smart-Summaries- und Anomaly-Highlighting-Panels über DATALAKE/ANOMALY-DETECTOR, mit einem ehrlichen statistischen Fallback.
- **[HYDRA-UMC-WATCH](https://github.com/JuanenRac/HYDRA-UMC-WATCH)** — WearOS-Begleit-App mit haptischen Alarmmustern und einem Sprach-Relay zum gekoppelten Telefon (noch nicht auf einer physischen Uhr ausgeführt).
- **[URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK)** — Firmware für ein Platinenmontagegestell mit echter Werkzeug-ID-Dekodierung und Smart-Idle-Vorheizlogik.
- **[HYDRA-UMC-UPDATER](https://github.com/JuanenRac/HYDRA-UMC-UPDATER)** — administratives Desktop-Tool, das jedes Repository in diesem Ökosystem entdeckt, klont und aktualisiert.
- **[HYDRA-UMC-OS-REBUILDER](https://github.com/JuanenRac/HYDRA-UMC-OS-REBUILDER)** — Windows/Linux-Desktop-Tool, das ein flashbereites CM5-Image baut, vorgeladen mit den aktuellsten Versionen des Ökosystems, mit Ersteinrichtungs-Konfiguration für WLAN/Benutzer/SSH im Stil von Raspberry Pi Imager.
- **[HYDRA-UMC-OPS-AGENT](https://github.com/JuanenRac/HYDRA-UMC-OPS-AGENT)** — Wartungsvorfall-Koordinator: eine Edge-Rolle mit niedrigem Privileg sammelt einen bereinigten Inventar-/Gesundheits-Snapshot, eine Control-Plane-Rolle rendert ihn schreibgeschützt und bittet einen KI-Anbieter um einen Diagnosevorschlag - wendet nie einen Patch an und stellt nie etwas bereit.
- **[HYDRA-UMC-DEV-SERVER](https://github.com/JuanenRac/HYDRA-UMC-DEV-SERVER)** — reproduzierbarer Entwicklungshost (Raspberry Pi 5 / CM5), der den Quellcode des Ökosystems vorhält und begrenzte Build-/Test-Aufgaben über eine dauerhafte Warteschlange ausführt; eine dedizierte Entwicklerrolle, ausdrücklich kein operativer CM5.

## 🖼️ Das Fenster, Schritt für Schritt

Diese Bilder zeigen das echte Fenster, ohne Bildschirm gezeichnet, so wie es sich öffnet (nichts verbunden, nichts gesendet). Die Anleitung führt durch das Deck, das Hilfefenster und das Update-Fenster.

![Das Fenster, Schritt für Schritt](docs/screenshots/tester-deck.png)

[Anleitung mit Bildern](docs/WINDOW_GUIDE.md)

<!-- urtc-section:updates -->
## 🔄 So wird aktualisiert

Dieses Programm kann nach einer neueren Version seiner selbst suchen: Die Schaltfläche „Nach Updates suchen“ fragt GitHub einmal und bietet ein signiertes Paket nur an, wenn es für Ihr System ist und neuer. Nichts wird von selbst geprüft oder installiert, solange Sie die Prüfung nicht einschalten, und ein Update braucht Ihre Bestätigung. Das Paket muss zu seinem SHA-256 und zur Signatur des im Programm angehefteten Release-Schlüssels passen; die vorherige Version bleibt erhalten und wird von selbst wiederhergestellt, wenn die neue nicht startet. `urtc-updater --cli package list|check|install|rollback` macht dasselbe auf der Kommandozeile für Flasher und Tester, und `install --file` funktioniert ohne Netzwerk.
<!-- /urtc-section:updates -->

<!-- urtc-section:heads -->
## 🧭 Mehrere Werkzeugköpfe an einem Bus

Die Firmware kann mehrere Werkzeugköpfe an einem CAN-Bus betreiben (die Multinode-Erweiterung). Sie ist **standardmäßig aus**, und ein Bus mit einem Kopf arbeitet genau wie bisher. Das Fenster **Köpfe** findet die Köpfe, listet jeden mit Adresse, Werkzeug und Seriennummer und zeigt seinen Zustand: bereit, ausgewählt, Adresskonflikt, Fehler gespeichert, im Bootloader oder verloren. Sie wählen einen aus, das Programm fragt nach einer Bestätigung und sendet erst danach etwas an diesen Kopf; solange mehrere Köpfe am Bus hängen, wird ein Befehl abgelehnt, bis einer ausgewählt ist und es bestätigt hat. Geht der ausgewählte Kopf verloren, wechseln alle Köpfe in ihren sicheren Zustand (ein Kontrollkästchen des Fensters schaltet das ab). Getestet wurde nur gegen ein Modell des Busses, nicht mit Platinen. Siehe `docs/MULTINODE.md` in URTC-COMMON.
<!-- /urtc-section:heads -->

<!-- urtc-section:compatibility -->
## 🧩 Kompatibilität

Welche Versionen der URTC-Programme zusammenarbeiten und welche Protokollversion jede spricht, steht in der Kompatibilitätstabelle, die URTC-COMMON erzeugt: [docs/COMPATIBILITY.md](https://github.com/JuanenRac/URTC/blob/main/docs/COMPATIBILITY.md).
<!-- /urtc-section:compatibility -->

## 📜 LIZENZ

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

---

## 📚 Dokumentation & Community

- **[CONTRIBUTING.md](CONTRIBUTING.md)** — Technologie-Stack und Coding-Richtlinien für einen Pull Request.
- **[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)** — die in dieser Community erwarteten Verhaltensstandards.
- **[SECURITY.md](SECURITY.md)** — wie man eine Schwachstelle meldet, und die echten Sicherheitsschwerpunkte dieses Projekts.
- **[SUPPORT.md](SUPPORT.md)** — wo man Fragen stellt und Fehler meldet.
- **[LICENSE.md](LICENSE.md)** — die eigene Lizenz dieses Projekts.

## 👤 AUTOR

**JuanenRac** (Electro Hobby 3D)
📧 electrohobby3d@gmail.com
📺 [youtube.com/@electrohobby3d](https://youtube.com/@electrohobby3d)
