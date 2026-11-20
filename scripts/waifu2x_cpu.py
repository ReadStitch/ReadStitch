#!/usr/bin/env python3
"""Waifu2X CPU Denoise / Upscaler using ONNX Runtime.

Engine for low-end / potato PCs that lack Vulkan or GPU support.
Zero GPU or Vulkan dependencies required.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
import urllib.request

import numpy as np
from PIL import Image

try:
    import onnxruntime as ort
except ImportError:
    print(
        "[ERRO] onnxruntime não está instalado. Instale com: pip install onnxruntime",
        file=sys.stderr,
    )
    sys.exit(1)

SUPPORTED_EXTS = (
    ".png",
    ".webp",
    ".jpg",
    ".jpeg",
    ".jfif",
    ".bmp",
    ".tiff",
    ".tga",
    ".avif",
)

MODEL_URL_NOISE3 = (
    "https://huggingface.co/deepghs/waifu2x_onnx/resolve/main/"
    "20241017/onnx_models/cunet/art/noise3.onnx"
)

DEFAULT_CACHE_DIR = r"C:\Manhwa\Waifu2X\models-onnx"
LOCAL_ASSET_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "assets",
    "models",
    "waifu2x",
)


def ensure_model(model_path: str | None = None) -> str:
    """Ensure ONNX model is available locally, downloading if necessary."""
    if model_path and os.path.isfile(model_path):
        return model_path

    candidates = [
        os.path.join(DEFAULT_CACHE_DIR, "noise3.onnx"),
        os.path.join(LOCAL_ASSET_DIR, "noise3.onnx"),
    ]
    for c in candidates:
        if os.path.isfile(c) and os.path.getsize(c) > 1024 * 1024:
            return c

    target = candidates[0]
    os.makedirs(os.path.dirname(target), exist_ok=True)
    print(f"[Waifu2X-CPU] Baixando modelo Denoise (5 MB) para {target}...")
    try:
        urllib.request.urlretrieve(MODEL_URL_NOISE3, target)
        print("[Waifu2X-CPU] Download concluído com sucesso!")
        return target
    except Exception as e:
        print(f"[ERRO] Falha ao baixar modelo ONNX: {e}", file=sys.stderr)
        raise


class Waifu2xCpuEngine:
    def __init__(self, model_path: str, tile_size: int = 400):
        self.model_path = model_path
        self.tile_size = tile_size
        self.pad = 28  # CUNet margin / reflection padding

        opts = ort.SessionOptions()
        opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        opts.intra_op_num_threads = max(1, os.cpu_count() or 4)

        providers = ["CPUExecutionProvider"]
        if "DmlExecutionProvider" in ort.get_available_providers():
            providers.insert(0, "DmlExecutionProvider")

        self.session = ort.InferenceSession(
            self.model_path, sess_options=opts, providers=providers
        )
        self.input_name = self.session.get_inputs()[0].name

    def process_tile(self, tile_rgb: np.ndarray) -> np.ndarray:
        """Process a single (H, W, 3) uint8 tile."""
        pad = self.pad
        padded = np.pad(tile_rgb, ((pad, pad), (pad, pad), (0, 0)), mode="reflect")
        inp = np.transpose(padded.astype(np.float32) / 255.0, (2, 0, 1))[np.newaxis, ...]
        out = self.session.run(None, {self.input_name: inp})[0][0]
        out = np.clip(np.transpose(out, (1, 2, 0)) * 255.0, 0, 255).astype(np.uint8)
        return out

    def process_image(self, img: Image.Image) -> Image.Image:
        """Process a PIL Image using seamless tiling."""
        alpha = None
        if img.mode == "RGBA":
            alpha = img.split()[-1]
            img = img.convert("RGB")
        elif img.mode != "RGB":
            img = img.convert("RGB")

        arr = np.array(img)
        h, w, _ = arr.shape
        tile_size = self.tile_size

        res = np.zeros_like(arr)

        for y in range(0, h, tile_size):
            y_end = min(y + tile_size, h)
            for x in range(0, w, tile_size):
                x_end = min(x + tile_size, w)
                tile = arr[y:y_end, x:x_end]
                res[y:y_end, x:x_end] = self.process_tile(tile)

        out_img = Image.fromarray(res)
        if alpha is not None:
            out_img.putalpha(alpha)

        return out_img


def process_path(
    engine: Waifu2xCpuEngine,
    input_path: str,
    output_path: str,
    output_format: str,
) -> None:
    abs_in = os.path.abspath(input_path)
    abs_out = os.path.abspath(output_path)

    if os.path.isfile(abs_in):
        files_to_process = [(abs_in, abs_out)]
    elif os.path.isdir(abs_in):
        os.makedirs(abs_out, exist_ok=True)
        files_to_process = []
        for root, _, files in os.walk(abs_in):
            rel = os.path.relpath(root, abs_in)
            target_dir = abs_out if rel == "." else os.path.join(abs_out, rel)
            os.makedirs(target_dir, exist_ok=True)
            for f in files:
                if f.lower().endswith(SUPPORTED_EXTS):
                    src_file = os.path.join(root, f)
                    base, _ = os.path.splitext(f)
                    dest_file = os.path.join(target_dir, f"{base}.{output_format.lower()}")
                    files_to_process.append((src_file, dest_file))
    else:
        print(f"[ERRO] Entrada não encontrada: {input_path}", file=sys.stderr)
        return

    total = len(files_to_process)
    if total == 0:
        print("[Waifu2X-CPU] Nenhuma imagem encontrada para processar.")
        return

    print(f"[Waifu2X-CPU] Processando {total} imagem(ns) via CPU...")
    start_total = time.time()

    for idx, (src, dst) in enumerate(files_to_process, 1):
        t0 = time.time()
        filename = os.path.basename(src)
        print(f"[{idx}/{total}] {filename}...", end=" ", flush=True)

        try:
            with Image.open(src) as img:
                out_img = engine.process_image(img)

                save_kwargs = {}
                fmt_lower = output_format.lower()
                if fmt_lower in ("jpg", "jpeg"):
                    if out_img.mode == "RGBA":
                        out_img = out_img.convert("RGB")
                    save_kwargs["quality"] = 95
                elif fmt_lower == "webp":
                    save_kwargs["quality"] = 95

                out_img.save(dst, **save_kwargs)
            elapsed = time.time() - t0
            print(f"OK ({elapsed:.2f}s)")
        except Exception as e:
            print(f"FALHA: {e}")

    total_time = time.time() - start_total
    print(f"[Waifu2X-CPU] Concluído! {total} imagem(ns) em {total_time:.2f}s.\n")


def parse_args():
    parser = argparse.ArgumentParser(description="Waifu2X CPU Denoise Engine")
    parser.add_argument("-i", "--input", required=True, help="Input directory or file")
    parser.add_argument("-o", "--output", required=True, help="Output directory or file")
    parser.add_argument("-n", "--noise", default=3, type=int, help="Denoise level (default: 3)")
    parser.add_argument("-s", "--scale", default=1, type=int, help="Scale ratio (default: 1)")
    parser.add_argument("-f", "--format", default="jpg", help="Output format: jpg/webp/png (default: jpg)")
    parser.add_argument("-m", "--model", default=None, help="Path to ONNX model")
    parser.add_argument("-t", "--tile-size", default=400, type=int, help="Tile size (default: 400)")
    # Allow extra ignored args for compatibility with waifu2x-ncnn-vulkan CLI
    parser.add_argument("-g", default=None, help="Ignored (for CLI compatibility)")
    parser.add_argument("-j", default=None, help="Ignored (for CLI compatibility)")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    model_path = ensure_model(args.model)
    engine = Waifu2xCpuEngine(model_path, tile_size=args.tile_size)
    process_path(
        engine=engine,
        input_path=args.input,
        output_path=args.output,
        output_format=args.format,
    )
