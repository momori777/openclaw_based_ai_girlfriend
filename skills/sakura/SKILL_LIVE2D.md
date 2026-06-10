# Sakura × Live2D Bridge 集成 Skill（草稿）

> **当前状态：草稿**。先用 Sakura 静态 PNG 立绘跑通表情切换流程，
> 确认 `tone` → `expression` 映射无误后再切换到 Live2D 动态渲染。
>
> 切换方式：`character.json` 移除 `portrait` 字段，加入 `live2d` 配置块即可。
> **未切换之前 Live2D 集成代码完全不影响现有功能。**

## 架构

```
Sakura LLM 回复
  → parse_chat_reply()
    → ChatSegment { text, tone, translation, portrait }
      → PortraitController.apply_for_segment(segment)
        ┌─ 静态模式 (当前): 读 portraits/*.png → QPixmap
        └─ Live2D 模式 (未来): HTTP GET /api/emotion → Live2D 窗口
```

切换依靠 `PortraitController` 的一个分支：检测到 `profile.live2d` 时走 HTTP 调用而非本地 QPixmap 加载。

## 表情映射

Sakura 的 `tone` 键名（由 `card.md` 描述 + LLM 自由选择）需要映射到 Live2D 的 5 种表情：

| tone (Sakura) | Live2D expression | exp_json |
|---|---|---|
| 中性 | neutral | exp_01 |
| 害羞 | neutral | exp_01（无对应，复用中性） |
| 温柔 | happy | exp_02 |
| 不满 | angry | exp_04 |
| 傲娇 | angry | exp_04（最接近） |
| 困惑 | sad | exp_03（垂眼） |
| 惊讶 | surprised | exp_05 |
| 请求 | sad | exp_03（垂眼拜托感） |

**5 种 Live2D 表情无法覆盖全部 8 种 tone。** 这是核心限制——日后有了四季夏目自己模型的 8 种差分表情 exp 文件后可扩展。

## Live2D API 速查

详见 `live2d/SKILL.md`。关键接口：

```powershell
# 表情 + 文字组合
curl "http://localhost:19200/api/emotion?expression=happy&text=いいね！"

# 嘴型（配合 TTS 使用）
curl "http://localhost:19200/api/speak?action=start&text=おはよう"
curl "http://localhost:19200/api/speak?action=end"

# 重置
curl "http://localhost:19200/api/reset"
```

## character.json 加 Live2D 配置（计划）

```json
{
  "id": "shiki_natsume",
  "...": "...",
  "live2d": {
    "enabled": true,
    "bridge_url": "http://localhost:19200",
    "model_name": "ren",
    "expression_map": {
      "中性": "neutral",
      "害羞": "neutral",
      "温柔": "happy",
      "不满": "angry",
      "傲娇": "angry",
      "困惑": "sad",
      "惊讶": "surprised",
      "请求": "sad"
    },
    "motions": {
      "greeting": "mtn_01",
      "idle": "mtn_02",
      "special": "mtn_03"
    },
    "speak_sync": true
  }
}
```

## 集成点（代码改动计划）

### 1. `character_loader.py` — 解析 `live2d` 配置块

```python
@dataclass(frozen=True)
class Live2DConfig:
    enabled: bool = False
    bridge_url: str = "http://localhost:19200"
    model_name: str = ""
    expression_map: dict[str, str] = field(default_factory=dict)
    motions: dict[str, str] = field(default_factory=dict)
    speak_sync: bool = True
```

### 2. `portrait_controller.py` — 双模式分支

```python
class PortraitController:
    def __init__(self, ..., live2d_config: Live2DConfig | None = None):
        ...
        self.live2d = live2d_config

    def apply_for_segment(self, segment: ChatSegment) -> None:
        if self.live2d and self.live2d.enabled:
            self._live2d_apply(segment)
            return
        # 原有 QPixmap 逻辑 ...

    def _live2d_apply(self, segment: ChatSegment) -> None:
        tone = segment.tone or DEFAULT_TONE
        expression = self.live2d.expression_map.get(tone, "neutral")
        text = segment.display_text(self.subtitle_language)
        url = f"{self.live2d.bridge_url}/api/emotion?expression={expression}&text={text}"
        # 异步 HTTP GET，不阻塞 Qt 主循环
```

### 3. `subtitle_controller.py` — 嘴型同步

```python
# 在 play_segment_voice() 中：
if live2d_config and live2d_config.speak_sync:
    _live2d_speak_start(segment.text)
    # ... 播放 TTS 音频 ...
    _live2d_speak_end()
```

## 切换步骤

1. ✅ Sakura 用静态 PNG 跑通，确认 tone 选择符合预期
2. 将 `shiki_natsume/portraits/*.png` 补完（8 张差分，用户手动提取）
3. 确认 Live2D Bridge 在 19200 端口运行
4. 修改 `character.json`：移除 `portrait` 字段，加 `live2d` 配置块
5. 修改 `character_loader.py` + `portrait_controller.py` + `subtitle_controller.py`
6. 测试表情映射合理度
7. 后续：换四季夏目专属 Live2D 模型（替代当前的加藤惠模型）

## 风险点

- **Live2D Bridge 依赖 Node.js**：Sakura 启动前需确保 bridge 进程已运行
- **HTTP 调用是同步的**：需改为异步（`QNetworkAccessManager` 或 `urllib` in thread）避免阻塞 Qt 事件循环
- **表情数量不匹配**：5 Live2D vs 8 tone → 需要映射取舍，或等专属模型
- **嘴型时机对齐**：TTS 音频时长 ≠ 实际播放时长，嘴型 end 信号需靠 QMediaPlayer 的 `mediaStatusChanged` 事件而非定时器
