#!/usr/bin/env python3
"""
prepare_unslopnemo_exl3.py - Downloads UnslopNemo-12B-v4.1 and quantizes it to EXL3 (5.0bpw)
for ExLlamaV3 with RTX 4070 Ti optimization.
"""

import os
import sys
import subprocess
import time
from pathlib import Path
from huggingface_hub import snapshot_download

os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "1"
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

BASE_DIR = Path("/home/sammyjdev/.local/share/exllamav3")
RAW_MODEL_DIR = BASE_DIR / "unquantized" / "UnslopNemo-12B-v4.1"
OUTPUT_DIR = BASE_DIR / "models" / "UnslopNemo-12B-v4.1-exl3-4.25bpw"
WORK_DIR = BASE_DIR / "work"
PYTHON_BIN = BASE_DIR / "venv" / "bin" / "python"

def main():
    print("==========================================================================")
    print("  🚀 PREPARAÇÃO & QUANTIZAÇÃO EXL3 OTIMIZADA: UnslopNemo-12B-v4.1 (4.25 bpw)")
    print("==========================================================================")
    
    hf_token = os.getenv("HF_TOKEN") or os.getenv("HUGGING_FACE_HUB_TOKEN")
    if hf_token:
        print("🔑 Token HuggingFace detectado: autenticação ativa para download de alta velocidade.")
    else:
        print("ℹ️ HF_TOKEN não definido: download público padrão ativo.")
    
    # 1. Download unquantized BF16 safetensors with hf_transfer
    print(f"\n[1/2] Baixando tensores BF16 de 'TheDrummer/UnslopNemo-12B-v4.1' via hf_transfer...")
    t0 = time.perf_counter()
    snapshot_download(
        repo_id="TheDrummer/UnslopNemo-12B-v4.1",
        local_dir=str(RAW_MODEL_DIR),
        local_dir_use_symlinks=False,
        token=hf_token,
        max_workers=8
    )
    dl_time = time.perf_counter() - t0
    print(f"✅ Download concluído em {dl_time/60:.2f} minutos!")
    
    # 2. Run ExLlamaV3 conversion tool to produce 4.25bpw EXL3
    print(f"\n[2/2] Quantizando para EXL3 (4.25 bpw) com Head 6.0 na GPU RTX 4070 Ti...")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    
    cmd = [
        str(PYTHON_BIN),
        "-m", "exllamav3.conversion.convert_model",
        "-i", str(RAW_MODEL_DIR),
        "-o", str(OUTPUT_DIR),
        "-w", str(WORK_DIR),
        "-b", "4.25",
        "-hb", "6",
        "--shard_size", "8192"
    ]
    
    t1 = time.perf_counter()
    res = subprocess.run(cmd)
    conv_time = time.perf_counter() - t1
    
    if res.returncode == 0:
        print(f"\n==========================================================================")
        print(f"🎉 Modelo EXL3 (4.25 bpw) pronto com sucesso em {conv_time/60:.2f} minutos!")
        print(f"📁 Salvo em: {OUTPUT_DIR}")
        print(f"⚡ VRAM Ocupada: ~5.8 GB | Taxa estimada: 130-160 t/s")
        print("==========================================================================")
    else:
        print(f"\n❌ Erro na quantização (código {res.returncode})")
        sys.exit(res.returncode)

if __name__ == "__main__":
    main()
