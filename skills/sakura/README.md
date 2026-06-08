[English](docs/README.en.md)

# Sakura Desktop Pet

最近推完水晶社的新作，~~推完自动变成学姐的狗~~，已经变成学姐的形状了，夜里辗转反侧怎么都睡不着，所以起来开发了这个桌宠 Agent 框架。

Sakura 最大的特点是 **她会主动找你**。传统聊天机器人只有在你先开口时才会回应，就像一扇需要你敲门才会开的锁；Sakura 更像一个坐在你旁边的人，你不需要一直和她说话，但她知道你在做什么，偶尔觉得该说点什么的时候会自己开口。

比如你正在打游戏，她瞥见屏幕上的死亡提示，凑过来说「已经第三回了…要不要帮你查下攻略？」同意后就真的打开浏览器搜了一圈，把要点贴进备忘录。

或者是你在浏览其他角色的图片时，会吃醋地说「又在看别人了啊…」要求你多看看她的立绘，偶尔还会因为你太久没看她而生气地说「都不理我了啊…」。

所以 Sakura 实现的是一个一直在角落、会观察、会偶尔插话的角色。她的对话风格、表情、语音都由角色卡驱动，而工具能力（浏览器操作、屏幕截图、文件读取、Web 搜索、提醒、长期记忆等）则来自内置的 Agent 引擎。

把它想成一个定制角色的桌面 Agent。

![Sakura 预览](assets/sakura_01.png)
![N.A.V.I. 预览](assets/navi_01.png)
## 新手教程（零基础也能用）

**不需要会编程。** 推荐直接使用 **Release 里的最新版本**，不要只下载 GitHub 页面上的源码压缩包。源码包缺少预置 `runtime`，无法启动

> **平台提醒：** Windows 版本是当前主要测试目标。linux/mac 用户可以使用源码自行安装

### 第一步：下载发布包

