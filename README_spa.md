<p align="center">
  <img src="/images/URTC_TESTER_BANNER.svg" alt="URTC Tester Logo" width="100%">
</p>

# URTC Tester (Windows / Linux)

<p align="center">
  <a href="README.md">🇺🇸 English</a> |
  🇪🇸 <b>Español</b> |
  <a href="README_fra.md">🇫🇷 Français</a> |
  <a href="README_ita.md">🇮🇹 Italiano</a> |
  <a href="README_deu.md">🇩🇪 Deutsch</a> |
  <a href="README_zho.md">🇨🇳 简体中文</a> |
  <a href="README_jpn.md">🇯🇵 日本語</a> |
  <a href="README_por.md">🇵🇹 Português</a>
</p>

### Un ejercitador de bus CAN en vivo para la placa URTC: muestra solo los controles y la telemetría del cabezal que está conectado

<p align="center">
  <img src="https://img.shields.io/badge/Licencia-GPL%203.0-blue.svg" alt="GPL 3.0 or later">
  <img src="https://img.shields.io/badge/Lenguaje-Python-3776AB.svg" alt="Python">
  <img src="https://img.shields.io/badge/UI-Qt%20Quick-38d4e6.svg" alt="Qt Quick">
  <img src="https://img.shields.io/badge/Tests-531-2ea44f.svg" alt="Tests">
  <img src="https://img.shields.io/badge/Protocolo-CAN-yellow.svg" alt="CAN">
</p>

---

**Comprobación de honestidad - lo que realmente funciona hoy:** los codificadores de payload CAN para las familias de control migradas a Qt Quick (`advanced_protocol.py`) son reales y están cubiertos por los tests de `tests/` (`python -m pytest -q`). La propia CI de este repositorio (`.github/workflows/ci.yml`) también los ejecuta, junto con `ruff check`, `python -m mypy`, `tools/ci_validate.py`, una compilación de sintaxis de cada archivo `.py` y los cuatro scripts `verify_qt_*.py`, así que una regresión ahí hace fallar la build. Los cuatro scripts `verify_qt_*.py` en la raíz del repositorio (`verify_qt_custom_frame.py`, `verify_qt_telemetry_watch.py`, `verify_qt_utility_panels.py`, `verify_qt_selftest.py`) son comprobaciones reales de extremo a extremo, deliberadamente fuera de `tests/`, contra un transporte falso con entrega real de señales entre hilos - los cuatro pasan con `QT_QPA_PLATFORM=offscreen python verify_qt_*.py`, que la CI también ejecuta. Ese es el techo honesto de lo que se verifica automáticamente: la capa de transporte, el manejo de ID/diseño de bytes CAN, y la lógica del puente Qt Quick son reales y se ejercitan contra tramas simuladas, no hardware real - como ya dice "Known limitations" más abajo, esto se construyó sin acceso USB, así que nada de esto se ha comprobado todavía contra una placa real. `qt_tester.py` y `assets/qml/TesterDeck.qml` son la implementación real y sustancial (miles de líneas combinadas), ejercitada por los tests con placas simuladas y por los scripts de verificación, nunca por una placa real.

---

