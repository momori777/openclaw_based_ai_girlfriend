"""app/plugins/manager.py — Sakura 原生插件管理器。"""

from __future__ import annotations

import importlib
import importlib.util
import inspect
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType
from typing import Any

from app.agent.tool_registry import ToolRegistry
from app.core.debug_log import debug_log
from app.plugins.adapters import contribution_to_app_tool
from app.plugins.capabilities import PluginCapabilities
from app.plugins.discovery import PluginDiscovery
from app.plugins.models import PluginManifest, PluginSpec, ToolContribution
from sdk.plugin import PluginBase
from sdk.plugin_host_context import PluginContext, PluginHostContext
from sdk.register import PluginCapabilityRegistry
from sdk.types import PluginManifestView


OPENAI_TOOL_NAME_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


@dataclass
class PluginLoadResult:
    """单个插件的加载结果。"""

    spec: PluginSpec
    manifest: PluginManifest | None = None
    capabilities: PluginCapabilities | None = None
    error: str | None = None
    loaded: bool = False


@dataclass
class PluginManager:
    """发现、加载、校验并收集插件贡献。"""

    base_dir: Path
    _loaded: list[PluginLoadResult] = field(default_factory=list)
    _plugins: list[PluginBase] = field(default_factory=list)

    def load_from_config(self, tool_registry: ToolRegistry) -> None:
        """兼容旧 SakuraPluginManager 调用：加载并注册插件工具。"""
        self.load_all(tool_registry)

    def load_all(self, tool_registry: ToolRegistry | None = None) -> list[PluginLoadResult]:
        """加载所有启用插件；传入 ToolRegistry 时同步注册工具贡献。"""
        specs = PluginDiscovery(self.base_dir).discover_enabled()
        results: list[PluginLoadResult] = []
        known_tool_names = _tool_names_from_registry(tool_registry)
        for spec in specs:
            result = self._load_one(spec, tool_registry, known_tool_names)
            results.append(result)
            if result.error and spec.required:
                debug_log(
                    "PluginManager",
                    "必需插件加载失败，中止",
                    {"entry": spec.entry, "plugin_id": spec.plugin_id, "error": result.error},
                )
                break
        self._loaded = results
        return results

    def _load_one(
        self,
        spec: PluginSpec,
        tool_registry: ToolRegistry | None,
        known_tool_names: set[str],
    ) -> PluginLoadResult:
        result = PluginLoadResult(spec=spec)
        plugin: PluginBase | None = None
        try:
            _clear_legacy_registered_tools()
            plugin = _import_plugin(self.base_dir, spec)
            manifest = _build_manifest(self.base_dir, plugin, spec)
            result.manifest = manifest

            capability_registry = PluginCapabilityRegistry()
            context = _build_plugin_context(self.base_dir, manifest)
            _initialize_plugin(plugin, capability_registry, context)

            tools = [
                *capability_registry.tools,
                *_consume_legacy_registered_tool_contributions(),
            ]
            _validate_tool_contributions(tools, known_tool_names)

            capabilities = PluginCapabilities(
                plugin_id=manifest.plugin_id,
                tools=list(tools),
                settings_panels=list(capability_registry.settings_panels),
                tools_tabs=list(capability_registry.tools_tabs),
                chat_ui_widgets=list(capability_registry.chat_ui_widgets),
                prompt_patches=list(capability_registry.prompt_patches),
            )
            if tool_registry is not None:
                for contribution in capabilities.tools:
                    tool_registry.register(contribution_to_app_tool(contribution))
                    known_tool_names.add(contribution.name)
            else:
                known_tool_names.update(contribution.name for contribution in capabilities.tools)
            result.capabilities = capabilities
            result.loaded = True
            self._plugins.append(plugin)
            debug_log(
                "PluginManager",
                "插件已加载",
                {
                    "plugin_id": manifest.plugin_id,
                    "tools": len(capabilities.tools),
                    "tools_tabs": len(capabilities.tools_tabs),
                    "settings_panels": len(capabilities.settings_panels),
                    "chat_ui_widgets": len(capabilities.chat_ui_widgets),
                    "prompt_patches": len(capabilities.prompt_patches),
                },
            )
        except Exception as exc:
            result.error = str(exc)
            if plugin is not None:
                _shutdown_quietly(plugin)
            debug_log(
                "PluginManager",
                "插件加载失败",
                {"entry": spec.entry, "plugin_id": spec.plugin_id, "error": str(exc)},
            )
        finally:
            _clear_legacy_registered_tools()
        return result

    def collect_tools(self) -> list[ToolContribution]:
        tools: list[ToolContribution] = []
        for result in self._loaded:
            if result.capabilities:
                tools.extend(result.capabilities.tools)
        return tools

    def collect_settings_panels(self) -> list:
        panels: list = []
        for result in self._loaded:
            if result.capabilities:
                panels.extend(result.capabilities.settings_panels)
        return panels

    def collect_tools_tabs(self) -> list:
        tabs: list = []
        for result in self._loaded:
            if result.capabilities:
                tabs.extend(result.capabilities.tools_tabs)
        return tabs

    def collect_chat_ui_widgets(self) -> list:
        widgets: list = []
        for result in self._loaded:
            if result.capabilities:
                widgets.extend(result.capabilities.chat_ui_widgets)
        return widgets

    def collect_prompt_patches(self) -> list:
        patches: list = []
        for result in self._loaded:
            if result.capabilities:
                patches.extend(result.capabilities.prompt_patches)
        return patches

    @property
    def tools_tabs(self) -> list:
        return self.collect_tools_tabs()

    @property
    def settings_panels(self) -> list:
        return self.collect_settings_panels()

    @property
    def chat_ui_widgets(self) -> list:
        return self.collect_chat_ui_widgets()

    @property
    def prompt_patches(self) -> list:
        return self.collect_prompt_patches()

    def shutdown_all(self) -> None:
        """逆序关闭所有已加载插件。"""
        for plugin in reversed(self._plugins):
            _shutdown_quietly(plugin)

    @property
    def loaded_count(self) -> int:
        return sum(1 for result in self._loaded if result.loaded)

    @property
    def failed_count(self) -> int:
        return sum(1 for result in self._loaded if result.error)

    @property
    def results(self) -> list[PluginLoadResult]:
        return list(self._loaded)


