# app/core/builder/ — 应用装配层
#
# 本包负责将 Sakura 的各组件装配为可运行的 AppContext。
# 分为三个职责：
# - app_builder.py: 声明式装配 (AppBuilder)
# - service_container.py: 依赖容器 (ServiceContainer)
# - lifecycle.py: 启动/关闭生命周期管理
