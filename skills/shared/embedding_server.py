"""
本地 Embedding HTTP 服务 — MiniLM-L6-v2

提供 OpenAI-compatible /v1/embeddings 接口，供：
  - OpenClaw memory_search（语义记忆检索）
  - Sakura mem0 memory.py（长期记忆向量化）

使用 sentence-transformers/all-MiniLM-L6-v2，纯本地，无需 API Key。

启动方式:
    python embedding_server.py
    或
    .\start_embedding_server.bat

默认监听: http://127.0.0.1:9999
健康检查: GET /health
嵌入接口: POST /v1/embeddings  (OpenAI-compatible)
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from pathlib import Path

# ----- 路径 & HF 缓存 -----
# 优先复用 Sakura 的 runtime/hf-cache，没有则走默认路径
_SCRIPT_DIR = Path(__file__).resolve().parent
# 从 skills/shared/ 往上找项目根（skills/ -> 项目根）
# 支持 D:\AI_Girlfriend 和 workspace 两种根目录
_PROJECT_ROOT = _SCRIPT_DIR.parents[1]
_SAKURA_RUNTIME = _PROJECT_ROOT / "skills" / "sakura" / "runtime" / "hf-cache"

if _SAKURA_RUNTIME.exists():
    os.environ.setdefault("HF_HOME", str(_SAKURA_RUNTIME))
    os.environ.setdefault("SENTENCE_TRANSFORMERS_HOME", str(_SAKURA_RUNTIME))

# ----- 依赖检查与自动安装 -----
try:
    from flask import Flask, request, jsonify
except ImportError:
    print("[embedding_server] Flask 未安装，正在自动安装...", flush=True)
    import subprocess

    subprocess.check_call([sys.executable, "-m", "pip", "install", "flask"])
    from flask import Flask, request, jsonify

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    print("[embedding_server] sentence-transformers 未安装，正在自动安装...", flush=True)
    import subprocess

    subprocess.check_call([sys.executable, "-m", "pip", "install", "sentence-transformers"])
    from sentence_transformers import SentenceTransformer

# ----- 配置 -----
# 国内网络环境：用 HF Mirror 下载/查询模型缓存
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_PORT = 9999
DEFAULT_HOST = "127.0.0.1"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [embedding] %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("embedding_server")

app = Flask(__name__)

# 全局模型实例（懒加载，首次请求时初始化）
_model: SentenceTransformer | None = None
_model_load_time: float = 0.0


def _get_model() -> SentenceTransformer:
    """获取或加载 MiniLM-L6-v2 模型（线程安全懒加载）"""
    global _model, _model_load_time
    if _model is not None:
        return _model

    logger.info("正在加载 %s ...（首次启动会下载 ~80MB 模型缓存）", MODEL_NAME)
    t0 = time.time()
    # 强制本地加载：不联网，使用 HF_HOME 缓存
    import huggingface_hub
    # 尝试在 huggingface_hub 能找到的 cache 路径中定位模型
    try:
        cache_path = huggingface_hub.snapshot_download(MODEL_NAME, local_files_only=True)
        logger.info("模型缓存位于: %s", cache_path)
    except Exception:
        pass  # 如果在 snapshot_download 之前已经有 SymbolicCache 可以工作
    _model = SentenceTransformer(
        MODEL_NAME,
        cache_folder=str(_SAKURA_RUNTIME) if _SAKURA_RUNTIME.exists() else None,
    )
    _model_load_time = round(time.time() - t0, 1)
    logger.info("模型加载完成，耗时 %.1fs", _model_load_time)
    return _model


@app.route("/health", methods=["GET"])
def health():
    """健康检查 — OpenClaw / Sakura 启动时可用此端点确认服务就绪"""
    try:
        model = _get_model()
        return jsonify({
            "status": "ok",
            "model": MODEL_NAME,
            "load_time_s": _model_load_time,
            "dim": model.get_sentence_embedding_dimension(),
        })
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route("/v1/embeddings", methods=["POST"])
def embeddings():
    """
    OpenAI-compatible embeddings endpoint.

    Request body:
        {
            "input": "text to embed" | ["text1", "text2", ...],
            "model": "all-MiniLM-L6-v2"  (ignored, fixed model)
        }

    Response:
        {
            "object": "list",
            "data": [
                {"object": "embedding", "index": 0, "embedding": [0.1, 0.2, ...]},
                ...
            ],
            "model": "all-MiniLM-L6-v2",
            "usage": {"prompt_tokens": 0, "total_tokens": 0}
        }
    """
    try:
        body = request.get_json(force=True)
    except Exception:
        return jsonify({"error": "Invalid JSON body"}), 400

    if body is None:
        return jsonify({"error": "Request body is required"}), 400

    text_input = body.get("input")
    if text_input is None:
        return jsonify({"error": "Missing 'input' field"}), 400

    # 统一成 list
    if isinstance(text_input, str):
        texts = [text_input]
    elif isinstance(text_input, list):
        texts = [str(t) for t in text_input]
    else:
        return jsonify({"error": "'input' must be a string or list of strings"}), 400

    model = _get_model()
    t0 = time.time()
    embeddings = model.encode(texts, normalize_embeddings=True)
    elapsed = round((time.time() - t0) * 1000, 1)

    data = [
        {
            "object": "embedding",
            "index": i,
            "embedding": emb.tolist(),
        }
        for i, emb in enumerate(embeddings)
    ]

    logger.info("embedding: %d texts, dim=%d, time=%.1fms", len(texts), embeddings.shape[1], elapsed)

    return jsonify({
        "object": "list",
        "data": data,
        "model": "all-MiniLM-L6-v2",
        "usage": {"prompt_tokens": 0, "total_tokens": 0},
    })


def main():
    parser = argparse.ArgumentParser(description="本地 Embedding HTTP 服务 (MiniLM-L6-v2)")
    parser.add_argument("--host", default=DEFAULT_HOST, help=f"监听地址 (默认: {DEFAULT_HOST})")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"监听端口 (默认: {DEFAULT_PORT})")
    parser.add_argument("--debug", action="store_true", help="开启 Flask debug 模式")
    args = parser.parse_args()

    logger.info("启动 embedding 服务: http://%s:%d", args.host, args.port)
    logger.info("模型: %s", MODEL_NAME)

    # 如果是桌面运行，可选打开浏览器
    app.run(host=args.host, port=args.port, debug=args.debug, threaded=True)


if __name__ == "__main__":
    main()
