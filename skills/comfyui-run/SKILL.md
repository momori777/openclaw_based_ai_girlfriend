# ComfyUI 运行记录 — bochi control net_d

## 基本信息

- **运行日期**: 2026-05-29 02:38 (GMT+8)
- **工作流名称**: bochi control net_d
- **工作流 ID**: `64fccfdd-689f-4e5f-b82d-20d560b87ef6`
- **ComfyUI 地址**: `http://127.0.0.1:8188`
- **运行 ID (prompt_id)**: `0d8f2b13-9204-426d-a74a-5140416c3255`

## 模型配置

| 组件 | 值 |
|------|-----|
| Checkpoint | `miaomiaoHarem_v20.safetensors` |
| VAE | Checkpoint 自带 |
| 采样器 | euler_ancestral |
| 调度器 | simple |
| 步数 (steps) | 30 |
| CFG Scale | 5.0 |
| Denoise | 1.0 |

## 图像参数

| 参数 | 值 |
|------|-----|
| 宽 | 1008 px |
| 高 | 1200 px |
| 种子 | `980902536695208` (randomize) |

## Prompt

**Positive (CLIPTextEncodeSDXL)**:
```
masterpiece, best quality, amazing quality, absurdres, 1 girl, Gotou Hitori, pink hair, blue eyes, full_body, hair ornament
```

**Negative (CLIPTextEncodeSDXL)**:
```
normal quality, censored, worst quality, monochrome, grayscale, skin spots, acnes, skin blemishes, age spot, (ugly:1.1), blurry, bad hands, bad anatomy, signature, username
```

## Workflow 节点结构

| 节点 | 类型 | 说明 |
|------|------|------|
| 4 | CheckpointLoaderSimple | 加载 checkpoint |
| 28 | EmptySD3LatentImage | 生成空 latent (1008×1200) |
| 38 | CLIPTextEncodeSDXL | 正向条件编码 (1024×1024) |
| 39 | CLIPTextEncodeSDXL | 反向条件编码 (1024×1024) |
| 3 | KSampler | 主采样 (30步, CFG 5.0) |
| 8 | VAEDecode | VAE 解码 |
| 9 | SaveImage | 保存输出 (`ComfyUI_bochi_00001_.png`) |

**注意**: 工作流中还包含节点 6、7、26、27、31、32、33，但这些节点的输出未接入主链路（links 为空），属于未使用的废弃节点。

## 显存优化

ComfyUI 启动器使用动态 VRAM 加载策略：

```
SDXLClipModel:  1560 MB staged
SDXL:          4897 MB staged
AutoencoderKL:  159 MB staged
总计:          ~6.6 GB  (分阶段加载，非一次性)
0 models unloaded (首次运行无需卸载)
```

## 执行时间线

| 时间 | 事件 |
|------|------|
| T+0s | Prompt 提交 (`/prompt` API) |
| T+2s | 执行开始 (execution_start) |
| T+2s | 节点缓存命中 (execution_cached) |
| T+65s | 执行完成 (execution_success) |
| 输出 | `ComfyUI_bochi_00001_.png` → `ComfyUI/output/` |

## API 调用方式

**提交 Prompt:**
```bash
curl.exe -s http://127.0.0.1:8188/prompt \
  -H "Content-Type: application/json" \
  -d @comfyui_prompt.json
```

**查询结果:**
```bash
curl.exe -s http://127.0.0.1:8188/history/<prompt_id>
```

**下载图片:**
```bash
curl.exe -s http://127.0.0.1:8188/view/<filename> -o output.png
```

## 经验/注意事项

1. **JSON 传参**: Windows PowerShell 下 `curl` 是 `Invoke-WebRequest` 别名，长 JSON 字符串容易被反引号 (`) 截断。建议将 prompt JSON 写入文件，用 `-d @file.json` 方式传递。
2. **工作流 ID 不是 API 端点**: 浏览器 URL 中的 `#<workflow_id>` 是前端会话标识，不是 ComfyUI API 路径。获取最新 prompt 需查询 `/history` 端点。
3. **动态 VRAM 加载**: 启动器自动分阶段加载模型（Clip → UNet → VAE），显著降低峰值显存。6GB 级显存即可运行 SDXL 模型。
4. **废弃节点**: 工作流中可能有大量未连接节点，提交前建议清理以减少不必要的初始化开销。
5. **等待完成**: 30步 SDXL 采样约需 60-90 秒，查询 `/history` 时需轮询直到 `completed: true`。

## 关联文件

- Prompt JSON: `comfyui_prompt.json` (workspace 根目录)
- 输出图片: `comfyui_output.png` (workspace 根目录，为本次运行的快照)