def _tool_names_from_registry(tool_registry: ToolRegistry | None) -> set[str]:
    if tool_registry is None:
        return set()
    return {tool.name for tool in tool_registry.all()}


def _import_plugin(base_dir: Path, spec: PluginSpec) -> PluginBase:
    module_name, _, class_name = spec.entry.partition(":")
    if not module_name or not class_name:
        raise ValueError(f"插件入口格式无效：{spec.entry}")
    module = _import_plugin_module(base_dir, spec, module_name)
    plugin_cls = getattr(module, class_name)
    if not isinstance(plugin_cls, type):
        raise TypeError(f"插件入口不是类：{spec.entry}")
    plugin = plugin_cls()
    if not isinstance(plugin, PluginBase):
        raise TypeError(f"插件入口不是 PluginBase：{spec.entry}")
    return plugin


def _import_plugin_module(base_dir: Path, spec: PluginSpec, module_name: str) -> ModuleType:
    plugin_root = spec.plugin_root
    if plugin_root is not None and not module_name.startswith("plugins."):
        file_module = _module_file_from_relative_entry(plugin_root, module_name)
        if file_module.is_file() and not _is_current_project_root(base_dir):
            return _load_module_from_file(spec.plugin_id or plugin_root.name, module_name, file_module)
        package_module = _package_module_name(plugin_root, module_name)
        if package_module:
            _ensure_sys_path(base_dir)
            try:
                return importlib.import_module(package_module)
            except ModuleNotFoundError:
                pass
        if file_module.is_file():
            return _load_module_from_file(spec.plugin_id or plugin_root.name, module_name, file_module)
    _ensure_sys_path(base_dir)
    return importlib.import_module(module_name)


def _package_module_name(plugin_root: Path, module_name: str) -> str:
    if plugin_root.parent.name != "plugins":
        return ""
    if not (plugin_root.parent / "__init__.py").is_file():
        return ""
    if not (plugin_root / "__init__.py").is_file():
        return ""
    return f"plugins.{plugin_root.name}.{module_name}"


def _module_file_from_relative_entry(plugin_root: Path, module_name: str) -> Path:
    return plugin_root.joinpath(*module_name.split(".")).with_suffix(".py")


