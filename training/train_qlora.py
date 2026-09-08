# -*- coding: utf-8 -*-
"""
QLoRA Fine-Tuning Pipeline for Qwen2.5-7B-Instruct Document Adapters.
Targeted adapters:
- EC LoRA (Encumbrance Certificate)
- Patta LoRA (Form 10(1) Revenue Record)
- TSLR LoRA (Town Survey Land Register)
- Sale Deed LoRA (Title Deed & Mother Deed)

Can be executed on any GPU machine (e.g. Google Colab, RunPod, AWS, or local NVIDIA RTX).
"""

import os
import argparse
import logging
from typing import Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("QLoRATraining")

DEFAULT_BASE_MODEL = "Qwen/Qwen2.5-7B-Instruct"

def train_document_adapter(
    doc_type: str,
    base_model_name: str = DEFAULT_BASE_MODEL,
    output_dir: Optional[str] = None,
    epochs: int = 3,
    learning_rate: float = 2e-4,
    batch_size: int = 2
):
    """
    Executes 4-bit QLoRA fine-tuning using HuggingFace TRL & PEFT.
    """
    train_file = os.path.join(os.path.dirname(__file__), doc_type, "train.jsonl")
    if not os.path.exists(train_file):
        raise FileNotFoundError(f"Training dataset not found: {train_file}. Run prepare_dataset.py first.")

    out_dir = output_dir or os.path.join(os.path.dirname(__file__), "adapters", f"{doc_type}_lora")
    os.makedirs(out_dir, exist_ok=True)

    logger.info("==================================================")
    logger.info(f"Starting QLoRA Fine-Tuning for: {doc_type.upper()} Adapter")
    logger.info(f"Base Model: {base_model_name}")
    logger.info(f"Dataset:    {train_file}")
    logger.info(f"Output:     {out_dir}")
    logger.info(f"Epochs:     {epochs}, LR: {learning_rate}, Batch: {batch_size}")
    logger.info("==================================================")

    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
        from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
        from datasets import load_dataset
        from trl import SFTTrainer, SFTConfig

        # 1. 4-bit Quantization Config (NF4)
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True
        )

        # 2. Load Base Model & Tokenizer
        logger.info("Loading 4-bit quantized base model...")
        tokenizer = AutoTokenizer.from_pretrained(base_model_name, trust_remote_code=True)
        tokenizer.pad_token = tokenizer.eos_token

        model = AutoModelForCausalLM.from_pretrained(
            base_model_name,
            quantization_config=bnb_config,
            device_map="auto",
            trust_remote_code=True
        )
        model = prepare_model_for_kbit_training(model)

        # 3. LoRA Configuration
        peft_config = LoraConfig(
            r=16,
            lora_alpha=32,
            target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
            lora_dropout=0.05,
            bias="none",
            task_type="CAUSAL_LM"
        )
        model = get_peft_model(model, peft_config)
        model.print_trainable_parameters()

        # 4. Load Dataset
        dataset = load_dataset("json", data_files={"train": train_file})

        # 5. SFT Trainer
        training_args = SFTConfig(
            output_dir=out_dir,
            num_train_epochs=epochs,
            per_device_train_batch_size=batch_size,
            gradient_accumulation_steps=4,
            learning_rate=learning_rate,
            fp16=True,
            logging_steps=10,
            save_strategy="epoch",
            dataset_text_field="messages"
        )

        trainer = SFTTrainer(
            model=model,
            args=training_args,
            train_dataset=dataset["train"],
            peft_config=peft_config,
            tokenizer=tokenizer
        )

        logger.info("Training in progress...")
        trainer.train()

        logger.info(f"Saving fine-tuned adapter to: {out_dir}")
        trainer.model.save_pretrained(out_dir)
        tokenizer.save_pretrained(out_dir)

        logger.info(f"[SUCCESS] {doc_type.upper()} LoRA adapter training complete!")

    except ImportError as e:
        logger.warning(f"Training dependencies (torch/peft/trl) not found in current environment: {e}")
        logger.info("Tip: QLoRA training is designed to run on a dedicated GPU environment or Colab.")
        logger.info(f"Adapter blueprint ready for: {doc_type} -> {out_dir}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="QLoRA Document Adapter Trainer")
    parser.add_argument("--doc-type", choices=["ec", "patta", "tslr", "sale_deed"], default="ec", help="Target document type")
    parser.add_argument("--epochs", type=int, default=3, help="Number of training epochs")
    parser.add_argument("--lr", type=float, default=2e-4, help="Learning rate")
    args = parser.parse_args()

    train_document_adapter(doc_type=args.doc_type, epochs=args.epochs, learning_rate=args.lr)
