<p align="center">
  <img src="/images/URTC_LOGO_TESTER.svg" alt="URTC Tester Logo" width="100%">
</p>

# URTC Tester (Windows / Linux)

**Version:** 1.1 · **Autor:** JuanenRac (Electro Hobby 3D) &lt;electrohobby3d@gmail.com&gt;

Lizenz: **GPL-3.0** für den Quellcode, **CC BY-SA 4.0** für diese
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

## 1. Beziehung zum Flasher

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

## 2. Installation und Ausführung

Dasselbe Schema wie der Flasher:

```
pip install -r requirements.txt
python urtc_tester.py          # Windows
python3 urtc_tester.py         # Linux
```

Oder erstellen Sie ein eigenständiges Binary: `build_exe.bat` unter
Windows, `./build_exe.sh` unter Linux. Beide bereinigen zuerst
`build/`/`dist/` und bündeln `assets/` (das Banner und das Symbol) in
das Executable - siehe das eigene README des Flashers für die
vollständige Begründung hinter diesen Skripten, da sie hier identisch
gilt.

**Beim Start** wird das Banner 5 Sekunden lang zentriert auf dem
Bildschirm angezeigt, bevor das Hauptfenster erscheint, statt im
Fenster selbst zu leben - wie beim Flasher, und aus demselben Grund
(hält das Fenster selbst kompakt). Das Fenster-/Taskleisten-Symbol ist
ebenfalls ein kleines eigenständiges Design, nicht das verkleinerte
Banner.

### Menüleiste

- **Datei** - Protokolle speichern (das Protokoll auf dem Bildschirm als
  Klartext; für ein vollständigeres Paket mit Systemdiagnose siehe
  stattdessen "Protokolle und Debug-Pakete" weiter unten), und Beenden.
- **Sprache** - zwischen den 5 verfügbaren Sprachen wechseln (siehe
  "Sprache" weiter oben, wie Übersetzungen funktionieren).
- **Hilfe** - Readme (öffnet diese Datei in einem schreibgeschützten
  Betrachterfenster; übernimmt automatisch eine übersetzte Version,
  sobald eine für die aktuelle Sprache existiert), URTC GitHub (öffnet
  das Repository des Projekts in Ihrem Browser), Lizenz (die
  GPL-3.0-Lizenz dieses Tools, gelesen aus der eigenen `LICENSE`-Datei
  des Repositorys), und Über (Version und Autor).

### Dateistruktur

Dieses Tool ist aus Gründen der Lesbarkeit in Module nach Zuständigkeit
organisiert - es gibt keinen funktionalen Unterschied zwischen separaten
Dateien und einer großen Datei. `tester_config.py` enthält die
Konfigurations-/Sprach-/Protokollkonstanten, `tester_transports.py`
enthält SLCAN/SocketCAN, `tester_bus_monitor.py` enthält den
Hintergrund-CAN-Lese-Thread, und `TesterGUI` selbst ist aufgeteilt auf
`tester_gui_core.py` (Verbindung, Erkennung, Fenster-Lebenszyklus, und
die Menüleiste) plus 3 Mixins, die es kombiniert:
`tester_common_panels.py` (Panels für globale Steuerung/F-RAM/
Erweiterung/Selbsttest/Bus-Monitor/benutzerdefinierten Frame),
`tester_panel_helpers.py` (gemeinsame Hilfsprogramme, die jeder
Werkzeug-Panel-Builder verwendet), und `tester_tool_panels.py` (19
werkzeugspezifische Panel-Builder, die alle 25 Profile abdecken -
mehrere Werkzeuge teilen sich denselben Builder, z. B. deckt
`_build_motion_panel` allein 7 davon ab). `urtc_tester.py` ist jetzt nur
noch der Einstiegspunkt - CLI-freier Start und der Splash-Screen.

