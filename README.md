```
automation-platform/
├─ README.md
├─ pyproject.toml                 # 统一依赖与打包（也可 requirements.txt）
├─ docker/
│  ├─ Dockerfile
│  └─ docker-compose.yml          # 后端 + postgres + redis（后面用）
├─ backend/
│  ├─ app/
│  │  ├─ main.py                  # FastAPI 入口
│  │  ├─ core/
│  │  │  ├─ config.py             # 环境变量/配置
│  │  │  └─ logging.py            # 日志配置
│  │  ├─ api/
│  │  │  ├─ health.py             # /health
│  │  │  └─ scripts.py            # /scripts /runs API
│  │  ├─ schemas/
│  │  │  ├─ script.py             # Pydantic：Script、Run
│  │  │  └─ common.py
│  │  ├─ services/
│  │  │  ├─ registry.py           # 脚本注册表：列出有哪些脚本
│  │  │  └─ runner.py             # 运行器：启动/停止/查询状态
│  │  └─ storage/
│  │     └─ state_store.py         # 状态存储（先用内存，后面换 Redis）
│  └─ tests/
│     └─ test_health.py
├─ scripts/                       # ✅ “自动化脚本仓库”
│  ├─ README.md
│  ├─ examples/
│  │  ├─ hello_sleep.py            # 示例脚本：跑 5 秒输出日志
│  │  └─ capture_demo.py           # 示例：截图/识别（可选）
│  └─ coc/
│     ├─ __init__.py
│     └─ builder_base_attack.py    # 真实的自动化入口（后续搬进来）
├─ script_specs/                  # ✅ 脚本“登记信息”（配置驱动）
│  ├─ hello_sleep.yaml
│  └─ coc_builder_base_attack.yaml
└─ run_local.sh                   # 一键本地启动（可选）
```

```angular2html
┌───────────────┐
│   Client      │  浏览器 / curl / 前端 / HR 点域名
└──────┬────────┘
       │ HTTP
┌──────▼────────┐
│   app/api     │  
│ (路由层)       │
└──────┬────────┘
       │ Python 函数调用
┌──────▼────────┐
│ app/services  │  业务逻辑（跑脚本 / 管理状态）
└──────┬────────┘
       │
┌──────▼────────┐
│ app/storage   │  状态存储（内存 / Redis）
└───────────────┘
```