打开 [Releases 页面](https://github.com/Rvosy/sakura/releases)，下载最新的构建包。

Release 里常见的文件含义如下：

| 文件名 | 是什么 | 适合谁下载 |
|:-:|---|---|
| `sakura-v0.9.x-windows-x64.zip` | Windows 完整包，包含项目文件和 `runtime` | **Windows 新手首选** |
| `runtime-windows-x64.zip` | 只有 Windows 预置 Python 运行环境 | 拉源码、缺 `runtime` 的用户 |

> 如果你只是想运行桌宠，下载 `sakura-v0.9.x-windows-x64.zip` 这种 **完整包**。`runtime` 包不是完整程序，单独下载后不能直接启动。

### 第二步：安装依赖

解压完整包后，进入解压出来的软件目录。

- **Windows 用户：** 双击 `install.bat`，等待完成（约 5-15 分钟）。
- **Mac 用户：** 可尝试双击 `install.command`，或在终端进入项目目录后运行 `bash scripts/install.sh`。但 Mac 没有实机测试过，遇到问题请优先反馈日志。
- **Linux 用户：** 当前没有正式发布包；如果从源码运行，进入项目目录后运行 `bash scripts/install.sh`。

> 如果是直接拉取的源码，需要先从 Release 页面下载对应平台的预编译依赖包（`sakura-runtime-*.zip`），把里面的 `runtime` 文件夹放到项目根目录，再运行安装脚本。
> 不管下载的是 Release 完整包还是 GitHub 源码，这一步都要做。装完命令行窗口会自动关闭。

### 第三步：获取 API Key

桌宠需要一个「AI 大脑」才能说话，你需要一个 API Key。就像给手机插 SIM 卡才能上网一样。

1. **获取 API Key。** 可以从以下任一渠道获得：
   - 国内中转站如 [GemAI](https://api.gemai.cc/register?aff=rwbQ)（有便宜且按次计费的 gemini-flash 系列模型）
   - 其他任何兼容 OpenAI 接口格式的服务

> **目前不要使用 DeepSeek 系列模型！**
>
> Sakura 的很多功能（屏幕观察、图像识别等）直接依赖模型的多模态能力（视觉理解），而 DeepSeek 系列模型不具备多模态能力，使用后会导致桌宠无法正常观察屏幕、识别图像等功能失效。
>
> 请选择支持视觉/多模态的模型，例如 Gemini Flash 等。

### 第四步：一键启动

- **Windows 用户：** 双击项目根目录的 **`start.bat`**
- **Mac 用户：** 可尝试双击 `start.command`，或在终端里运行 `bash scripts/start.sh`。再次提醒：Mac 没有实机测试过。
- **Linux 用户：** 在终端里运行 `bash scripts/start.sh`
- **右键** 桌宠或托盘图标可以打开菜单（设置、聊天记录等）

### 第五步：获取角色包

暂时只有百度网盘：

- **[百度网盘](https://pan.baidu.com/s/5ZXvAi6n6i7-OJAYeWDpprg)**：包含所有已发布的角色包。

角色包会携带角色卡、立绘、语音参考音频，以及该角色可用的 GPT-SoVITS 权重（例如 `voice/models/*.ckpt`、`voice/models/*.pth`）。源码仓库和 TTS 运行环境安装脚本不会单独下载这些角色声线权重；如果完整包中没有对应角色资源，需要先通过角色包渠道获取并导入。

安装方式：

1. 下载角色包
2. 打开 Sakura 设置页
3. 选择导入角色包

### 如何更新版本？

如果你已经装过旧版，推荐按下面方式更新：

1. 关闭正在运行的 Sakura。
2. 下载同平台的最新**完整包**，例如 Windows 用户下载 `sakura-v0.9.x-windows-x64.zip`。
3. 解压新包，把新包里的文件复制到旧 Sakura 目录，遇到同名文件选择 **覆盖/替换**。
4. 如果启动失败，再运行一次安装脚本：Windows 双击 `install.bat`；Mac/Linux 运行 `bash scripts/install.sh`。
5. 启动 Sakura：Windows 双击 `start.bat`；Mac 可尝试 `start.command` 或 `bash scripts/start.sh`。

## 核心功能

- **角色包驱动。** 角色卡、立绘、语音参考和 GPT-SoVITS 权重都可以按角色包组织。
- **主动关怀。** Sakura 可以按周期观察上下文，主动发起提醒、关心或建议。
- **分段双语回复。** 模型输出日文原文、中文字幕、语气和立绘标识，UI 同步驱动字幕、表情和语音。
- **语气联动表情和语音。** 语气标签会同时影响立绘切换和 TTS 参考音频选择。
- **屏幕观察。** 支持按需截图和自主屏幕观察，把视觉摘要纳入对话上下文。
- **工具调用。** 支持浏览器操作、桌面操作、文件读取、Web 搜索、提醒、待办、笔记和记忆等工具。
- **权限确认。** 高风险工具会先请求用户确认，再执行实际动作。
- **长期记忆。** 记忆先进入候选区，确认后才写入正式记忆，并支持自动整理。
- **插件和 MCP 扩展。** 支持本地插件、MCP Server 和内置 Web 搜索 MCP Server。
- **历史、调试和 UI 控制。** 支持聊天历史回看、调试日志、立绘缩放和动效配置。

## 技术文档

想了解运行时架构、启动流程、项目结构、配置项、TTS 技术细节或插件开发入口，请看：

- [Sakura 技术讲解 README](docs/TECHNICAL_README.md)
- [Sakura 插件 SDK 文档](docs/SAKURA_PLUGIN_SDK.md)

## Star History

<a href="https://www.star-history.com/?repos=Rvosy%2Fsakura&type=date&legend=top-left">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/chart?repos=Rvosy/sakura&type=date&theme=dark&legend=top-left" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/chart?repos=Rvosy/sakura&type=date&legend=top-left" />
   <img alt="Star History Chart" src="https://api.star-history.com/chart?repos=Rvosy/sakura&type=date&legend=top-left" />
 </picture>
</a>