**Sprache**: Englisch als Standard. Wird über das Menü **Sprache** (in
der Menüleiste oben im Fenster) gewechselt statt über ein Dropdown im
Hauptfenster - wechselt die Oberfläche (Beschriftungen, Schaltflächen,
Dialoge, und Protokollnachrichten) zu einer der 5 verfügbaren Sprachen,
speichert sofort in `config.json` neben diesem Tool, angewendet beim
nächsten Start. Übersetzungen leben in reinen Textdateien unter
`language/` (`english.lng`, `spanish.lng`, `italian.lng`, `french.lng`,
`german.lng`) als einfache `SCHLÜSSEL=Wert`-Paare, eines pro Zeile -
Zeilen, die mit `#` beginnen, und leere Zeilen werden ignoriert, und ein
wörtliches `\n` innerhalb eines Werts wird zu einem echten Zeilenumbruch
(verwendet von der Handvoll mehrzeiliger Dialognachrichten). Direkt
editierbar, wenn eine Übersetzung korrigiert werden muss, oder als
Ausgangspunkt für eine andere Sprache (fügen Sie `language/<name>.lng`
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

## 3. Wie es funktioniert

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
demselben Grund.

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
ignoriert (gemäß `docs/CANBUS.TXT`) - die Farbe gilt in beiden Fällen
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
  ist (`0x1A7` - siehe `CANBUS.TXT`) - nur relevant, wenn der obige
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
`docs/CANBUS.TXT` dokumentiert ist. Keine Validierung über den
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
neben ihrer Live-Temperaturmessung - ein einfaches Tkinter-Canvas-Widget,
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

## 4. Werkzeugabdeckung

Jedes der 25 Profile hat sein eigenes Panel, direkt aus
`docs/CANBUS.TXT` aufgebaut:

| Werkzeug | Steuerelemente | Live-Telemetrie |
|---|---|---|
| Lötkolben | Solltemperatur, Ein/Aus; Lötzinnvorschub Richtung + Schrittzahl (Einmalbewegung); Abfrage und Zurücksetzen der Vorschubposition auf 0 | Ist-Temperatur; Vorschubposition (Schätzung im offenen Regelkreis) |
| Pasten-/Flüssigkeitsspender, Schraubendreher, beide Greifer, SMT Pick & Place, Vacuum Gripper (LG) | Richtung + Schrittzahl (Einmalbewegung) | keine (gemeinsames 0x120, keine Telemetrie für keines dieser 7) |
| Vakuum-Aufnahme | keine | Analogmessung, Teil erkannt |
| Bohrer | Geschwindigkeit + Richtung | Ist-Drehzahl, Endanschlag |
| AOI-Inspektion | Ringmodus (aus/Stroboskop/kontinuierlich) + Stroboskopperiode | Endanschlag |
| Lasergravierer | Leistung + Interlock scharf/sicher | Endanschlag |
| 3D-Drucker | Düsensollwert, Extruderrichtung/-schritte, Schichtlüfterleistung, Hotend-Lüfterleistung | Hotend-Temperatur, Schichtlüfter-Drehzahl, Hotend-Lüfter-Drehzahl |
| Scan-Sonde | keine | Anzahl Aufprallereignisse + Zeitstempel (`0x095` mit höchster Priorität) |
| Elektromagnet | Kontrollkästchen Spule erregen/lösen | keine |
| Punktschweißgerät | Impulsdauer + Auslösen | keine (löst nur aus, wenn der Kontaktsensor zuvor HIGH liest - siehe das eigene `0x1C0` in `docs/CANBUS.TXT`) |
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
`docs/CANBUS.TXT`), also ist es ein einfaches einmaliges Senden.

## 5. Protokolle und Debug-Pakete

Wie beim Flasher: ein zeitgestempeltes Sitzungsprotokoll wird
automatisch nach `logs/` geschrieben (sicher zu
löschen), und **Debug-Paket exportieren** speichert eine `.zip`-Datei
mit dem aktuellen Bildschirmprotokoll plus grundlegender Systemdiagnose
(Betriebssystem, Python-Version, aktueller Transport/Port/Bitrate,
erkanntes Werkzeug) zur Weitergabe an denjenigen, der ein
Werkzeugkopfproblem debuggt.