def _load_module_from_file(plugin_id: str, module_name: str, module_path: Path) -> ModuleType:
    safe_plugin_id = re.sub(r"[^A-Za-z0-9_]", "_", plugin_id)
    safe_module_name = re.sub(r"[^A-Za-z0-9_]", "_", module_name)
    import_name = f"sakura_user_plugins.{safe_plugin_id}.{safe_module_name}"
    spec = importlib.util.spec_from_file_location(import_name, module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"无法加载插件模块：{module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[import_name] = module
    spec.loader.exec_module(module)
    return module


def _ensure_sys_path(base_dir: Path) -> None:
    path_text = str(base_dir)
    if path_text not in sys.path:
        sys.path.insert(0, path_text)


def _is_current_project_root(base_dir: Path) -> bool:
    try:
        return base_dir.resolve() == Path.cwd().resolve()
    except OSError:
        return False


def _build_manifest(base_dir: Path, plugin: PluginBase, spec: PluginSpec) -> PluginManifest:
    plugin_id = _string_attr(plugin, "plugin_id") or spec.plugin_id
    if not plugin_id:
        raise ValueError(f"插件缺少 plugin_id：{spec.entry}")
    version = _string_attr(plugin, "plugin_version") or spec.version
    plugin_root = spec.plugin_root or _plugin_root_from_entry(base_dir, spec.entry, spec.plugin_id)
    return PluginManifest(
        plugin_id=plugin_id,
        name=spec.name or plugin_id,
        description=spec.description,
        version=version or "0.0.0",
        api_version=spec.api_version,
        priority=spec.priority,
        enabled=spec.enabled,
        required=spec.required,
        entry=spec.entry,
        plugin_root=plugin_root,
    )


def _string_attr(plugin: PluginBase, name: str) -> str:
    value = getattr(plugin, name, "")
    if isinstance(value, str):
        return value.strip()
    return ""


def _build_plugin_context(base_dir: Path, manifest: PluginManifest) -> PluginContext:
    plugin_root = manifest.plugin_root or base_dir / "plugins" / manifest.plugin_id
    data_dir = base_dir / "data" / "plugins" / manifest.plugin_id
    data_dir.mkdir(parents=True, exist_ok=True)
    manifest_view = PluginManifestView(
        plugin_id=manifest.plugin_id,
        name=manifest.name,
        description=manifest.description,
        version=manifest.version,
        api_version=manifest.api_version,
        priority=manifest.priority,
        enabled=manifest.enabled,
        required=manifest.required,
    )
    return PluginContext(
        base_dir=base_dir,
        plugin_root=plugin_root,
        data_dir=data_dir,
        manifest=manifest_view,
    )


def _initialize_plugin(
    plugin: PluginBase,
    register: PluginCapabilityRegistry,
    context: PluginContext,
) -> None:
    initialize = plugin.initialize
    parameter_count = len(inspect.signature(initialize).parameters)
    if parameter_count >= 3:
        initialize(  # type: ignore[misc]
            register,
            context.plugin_root,
            PluginHostContext(base_dir=context.base_dir),
        )
        return
    initialize(register, context)  # type: ignore[misc]


def _validate_tool_contributions(
    tools: list[ToolContribution],
    known_tool_names: set[str],
) -> None:
    local_tool_names: set[str] = set()
    for contribution in tools:
        if not callable(contribution.handler):
            raise ValueError(f"插件工具缺少处理器：{contribution.name}")
        if not OPENAI_TOOL_NAME_RE.fullmatch(contribution.name):
            raise ValueError(f"插件工具名无效：{contribution.name}")
        if contribution.name in known_tool_names or contribution.name in local_tool_names:
            raise ValueError(f"插件工具名重复：{contribution.name}")
        local_tool_names.add(contribution.name)


def _clear_legacy_registered_tools() -> None:
    module = sys.modules.get("sdk.tool_registry")
    clear = getattr(module, "clear_registered_tools", None) if module is not None else None
    if callable(clear):
        clear()


def _consume_legacy_registered_tool_contributions() -> list[ToolContribution]:
    module = sys.modules.get("sdk.tool_registry")
    registered_tools = getattr(module, "registered_tools", None) if module is not None else None
    if not callable(registered_tools):
        return []
    contributions: list[ToolContribution] = []
    for registered in registered_tools():
        parameters = getattr(registered, "parameters", {})
        func = getattr(registered, "func", None)
        contributions.append(
            ToolContribution(
                name=str(getattr(registered, "name", "")),
                description=str(getattr(registered, "description", "")),
                parameters=parameters if isinstance(parameters, dict) else {},
                handler=_legacy_tool_handler(func, parameters if isinstance(parameters, dict) else {}),
                group=str(getattr(registered, "group", "default")),
                risk=str(getattr(registered, "risk", "low")),
                requires_confirmation=bool(getattr(registered, "requires_confirmation", False)),
            )
        )
    _clear_legacy_registered_tools()
    return contributions


def _legacy_tool_handler(func: Any, parameters: dict[str, Any]) -> Any:
    if not callable(func):
        return None

    def handler(arguments: dict[str, Any]) -> Any:
        properties = parameters.get("properties")
        if not isinstance(properties, dict):
            return func(**arguments)
        kwargs = {
            name: arguments[name]
            for name in properties
            if name in arguments
        }
        return func(**kwargs)

    return handler


def _plugin_root_from_entry(base_dir: Path, entry: str, plugin_id: str) -> Path:
    module_name = entry.partition(":")[0]
    parts = module_name.split(".")
    if len(parts) >= 2 and parts[0] == "plugins":
        return base_dir / "plugins" / parts[1]
    if plugin_id:
        return base_dir / "plugins" / plugin_id
    return base_dir / "plugins"


def _shutdown_quietly(plugin: PluginBase) -> None:
    try:
        plugin.shutdown()
    except Exception as exc:
        debug_log(
            "PluginManager",
            "插件关闭失败",
            {"plugin": getattr(plugin, "plugin_id", "unknown"), "error": str(exc)},
        )
