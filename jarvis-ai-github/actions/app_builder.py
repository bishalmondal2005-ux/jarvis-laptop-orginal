"""
actions/app_builder.py - App & Website Creation (Google AI Studio & VS Code) for JARVIS.

Supports:
1. Google AI Studio Route:
   Automatically opens Google AI Studio (https://aistudio.google.com), generates a rich,
   professional prompt based on user's requirements, pastes it into AI Studio, and begins creation.
2. VS Code Local Coding Route:
   When user asks to write code in VS Code, creates project directories and source files
   (HTML/CSS/JS, Python, React, Flutter, etc.) and opens the project in Visual Studio Code.
"""
from __future__ import annotations

import os
import re
import sys
import time
import shutil
import subprocess
import threading
import webbrowser
from pathlib import Path
from typing import Any, Optional

from core import outcome
from core.lazyimport import LazyModule, installed

_PYAUTOGUI = installed("pyautogui")
_PYPERCLIP = installed("pyperclip")

pyautogui = LazyModule("pyautogui")
pyperclip = LazyModule("pyperclip")

def _get_projects_dir() -> Path:
    candidates = [
        Path.home() / "Downloads" / "JARVIS_Projects",
        Path.home() / "Projects",
        Path(__file__).resolve().parent.parent / "projects",
    ]
    for p in candidates:
        try:
            p.mkdir(parents=True, exist_ok=True)
            return p
        except Exception:
            continue
    p = Path(__file__).resolve().parent.parent / "projects"
    try:
        p.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    return p


def _enhance_app_prompt(description: str, app_type: str = "web_app") -> str:
    """Enhance user's app/website idea into an expert specification prompt for AI Studio."""
    d = description.strip()
    return (
        f"You are a Senior Principal Software Architect. Build a complete, production-ready {app_type}: {d}.\n\n"
        "Requirements:\n"
        "1. Architecture & Design: Modern, visually stunning UI with responsive layout, dark/light theme, clean hierarchy.\n"
        "2. Complete Implementation: Provide all necessary frontend components, state management, and backend/API logic.\n"
        "3. Production Quality: Include robust error handling, responsive animations, clean modular code, and comprehensive comments.\n"
        "Output all complete source files ready for deployment."
    )


def _open_in_ai_studio(description: str, app_type: str) -> str:
    """Opens Google AI Studio, pastes the improved app specification prompt and starts generation."""
    prompt = _enhance_app_prompt(description, app_type)
    url = "https://aistudio.google.com/prompts/new_chat"
    webbrowser.open(url)

    def _automate():
        time.sleep(4.0)  # wait for browser to load AI Studio
        if _PYPERCLIP:
            pyperclip.copy(prompt)
        if _PYAUTOGUI:
            paste_key = "ctrl"
            pyautogui.hotkey(paste_key, "v")
            time.sleep(0.4)
            pyautogui.press("enter")
            print("[AppBuilder] Prompt submitted to Google AI Studio.")

    threading.Thread(target=_automate, daemon=True).start()
    return f"Opened Google AI Studio. Submitted comprehensive architecture prompt for {app_type}."


def _find_vscode() -> Optional[str]:
    """Finds the VS Code executable on Windows."""
    # Check PATH
    code_path = shutil.which("code")
    if code_path:
        return code_path

    # Common Windows locations
    candidates = [
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Microsoft VS Code" / "Code.exe",
        Path(os.environ.get("PROGRAMFILES", "")) / "Microsoft VS Code" / "Code.exe",
        Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Microsoft VS Code" / "Code.exe",
    ]
    for c in candidates:
        if c.exists():
            return str(c)
    return None