## 6. Bekannte Einschränkungen

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
  Eine Erfassung muss bereits ausgelöst und als bereit gemeldet worden
  sein (Status Prüfen), bevor Wärmebild Lesen echte Daten zurückgibt -
  zu frühes Lesen zeichnet einfach das, was im eigenen Puffer des
  Sensors zuletzt gespeichert war.
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
├── urtc_tester.py             Einstiegspunkt - Start ohne CLI und der
│                                Startbildschirm
├── tester_config.py            Konfigurations-/Sprach-/Protokollkonstanten
│                                (CAN-IDs, Werkzeugnamen, MOTION_TOOL_IDS,
│                                AVAILABLE_LANGUAGES, EXPANSION_BOARD_TYPES)
├── tester_transports.py        SLCAN- und SocketCAN-Transportklassen
├── tester_bus_monitor.py       Hintergrund-Thread für CAN-Lesevorgänge
│                                (CANBusMonitor)
├── tester_gui_core.py          TesterGUI-Kern - Verbindung, Erkennung,
│                                Fensterlebenszyklus und die Menüleiste; die
│                                Klasse, in der die 3 untenstehenden Mixins
│                                kombiniert werden
├── tester_common_panels.py     CommonPanelsMixin - globale/F-RAM/Erweiterungs-/
│                                Self-Test-/Bus-Monitor-/benutzerdefinierte-Frame-
│                                Panels (die immer sichtbaren Bereiche)
├── tester_panel_helpers.py     PanelHelpersMixin - gemeinsame Hilfsfunktionen,
│                                die jeder Werkzeugpanel-Builder verwendet
├── tester_tool_panels.py       ToolPanelsMixin - 19 werkzeugspezifische
│                                Panel-Builder, die alle 25 Werkzeugprofile
│                                abdecken (mehrere Werkzeuge teilen sich einen
│                                Builder, z. B. deckt `_build_motion_panel`
│                                allein 7 davon ab)
├── requirements.txt            Einzige Abhängigkeit: pyserial>=3.5
├── build_exe.bat               Build-Skript für die eigenständige Windows-Binary
│                                (PyInstaller)
├── build_exe.sh                Dasselbe, für Linux
├── URTC_Tester.spec            PyInstaller-Spec, die von beiden Build-Skripten
│                                verwendet wird
├── assets/
│   ├── URTC_APP_ICON.svg       Quelle des Fenster-/Taskleisten-Icons (kleines
│                                eigenständiges Design)
│   ├── URTC_LOGO_TESTER.svg    Quelle des Start-Banners
│   ├── urtc_icon.ico           Windows-Icon, erzeugt aus URTC_APP_ICON.svg
│   ├── urtc_icon.png           Dasselbe, als PNG (Linux)
│   └── urtc_tester_banner.png  PNG des Start-Banners, gerendert aus dem obigen
│                                SVG
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
│   └── german.lng
├── logs/                       Sitzungsprotokolle, die hier zur Laufzeit
│                                geschrieben werden (gefahrlos löschbar)
├── LICENSE                     Vollständiger Lizenztext - siehe Lizenz und
│                                Urheberrechtshinweise unten
├── README.md                   Englische Version
├── README_spa.md               Spanische Übersetzung
├── README_ita.md               Italienische Übersetzung
├── README_fra.md               Französische Übersetzung
└── README_deu.md               Diese Datei
```

## 📸 Fotos

<p align="center">
  <img src="images/URTC_TESTER_V1_1.png" alt="URTC Tester Fenster" width="700">
</p>

## 🔗 Verwandte Projekte

Dieses Projekt ist Teil eines größeren Robotik-Ökosystems desselben Autors (JuanenRac / Electro Hobby 3D). Gut zu wissen, denn eine Anfrage könnte sich tatsächlich auf eines davon beziehen statt auf dieses Repository:

**HYDRA-UMC-Plattform** — die Multi-Roboter-Mikrofabrikzelle
- **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** — die Hauptplatine selbst: Raspberry-Pi-CM5-Host + dualer STM32H745-Echtzeit-Coprozessor, der bis zu 8 verteilte Roboterarme über CAN-OTA/SPI-OTA orchestriert. Eigene Hardware + Firmware, GPL-3.0/CERN-OHL-S v2/CC BY-SA 4.0.
- **[HYDRA-UMC STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)** — webbasiertes Steuerungs-Dashboard für HYDRA-UMC: Multi-Roboter-3D-Visualisierung, Kinematik-/Trajektorienaufzeichnung, CAN-OTA-Flashing und -Tests für die gesamte Plattform. React + Vite + Three.js.
- **[HYDRA-UMC-ANDROID-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-ANDROID-CONTROL)** — Android-Steuerungs-App für HYDRA-UMC über Wi-Fi/Bluetooth. Echte, funktionierende App - vollständiger Funktionsumfang zur Fernsteuerung, JWT-Authentifizierung, verschlüsselte Speicherung von Zugangsdaten.
- **[HYDRA-UMC-IOS-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-IOS-CONTROL)** — iOS/iPadOS-Steuerungs-App für HYDRA-UMC über Wi-Fi, gebaut in Flutter (plattformübergreifend, unter Windows ohne Mac verifizierbar; die endgültige `.ipa`-Paketierung benötigt weiterhin Xcode). Echte, funktionierende App - derselbe Funktionsumfang wie die Android-App.
- **[HYDRA-UMC-SUITE](https://github.com/JuanenRac/HYDRA-UMC-SUITE)** — Desktop-Kommandozentrale (Python/PySide6) für den Schwarm: Multi-Controller-Netzwerkerkennung, bidirektionale Live-Synchronisation, echtes 3D-Roboter-Viewport, andockbarer Arbeitsbereich im Photoshop-Stil. Echt und funktionierend, kein Platzhalter.
- **[HYDRA-UMC-EDITOR-URDF](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-URDF)** — grafischer URDF-Ersteller/-Editor für den Desktop (Python/PySide6) für den eigenen Modellkatalog dieses Projekts: zieht Quelldateien von GitHub oder einem lokalen Ordner, prüft die Machbarkeit der Freiheitsgrade, bearbeitet Farbe/Skalierung/Kinematik mit Live-3D-Vorschau und überträgt das fertige Ergebnis an einen laufenden STUDIO-Server. Echt und funktionierend, kein Platzhalter.
- **[HYDRA-UMC-DSI](https://github.com/JuanenRac/HYDRA-UMC-DSI)** — geplant: eine native Touch-UI für den eigenen 5"/7"-DSI-Touchscreen von HYDRA-UMC (1280×720, gleiche Auflösung bei beiden Größen) auf dem Compute Module 5, die diesen selben Server direkt von der Platine aus steuert. Noch nicht begonnen.

**URTC-Plattform** — der Werkzeugkopf-Controller, den jeder HYDRA-UMC-Roboterarm trägt
- **[URTC](https://github.com/JuanenRac/URTC)** — Universal Robot Tool Controller: STM32F303-basierter CAN-Bus-Werkzeugkopf-Controller, 25 vollständig implementierte Werkzeugprofile, CAN-OTA-Firmware-Update.
- **[URTC Flasher](https://github.com/JuanenRac/URTC-FLASHER)** — Desktop-Tool für CAN-OTA + vollständiges SWD/JTAG-Chip-Flashing für URTC-Platinen (Windows/Linux).
- URTC Tester *(dieses Repository)* — Desktop-Tool zur Live-CAN-Bus-Diagnose für URTC-Platinen, ein Panel pro Werkzeugprofil (Windows/Linux).
- **[URTC Web Studio](https://github.com/JuanenRac/URTC-WEB-STUDIO)** — browserbasierte Alternative zu den beiden obigen Desktop-Tools (Web Serial API + SLCAN), keine lokale Installation nötig.

## 📜 Lizenz und Urheberrechtshinweise

URTC Tester ist (c) 2026 JuanenRac (Electro Hobby 3D). Dieser Hinweis
muss in jeder Verteilung dieses Projekts oder abgeleiteter Werke
enthalten sein.

Dieses Projekt besteht aus Quellcode und seiner eigenen Dokumentation,
die unter verschiedenen Lizenzen verfügbar gemacht werden - jede
passend zu dem, was sie tatsächlich abdeckt:

1. Der Quellcode (`urtc_tester.py` und jedes `tester_*.py`-Modul) und
   jedes daraus über `build_exe.bat`/`build_exe.sh` erstellte Binary
   sind unter der **GNU General Public License v3.0 (GPL-3.0)**
   verfügbar. Vollständiger Text unter
   https://www.gnu.org/licenses/gpl-3.0.html.

2. Die Dokumentation (dieses README und seine eigenen Übersetzungen -
   `README_spa.md`, `README_ita.md`, `README_fra.md`, `README_deu.md`)
   ist unter **Creative Commons Attribution-ShareAlike 4.0
   International (CC BY-SA 4.0)** verfügbar. Vollständiger Text unter
   https://creativecommons.org/licenses/by-sa/4.0/.

Dieses Tool ist der Live-CAN-Bus-Diagnose-Begleiter des
[URTC (Universal Robot Tool Controller)](https://github.com/JuanenRac/URTC)
-Projekts - siehe das eigene Repository dieses Projekts für die
Platinen-Firmware, Hardware-Designs und die vollständige
Protokolldokumentation, die dieses Tool ausübt. Die eigene Firmware von
URTC ist GPL-3.0 und ihre Hardware-Designs sind CERN-OHL-S v2; die
eigene Lizenz dieses Tools erstreckt sich hier nicht auf dieses
separate Projekt, und umgekehrt. Eine webbasierte Alternative, die
ähnliches Terrain abdeckt, existiert ebenfalls unter
[URTC Web Studio](https://github.com/JuanenRac/URTC-WEB-STUDIO).

Wenn Sie auf diesem Projekt aufbauen, denken Sie an die Lizenztrennung:
Codeänderungen sollten GPL-3.0 bleiben, Dokumentationsableitungen
sollten CC BY-SA bleiben - jeweils mit Zuschreibung zurück an dieses
Projekt und seinen Autor.

## 👤 Autor

**JuanenRac** (Electro Hobby 3D)
📧 electrohobby3d@gmail.com
📺 [youtube.com/@electrohobby3d](https://youtube.com/@electrohobby3d)

