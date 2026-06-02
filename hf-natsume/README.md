# AI Girlfriend — Shiki Natsume (四季夏目) · Model Repository

This is the model distribution repository for [AI Girlfriend 四季夏目](https://github.com/TAOTAO777/ai-girlfriend-natsume).

📖 **English** | [中文](#chinese)

---

## ⚠️ Disclaimer

All model files in this repository are **existing community open-source models**. I am only mirroring and redistributing them for convenience. **I claim no ownership** over any of these models.

Original authors and licenses:

| Model | Author | Source | License |
|-------|--------|--------|---------|
| Qwen3.6-35B-A3B-APEX | mudler | [HuggingFace](https://huggingface.co/mudler/Qwen3.6-35B-A3B-uncensored-heretic-APEX-GGUF) | Apache 2.0 (Qwen) |
| WAI-Nsfw-Illustrious-17 | WAI0731 | [CivitAI](https://civitai.com/models/1185480) | Community model |
| miaomiaoHarem_v20 | miaomiao0226 | [CivitAI](https://civitai.com/models/1033365) | Community model |
| GPT-SoVITS weights | Self-trained | — | Free to use |

**This project is purely non-profit and personal.** No commercial use intended.
If any original author objects to mirror distribution, please contact me to take it down.

## Download

```powershell
# Download everything
huggingface-cli download TAOTAO777/ai-girlfriend-natsume --local-dir ./models

# Or selectively:
huggingface-cli download TAOTAO777/ai-girlfriend-natsume llm/ --local-dir ./models
huggingface-cli download TAOTAO777/ai-girlfriend-natsume comfyui-checkpoints/ --local-dir ./checkpoints
huggingface-cli download TAOTAO777/ai-girlfriend-natsume gpt-sovits-weights/ --local-dir ./gpt-sovits-weights
```

## Directory Mapping

Place downloaded files according to the source project's expected paths:

```
llm/
└── Qwen3.6-35B-A3B-APEX-I-Compact.gguf
    → Expected at: <your vllm>/models/

comfyui-checkpoints/
├── WAI-Nsfw-Illustrious-17.safetensors
└── miaomiaoHarem_v20.safetensors
    → Expected at: <ComfyUI>/models/checkpoints/

gpt-sovits-weights/
├── SoVITS_weights_v2Pro/xxx-e30.ckpt
└── GPT_weights_v2Pro/xxx_e20_s6240.pth
    → Expected at: <GPT-SoVITS>/SoVITS_weights_v2Pro/ and GPT_weights_v2Pro/
```

## Main Project Repo

Source code and configuration: [TAOTAO777/ai-girlfriend-natsume](https://github.com/TAOTAO777/ai-girlfriend-natsume) (GitHub)

---

<h2 id="chinese">中文章节</h2>

## ⚠️ 免责声明

本仓库中的模型文件均为**社区开源模型**，本人仅做收集和镜像分发，**不声称任何所有权**。本项目完全非盈利，纯个人兴趣，不涉及任何商业用途。若原作者认为镜像分发不妥，请联系我删除。

### 原作者列表

| 模型 | 原作者 | 原始来源 | 许可证 |
|------|--------|---------|--------|
| Qwen3.6-35B-A3B-APEX | mudler | [HuggingFace](https://huggingface.co/mudler/Qwen3.6-35B-A3B-uncensored-heretic-APEX-GGUF) | Apache 2.0 (Qwen) |
| WAI-Nsfw-Illustrious-17 | WAI0731 | [CivitAI](https://civitai.com/models/1185480) | 社区模型 |
| miaomiaoHarem_v20 | miaomiao0226 | [CivitAI](https://civitai.com/models/1033365) | 社区模型 |
| GPT-SoVITS 权重 | 本人训练 | — | 自由使用 |

### 下载方式

```powershell
# 全量下载
huggingface-cli download TAOTAO777/ai-girlfriend-natsume --local-dir ./models
```

### 目录对应

```
llm/           → <你的vllm>/models/
comfyui-checkpoints/  → <ComfyUI>/models/checkpoints/
gpt-sovits-weights/   → <GPT-SoVITS>/SoVITS_weights_v2Pro/ + GPT_weights_v2Pro/
```

### 主项目

代码和配置：[TAOTAO777/ai-girlfriend-natsume](https://github.com/TAOTAO777/ai-girlfriend-natsume) (GitHub)
