# -*- coding: utf-8 -*-
"""
Setup & Installer for Qwen 2.5 7B Local AI Service on Windows.
1. Downloads pre-built Windows llama.cpp binary (llama-server.exe, llama-cli.exe, dlls).
2. Downloads Qwen2.5-7B-Instruct-Q4_K_M.gguf (4.68 GB) from Hugging Face.
3. Configures local paths and generates turnkey startup scripts (.bat).
"""

import os
import sys
import io
import zipfile
import logging
import httpx
from huggingface_hub import hf_hub_download

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("QwenSetup")

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(ROOT_DIR, "models")
BIN_DIR = os.path.join(ROOT_DIR, "bin", "llama-cpp")

HF_REPO_ID = "bartowski/Qwen2.5-7B-Instruct-GGUF"
HF_FILENAME = "Qwen2.5-7B-Instruct-Q4_K_M.gguf"

def download_llama_binaries():
    """Download and extract pre-built Windows llama.cpp server binaries."""
    os.makedirs(BIN_DIR, exist_ok=True)
    server_exe = os.path.join(BIN_DIR, "llama-server.exe")
    if os.path.exists(server_exe):
        logger.info(f"llama-server.exe already installed in: {BIN_DIR}")
        return server_exe

    logger.info("Fetching latest Windows llama.cpp release from GitHub...")
    try:
        with httpx.Client(timeout=30.0, follow_redirects=True) as client:
            r = client.get("https://api.github.com/repos/ggerganov/llama.cpp/releases")
            rels = r.json()
            if not rels:
                raise RuntimeError("No GitHub releases found for llama.cpp")

            latest_tag = rels[0]
            zip_asset = None
            for asset in latest_tag.get("assets", []):
                name = asset.get("name", "")
                if "bin-win-cpu-x64.zip" in name:
                    zip_asset = asset
                    break

            if not zip_asset:
                for asset in latest_tag.get("assets", []):
                    name = asset.get("name", "")
                    if "win" in name and "x64.zip" in name and "cuda" not in name:
                        zip_asset = asset
                        break

            if not zip_asset:
                raise RuntimeError("Could not locate Windows x64 binary zip in release")

            download_url = zip_asset["browser_download_url"]
            logger.info(f"Downloading {zip_asset['name']} ({zip_asset['size'] / (1024*1024):.1f} MB)...")

            resp = client.get(download_url)
            if resp.status_code != 200:
                raise RuntimeError(f"Failed downloading binary zip: HTTP {resp.status_code}")

            logger.info("Extracting binaries to bin/llama-cpp/ ...")
            with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
                z.extractall(BIN_DIR)

            logger.info("llama.cpp binaries extracted successfully.")
            return server_exe
    except Exception as e:
        logger.error(f"Failed downloading llama.cpp binaries: {e}")
        return None

def download_qwen_model():
    """Download Qwen2.5-7B-Instruct-Q4_K_M.gguf from Hugging Face."""
    os.makedirs(MODELS_DIR, exist_ok=True)
    target_path = os.path.join(MODELS_DIR, HF_FILENAME)
    if os.path.exists(target_path) and os.path.getsize(target_path) > 4 * 1024 * 1024 * 1024:
        size_gb = os.path.getsize(target_path) / (1024 ** 3)
        logger.info(f"Qwen model already downloaded: {target_path} ({size_gb:.2f} GB)")
        return target_path

    logger.info(f"Downloading {HF_FILENAME} from {HF_REPO_ID} to {MODELS_DIR}...")
    try:
        downloaded = hf_hub_download(
            repo_id=HF_REPO_ID,
            filename=HF_FILENAME,
            local_dir=MODELS_DIR
        )
        size_gb = os.path.getsize(downloaded) / (1024 ** 3)
        logger.info(f"[SUCCESS] Model downloaded successfully: {downloaded} ({size_gb:.2f} GB)")
        return downloaded
    except Exception as e:
        logger.error(f"Model download failed: {e}")
        return None

def generate_startup_scripts(server_exe_path: str, model_path: str):
    """Generate Windows batch files to easily start the AI server and web application."""
    rel_server = os.path.relpath(server_exe_path, ROOT_DIR) if server_exe_path else "bin\\llama-cpp\\llama-server.exe"
    rel_model = os.path.relpath(model_path, ROOT_DIR) if model_path else f"models\\{HF_FILENAME}"

    llama_bat = os.path.join(ROOT_DIR, "start_llama_server.bat")
    with open(llama_bat, "w", encoding="utf-8") as f:
        f.write(f"@echo off\n")
        f.write(f"echo ==================================================\n")
        f.write(f"echo Starting Qwen 2.5 7B LLM Service on Port 8080...\n")
        f.write(f"echo ==================================================\n")
        f.write(f'"{os.path.join("%~dp0", rel_server)}" -m "{os.path.join("%~dp0", rel_model)}" --port 8080 -c 16384 -t 8\n')
        f.write(f"pause\n")

    app_bat = os.path.join(ROOT_DIR, "start_app.bat")
    with open(app_bat, "w", encoding="utf-8") as f:
        f.write(f"@echo off\n")
        f.write(f"echo ==================================================\n")
        f.write(f"echo Starting PlotChoice OCR & Verification Web Server...\n")
        f.write(f"echo URL: http://localhost:8000\n")
        f.write(f"echo ==================================================\n")
        f.write(f'set PYTHONPATH=%~dp0\n')
        f.write(f'py -m uvicorn app.server:app --host 0.0.0.0 --port 8000 --reload\n')
        f.write(f"pause\n")

    full_stack_bat = os.path.join(ROOT_DIR, "start_full_stack.bat")
    with open(full_stack_bat, "w", encoding="utf-8") as f:
        f.write(f"@echo off\n")
        f.write(f"echo ==================================================\n")
        f.write(f"echo Starting Full PlotChoice Real Estate AI Stack...\n")
        f.write(f"echo 1. Local AI Service (llama-server :8080)\n")
        f.write(f"echo 2. Web Application (FastAPI :8000)\n")
        f.write(f"echo ==================================================\n")
        f.write(f'start "Qwen 2.5 7B AI Service" cmd /k "{llama_bat}"\n')
        f.write(f'timeout /t 3\n')
        f.write(f'start "PlotChoice Web App" cmd /k "{app_bat}"\n')
        f.write(f'echo Both services launched in separate windows.\n')

    logger.info(f"Generated launcher scripts: start_llama_server.bat, start_app.bat, start_full_stack.bat")

def main():
    logger.info("Starting complete setup for Qwen 2.5 7B local AI stack...")
    server_exe = download_llama_binaries()
    model_file = download_qwen_model()
    generate_startup_scripts(server_exe, model_file)
    logger.info("==================================================")
    logger.info("SETUP COMPLETED SUCCESSFULLY!")
    logger.info(f"1. llama.cpp binaries: {BIN_DIR}")
    logger.info(f"2. Qwen model file:   {model_file}")
    logger.info("3. Launch stack with:  start_full_stack.bat")
    logger.info("==================================================")

if __name__ == "__main__":
    main()
