# 四季夏目 画图 Prompt 模板

## 角色特征

- **发色**: 黑色长直发
- **瞳色**: 金色/黄色
- **气质**: 高岭之花、清冷、外冷内热
- **着装偏好**: 女仆装、深色系连衣裙、校服、和风（巫女服/振袖）

## 可用模型

| 模型 | 大小 | 特点 | 数据截止 |
|------|------|------|----------|
| **WAI-Nsfw-Illustrious-17** (默认) | 6.5GB | 层次分明，画风干净 | 2025-05 |
| **miaomiaoHarem_v20** | 6.5GB | 偏油润，知识库更新 | 2026-01 |

**选择建议**: 一般用 WAI 层次感好；需要更新更全的知识库（新角色/新画风）时切 miaomiaoHarem。

## 正向 Prompt 模板

```
masterpiece, best quality, (shiki natsume:1.2), 1girl, solo,
long black hair, (yellow eyes:1.1), (cold expression:0.5), 
[场景描述], [着装描述],
detailed face, detailed eyes, cinematic lighting, beautiful detailed background,
(atmosphere:0.8)
```

## 常用场景组合

1. **夜空神社**
   - 场景: night sky, starry night, japanese shrine, moonlight, torii gate, lanterns
   - 着装: japanese shrine maiden outfit, red hakama

2. **咖啡馆**
   - 场景: cafe, warm lighting, window, rain outside
   - 着装: black dress, elegant

3. **日常校园**
   - 场景: school, cherry blossoms, spring
   - 着装: school uniform

4. **冬雪**
   - 场景: snow, winter, quiet street, warm light from window
   - 着装: black coat, scarf

5. **花**
   - 场景: garden, flowers, sunset
   - 着装: yukata, casual japanese dress

## 负向 Prompt（固定）

```
lowres, bad anatomy, bad hands, text, error, extra fingers, missing fingers, blurry,
jpeg artifacts, watermark, signature, bad proportions, monochrome
```

## 分辨率灵活调整指南

脚本第5/6参数控制宽和高。支持任意组合，脚本会自动对齐到8的倍数。

| 常用尺寸 | 宽  | 高  | 适用场景 |
|----------|-----|-----|----------|
| 方图     | 1024 | 1024 | 头像/封面 |
| 竖版壁纸 | 768  | 1024 | 手机壁纸 |
| 竖版高清 | 1024 | 1536 | 全身立绘 |
| 竖版超清 | 1200 | 1500 | 精细立绘（默认） |
| 横版     | 1536 | 1024 | 横版插画 |
| 横版宽屏 | 1920 | 1024 | 宽屏壁纸 |
| 小图快速 | 640  | 768  | 快速预览 |

**注意**: 分辨率越高越慢（会触发 tiled VAE 解码），1200x1500 约 50s，640x768 约 15s。

## 默认参数

| 参数 | 默认值 |
|------|--------|
| 模型 | WAI-Nsfw-Illustrious-17.safetensors |
| 步数 | 30 |
| CFG | 6.0 |
| 尺寸 | 1200x1500 |
| Sampler | euler_ancestral |
| Scheduler | normal |

## 可用 Sampler 算法列表

| Sampler | 类型 | 特点 | 推荐? |
|---------|------|------|-------|
| **euler_ancestral** | 祖先采样 | 默认，速度快，多样性好，细节丰富 | ⭐ 推荐 |
| **euler** | 一阶ODE | 稳定，无额外噪声，适合二次重绘 | |
| **dpmpp_2s_ancestral** | 二阶祖先 | 比 euler_ancestral 更细腻，收敛更快 | ⭐ 推荐 |
| **dpmpp_2m** | 二阶多步 | 稳定高细节，无水印感，适合写实 | ⭐ 推荐 |
| **dpmpp_2m_sde** | SDE 二阶 | 更强的随机性，艺术风格化，但可能过锐 | |
| **dpmpp_2m_sde_gpu** | SDE 二阶 GPU | 同 dpmpp_2m_sde，GPU 优化版 | |
| **dpmpp_3m_sde** | 三阶SDE | 最高质量但最慢，适合最终出图 | |
| **heun** | 二阶ODE | 准确但慢两倍，适合对质量苛刻时 | |
| **heunpp2** | 改进 Heun | 比 Heun 快，质量接近 | |
| **dpm_2_ancestral** | 二阶祖先 | 老牌采样器，比 euler_a 稍锐 | |
| **lms** | 线性多步 | 稳定但偏模糊，不推荐 | |
| **ddim** | 经典去噪 | 一致性高，适合图生图 | |
| **uni_pc** | 高阶加速 | 5-10 步可用，快速预览首选 | |
| **lcm** | 极速采样 | 4-8 步出图，质量较低 | |
| **sa_solver** | 自适应求解 | 质量好但较慢 | |

## 可用 Scheduler 列表

| Scheduler | 特点 |
|-----------|------|
| **normal** (默认) | 标准线性调度，通用 |
| **karras** | 更适合高CFG，细节更锐，常用 |
| **exponential** | 指数衰减，偏柔和 |
| **sgm_uniform** | 均匀间隔，有些模型专属 |
| **ddim_uniform** | DDIM 专属均匀调度 |
| **simple** | 简单线性 |
| **beta** | 实验性，少用 |

## 推荐组合

| 用途 | Sampler | Scheduler | 步数 | CFG |
|------|---------|-----------|------|-----|
| **默认均衡** (现在) | euler_ancestral | normal | 30 | 6.0 |
| **更细腻层次** | dpmpp_2s_ancestral | karras | 30 | 6.0 |
| **最高质量** | dpmpp_3m_sde | karras | 35 | 5.5 |
| **快速出图** | uni_pc | normal | 12 | 5.0 |
| **动漫风格** | dpmpp_2m | normal | 28 | 5.5 |

## 调用示例

```powershell
# 默认：停 llama → 跑图 → 重启（默认 manage_llama=True）
& "E:\comfyui\ComfyUI-aki-v3\python\python.exe" "C:\Users\TK\.openclaw\workspace\qqbot\skills\comfyui\comfyui_call.py" "正向prompt" "负向prompt"

# 不停 llama（显存够时）：对话不中断
& "E:\comfyui\ComfyUI-aki-v3\python\python.exe" "C:\Users\TK\.openclaw\workspace\qqbot\skills\comfyui\comfyui_call.py" "正向prompt" "负向prompt" -1 1200 1500 30 6.0 "WAI-Nsfw-Illustrious-17.safetensors" --no-manage-llama

# 切换 miaomiaoHarem (偏油润, 2026-01)
& "E:\comfyui\ComfyUI-aki-v3\python\python.exe" "C:\Users\TK\.openclaw\workspace\qqbot\skills\comfyui\comfyui_call.py" "正向prompt" "负向prompt" -1 1200 1500 30 6.0 "miaomiaoHarem_v20.safetensors"

# 快速小图
& "E:\comfyui\ComfyUI-aki-v3\python\python.exe" "C:\Users\TK\.openclaw\workspace\qqbot\skills\comfyui\comfyui_call.py" "正向prompt" "负向prompt" -1 640 768 20 5.0
```

> ⚠️ **manage_llama 问题**：默认会停 llama-server（对话中断 ~70秒），跑完自动重启。如果显存够（20GB+），可以设 manage_llama=False 不停 llama。显存不足时会自动 fallback 到停 llama 模式。

## 完整调用参数格式

```
python comfyui_call.py "正prompt" "负prompt" [seed] [宽] [高] [步数] [CFG] [模型名]
```

所有参数按位置顺序，想跳过的中间参数可以省略（会走默认值），只有prompt是必填。
