# The window of the tester, step by step

These pictures are the real window, loaded without a screen and drawn to a file by `tools/capture_screens.py` (`python tools/capture_screens.py` writes them again). They show the program as it opens: nothing is connected, nothing is sent, and the language is English (the picture of the tool heads is the exception: it shows the window over a modelled bus). The same texts exist in the eight languages of the program, and the **Help** button of the deck shows the quick guide in the language you chose.

## 1. The deck as it opens

![The deck of the tester as it opens](screenshots/tester-deck.png)

* **Transport gate** (left): choose the serial port of the SLCAN adapter (or a SocketCAN interface on Linux) and the bit rate, then press **Connect**. **Auto-detect** only listens to the bus, sends nothing and finds the bit rate. With no hardware, run `python -m urtc_can.virtual_board`, set `URTC_VIRTUAL_PORT=socket://127.0.0.1:7777` and the virtual board appears in the list of ports.
* **Safety mode**: the program starts listen-only. Everything that sends something needs the active mode, the profile of the tool and a second confirmation; heaters and motors switch off when the program stops talking to them.
* **Tool profile**: the commands of a tool unlock only when the tool that answers is the one selected.
* **Identity and health checkpoints** (right): the four steps of a first connection, the passive bus window, the advanced profile control and the active tool read-out.

## 2. Help

![The Help window of the tester](screenshots/tester-help.png)

The **Help** button opens seven short steps in the language of the window (the last ones are the history, several heads and updates): connect, read and query, move or heat with care, the black box and the replay of a saved trace, several heads and working without a board.

## 3. Check for updates

![The update window of the tester](screenshots/tester-updates.png)

**Check for updates** asks GitHub once, only when you press it. Both options are conservative: the check at start is off, and an update is installed only after you confirm it and only if the signature of the package matches the key of the releases pinned in the program; the previous version is kept so you can go back.

## 4. Several tool heads

![The window of the tool heads of the tester](screenshots/tester-heads.png)

The **Tool heads** button opens the window that finds the heads when more than one shares the bus (the multinode extension of the firmware, which is **off by default**: with it off, **Find heads** finds nobody, the bus counts as one head and everything is sent as it always was). The picture is taken over a modelled bus of seven heads, one in each state a head can be in, so it shows the window and not a real bus:

* Each head has its **address**, its **tool**, its **serial number** and a **state** written in words: *Ready*, *Selected*, *Address conflict* (two boards on one address; neither can be selected), *Fault latched*, *In its bootloader* or *Lost* (no status for too long). Only a ready head has a **Select** button.
* **Select** asks you to confirm. Nothing is sent to a head until it has confirmed that it is selected; while several heads are on the bus, any command to the board is refused until one is selected (the frames of the extension itself are not).
* If the selected head is lost, faults, enters its bootloader or no longer reports itself selected, the window shows why in a banner. By default every head is also put in its safe state, so no output stays on without a host watching it; the checkbox at the bottom switches that off (it asks first, and the banner then says that the outputs were left as they are).
* The line under the title says whether the head reports the extension as on, off, or saved but waiting for the next power-up. This has been tried against a model of the bus only, never against boards.

## 5. History

The **History** button next to **Help** opens the history of operations: the evidence records (`urtc-evidence/1`) that the tester wrote, newest first, with the kind, the result, the tool, the board and the versions. Each record is checked when the window opens; one that was edited after it was written, a file that is not JSON or a record of another format is shown as **NOT VALID** with what is wrong. You can filter by result and by text, or reduce the list to the records that fail. The window reads the folder again each time it opens (or when you press **Read again**), shows at most 500 rows and says how many there are, and never changes anything on disk. It is the same window, in the eight languages, in the flasher, the tester and the updater.
From the command line, `python urtc_tester.py --headless history [FOLDER] [--json]` gives the same list for a folder (see [HEADLESS.md](HEADLESS.md)).
The **Report** button writes `evidence_report.html` and `evidence_report.pdf` in the same folder: every record, the result of checking it and a mark that says whether it came from a simulation; it changes no record. `python urtc_tester.py --headless report --evidence-dir DIR --out FILE` does the same without a window.

## The same pictures in the other languages

The program has eight interface languages. These are the same four pictures of the tester taken with each of them (`python tools/capture_screens.py --all-languages` writes them again; `--language german` writes one language). The texts are those of the program, not of this page, so a picture shows exactly what a person who chose that language sees.

| Language | Window | Help | Updates | Tool heads |
|---|---|---|---|---|
| English | [window](screenshots/tester-deck.png) | [help](screenshots/tester-help.png) | [updates](screenshots/tester-updates.png) | [heads](screenshots/tester-heads.png) |
| Español | [window](screenshots/tester-deck-es.png) | [help](screenshots/tester-help-es.png) | [updates](screenshots/tester-updates-es.png) | [heads](screenshots/tester-heads-es.png) |
| Deutsch | [window](screenshots/tester-deck-de.png) | [help](screenshots/tester-help-de.png) | [updates](screenshots/tester-updates-de.png) | [heads](screenshots/tester-heads-de.png) |
| Français | [window](screenshots/tester-deck-fr.png) | [help](screenshots/tester-help-fr.png) | [updates](screenshots/tester-updates-fr.png) | [heads](screenshots/tester-heads-fr.png) |
| Italiano | [window](screenshots/tester-deck-it.png) | [help](screenshots/tester-help-it.png) | [updates](screenshots/tester-updates-it.png) | [heads](screenshots/tester-heads-it.png) |
| 日本語 | [window](screenshots/tester-deck-ja.png) | [help](screenshots/tester-help-ja.png) | [updates](screenshots/tester-updates-ja.png) | [heads](screenshots/tester-heads-ja.png) |
| 简体中文 | [window](screenshots/tester-deck-zh.png) | [help](screenshots/tester-help-zh.png) | [updates](screenshots/tester-updates-zh.png) | [heads](screenshots/tester-heads-zh.png) |
| Português | [window](screenshots/tester-deck-pt.png) | [help](screenshots/tester-help-pt.png) | [updates](screenshots/tester-updates-pt.png) | [heads](screenshots/tester-heads-pt.png) |

## What the pictures do not show

They do not show a board answering. Nothing in this guide has been run against a real board; the README lists what has and has not been checked.