def _build_in_vscode(project_name: str, description: str, tech_stack: str = "web") -> tuple[bool, str]:
    """Creates a complete local project and opens it in Visual Studio Code."""
    safe_name = re.sub(r"[^a-zA-Z0-9_\-]", "_", project_name.lower().strip()) or "jarvis_app"
    projects_dir = _get_projects_dir()
    project_dir = projects_dir / safe_name
    project_dir.mkdir(parents=True, exist_ok=True)

    # Generate initial template files based on tech stack
    if "python" in tech_stack.lower():
        (project_dir / "main.py").write_text(
            f'"""\n{project_name}\nDescription: {description}\n"""\n\n'
            'def main():\n'
            f'    print("Starting {project_name}...")\n\n'
            'if __name__ == "__main__":\n'
            '    main()\n',
            encoding="utf-8"
        )
        (project_dir / "requirements.txt").write_text("# Project dependencies\nrequests\n", encoding="utf-8")
    else:
        # Default modern web app
        (project_dir / "index.html").write_text(
            f'<!DOCTYPE html>\n<html lang="en">\n<head>\n'
            f'  <meta charset="UTF-8">\n'
            f'  <meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
            f'  <title>{project_name}</title>\n'
            f'  <link rel="stylesheet" href="style.css">\n'
            f'</head>\n<body>\n'
            f'  <div id="app">\n'
            f'    <h1>{project_name}</h1>\n'
            f'    <p>{description}</p>\n'
            f'  </div>\n'
            f'  <script src="app.js"></script>\n'
            f'</body>\n</html>\n',
            encoding="utf-8"
        )
        (project_dir / "style.css").write_text(
            ':root { --bg: #0f172a; --text: #f8fafc; --accent: #38bdf8; }\n'
            'body { margin: 0; padding: 2rem; background: var(--bg); color: var(--text); font-family: sans-serif; }\n'
            'h1 { color: var(--accent); }\n',
            encoding="utf-8"
        )
        (project_dir / "app.js").write_text(
            f'// {project_name} Application Logic\n'
            'document.addEventListener("DOMContentLoaded", () => {\n'
            '  console.log("App initialized!");\n'
            '});\n',
            encoding="utf-8"
        )

    (project_dir / "README.md").write_text(
        f"# {project_name}\n\n{description}\n\nBuilt with JARVIS.\n",
        encoding="utf-8"
    )

    # Launch VS Code
    vscode_exe = _find_vscode()
    if vscode_exe:
        try:
            subprocess.Popen([vscode_exe, str(project_dir)])
            return True, f"Created project '{project_name}' at {project_dir} and opened in Visual Studio Code."
        except Exception as e:
            return True, f"Created project at {project_dir}, but error opening VS Code: {e}"
    else:
        return True, f"Created project at {project_dir}. (VS Code executable not found on PATH)."


def app_builder(parameters: dict | None = None) -> str:
    params = parameters or {}
    mode = params.get("mode", "auto").lower().strip()
    description = params.get("description", "").strip()
    app_type = params.get("app_type", "web_app").strip()
    project_name = params.get("project_name", "").strip()

    if not description and not project_name:
        return outcome.failed("app_builder", "Please provide a description of the app or website to build.")

    if not project_name:
        words = description.split()[:4]
        project_name = "_".join(words).lower()

    print(f"[AppBuilder] mode={mode}, project={project_name}, type={app_type}")

    # If user explicitly requested VS Code local coding
    if mode in ("vscode", "local", "code"):
        success, msg = _build_in_vscode(project_name, description, app_type)
        return outcome.done("app_builder", mode="vscode", project=project_name, message=msg)

    # If user requested Google AI Studio OR auto
    if mode in ("ai_studio", "auto", "browser"):
        msg = _open_in_ai_studio(description, app_type)
        return outcome.done("app_builder", mode="ai_studio", message=msg)

    # Fallback to local VS Code
    success, msg = _build_in_vscode(project_name, description, app_type)
    return outcome.done("app_builder", mode="vscode", project=project_name, message=msg)


TOOL = {
    "name": "app_builder",
    "description": (
        "Creates mobile apps, websites, and software projects. "
        "Two modes: "
        "1. mode='ai_studio': Opens Google AI Studio (https://aistudio.google.com), generates a rich "
        "professional architecture prompt from user's idea, pastes it, and starts generation. "
        "2. mode='vscode': Creates project files/folders locally and opens the project in Visual Studio Code. "
        "Use this whenever the user asks to build an app, website, or write code in VS Code."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "description": {
                "type": "STRING",
                "description": "What the mobile app, website, or project should do (features, UI, logic).",
            },
            "mode": {
                "type": "STRING",
                "description": "'ai_studio' (Google AI Studio in Chrome), 'vscode' (local project opened in VS Code), or 'auto'. Default: 'auto'.",
            },
            "app_type": {
                "type": "STRING",
                "description": "'web_app' (website/web application), 'mobile_app' (Android/iOS app), or 'python_app'. Default: 'web_app'.",
            },
            "project_name": {
                "type": "STRING",
                "description": "Short name for the project folder (e.g. 'ecommerce_shop', 'fitness_tracker').",
            },
        },
        "required": ["description"],
    },
    "handler": app_builder,
}
