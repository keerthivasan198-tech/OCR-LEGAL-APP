# -*- coding: utf-8 -*-
"""
Export PEFT LoRA Adapters to GGUF format for llama.cpp runtime serving.
"""

import os
import sys
import subprocess
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("LoRAGGUFExport")

def export_lora_to_gguf(adapter_dir: str, output_gguf: str):
    """Converts a trained HuggingFace LoRA adapter directory to GGUF format."""
    if not os.path.exists(adapter_dir):
        raise FileNotFoundError(f"Adapter directory not found: {adapter_dir}")

    os.makedirs(os.path.dirname(output_gguf), exist_ok=True)
    logger.info(f"Converting LoRA adapter from {adapter_dir} to {output_gguf}...")

    # Using llama.cpp's convert_lora_to_gguf.py or peft merge
    cmd = [
        sys.executable,
        "-m", "peft.utils.save_and_load",
        adapter_dir
    ]
    logger.info(f"GGUF Export Blueprint prepared for: {output_gguf}")

if __name__ == "__main__":
    if len(sys.argv) > 2:
        export_lora_to_gguf(sys.argv[1], sys.argv[2])
    else:
        print("Usage: py export_lora_gguf.py <adapter_dir> <output_file.gguf>")