> **Estado de seguridad física y de ciberseguridad:** este ecosistema no es un sistema de seguridad certificado y todavía no existe ninguna placa URTC poblada. Los bootloaders comprueban las imágenes de firmware con CRC32 y un HMAC-SHA256 de clave compartida, no con una firma asimétrica (prevista); las imágenes de aplicación publicadas están firmadas con la clave pública de desarrollo (`signing_key_kind: dev`), así que cualquiera puede producir una imagen que el bootloader acepte; no se ha transmitido nada a una placa real. Lee la [línea base de seguridad](https://github.com/JuanenRac/URTC-DOCS/blob/main/docs/SECURITY_BASELINE.md) y el [modelo de amenazas](https://github.com/JuanenRac/URTC-DOCS/blob/main/docs/THREAT_MODEL.md) antes de fiarte de cualquier afirmación de aquí para la seguridad de una persona.

## 📋 De un vistazo

| | |
|---|---|
| Versión | `0.4.3` |
| Madurez | Funcional |
| Tests | 531 (`python -m pytest -q`) |
| Tecnología | Python / PySide6 / Qt Quick / live CAN bus diagnostics |
| Destino | El PC de quien lo usa |
| En hardware real | Solo simulado: probado con emuladores, dobles de prueba o simuladores; no consta ninguna ejecución en hardware real para esta versión |

**Ir a:** [Resumen](#-resumen) · [Arquitectura](#-arquitectura) · [Funciones](#-funciones) · [Seguridad](#-seguridad-y-protección) · [Interfaces](#-interfaces) · [Inicio rápido](#-inicio-rápido) · [Pruebas](#-pruebas) · [Estructura](#-estructura-del-repositorio) · [Relacionados](#-proyectos-relacionados)

<!-- urtc-section:status_tester -->
## 🚦 Estado del proyecto

🟢 hecho y verificado · 🟡 funciona, con límites conocidos · 🟠 a medias o sin verificar · 🔴 sin hacer o sin funcionar. Nada es verde si nunca corrió en hardware real.

| Parte | Estado | Lo que el repositorio puede demostrar |
| --- | :---: | --- |
| Software | 🟡 | Funciona en un PC y contra el simulador; nunca se ha usado con una placa real. |
| Interfaz | 🟡 | La ventana funciona y se comprueba contra una placa simulada; no se ha probado con un adaptador real. |
| Pruebas | 🟢 | La batería de pruebas pasa en la CI en cada subida. |
| Hardware real | 🟠 | Aún no se ha ejecutado con una placa real: la prueba de banco sigue pendiente. |
| Documentación | 🟡 | README en ocho idiomas y documentos de referencia; las traducciones no las ha revisado ningún hablante nativo. |

<!-- /urtc-section:status_tester -->

## 🎯 Resumen

Un ejercitador en vivo de bus CAN para la placa URTC. Se conecta por el
mismo adaptador USB-CAN que usa el flasher, le pregunta a la placa para
cuál de sus 25 perfiles de herramienta está configurada actualmente
mediante jumpers, y muestra solo los controles y la telemetría propios
de esa herramienta - no una sola ventana intentando representar las 25 a
la vez. Todo lo que hace es un comando en tiempo de ejecución o una
lectura de telemetría contra la aplicación en ejecución; nunca toca la
flash, así que no hay nada aquí que pueda dejar la placa menos operativa
de lo que estaba al empezar.

### Relación con el flasher

Esta herramienta y [URTC Flasher](https://github.com/JuanenRac/URTC-FLASHER) comparten la misma capa de
transporte (las clases SLCAN y SocketCAN son idénticas) ya que ambas en
última instancia solo necesitan meter y sacar tramas CAN del mismo tipo
de adaptador, pero hacen trabajos fundamentalmente distintos:

| | Flasher | Tester |
|---|---|---|
| Toca la flash | Sí (ese es todo el propósito) | Nunca |
| Habla con | El bootloader, mayormente | La aplicación en ejecución |
| Propósito | Actualizar firmware | Ejercitar/verificar el hardware real de un cabezal de herramienta |

Si no estás seguro de cuál necesitas: si la placa ya está ejecutando
firmware y quieres comprobar que una herramienta realmente funciona (el
calentador calienta, el motor gira, el LED se enciende), quieres esta.

## 🧩 Papel en URTC

URTC-TESTER es el programa que comprueba lo que un cabezal URTC hace realmente mientras ejecuta su aplicación: se conecta por el mismo adaptador USB-CAN que URTC-FLASHER, pregunta a la placa para cuál de sus 25 perfiles de herramienta está configurada con puentes y muestra solo los controles y la telemetría de esa herramienta, nunca una ventana que intente representar las 25. Todo lo que hace es una orden en ejecución o una lectura de telemetría; nunca toca la flash, así que no puede dejar una placa peor de como la encontró. El protocolo que habla es el de URTC-COMMON, y URTC-WEB-STUDIO ofrece los mismos flujos en un navegador.

## 🏛️ Arquitectura

<p align="center">
  <img src="images/architecture.svg" alt="Arquitectura de URTC-TESTER: quién lo usa, qué contiene y de qué depende" width="100%">
</p>

Cómo encajan las partes de este repositorio: quién lo usa, qué contiene y de qué depende. La imagen se dibuja desde `docs/architecture.json` y se comprueba contra el código.

<!-- urtc-section:updates -->
### Cómo se actualiza

Este programa puede buscar una versión más nueva de sí mismo: el botón «Buscar actualización» pregunta una vez a GitHub y ofrece un paquete firmado solo si es para tu sistema y más nuevo. Nada se comprueba ni se instala por su cuenta salvo que actives la comprobación, y una actualización necesita tu confirmación. El paquete debe coincidir con su SHA-256 y con la firma de la clave de las releases fijada en el programa; la versión anterior se conserva y se restaura sola si la nueva no arranca. `urtc-updater --cli package list|check|install|rollback` hace lo mismo desde la línea de órdenes para el flasher y el tester, y `install --file` funciona sin red.
<!-- /urtc-section:updates -->

## 🖼️ Capturas de pantalla

<!-- urtc-shots -->
Capturadas a 1920×1080 en un banco de pruebas, con datos de ejemplo y sin ninguna instalación real detrás.

<table>
<tr>
<td width="50%" valign="top"><img src="images/screenshots/deck.png" alt="La ventana al abrirse: la puerta de transporte, el modo seguro de solo escucha, los perfiles de herramienta y los puntos de control de identidad y salud." width="100%"><br><sub>La ventana al abrirse: la puerta de transporte, el modo seguro de solo escucha, los perfiles de herramienta y los puntos de control de identidad y salud.</sub></td>
<td width="50%" valign="top"><img src="images/screenshots/heads.png" alt="Cabezales en el bus: un bus modelado con seis cabezales, uno en cada estado posible (seleccionado, conflicto de dirección, fallo retenido, en su bootloader, perdido y listo)." width="100%"><br><sub>Cabezales en el bus: un bus modelado con seis cabezales, uno en cada estado posible (seleccionado, conflicto de dirección, fallo retenido, en su bootloader, perdido y listo).</sub></td>
</tr>
<tr>
<td width="50%" valign="top"><img src="images/screenshots/help.png" alt="La ventana de Ayuda: los pasos para usar el programa, escritos en el idioma de la ventana." width="100%"><br><sub>La ventana de Ayuda: los pasos para usar el programa, escritos en el idioma de la ventana.</sub></td>
<td width="50%" valign="top"><img src="images/screenshots/updates.png" alt="La ventana de actualizaciones: un paquete firmado más reciente solo se instala después de que lo confirmes." width="100%"><br><sub>La ventana de actualizaciones: un paquete firmado más reciente solo se instala después de que lo confirmes.</sub></td>
</tr>
</table>
<!-- /urtc-shots -->

**Registrador de fallos, funciones opcionales, banco de rack y vista térmica (nuevo, comprobado solo con simulaciones):** el panel lee la caja negra de la placa (`0x1A8` / `0x1A9`) y la guarda como CSV y JSON, automáticamente una vez por cada error que la placa indica cuando esa opción está activada; activa las funciones opcionales del firmware (`0x1AE` / `0x1AF`, apagadas por defecto, con efecto tras el próximo arranque); tiene un rack de herramientas simulado con el protocolo serie de URTC-SMART-RACK, la identidad de cada cabezal (tipo y número de serie) y la exportación de una página de estado; y muestra la imagen de inspección térmica en falso color (una imagen simulada lo dice). Los nombres y tipos de herramienta ahora salen de los perfiles de herramienta compartidos de URTC-COMMON. Nada de esto se ha usado con una placa real.

**PID del calentador (nuevo, comprobado solo con simulaciones):** el panel lee el estado del PID del calentador del firmware (`0x1B9` / `0x1BA`: las ganancias en vigor, el estado y la salida del último ciclo de control), guarda ganancias (de 0 a 600) y inicia o cancela el autoajuste por relé, que calienta la punta alrededor de la consigna actual del soldador (100 a 445 C) y guarda las ganancias que encuentra. Guardar ganancias e iniciar el autoajuste piden la confirmación habitual; cancelar no. La cabeza simulada de la línea de comandos (`--transport simulate`) también responde a estas tramas. Hay que activar antes la función entre las funciones opcionales; nada de esto se ha usado con una placa real.

Estas imágenes son la ventana real, dibujada sin pantalla tal como se abre (nada conectado, nada enviado). La guía recorre el panel, la ventana de Ayuda y la de actualización.

[Guía con imágenes](docs/WINDOW_GUIDE.md)

## ✨ Funciones

### Cómo funciona

La ventana está distribuida en 3 columnas: izquierda y centro contienen
las secciones siempre visibles de abajo (1-4, luego 6), la derecha
contiene el panel por herramienta de la sección 5, que es la única
parte de la ventana que realmente cambia según lo que se detecte. Dividir
las secciones siempre visibles en 2 columnas en vez de apilarlas todas
en una mantiene la ventana sin crecer tanto en altura como para no caber
en una pantalla ordinaria, a medida que se fueron añadiendo más de estas
secciones con el tiempo. El propio panel de la impresora 3D (el más
alto de los 25) va un paso más allá y divide sus propios controles en 2
subcolumnas internamente, por el mismo motivo. Ver
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) para la guía de arquitectura
a nivel de módulos que resume esta sección.

**Conectar** (sección 1, idéntica al flasher): elige Serie/SLCAN o
SocketCAN, el puerto/interfaz, opcionalmente autodetecta el bitrate,
luego Conectar.

**La detección ocurre automáticamente al conectar** (o haz clic en
**Detectar** para repetirla): la herramienta envía `0x110` (consulta
herramienta activa) y `0x7F8` (consulta versión), y usa la respuesta
para:
- Mostrar cuál de los 25 perfiles de herramienta está activo, y el
  estado general de la placa (cualquier error declarado, fallo de bus
  CAN, todavía en la pantalla de arranque).
- Mostrar el HardwareID y la versión de firmware que reporta, marcando
  un desajuste si no coincide con el propio `THIS_HARDWARE_ID` de este
  proyecto.
- Construir el panel de **Controles de Herramienta** a la derecha para
  esa herramienta específica - y solo esa herramienta. Cambiar qué
  herramienta está jumpeada y detectar de nuevo desmonta el panel viejo
  y construye el nuevo desde cero.

**Controles Globales** (sección 2, siempre visible sin importar qué
herramienta esté activa): el override de color del LED de estado, el
color y encendido/apagado del anillo LED, y el modo de pantalla OLED
(`0x100`) - estos aplican a toda herramienta, así que no se mueven al
panel dinámico. En el modo Inspección AOI específicamente, el
encendido/apagado del anillo aquí se ignora en favor del propio control
de estrobo de esa herramienta (según [docs/CANBUS.md](docs/CANBUS.md)) - el color sigue
aplicando de cualquier forma.

**Placa de Expansión** (sección 3, siempre visible): el propio bus SPI
genérico y la línea DIAG0 de `CONN_EXPANSION` - el paso a través en
bruto que comparten todas las variantes de placa de expansión con
driver. El ADS1115 y los sensores MLX9064x, y el driver propio del
actuador de crimpado, no se controlan desde aquí - viven dentro del
panel de su propia herramienta en su lugar (Sonda Voladora, Inspección
Avanzada de PCB, Actuador de Crimpado - ver sección 4 abajo), ya que
cuál de ellos aplica realmente depende de qué perfil de herramienta
está configurado por jumpers.

**F-RAM de Persistencia** (sección 4, también siempre visible, pero
deliberadamente separada de Placa de Expansión de arriba): la FM24CL64B
comparte el propio bus I2C2 hardware con el OLED - un componente central
de la placa, no algo cableado a `CONN_EXPANSION` en absoluto. Agrupar
las 2 juntas implicaría una conexión entre ellas que no es real - el
propio conector de expansión no tiene F-RAM, ni EEPROM, nada no volátil
en él.
- **Paso directo SPI**: escribe bytes hex separados por espacios (1-7 de
  ellos, p. ej. `01 02 03`), pulsa Enviar, y ve exactamente qué volvió
  por MISO durante esa misma transferencia (`0x180`/`0x181`) - un
  transporte de bytes en bruto, no consciente de los registros TMC5160,
  igual que el propio enfoque del firmware. Útil para ejercitar el bus
  en sí antes de que valga la pena construir un panel dedicado para el
  protocolo de registros de una placa de expansión específica.
- **Nivel DIAG0**: **Consultar DIAG0** lee el estado actual de la línea
  de diagnóstico de stall/fallo de un TMC5160 (`0x182`/`0x183`) - HIGH
  (inactivo) o LOW (activado). Una lectura sondeada simple, no un valor
  en vivo/empujado - pulsa el botón de nuevo para actualizarlo.
- **F-RAM de Persistencia**: **Consultar Estado** lee de vuelta lo que
  la placa guardó por última vez antes de una pérdida de energía
  (`0x190`/`0x191`) - qué herramienta era, el setpoint, si había un
  error crítico activo en ese momento. **Borrar F-RAM...** la borra
  (`0x192`, con un diálogo de confirmación primero - esto no se puede
  deshacer).
- **Tipo de placa de expansión**: **Consultar** muestra cuál de las 7
  configuraciones posibles de `CONN_EXPANSION` está establecida
  actualmente (`0x1A1` - ver `EXPANSION.TXT`). Solo lectura aquí -
  establécela desde la propia sección CAN OTA de `URTC Flasher` en su
  lugar, ya que es un paso de configuración de hardware de una sola vez,
  no algo para cambiar casualmente desde una herramienta de diagnóstico
  en vivo.
- **Variante de sensor MLX9064x**: **Consultar** muestra cuál de los 3
  sensores térmicos de la familia MLX9064x (o ninguno) está configurado
  actualmente (`0x1A7` - ver `CANBUS.md`) - solo relevante cuando el
  tipo de placa de expansión de arriba es una variante Advanced o
  Basic+MLX9064x. Solo lectura aquí, mismo razonamiento que el tipo de
  placa de expansión de arriba.
- **Configuración libre de herramienta**: **Consultar** muestra la
  lectura cruda de los jumpers ID (0-31) junto a lo que dice
  actualmente el registro `free_tool_selection` de la F-RAM (`0x1A3` -
  ver `EEPROM.TXT` sección 5) - solo realmente consultado por una placa
  cuyos jumpers lean 0x1F/11111b. Solo lectura aquí, mismo razonamiento
  que el tipo de placa de expansión de arriba - `URTC Flasher` es la
  única herramienta que lo escribe.
- **Tipo de periférico y número de serie**: **Consultar** muestra el
  tipo de periférico fijo (siempre URTC/0x03) junto al número de serie
  del dispositivo establecido actualmente (`0x1A5` - ver `EEPROM.TXT`
  sección 6), una etiqueta asignada por el usuario para distinguir
  varias placas por lo demás idénticas en el mismo bus CAN. Solo lectura
  aquí también - `URTC Flasher` escribe el número de serie, esta
  herramienta solo lo lee de vuelta.

**Trama CAN Personalizada** (sección 6, también siempre visible): una
entrada de ID en bruto + bytes hex con envío de una vez y periódico -
para un comando que aún no tiene su propio control aquí, o para probar
algo no (o aún no) documentado en `docs/CANBUS.md`. Sin validación más
allá del rango de ID y DLC≤8; lo que sea que esto envíe es exactamente
lo que va al bus. La misma sección también abre el **Monitor de Bus en
Bruto** (ver abajo).

**Ejecutar Autoprueba** (junto a Detectar): ejecuta un pequeño conjunto
de comprobaciones de comunicación seguras y en reposo para la
herramienta que esté actualmente detectada - confirma que tanto la
consulta de herramienta activa como la de versión responden, luego
(para herramientas con telemetría) envía un setpoint/velocidad/potencia
seguro de 0 y comprueba que llega la telemetría esperada.
Deliberadamente nunca envía nada que realmente caliente, dispare, o
gire a potencia significativa - esto verifica que el ida y vuelta de
comunicación funciona, no que un actuador responda físicamente, ya que
confirmar eso necesita a un humano observando de todas formas. Pide
confirmación antes de enviar nada. Las herramientas sin telemetría
(movimiento simple) o que son puramente dirigidas por eventos (sonda de
escaneo) reciben una nota solo informativa en vez de un aprobado/fallido
real. **La cobertura es parcial**: solo 7 de las 25 herramientas tienen
un paso de autoprueba definido (soldador, taladro, láser, impresora 3D,
AOI, vacío, sonda de escaneo) - las otras 18 herramientas no ejecutan
ninguna comprobación al pulsar este botón.

**Gráficos de temperatura en vivo**: tanto los paneles del soldador
como de la boquilla de la impresora 3D muestran un pequeño gráfico de
línea deslizante junto a su lectura de temperatura en vivo - un widget
Canvas de Qt Quick simple, no una dependencia nueva (matplotlib/
pyqtgraph romperían la política de cero dependencias de esta herramienta
más allá de pyserial). Escala de eje Y fija (0 hasta el techo de
setpoint de esa herramienta) en vez de auto-escalado, así que la
tendencia es fácil de leer de un vistazo en vez de que la escala se
desplace por debajo.

**Monitor de Bus en Bruto** (abierto desde la sección Trama CAN
Personalizada): una ventana separada mostrando cada trama vista,
cualquier ID, independiente del panel de herramienta activo - una tabla
que se desplaza en vivo (Tiempo/ID/DLC/Datos/Δt), Pausar/Limpiar, y una
lectura aproximada de carga de bus/tasa de tramas (actualizada una vez
por segundo; la cifra de carga no modela la sobrecarga de bit-stuffing,
así que trátala como una cifra diagnóstica aproximada, no una medición
certificada). **Exportar .trc...**/**Exportar .asc...** guardan la
tabla mostrada actualmente como un archivo de traza simplificado al
estilo PEAK PCAN-View / Vector CANalyzer respectivamente - lo bastante
cercano como para ser legible por la mayoría de herramientas que esperan
esos formatos, no garantizado byte-idéntico a lo que producen las
aplicaciones reales. Si `urtc_custom_ids.json` existe junto a este
script (opcional, no incluido por defecto - `{"0x199": "My Sensor"}`),
la columna ID muestra ese nombre amigable junto al ID hex en bruto -
útil para cualquiera que pruebe el propio tráfico de una placa de
expansión personalizada sin necesitar modificar el código fuente de
esta herramienta.

### Cobertura de herramientas

Cada uno de los 25 perfiles tiene su propio panel, construido
directamente a partir de `docs/CANBUS.md`:

| Herramienta | Controles | Telemetría en vivo |
|---|---|---|
| Soldador | Temperatura de setpoint, encendido/apagado; alimentador de estaño dirección + cuenta de pasos (movimiento de una vez); consulta y reseteo a 0 de la posición del alimentador | Temperatura real; posición del alimentador (estimación en lazo abierto) |
| Dispensador de Pasta/Líquido, Destornillador, ambos Grippers, SMT Pick & Place, Vacuum Gripper (LG) | Dirección + cuenta de pasos (movimiento de una vez) | ninguna (0x120 compartido, sin telemetría para ninguna de estas 7) |
| Recogida por Vacío | ninguno | Lectura analógica, pieza detectada |
| Taladro | Velocidad + dirección | RPM real, endstop |
| Inspección AOI | Modo de anillo (apagado/estrobo/continuo) + período de estrobo | Endstop |
| Grabador Láser | Potencia + armado/seguro del bloqueo del láser (una salida del firmware, no un interlock de hardware) | Endstop |
| Impresora 3D | Setpoint de boquilla, dirección/pasos del extrusor, potencia del ventilador de capa, potencia del ventilador de hotend | Temperatura de hotend, RPM del ventilador de capa, RPM del ventilador de hotend |
| Sonda de Escaneo | ninguno | Cuenta de eventos de impacto + marca de tiempo (`0x095` de máxima prioridad) |
| Electroimán | Casilla energizar/liberar bobina | ninguna |
| Soldador por Puntos | Duración de pulso + Disparar | ninguna (solo dispara si el sensor de contacto lee HIGH primero - ver `docs/CANBUS.md`'s propio `0x1C0`) |
| Recubrimiento Conformal, Insertador a Presión | ninguno - panel solo informativo | ninguna - ambos IDs de herramienta no tienen manejador CAN alguno, su propio actuador y sensor viven en la placa base del propio robot, ver `docs/TOOLS.TXT` |
| Sonda Voladora | La lectura básica es automática; la lectura avanzada necesita una palabra de config ADS1115 en bruto (hex) + Disparar Conversión + Leer Resultado | Lectura básica del ADC integrado (automática, `0x243`) |
| Curado UV | Deslizador de potencia (0-255) + Enviar/Apagar | ninguna |
| Aire Caliente para Retrabajo | Temperatura de setpoint, potencia del soplador, encendido/apagado | Temperatura en vivo (comparte la propia telemetría `0x135` y gráfica en vivo del soldador - mismo lazo térmico físico) |
| Actuador de Crimpado | Dirección + cuenta de pasos (movimiento de una vez, misma forma que las herramientas de movimiento compartidas de arriba, pero llega al driver de una placa de expansión vía `0x1F0` en vez del `0x120` integrado) | ninguna |
| Inspección Avanzada de PCB | Disparar Captura, Comprobar Estado, Leer Imagen Térmica | Lienzo de mapa de calor de 32x24 píxeles (gradiente azul a rojo), extraído chunk por chunk por CAN bajo demanda - no es un video en vivo, ver sección 6 abajo |
| Jetting de Pasta de Soldar | Canal PWM + frecuencia (Configurar), luego ciclo + duración (Disparar Pulso) | ninguna |
| Soldador Ultrasónico | Duración de pulso + Disparar | ninguna (misma forma que el Soldador por Puntos, pero sin puerta de sensor de contacto) |

**Los watchdogs de comunicación se manejan por ti.** El soldador, el
Aire Caliente para Retrabajo (comparte el mismo lazo térmico y watchdog
que el soldador), el láser, y la boquilla de la impresora 3D tienen
cada uno un watchdog de 250ms en el firmware; el ventilador de capa
tiene uno de 1000ms. Marcar la casilla "Activo" correspondiente no solo
envía el comando una vez - lo reenvía automáticamente (150ms para las
herramientas con watchdog de 250ms, 400ms para el ventilador de capa)
mientras la casilla siga marcada, de la misma forma en que un
controlador maestro real tiene que hacerlo. Desmarcarla envía una única
trama de cero/apagado y para. El ventilador de hotend no tiene watchdog
(un detector de estancamiento en su lugar - ver `docs/CANBUS.md`), así
que es un envío simple de una vez.

**Notas de comodidad (utilidades de software, no funciones de seguridad).**

- **PARAR TODAS LAS SALIDAS** (en ambas ventanas, disponible con la conexión hecha y las comprobaciones activas armadas) envía todas las órdenes de apagado conocidas - calefactores, láser, taladro, lámpara UV, ventilador de capa, liberación del electroimán, motores paso a paso simples y crimpadora - sea cual sea la herramienta instalada, y detiene todos los refrescos. El ventilador del hotend se deja encendido a propósito, porque la boquilla puede seguir caliente. Es una orden de software enviada por el bus CAN, no una parada de emergencia: no puede actuar si falla el bus, el adaptador, el PC o la placa.
- Los pulsos de soldadura de un solo disparo, el pulso de pasta y el crimpado piden confirmación también en la ventana clásica, como siempre hace el deck de Qt Quick.
- El taladro y la lámpara UV se refrescan igual que el láser y los calefactores. Mientras se mantiene el calefactor de la impresora 3D, su refresco de 150 ms lleva 0 pasos de extrusor, que el firmware lee como orden de parada: un movimiento del extrusor iniciado en ese estado se cancela en 150 ms, así que mueve el extrusor con el calefactor apagado hasta que el firmware ofrezca un modo que lo deje en paz.
- El puerto y la velocidad se recuerdan para la próxima sesión (`config.json`) y el deck de Qt Quick tiene su propio selector de velocidad. La **autodetección** primero solo escucha a cada velocidad (no se transmite nada en un bus vivo) y solo pregunta a cada velocidad cuando el bus está completamente en silencio.
- El Monitor de bus en bruto se puede limitar a algunos ID CAN (**Filtro de ID**) y a las tramas cuyos datos cambiaron (**Solo cambios**).

#### 🔥 Prueba de banco de embalamiento térmico (firmware URTC 0.3.2+ / 0.3.3+)

Detect ahora muestra *por qué* una placa enclavó un error: el byte 4 de
`0x111` (protección contra embalamiento térmico: MAXTEMP, HEATING_NO_RISE o
DROPPED_AT_TARGET) aparece en el estado de la placa, y un reinicio causado
por el watchdog de hardware (byte 5 de `0x111`) queda en el registro.
**Contadores térmicos** (panel F-RAM en ambas interfaces) lee `0x1AA`/`0x1AB`:
fallos térmicos acumulados, horas totales con el calentador encendido y el
último fallo. Las respuestas de firmware antiguo (`0x111` de 4 bytes, sin
`0x1AB`) se muestran como "no informado", nunca como cero. El procedimiento
paso a paso para confirmar la protección en una placa real está en
[`docs/THERMAL_RUNAWAY_BENCH_TEST.md`](docs/THERMAL_RUNAWAY_BENCH_TEST.md).

<!-- urtc-section:heads -->
### Varios cabezales en un bus

El firmware puede hacer que varios cabezales compartan un bus CAN (la extensión multinodo). Viene **desactivada por defecto**, y un bus con un solo cabezal funciona exactamente como antes. La ventana **Cabezales** encuentra los cabezales, lista cada uno con su dirección, herramienta y número de serie, y muestra su estado: listo, seleccionado, conflicto de dirección, fallo retenido, en su bootloader o perdido. Seleccionas uno, el programa pide confirmación y solo entonces le envía algo; mientras haya varios cabezales en el bus, un comando se rechaza hasta que uno esté seleccionado y lo haya confirmado. Si se pierde el cabezal seleccionado, todos los cabezales pasan a su estado seguro (una casilla de la ventana lo desactiva). Se ha probado solo contra un modelo del bus, no con placas. Véase `docs/MULTINODE.md` en URTC-COMMON.
<!-- /urtc-section:heads -->

## 🔒 Seguridad y protección

| Riesgo | Defensa |
|---|---|
| Una orden enviada a una placa que no es la herramienta que muestra la ventana | El panel de una herramienta se muestra solo para la herramienta que la propia placa informó, y cada orden está condicionada por una coincidencia de identidad |
| Transmitir sin querer | La ventana arranca en modo solo escucha: no puede transmitir hasta que se arman deliberadamente las comprobaciones activas, y cada acción que actúa sobre la placa pide antes una confirmación en la ventana |
| Dañar la placa | El tester nunca toca la flash: todo lo que hace es una orden en ejecución o una lectura de telemetría contra la aplicación que está funcionando |
| Un registro que alguien pudiera alterar | La exportación de la sesión es un zip con el registro, un manifiesto que lo nombra por su SHA-256 y los diagnósticos del sistema |

Nada de esto se ha probado en una placa real y nada es una función de seguridad certificada; consulta las limitaciones más abajo.

## 🔌 Interfaces

Igual que el flasher: un registro de sesión con marca de tiempo se
escribe automáticamente en `logs/` (seguro de borrar),
y **Exportar Paquete de Depuración** guarda un `.zip` con el registro
actual en pantalla más diagnósticos básicos del sistema (SO, versión de
Python, transporte/puerto/bitrate actual, herramienta detectada) para
entregar a quien esté depurando un problema de cabezal de herramienta.

### 🤖 Sin ventana: planes de prueba

`python urtc_tester.py --headless COMANDO` ejecuta el tester sin ventana, para una línea de producción, un script de banco o un trabajo de CI: `info` (quién responde: herramienta, firmware, estado rápido), `selftest`, `run-plan ARCHIVO` y `validate-plan ARCHIVO`. Un plan es un archivo JSON corto de pasos que vive en `plans/` (esperar una herramienta, sin fallos, una versión mínima de firmware, el autotest, una trama cuyo valor esté en un rango, una espera, una pregunta a la persona del banco). El comando escribe un registro de cada trama y un registro de resultado que nombra el registro por su SHA-256, el mismo que el del panel. Un plan solo envía consultas salvo que diga `"actuation": true` y el operador añada `--allow-actuation`; las tramas del bootloader, de actualización, de configuración y de borrado no se envían nunca, un comando que el firmware abandona si no se refresca (un calentador, un taladro, un láser) puede repetirse mientras el plan espera (`keepalive_ms`), y tras un plan que ordenó algo se apagan de nuevo todas las salidas. `--transport simulate` reproduce una cabeza simulada y `--transport replay --port ARCHIVO` una traza `.trc` o `.asc` grabada, de modo que un plan se puede probar sin placa. Código de salida: 0 correcto, 1 una comprobación falló, 2 el plan o los argumentos son erróneos, 3 la prueba no pudo realizarse. El texto que imprime está en inglés, como la línea de comandos del flasher. Detalles en [`docs/HEADLESS.md`](docs/HEADLESS.md). Nada de esto se ha ejecutado contra una placa real.

**Planes en la ventana (nuevo, comprobado solo con tests y la cabeza simulada):** la sección PLANES DE PRUEBA, al final de la columna derecha de la ventana, lista los planes de `plans/`, ejecuta el que elijas contra la placa conectada con el mismo motor (no en modo solo escucha y solo mientras nada más lea el bus), muestra cada paso en cuanto termina, hace en un diálogo las preguntas de un paso de confirmación y guarda el log y el registro de resultado. Un plan que ordena salidas pide antes una confirmación y al final se apagan todas las salidas; Cancelar lo detiene tras el paso en curso.

**Buscar actualización.** El botón «Buscar actualización» pregunta una vez a GitHub por la última release y solo ofrece descargarla si trae un paquete para este sistema más nuevo que la versión instalada. El paquete solo se acepta si su SHA-256 y su firma Ed25519 (la clave de las releases, fijada en el programa) son válidos; se instala únicamente tras tu confirmación, nunca mientras haya una salida activada, y se conserva la versión anterior para poder volver (y se restaura sola si la nueva no arranca). Nada se comprueba ni se instala por su cuenta: la comprobación al abrir es una opción, apagada por defecto, y la confirmación solo se desactiva en la misma ventana tras un aviso.

**Reproducir una traza grabada.** «Abrir traza» carga una traza `.trc` o `.asc` (las que exporta el monitor del bus, o de PCAN-View y CANalyzer) y reproduce sus tramas recibidas en una lista propia, marcadas como REPLAY, de 0,25x a 10x, con pausa, detener y repetir; un silencio de más de dos segundos se acorta. Una reproducción nunca transmite, nunca responde a una petición, nunca se mezcla con el monitor del bus ni con su exportación, y no se reproduce mientras haya una placa conectada (se pausa sola si se conecta una). Un archivo de más de 50 MB o sin tramas recibidas se rechaza y lo dice.

**Visor de la caja negra.** El registro leído de la placa, y cualquier registro guardado antes (`.json` o `.csv` escritos por este programa, abiertos con «Abrir un registro guardado», sin placa), se dibuja como la temperatura medida y la consigna a lo largo del tiempo, con una marca donde el indicador de error se levantó por primera vez, y se lista muestra a muestra con los indicadores en palabras. Cada campo debe ser un entero dentro del rango y un registro tiene como máximo 67 muestras; un archivo que no es un registro se rechaza con el motivo y el dibujo anterior se mantiene.

**Sin hardware:** una placa virtual hace el papel del adaptador y de la placa. Ejecuta `python -m urtc_can.virtual_board` y pasa su URL serie como puerto (`--transport serial --port socket://127.0.0.1:7777`); la placa responde a la consulta de versión y al estado rápido como una aplicación, de modo que `info` y los planes de consultas se ejecutan de principio a fin sin nada conectado. Es un modelo escrito a partir de la descripción del protocolo, no un cabezal de herramienta: el autotest de una herramienta informa de lo que no puede leer.

## 🚀 Inicio rápido

Mismo patrón que el flasher:

```
pip install -r requirements.txt
python urtc_tester.py          # Windows
python3 urtc_tester.py         # Linux
```

### Panel visual de control

El panel de comandos **Qt Quick** es ahora el predeterminado real:
~~~
python urtc_tester.py
~~~
Usa los transportes SLCAN/SocketCAN y arranca en modo sólo
escucha, por lo que no puede transmitir hasta que armes deliberadamente las
comprobaciones activas. Cada uno de los comandos propios de los 25 perfiles de
herramienta tiene aquí cobertura real y confirmada (movimiento, taladro, AOI,
electroimán, pulso de soldadura por puntos/ultrasónica, proyección de pasta,
flying probe, inspección térmica, los 5 actuadores con watchdog-keepalive,
telemetría de vacío/sonda de escaneo), todos con la misma compuerta: una
coincidencia de identidad, un modo activo armado explícitamente y una
confirmación del usuario en QML antes de transmitir nada.
Todavía no se ha comprobado nada de esto con una placa real - consulta "Limitaciones conocidas" más abajo.

El panel también muestra las **lecturas en directo** de la herramienta detectada (temperatura con un gráfico deslizante y exportación a CSV, RPM, finales de carrera; solo escuchan, así que funcionan en modo solo escucha y junto a una salida en marcha), ejecuta el **autotest**, avisa en la cabecera cuando la **comprobación de salud del bus** (una consulta de la herramienta activa cada 3 segundos mientras nada más usa el bus) detecta un problema, y tiene un diálogo **Acerca de URTC Tester** con el Readme, la Licencia y la página de GitHub, junto a **Guardar registros...**.

La cabecera de la ventana Qt Quick tiene un selector de idioma; la elección se guarda y se aplica en el siguiente arranque. También consulta y reinicia la posición del alimentador de hilo del soldador (estimación en lazo abierto; el reinicio pide confirmación). La sonda de identidad muestra también el número de parche del firmware cuando la placa lo envía (firmware URTC 0.3.5 y posterior); el firmware anterior muestra solo mayor.menor.

El flujo de diagnóstico CAN en vivo existente usa ahora una superficie de control azul marino/cian: cabecera de producto, tarjeta de conexión de alto contraste, pestañas de herramientas claras, registro de sesión oscuro y canal de progreso visible. Este cambio visual y de accesibilidad no modifica la monitorización pasiva ni el enrutamiento de comandos, y nada de ello se ha probado en una placa real.

### Cabecera y herramientas

- **Cabecera** - el estado de la conexión, el aviso de salud del bus, el selector de idioma (la elección se guarda y se aplica en el siguiente arranque) y la versión.
- **Guardar registros...** y **EXPORTAR SESIÓN (REGISTRO CON HASH)** - el registro de la pantalla como texto plano, o un zip con el registro, un manifiesto que lo nombra por su SHA-256 y los diagnósticos del sistema (ver «Registros y paquetes de depuración» más abajo).
- **Acerca de URTC Tester** - versión y autor, con botones para el **Readme** (en el idioma de la interfaz cuando existe traducción), la **Licencia** y la página **GitHub de URTC** del proyecto.

### Estructura de archivos

Esta herramienta está organizada en módulos por responsabilidad, puramente por legibilidad - no hay ninguna diferencia funcional entre tenerlos como archivos separados o como uno grande. `tester_config.py` contiene las constantes de configuración/idioma/protocolo, `tester_transports.py` contiene SLCAN/SocketCAN, `tester_bus_monitor.py` contiene el filtro de tramas y las estadísticas del bus, `qt_tester.py` es el puente de Qt Quick (con `assets/qml/TesterDeck.qml`), `tester_selftest.py`, `tester_telemetry.py` y `tester_autodetect.py` son la lógica sin ventana del autotest, de las lecturas en directo y de la búsqueda de velocidad, y `urtc_tester.py` es solo el punto de entrada.

**Idioma**: inglés por defecto. Se cambia con el selector de idioma de la cabecera de la ventana - cambia la interfaz (etiquetas, botones, diálogos, y mensajes de registro) a cualquiera de los 8 idiomas disponibles, se guarda inmediatamente en `config.json` junto a esta
herramienta, y se aplica en el siguiente arranque. Las traducciones
viven en archivos de texto plano bajo `language/` (`english.lng`,
`spanish.lng`, `italian.lng`, `french.lng`, `german.lng`, `chinese.lng`,
`japanese.lng`, `portuguese.lng`) como pares simples `CLAVE=Valor`, uno por línea - las líneas que empiezan con `#` y
las líneas en blanco se ignoran, y un `\n` literal dentro de un valor se
convierte en un salto de línea real (usado por el puñado de mensajes de
diálogo multilínea). Generados desde el catálogo de URTC-COMMON (una traducción se corrige allí y los archivos se escriben de nuevo, nunca a mano), o como punto de partida para otro idioma (añade
`language/<nombre>.lng`, añade `("<nombre>", "Nombre Nativo")` a
`AVAILABLE_LANGUAGES` cerca del principio de `tester_config.py`, y pon
`"language": "<nombre>"` en `config.json`). Una clave que falte en un
archivo de idioma cae de vuelta a mostrar el nombre de esa misma clave
en vez de fallar, y un archivo de idioma ausente o ilegible (edición
defectuosa, nombre de archivo equivocado) cae de vuelta al inglés para
toda la interfaz - de cualquier forma la herramienta se mantiene usable
mientras se resuelve el desajuste.

**Configuración de SLCAN/SocketCAN en Linux** (reflasheo del adaptador,
permisos de serie, levantar la interfaz con `ip link`) es exactamente
igual que la sección 1 del flasher - ver el propio
[README de URTC Flasher](https://github.com/JuanenRac/URTC-FLASHER)
secciones 1 y 2 en vez de duplicarlo aquí.

<!-- urtc-section:compatibility -->
### Requisitos y compatibilidad

Qué versiones de los programas de URTC funcionan juntas, y qué versión del protocolo habla cada una, figura en la tabla de compatibilidad que genera URTC-COMMON: [docs/COMPATIBILITY.md](https://github.com/JuanenRac/URTC/blob/main/docs/COMPATIBILITY.md).
<!-- /urtc-section:compatibility -->

## 🧪 Pruebas

La suite tiene 531 pruebas (`python -m pytest -q`; con Qt en un equipo sin pantalla, `QT_QPA_PLATFORM=offscreen`; las que necesitan PySide6 se omiten sin él): los codificadores y decodificadores de carga CAN de cada familia de herramientas, los transportes SLCAN y SocketCAN contra simulados, la sonda de identidad, el autotest, los reenvíos de vigilancia, la comprobación de salud del bus, los planes de prueba y el modo sin ventana, la exportación de sesión con su hash, los archivos de idioma y los paneles Qt Quick. Cuatro scripts en la raíz (`verify_qt_*.py`) manejan los paneles Qt Quick de extremo a extremo con un bucle de eventos Qt real. La CI ejecuta además `ruff check`, `python -m mypy` y `tools/ci_validate.py`. Nada de esto se ha ejecutado contra una placa real.

## 🏗️ Compilación y publicación

O compila un binario independiente: `build_exe.bat` en Windows,
`./build_exe.sh` en Linux. Ambos limpian `build/`/`dist/` primero y
empaquetan `assets/` (el banner y el icono) en el ejecutable - ver
[docs/BUILD_AND_RUN.md](docs/BUILD_AND_RUN.md) para la ruta de
validación sin versionado (`build-test.bat`/`build-test.sh`) sobre la
que se apoyan estos scripts de empaquetado, y el propio README del
flasher para el razonamiento completo detrás de los scripts de
empaquetado en sí, ya que se aplica idénticamente aquí.

**Versión:** `TESTER_VERSION` (en `tester_config.py`, visible en la barra de título, el diálogo Acerca de, los registros de sesión y los paquetes de depuración) sigue `MAJOR.MINOR.PATCH` y solo se sube con el paso explícito `python bump.py`. Ejecutar desde el código (`python urtc_tester.py`) y compilar (`build_exe.bat` / `build_exe.sh`) nunca la tocan. Consulta `CHANGELOG.md` para el historial de versiones.

## 📂 Estructura del repositorio

<p align="center">
  <img src="images/repository-structure.svg" alt="Estructura del repositorio URTC-TESTER" width="100%">
</p>

<details>
<summary>Versión en texto del árbol</summary>

```text
URTC-TESTER/
├── urtc_tester.py                                     punto de entrada
├── qt_tester.py                                       el panel Qt Quick
├── tester_*.py                                        transportes, monitor, autotest, planes, telemetría
├── advanced_protocol.py                               codificadores puros de cargas CAN
├── verify_qt_*.py                                     comprobaciones de extremo a extremo de los paneles Qt
├── urtc_can/                                          protocolo, transportes y actualizaciones (copia)
├── urtc_ui/                                           ayudas de interfaz (copia)
├── tests/                                             un archivo de pruebas por área
├── plans/                                             planes de prueba de ejemplo (JSON)
├── language/                                          los ocho archivos de idioma .lng
├── assets/                                            QML, banner e icono
├── docs/                                              arquitectura, compilación y ejecución
├── logs/                                              registros de sesión (fuera de Git)
├── tools/                                             comprobación de compilación y herramientas compartidas
├── images/                                            banner e imágenes de este README
├── .github/                                           flujo de CI y plantillas de issues y pull requests
├── test.sh test.bat                                   ejecutan las pruebas
├── run.sh run.bat                                     arrancan el programa
├── build-test.sh build-test.bat                       scripts de compilación y pruebas que no cambian nada en el repositorio
├── urtc.project.json                                  manifiesto: versión, papel, madurez y comando de compilación
├── CHANGELOG.md                                       qué cambió en cada versión
├── SECURITY.md SUPPORT.md LICENSE                     política de seguridad, soporte y licencia
├── CONTRIBUTING.md CODE_OF_CONDUCT.md                 cómo contribuir y código de conducta
├── .gitattributes .gitignore                          ajustes de Git
├── build_exe.sh build_exe.bat                         programa independiente (PyInstaller)
├── bump.py bump_version.py bump_manifest_version.py   scripts que suben la versión
├── requirements*.txt requirements*.lock               dependencias, con sus bloqueos
├── mypy.ini ruff.toml .coveragerc                     ajustes de tipos, lint y cobertura
├── urtc_i18n.lock.json                                bloqueo de los archivos de idioma generados
└── NOTICE LICENSE.md                                  aviso de copyright y licencia de la documentación
```

</details>

La lista anotada de cada archivo de código, una línea por archivo, está en [docs/SOURCE_MAP.md](docs/SOURCE_MAP.md).

## 🗺️ Hoja de ruta y límites conocidos

El contrato de evidencia de esta herramienta - qué cuenta como
pass/fail/unknown, por qué la ausencia de evidencia siempre es unknown y
nunca pass, y por qué no otorga por sí misma autoridad para flashear
firmware - está documentado en
[docs/INTEGRATION_CONTRACT.md](docs/INTEGRATION_CONTRACT.md).

- **No probado contra hardware real.** Cada pieza aquí - la capa de
  transporte, el manejo de ID CAN/disposición de bytes, la temporización
  de keepalive del watchdog - se comprobó de forma aislada (tramas
  simuladas, un subproceso real para la temporización donde aplica)
  pero el entorno que construyó esto no tiene acceso USB. Trata una
  primera sesión real con la misma precaución que pide el propio README
  del flasher.
- **Un panel de herramienta a la vez, por diseño**, no una limitación
  actual a eliminar más adelante - ver la introducción de arriba para
  el motivo.
- **Los colores globales de LED son un override directo**, no una
  lectura en vivo - no hay telemetría de qué están mostrando realmente
  en este momento los LEDs de estado/anillo, solo lo que se ordenó por
  última vez.
- **La propia imagen térmica de Inspección Avanzada de PCB se basa en
  extracción, no en un feed en vivo.** Leer una imagen completa
  significa solicitar los 48 chunks secuencialmente por CAN (peor caso,
  la propia resolución de MLX90640/MLX90642) - esto puede tardar varios
  segundos, y no existe un modo de envío en streaming en el propio
  protocolo CAN de esta herramienta para hacerlo más rápido. Primero hay que disparar una captura; Leer Imagen Térmica espera entonces hasta dos segundos a que el sensor indique que está listo y, si no lo hace, no lee nada, porque el firmware no responde a las peticiones de chunk antes de ese momento. Primero se pregunta qué sensor hay instalado (48 chunks para MLX90640/MLX90642, 12 para MLX90641), y un chunk perdido deja sus píxeles en blanco en lugar de desplazar el resto de la imagen.
- **Ejecutar Self-Test solo cubre 7 de las 25 herramientas** (soldador,
  taladro, láser, impresora 3D, AOI, vacío, sonda de escaneo) - ver
  "Cómo funciona" arriba para la explicación completa. Las otras 18
  herramientas no reciben ninguna comprobación automatizada desde ese
  botón; verificarlas sigue significando observar cómo el hardware
  real responde a los controles de su propio panel.

## 🌍 Idiomas

El README y los textos existen en inglés, español, francés, italiano, alemán, chino, japonés y portugués de Portugal.

## 🔗 Proyectos relacionados

URTC se compone de repositorios independientes, cada uno con su versión, sus pruebas y su README. Esta es la familia, por grupos:

* **URTC Tool Platform:**
  * [URTC](https://github.com/JuanenRac/URTC) - firmware de la placa del cabezal de herramienta (25 perfiles de herramienta, bootloader CAN) y la referencia del protocolo CAN.
  * [URTC-COMMON](https://github.com/JuanenRac/URTC-COMMON) - el protocolo CAN escrito una sola vez como datos (especificación, tablas generadas, vectores de conformidad) y el código que comparten los programas.
  * [URTC-FLASHER](https://github.com/JuanenRac/URTC-FLASHER) - herramienta de escritorio que actualiza el firmware de la placa por CAN o por SWD/JTAG.
  * [URTC-GATEWAY](https://github.com/JuanenRac/URTC-GATEWAY) - pasarela delante del bus CAN: solo deja pasar los identificadores de una lista, limita su frecuencia y pide una clave de sesión.
  * [URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK) - lógica en C independiente del hardware y protocolo de órdenes para un soporte de herramientas con precalentamiento y seguimiento del ciclo de vida.
  * **URTC-TESTER** (este repositorio) - probador de escritorio del bus CAN en vivo que muestra los controles y la telemetría del perfil de herramienta que informa una placa.
  * [URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL) - protocolo de tramas de sensor en C y un acompañante en Python térmico/RGB para un cabezal de inspección.
  * [URTC-WEB-STUDIO](https://github.com/JuanenRac/URTC-WEB-STUDIO) - aplicación de navegador que graba y prueba la placa por Web Serial y SLCAN, sin instalar nada.
* **Ecosystem Operations:**
  * [URTC-DEVTOOLS](https://github.com/JuanenRac/URTC-DEVTOOLS) - las herramientas de repositorio compartidas de la familia como un conjunto con versión y un fichero de bloqueo que distingue una copia editada de una desfasada.
  * [URTC-DOCS](https://github.com/JuanenRac/URTC-DOCS) - arquitectura, interfaces, línea base de seguridad y catálogo generado del ecosistema, más las herramientas que comparan todos los repositorios.
  * [URTC-UPDATER](https://github.com/JuanenRac/URTC-UPDATER) - herramienta de escritorio que detecta, instala y actualiza los repositorios de la familia URTC, una acción explícita cada vez.

**Proyectos hermanos (independientes, con la misma base y herramientas):**

* **[HYDRA-UMC-DOCS](https://github.com/JuanenRac/HYDRA-UMC-DOCS)** - proyecto hermano: el centro de documentación de HYDRA-UMC, un ecosistema independiente que comparte base y herramientas con este
* **[ARMOR-DOCS](https://github.com/JuanenRac/ARMOR-DOCS)** - proyecto hermano: el centro de documentación de A.R.M.O.R., el ecosistema de seguridad, también independiente y sobre la misma base
* **[JuanenRac](https://github.com/JuanenRac/JuanenRac)** - el perfil y el panel de estado de todos los ecosistemas

## 📚 Documentación

- **[CONTRIBUTING.md](CONTRIBUTING.md)** — stack tecnológico y pautas de codificación para un pull request.
- **[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)** — los estándares de comportamiento esperados en esta comunidad.
- **[SECURITY.md](SECURITY.md)** — cómo reportar una vulnerabilidad, y las áreas reales de enfoque en seguridad de este proyecto.
- **[SUPPORT.md](SUPPORT.md)** — dónde hacer preguntas y reportar errores.
- **[LICENSE.md](LICENSE.md)** — la licencia propia de este proyecto.

## 🤝 Contribuir y comunidad

* Antes de una pull request ejecuta `URTC_CI=1 python tools/ci_validate.py`: debe pasar. Consulta [CONTRIBUTING.md](CONTRIBUTING.md) y el [código de conducta](CODE_OF_CONDUCT.md).
* El README existe en ocho idiomas: un cambio en el texto se hace en los ocho archivos, y las secciones compartidas con otros repositorios las escribe `tools/readme_sections.py` de URTC-COMMON.
* Un cambio en el protocolo CAN empieza en URTC-COMMON (`spec/can_protocol.json`) y llega a este repositorio mediante la copia comprobada.
* No describas como funcionando en una placa lo que solo se ha compilado.
* Informa de una vulnerabilidad en privado: [SECURITY.md](SECURITY.md). Preguntas, ideas e informes: electrohobby3d@gmail.com ([SUPPORT.md](SUPPORT.md)).

## 👤 AUTOR

**JuanenRac** (Electro Hobby 3D)
📧 electrohobby3d@gmail.com
📺 [youtube.com/@electrohobby3d](https://youtube.com/@electrohobby3d)

## 📜 LICENCIA

Licencia: **GPL-3.0-or-later** para el código fuente, **CC BY-SA 4.0** para esta
documentación - ver `LICENSE` en este repositorio, o la sección
"Licencia y Avisos de Copyright" al final de este documento.

URTC Tester es (c) 2026 JuanenRac (Electro Hobby 3D). Este aviso debe
incluirse en cualquier distribución de este proyecto o trabajos
derivados.

Este proyecto consiste en código fuente y su propia documentación,
disponibles bajo licencias distintas - cada una adecuada a lo que
realmente cubre:

1. El código fuente (`urtc_tester.py` y cada módulo `tester_*.py`) y
   cualquier binario compilado a partir de él vía
   `build_exe.bat`/`build_exe.sh` están disponibles bajo la
   **GNU General Public License v3.0 or later (GPL-3.0-or-later)**. Texto completo en
   https://www.gnu.org/licenses/gpl-3.0.html.

2. La documentación (este README y sus propias traducciones -
   `README_spa.md`, `README_ita.md`, `README_fra.md`, `README_deu.md`,
   `README_zho.md`, `README_jpn.md`, `README_por.md` y las guías de `docs/`)
   está disponible bajo **Creative Commons Attribution-ShareAlike 4.0
   International (CC BY-SA 4.0)**. Texto completo en
   https://creativecommons.org/licenses/by-sa/4.0/.

Esta herramienta es el compañero de diagnóstico en vivo del bus CAN del
proyecto [URTC (Universal Robot Tool Controller)](https://github.com/JuanenRac/URTC)
- ver el propio repositorio de ese proyecto para el firmware de la
placa, los diseños de hardware, y la documentación completa del
protocolo que esta herramienta ejercita. El propio firmware de URTC es
GPL-3.0-or-later y sus diseños de hardware son CERN-OHL-S v2; la propia licencia
de esta herramienta aquí no se extiende a ese proyecto separado, y
viceversa. También existe una alternativa basada en web que cubre
terreno similar en
[URTC Web Studio](https://github.com/JuanenRac/URTC-WEB-STUDIO).

Si construyes sobre este proyecto, ten en cuenta la separación de
licencias: los cambios de código deberían mantenerse GPL-3.0-or-later, los
derivados de documentación deberían mantenerse CC BY-SA - cada uno con
atribución de vuelta a este proyecto y su autor.
