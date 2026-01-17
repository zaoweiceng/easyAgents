#!/usr/bin/env python3
"""
easyAgent API服务启动脚本
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import uvicorn

def main():
    """启动API服务"""
    print("=" * 70)
    print("easyAgent API服务启动脚本")
    print("=" * 70)

    # 检查环境
    try:
        import fastapi
        import uvicorn
        print(f"\n✓ FastAPI版本: {fastapi.__version__}")
        print(f"✓ Uvicorn版本: {uvicorn.__version__}")
    except ImportError as e:
        print(f"\n✗ 缺少依赖: {e}")
        print("\n请先安装依赖:")
        print("  pip install -r requirements_api.txt")
        return 1

    print("\n" + "=" * 70)
    print("启动选项:")
    print("=" * 70)
    print("1. 开发模式 (自动重载)")
    print("2. 生产模式 (不重载)")
    print("3. 自定义端口")

    choice = input("\n请选择 (1-3，默认1): ").strip() or "1"

    if choice == "1":
        # 开发模式
        host = "0.0.0.0"
        port = 8000
        reload = True
        print(f"\n启动开发模式: http://{host}:{port}")
        print("API文档: http://localhost:8000/docs")
        print("\n按 Ctrl+C 停止服务器\n")

    elif choice == "2":
        # 生产模式
        host = "0.0.0.0"
        port = 8000
        reload = False
        workers = 4
        print(f"\n启动生产模式: http://{host}:{port}")
        print("使用 {workers} 个worker进程\n")

    elif choice == "3":
        # 自定义端口
        host = input("主机地址 (默认0.0.0.0): ").strip() or "0.0.0.0"
        port = int(input("端口号 (默认8000): ").strip() or "8000")
        reload = True
        print(f"\n启动自定义配置: http://{host}:{port}")
        print("API文档: http://localhost:{port}/docs\n")

    else:
        print("无效选择，使用默认配置")
        host = "0.0.0.0"
        port = 8000
        reload = True

    print("=" * 70)

    try:
        if choice == "2":
            # 生产模式
            uvicorn.run(
                "api.server:app",
                host=host,
                port=port,
                workers=workers,
                log_level="info",
                access_log=True
            )
        else:
            # 开发模式或自定义
            uvicorn.run(
                "api.server:app",
                host=host,
                port=port,
                reload=reload,
                log_level="info"
            )
    except KeyboardInterrupt:
        print("\n\n服务已停止")
    except Exception as e:
        print(f"\n启动失败: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
