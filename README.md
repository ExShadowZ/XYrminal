# XYrminal

**A multi-protocol terminal for COM, TCP and UDP — a Swiss Army knife for embedded engineers.**

XYrminal brings together a serial terminal, a network client and server, a live chart builder, a scenario engine for automation, and file transfer to microcontrollers — all in one window. What usually takes five separate programs happens here in a single window, with the same controls, shared macros and triggers on every tab.

---

## Table of Contents

- [XYrminal](#xyrminal)
  - [Table of Contents](#table-of-contents)
  - [1. What the program can do](#1-what-the-program-can-do)
  - [2. Interface: five tabs](#2-interface-five-tabs)
  - [3. Working with a COM port](#3-working-with-a-com-port)
    - [Connecting](#connecting)
    - [Port parameters](#port-parameters)
    - [Terminal settings](#terminal-settings)
    - [Transmitting](#transmitting)
  - [4. Working over TCP and UDP](#4-working-over-tcp-and-udp)
    - [Client](#client)
    - [Server](#server)
  - [5. Live plot](#5-live-plot)
  - [6. File transfer](#6-file-transfer)
  - [7. Macros](#7-macros)
  - [8. Scenarios](#8-scenarios)
  - [9. Highlight triggers](#9-highlight-triggers)
  - [10. Logs](#10-logs)
  - [11. Appearance and language](#11-appearance-and-language)
  - [12. What is remembered between runs](#12-what-is-remembered-between-runs)
  - [Feedback](#feedback)

---

## 1. What the program can do

- **Five connection modes in one window**: serial port (RS-232, RS-485, USB-CDC), TCP client, TCP server, UDP client, UDP server.
- **Receive and transmit data** as text or as raw bytes — HEX, DEC, OCT, BIN and more than ten text encodings, including Cyrillic, Japanese and Chinese.
- **Live plot**: parses numbers from the incoming stream by marker and draws several curves at once. Export to CSV for Excel.
- **File transfer** to devices: raw stream, XMODEM, YMODEM — with a progress bar and the ability to cancel.
- **Macros**: ten buttons on every tab for instant sending of pre-prepared commands.
- **Scenarios**: text files in which you can describe a sequence of actions, branches, loops, waiting for replies — and automate routine checks.
- **Triggers**: highlighting of the fragments you care about in the stream — for example, the word `ERROR` in red and `OK` in green.
- **Logs**: saving a session as plain text or as a colored HTML file that can be opened in any browser and replayed with the original delays.
- **Appearance**: ten built-in themes, a custom palette editor, interface scale from 75% to 150%.
- **Eight interface languages**: English, Russian, Belarusian, German, French, Chinese, Japanese, Korean.

---

## 2. Interface: five tabs

All work is done on five top-level tabs:

- **COM** — serial port.
- **TCP Client** — connect to a remote TCP server.
- **TCP Server** — listen on a local port, accept several clients at once.
- **UDP Client** — exchange with a fixed address and port.
- **UDP Server** — receive datagrams from any sender, with the option to reply and to broadcast.

Every tab has the same set of elements: connection settings at the top, terminal settings below them, the output area in the middle, and the transmit panel at the bottom. Once you have learned to work on one tab, you will have no trouble with the others.

The status bar at the bottom of the window shows the counters of received and sent bytes for the current tab and a button to reset them.

---

## 3. Working with a COM port

### Connecting

Choose a port from the drop-down list. If the device was connected after the program started, press **Scan** to refresh the list. The **Connect** button opens the port, **Disconnect** closes it.

While the port is open, the following become available:

- **DTR and RTS toggles** — control the two output lines. DTR is usually wired to the reset pin of a microcontroller, RTS to BOOT0 or a bootloader-enable pin. Clicking them flips the line without reopening the port, which is convenient when flashing.
- **Four indicators CD, RI, DSR, CTS** — show the state of the modem input lines. A bright color means the line is active, a dim one means it is not.

### Port parameters

Baud rate, data bits, parity, stop bits, flow control. Every drop-down list has a **Custom…** entry at the bottom — it opens a field for entering a non-standard value.

### Terminal settings

- **Auto-scroll** — the window scrolls to the bottom automatically when new data arrives.
- **Timestamps** — every line gets a prefix with the current time.
- **Auto-save log** — the current session is written to a file as it happens, without waiting for a manual save.
- **Encoding** — how to interpret incoming bytes: as raw numbers (HEX, DEC, OCT, BIN) or as text in one of many encodings.
- **Plot** — open the live plot panel.
- **Clear** — wipe the contents of the output window.
- **Save log** — write the current buffer to the logs folder.

### Transmitting

Type text into the input field and press Enter or **Send**. The up and down arrows cycle through the history of entered commands.

- **HEX** — treat the input as a sequence of hexadecimal bytes.
- **+CR** — append a line ending. If **CR=CR+LF** is also enabled, a CR+LF pair will be sent, otherwise only CR.

---

## 4. Working over TCP and UDP

### Client

On the **TCP Client** and **UDP Client** tabs you specify the address and port of the remote side, and optionally a local bind address and a connection timeout.

For the TCP client there is a **Keep connection** checkbox: if the link drops, the program will try to reconnect every two seconds until the connection is restored or until you press Disconnect.

The **Ping** block lets you check the reachability of a remote address over TCP and view statistics, similar to the PowerShell command-line utility. The **Check** button runs a fixed series of probes, **Start** begins periodic pinging, **Stop** ends it.

### Server

On the **TCP Server** tab you specify the local address and port to listen on, along with two checkboxes:

- **Echo** — return to each client everything that came from it.
- **Broadcast to all** — send the entered data to all connected clients at once.

The client list shows everyone currently connected. You can disconnect the selected client or all of them at once.

On the **UDP Server** tab you specify the local port and bind address. The program remembers the last sender and lets you reply to them, send data to an explicitly specified address, or send it out as a broadcast.

Incoming data is prefixed with the sender's address. Server events — connection, disconnection, starting and stopping listening — are printed in a dedicated color so that they are easy to tell apart from useful data.

---

## 5. Live plot

Press the **Plot** button in the terminal settings — the output area will split into two parts: text on the left, plot on the right.

Each row in the plot settings describes one variable and consists of two fields:

- **Name** — required; it will be displayed in the legend.
- **Parse marker** — optional. If set, the program searches for this marker in the incoming text and takes the first number after it. If the marker is empty, the first number in the received data block is taken.

You can define several rows — then several curves will appear on the same plot, each in its own color.

Controls:

- **Start** — begin collecting data.
- **Pause / Resume** — freeze the capture without losing data and resume it.
- **Stop** — end the session and close the panel.

The **T-Mode** toggle switches the horizontal axis from the sample index to "seconds ago". In this mode the plot scrolls continuously even when no new data arrives.

The **View** parameter determines how many points (in normal mode) or seconds (in T-Mode) fit into the window.

The **Export CSV** button saves all channels to a file that is convenient to open in Excel. Missing values remain as empty cells. The file is written in UTF-8 so that Russian channel names are displayed correctly.

Hovering the mouse over the plot brings up a tooltip with the exact value.

---

## 6. File transfer

File transfer is available on the **COM**, **TCP Client** and **UDP Client** tabs.

Select a file with the **Browse…** button, choose a protocol and press **Send file**. During the transfer a progress bar is shown; next to it there is a cancel button.

Supported protocols:

- **Raw** — send the file contents in chunks of bytes with a configurable delay between chunks. Suitable for bootloaders, images and configurations.
- **XMODEM** — the classic protocol with 128-byte blocks and integrity checking.
- **YMODEM** — an extension of XMODEM with the file name and size in the first block; the standard for STM32, ESP and AVR microcontrollers.
- **ZMODEM** — not implemented yet.

Chunk size, delay and the maximum allowed file size are configured in **Settings → Transfer settings**. There you can also enable remembering the last sent file so that the path and protocol are restored on the next launch.

The XMODEM, YMODEM and ZMODEM protocols do not work over UDP — this is a limitation of the protocol itself, not of the program.

---

## 7. Macros

Every tab has ten slots labeled M1…M10. Each slot is a pre-prepared command that is sent with a single click.

Each macro has its own **+CR**, **CR=CR+LF** and **HEX** flags — independent of the flags above the input field. This is convenient when you need to mix text and binary commands.

Hover over a macro button — a tooltip with its contents appears. Empty slots are disabled and cannot be pressed.

The macro editor opens through the **Settings → Configure macros** menu and lets you fill all ten slots for the selected tab. You can reset the macros of one tab or all of them at once through **Settings → Reset all macros**.

---

## 8. Scenarios

A scenario is a text file with the `.xyscen` extension in which commands are written one per line. Such a file can be assigned to any of the slots M1…M10 — then the slot button becomes `S#` and pressing it starts the scenario.

Scenarios let you automate routine checks: send a command, wait for a reply, check the contents, make a decision, repeat in a loop, log the result.

Two styles of writing are supported and can be freely mixed in the same file:

- **Simple style** — one command per line: send, wait, expect a reply, write to the log.
- **Block style** — a mini-language with variables, expressions, `if/else` conditions, `while` and `for` loops, comparison and arithmetic operators.

While the scenario is running, all macros and the input field are blocked. Progress is printed to the terminal as `[SCENARIO] …` lines in their own color. Next to the macros a **Stop** button appears in case the scenario needs to be interrupted.

A full description of commands, operators and built-in functions is available in the **Help** inside the program (menu **Help → Info**).

---

## 9. Highlight triggers

Triggers let you highlight the fragments you care about in the output stream — for example, the word `ERROR` with a red background and `OK` with green text.

The setup is done in **Settings → Configure triggers** separately for each tab. Each row specifies a text to search for and two colors — for the text and for the background. The search is case-insensitive. When two triggers overlap, the one higher in the list wins.

Up to fifty triggers can be defined per tab. They are also saved in colored HTML logs, so when such a log is opened in a browser the highlighting appears exactly as it did in the program.

You can reset the triggers of one tab or all of them at once through **Settings → Reset triggers**.

---

## 10. Logs

Everything that is printed to the terminal can be saved to disk.

- **Save log** — write the current buffer to the `logs` folder next to the program. The file name is generated automatically.
- **Save log as…** — choose the location and the save format:
  - plain text — for further processing;
  - colored HTML — for viewing in a browser with all the highlighting preserved.

Colored logs can be opened directly in the program through **Logs → Open log…**. A separate window opens with a **Play / Pause / Stop** toolbar that replays the log with the original delays between lines — as if you were watching a recording of the session in real time.

Plain text logs are loaded directly into the terminal of the current tab.

The **Open logs folder** button opens the `logs` folder in your file manager.

---

## 11. Appearance and language

The **Settings** menu lets you change the appearance of the program:

- **Theme** — ten built-in palettes, the "System" mode (follows the operating system's theme) and "Custom", where you can set your own colors for all interface elements. A separate "Random" item instantly generates a new palette.
- **Terminal text color** — recoloring each output category (timestamps, transmitted data, received data, server events, scenario output) independently of the others.
- **Language** — switch the interface language without restarting the program.
- **UI scale** — scale the interface from 75% to 150%. Useful on high-resolution monitors.

Appearance and language are remembered between runs.

---

## 12. What is remembered between runs

On exit the program saves, and on the next launch restores:

- the size and position of the window, the active tab;
- COM port, TCP and UDP settings, ping parameters;
- all toggles in the terminal and transmit blocks;
- group visibility on each tab;
- the selected theme, including the custom palette;
- the interface scale and language;
- the terminal colors;
- the log save format;
- all macros and all triggers;
- the last sent file, if the corresponding remembering option is enabled.

All of this is restored automatically — after a restart the program looks exactly as you left it.

---

## Feedback

- Telegram: https://t.me/oiiaiioiiia
- GitHub: https://github.com/ExShadowZ
- Email: ex.shadow.dev.c@gmail.com