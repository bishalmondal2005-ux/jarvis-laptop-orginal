# ⚡ JARVIS Mark-LVI — Next-Gen Multimodal Voice AI Assistant
### *With Dynamic Origin Island, Real-Time Live Dictation & Proactive Reminder Engine*

[![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![PyQt6](https://img.shields.io/badge/GUI-PyQt6-41CD52?style=for-the-badge&logo=qt&logoColor=white)](https://riverbankcomputing.com/software/pyqt/)
[![Gemini Live API](https://img.shields.io/badge/AI-Google%20Gemini%20Live-4285F4?style=for-the-badge&logo=google&logoColor=white)](https://ai.google.dev/)
[![OS](https://img.shields.io/badge/OS-Windows%20%7C%20macOS%20%7C%20Linux-0078D4?style=for-the-badge&logo=windows&logoColor=white)](#prerequisites)
[![License: CC BY-NC 4.0](https://img.shields.io/badge/License-CC%20BY--NC%204.0-lightgrey?style=for-the-badge)](https://creativecommons.org/licenses/by-nc/4.0/)

---

## 🌌 Overview

**JARVIS Mark-LVI** is a cutting-edge, real-time multimodal personal AI assistant designed to live natively on your desktop. Built atop Google's high-speed **Gemini Live API** and an asynchronous Python/PyQt6 architecture, JARVIS seamlessly hears, speaks, sees, thinks, and controls your operating system with zero subscription lock-in.

This updated edition features a floating **Dynamic Origin Island**, an **Ultra-Low Latency Real-Time Live Streaming Voice Typing Engine**, and a **Proactive Staggered To-Do & Reminder System** operating in the `Asia/Kolkata` (IST) timezone.

---

## ✨ Key Highlights & What's New

### 1. 🎙️ Ultra-Fast Real-Time Live Streaming Voice Typing
* **Instant On-The-Fly Typing:** Types words onto any active window in real-time as you speak—eliminating traditional multi-second round-trip latency.
* **Win32 Native C-Level API (2.9 ms):** Employs direct Windows native user32 clipboard injection (`ctypes.windll.user32`), executing keystrokes and Unicode text 150× faster than standard libraries.
* **3-Second Silence Watchdog:** Automatically finalizes and locks the dictation buffer within 3 seconds of user silence.
* **Multi-Language & Phonetic Support:**
  * **Bengali (বাংলা হরফ):** *"আমি ভালো আছি"*
  * **Banglish (Latin Phonetic):** *"Ami bhalo achi"*
  * **English:** *"Hello, I am testing voice dictation"*
  * **Hindi (हिंदी):** *"नमस्ते, आप कैसे हैं"*
* **Instant Stop Recognition:** Say *"stop typing"*, *"typing stop"*, *"stop"*, or *"thamo"* to instantly disengage typing mode and return to conversational mode.
* **Origin Island Indicator:** Displays a dynamic purple `⌨️ TYPING...` badge during active typing and switches to `✓ TEXT TYPED` upon completion.

---

### 2. 📝 Proactive To-Do List & Smart Reminders
* **Staggered Proactive Reminders (Time-Specific):**
  * **10 minutes before due:** 1st audio chime, voice alert, and Origin Island banner.
  * **5 minutes before due:** 2nd follow-up reminder.
  * **Exact due time:** Final alert.
* **Date-Specific Tasks (e.g., Birthdays, Due Dates):**
  * Automatically reminds you **1 day in advance** upon system startup or when JARVIS boots up.
* **Interactive GUI Management:**
  * **Top Header Button (`📝`):** Dedicated quick-access button right beside the settings icon.
  * **Settings Drawer Menu:** Instant launch pad under `📝 TO-DO LIST & REMINDERS`.
  * **Origin Island Menu:** Context menu entry to open the To-Do panel directly.
  * **In-Place Editor (`✎ Edit Mode`):** Modify task descriptions, dates, or times with a single `[ 💾 Save Changes ]` click.
* **IST Timezone Precision:** Native `Asia/Kolkata` (UTC+05:30) timezone parsing via Python `zoneinfo` and `tzdata`.

---

### 3. 🏝️ Dynamic Origin Island (Floating HUD)
* **Docked Floating Pill:** A sleek, non-intrusive floating island at the top of your screen displaying live state.
* **Audio Waveform Animation:** Real-time pulse visualization synchronized with your microphone input and JARVIS's voice output.
* **Thread-Safe Architecture:** Powered by PyQt6 Queued Signals (`task_started_sig`, `task_result_sig`, `reminder_alert_sig`, `typing_sig`), eliminating UI blocking and thread crashes.
* **Background Audio Alerts:** Non-blocking Windows sound chimes executed on detached daemon threads.
* **Custom Styling:** Full control over width, height, position, background opacity, accent colors, and custom animated GIFs.

---

### 4. 💤 Intelligent Sleep Mode & Single-Tab Web Browsing
* **Dedicated Sleep State (`"jarvis sleep"` / `"sleep"`):** Suspends listening, disengages command execution, and displays `💤 SLEEPING` on the island until woken up via `"wake up"` or `"hey jarvis"`.
* **Single-Tab Smart Browsing:** Prevents opening duplicate Chrome tabs when requesting links or charts already active in your browser.

---

### 5. 🧑‍🎤 Holographic Software Avatar & Multimodal Vision
* **Software 3D Face:** Fully animated head rendered with Qt `QPainter` and `numpy`—no heavy 3D engine or dedicated GPU required.
* **Formant-Driven Lip-Sync:** 50 mouth shapes per second derived directly from speech audio formants and phonetic Unicode transcripts.
* **Screen & Camera Vision:** Captures real-time desktop screenshots or webcam video to analyze code, charts, UI errors, and documents.

---

## 🏗️ System Architecture

```
JARVIS-Mark-LVI/
├── main.py                  # Core runtime engine, audio pipeline, Gemini Live socket & live dictation
├── ui.py                    # Primary HUD desktop interface (PyQt6) & holographic avatar renderer
├── setup.py                 # Automated dependency installer & system checker
├── requirements.txt         # Production-ready Python dependencies
├── .env.example             # Environment variable template
├── .gitignore               # Multi-layer git exclusion list for secrets and memories
│
├── core/
│   ├── origin_island.py     # Floating Dynamic Origin Island widget & signal handlers
│   ├── origin_island_settings.py # Island appearance, geometry & animation configurator
│   ├── todo_manager.py      # IST-based To-Do database engine with staggered reminder scheduler
│   ├── todo_ui.py           # Interactive PyQt6 To-Do cards, progress bar & edit modal
│   ├── action_loader.py     # Dynamic auto-discovery engine for modular tool actions
│   ├── hotkey.py            # Global push-to-talk & keyboard shortcut hooks
│   └── prompt.txt           # JARVIS persona & behavioral system instruction prompt
│
├── actions/
│   ├── todo_action.py       # Voice tool for To-Do operations (Add, List, Complete, Delete)
│   ├── speak_to_type.py     # Fast-path dictation action
│   ├── current_time.py      # Real-time clock & IST calendar tool
│   ├── computer_settings.py # Windows control (Volume, Display, Apps, Chrome single-tab)
│   ├── media_controller.py  # Media playback & YouTube controller
│   └── ...
│
├── config/
│   ├── api_keys.json.example# Template for user settings and API configuration
│   └── origin_island.json   # Dynamic Origin Island coordinates and appearance preferences
│
└── memory/
    ├── todo_list.json.example# Persistent To-Do storage template
    └── long_term.json.example# Personal assistant memory template
```

---

## ⚡ Quick Start & Installation

### 1. Prerequisites
* **Operating System:** Windows 10/11 (Full support), macOS, or Linux
* **Python:** Version `3.10`, `3.11`, or `3.12`
* **Google Gemini API Key:** Get a free API key from [Google AI Studio](https://aistudio.google.com/app/apikey)

### 2. Clone the Repository
```bash
git clone https://github.com/YOUR_USERNAME/JARVIS-Mark-LVI.git
cd JARVIS-Mark-LVI
```

### 3. Create a Virtual Environment
```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

### 5. Setup Configuration
Copy the configuration templates:
```bash
# Windows (PowerShell)
Copy-Item config\api_keys.json.example config\api_keys.json
Copy-Item .env.example .env

# Linux / macOS
cp config/api_keys.json.example config/api_keys.json
cp .env.example .env
```
Open `config/api_keys.json` and paste your Gemini API key:
```json
{
  "gemini_api_key": "YOUR_GEMINI_API_KEY_HERE",
  "assistant_name": "Jarvis",
  "user_name": "Sir"
}
```

### 6. Launch JARVIS
```bash
python main.py
```
*(Or double-click `run-mark-lvi.bat` on Windows).*

---

## 🗣️ Voice Commands Cheat-Sheet

| Category | Voice Command Examples | Description |
|---|---|---|
| **Live Dictation** | `"Jarvis type"`, `"Start typing"`, `"Type koro"`, `"Lekho"` | Enters real-time typing mode on the active text field. |
| **Stop Dictation** | `"Stop typing"`, `"Typing stop"`, `"Stop"`, `"Thamo"`, `"Done"` | Immediately finalizes text and returns to conversational mode. |
| **Time Reminders** | `"9 tai medicine khabo reminder diyo"` | Sets a reminder with 10-min, 5-min, and due-time alerts. |
| **Date Reminders** | `"20 January amar bday reminder set koro"` | Reminds 1 day prior (19th Jan) upon startup. |
| **View To-Dos** | `"Amar ki ki to do ache?"`, `"Show reminders"` | Lists upcoming tasks on screen and reads aloud. |
| **Complete Task** | `"Medicine khawa complete hoye geche"` | Marks the task as completed in the database. |
| **Sleep Mode** | `"Jarvis sleep"`, `"Go to sleep"` | Mutes microphone and pauses all command execution. |
| **Wake Up** | `"Wake up"`, `"Hey Jarvis"` | Re-activates voice listener and greets the user. |
| **Single-Tab Web** | `"Open YouTube"`, `"Open trading chart"` | Opens requested site in a single existing browser tab. |
| **System Control**| `"Volume 50% koro"`, `"Mute sound"`, `"Take a screenshot"` | Adjusts OS settings without touching keyboard/mouse. |

---

## ⚙️ Configuration & Customization

### Origin Island Customization
You can customize the Origin Island by right-clicking on it or through `config/origin_island.json`:
* `preset`: Choose between `custom`, `minimal`, `notch`, or `wide`.
* `x`, `y`: Screen position (default `y: 0` for top docking).
* `bg_color`, `accent_color`: Hex values for custom color grading.
* `custom_speaking_gif` / `custom_listening_gif`: Embed custom animation loops.

---

## 🔒 Security & Privacy

* **Zero Cloud Secret Leakage:** All API keys and local memories (`memory/long_term.json`, `memory/todo_list.json`, `config/api_keys.json`) are strictly excluded via `.gitignore`.
* **Local Processing:** Keystroke injection and audio monitoring run strictly in-memory on your local machine.

---

## 🤝 Contributing

Contributions, bug reports, and feature suggestions are welcome!
1. Fork the Project.
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`).
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`).
4. Push to the Branch (`git push origin feature/AmazingFeature`).
5. Open a Pull Request.

---

## 📜 License

This project is licensed under the **Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0)**.
* You are free to share and adapt the material for personal, non-commercial use with appropriate credit.
* Commercial distribution or monetization is prohibited without prior written consent.

---

## 🙏 Acknowledgements

* Original core foundation based on **Mark-LVI** by [FatihMakes](https://www.youtube.com/@FatihMakes).
* Google DeepMind & Google Cloud for the **Gemini Live API**.
* The open-source community for **PyQt6**, **sounddevice**, and **playwright**.
