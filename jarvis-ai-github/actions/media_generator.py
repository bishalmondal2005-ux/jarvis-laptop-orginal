"""
actions/media_generator.py - Media Generation & Chrome Gemini Automation for JARVIS.

Handles generation of:
- Images (direct generation via free Pollinations AI / Imagen + saving to disk/viewing)
- Videos & Music/Songs
- Full fallback to Google Chrome Gemini:
  Opens https://gemini.google.com, enriches user's idea into an expert creative prompt,
  pastes into Gemini prompt box, presses Enter, and handles download requests.
"""
from __future__ import annotations

import os
import sys
import time
import urllib.parse
import webbrowser
import threading
from pathlib import Path
from typing import Any, Optional

import requests
from core import outcome
from core.lazyimport import LazyModule, installed

_PYAUTOGUI = installed("pyautogui")
_PYPERCLIP = installed("pyperclip")

pyautogui = LazyModule("pyautogui")
pyperclip = LazyModule("pyperclip")

def _get_output_dir() -> Path:
    candidates = [
        Path.home() / "Downloads" / "JARVIS_Media",
        Path.home() / "Pictures" / "JARVIS_Media",
        Path(__file__).resolve().parent.parent / "output" / "media",
    ]
    for p in candidates:
        try:
            p.mkdir(parents=True, exist_ok=True)
            return p
        except Exception:
            continue
    p = Path(__file__).resolve().parent.parent / "media_out"
    try:
        p.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    return p


def _enhance_prompt(prompt: str, media_type: str = "image") -> str:
    """Enhance user's prompt into a professional, highly detailed generator prompt."""
    p = prompt.strip()
    if media_type == "image":
        return (
            f"Generate an ultra-detailed, cinematic high-resolution masterpiece: {p}. "
            "Photorealistic lighting, 8k resolution, Unreal Engine 5 render style, "
            "volumetric atmosphere, sharp focus, 85mm lens, f/1.8, award-winning photography."
        )
    elif media_type == "video":
        return (
            f"Generate a cinematic 4K video clip: {p}. "
            "Smooth cinematic camera panning, dynamic motion, 60fps, photorealistic lighting, "
            "atmospheric depth of field, professional color grading, film aesthetic."
        )
    elif media_type in ("music", "song", "audio"):
        return (
            f"Create a high-quality music track: {p}. "
            "Genre: Modern studio production, immersive audio mixing, rich harmonies, "
            "crisp percussion, melodic hooks, emotional resonance, studio mastered audio."
        )
    return p


def _generate_direct_image(prompt: str) -> tuple[bool, str, str]:
    """Generates an image directly via Pollinations AI API and saves locally."""
    try:
        enhanced = _enhance_prompt(prompt, "image")
        encoded = urllib.parse.quote(enhanced)
        url = f"https://image.pollinations.ai/prompt/{encoded}?width=1024&height=1024&model=flux&nologo=true"

        resp = requests.get(url, timeout=35)
        if resp.status_code == 200:
            timestamp = int(time.time())
            filename = f"jarvis_gen_{timestamp}.jpg"
            out_dir = _get_output_dir()
            file_path = out_dir / filename
            file_path.write_bytes(resp.content)

            # Open image in default Windows viewer
            try:
                os.startfile(str(file_path))
            except Exception:
                pass

            return True, str(file_path), enhanced
        return False, f"HTTP {resp.status_code}", enhanced
    except Exception as e:
        return False, str(e), prompt


def _open_in_gemini(prompt: str, media_type: str = "image") -> str:
    """Opens Chrome with Gemini, types the improved prompt, and submits."""
    enhanced = _enhance_prompt(prompt, media_type)

    # 1. Open Gemini in browser
    gemini_url = "https://gemini.google.com/app"
    webbrowser.open(gemini_url)

    # 2. In a background thread, wait for Gemini to load, copy prompt to clipboard, paste and press enter
    def _automate():
        time.sleep(3.5)  # wait for Chrome to focus and page to load
        if _PYPERCLIP:
            pyperclip.copy(enhanced)
        if _PYAUTOGUI:
            # Focus typing area and paste
            paste_key = "ctrl"
            pyautogui.hotkey(paste_key, "v")
            time.sleep(0.3)
            pyautogui.press("enter")
            print(f"[MediaGenerator] Prompt sent to Gemini: {enhanced[:60]}...")

    threading.Thread(target=_automate, daemon=True).start()
    return f"Opened Google Chrome with Gemini. Submitted enhanced prompt for {media_type}: '{enhanced[:100]}...'"


def media_generator(parameters: dict | None = None) -> str:
    params = parameters or {}
    media_type = params.get("media_type", "image").lower().strip()
    prompt = params.get("prompt", "").strip()
    action = params.get("action", "auto").lower().strip()

    if not prompt:
        return outcome.failed("media_generator", "No prompt provided for generation.")

    print(f"[MediaGenerator] Request: type={media_type}, action={action}, prompt={prompt[:80]}")

    # If user explicitly asked for direct image generation or auto for images
    if media_type == "image" and action in ("direct", "auto"):
        success, path_or_err, enhanced = _generate_direct_image(prompt)
        if success:
            return outcome.done(
                "media_generator",
                media_type="image",
                file=path_or_err,
                message=f"Image successfully generated and saved to {path_or_err}. Displaying now."
            )
        else:
            print(f"[MediaGenerator] Direct generation failed ({path_or_err}). Falling back to Chrome Gemini...")

    # Chrome Gemini route (for videos, songs, or image fallback/request)
    msg = _open_in_gemini(prompt, media_type)
    return outcome.done(
        "media_generator",
        media_type=media_type,
        route="gemini_chrome",
        message=msg
    )


TOOL = {
    "name": "media_generator",
    "description": (
        "Generates images, videos, or songs/music. "
        "Can generate images directly and display them, OR automatically open Google Chrome "
        "to Gemini (https://gemini.google.com), enrich the user's idea into an enhanced creative prompt, "
        "paste it, and hit Enter. "
        "Use this whenever the user asks to generate, create, or draw an image, video, song or music."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "media_type": {
                "type": "STRING",
                "description": "'image' (chobi/picture), 'video' (video clip), or 'music' (gaan/song/audio). Default: 'image'",
            },
            "prompt": {
                "type": "STRING",
                "description": "What to generate (e.g. 'a futuristic city at dusk', 'sad acoustic guitar song', 'drone flying over mountains')",
            },
            "action": {
                "type": "STRING",
                "description": "'auto' (try direct first, fallback to Gemini), 'direct' (generate and save directly), or 'gemini' (open in Chrome Gemini)",
            },
        },
        "required": ["prompt"],
    },
    "handler": media_generator,
}
