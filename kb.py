#!/usr/bin/env python3
"""DevOps & Infra 知识库 — CLI 入口"""

import argparse
import sys
from pathlib import Path

# 确保项目根目录在 Python path 中
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

# Windows 下强制 UTF-8 输出，避免 ✓ 等字符的编码错误
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def cmd_init() -> int:
    """初始化知识库目录结构。"""
    from engine.config import get_project_root
    root = get_project_root()
    from engine.indexer import init_index, init_log
    from engine.skill_gen import generate_meta_skills

    dirs = [
        root / "raw",
        root / "wiki" / "infra-daily",
        root / "wiki" / "infra-violation",
        root / "wiki" / "automation",
        root / "wiki" / "harbor",
        root / "schema",
        root / "skills",
        root / "web" / "routes",
        root / "web" / "templates",
        root / "web" / "static",
        root / "tests",
    ]

    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
        if not any(d.iterdir()):
            (d / ".gitkeep").touch()

    print("✓ 目录结构已创建")

    init_index()
    print("✓ wiki/index.md 已创建")

    init_log()
    print("✓ wiki/log.md 已创建")

    paths = generate_meta_skills()
    for p in paths:
        print(f"✓ skills/{p.name} 已创建")

    print(f"\n知识库初始化完成！")
    print(f"项目路径: {root}")
    print(f"\n下一步:")
    print(f"  1. 配置 LLM API Key（编辑 .env 文件）")
    print(f"  2. 上传原始文件到 raw/")
    print(f"  3. python kb.py ingest raw/<文件名>")
    print(f"  4. python kb.py serve")

    return 0


def cmd_ingest(args) -> int:
    """导入知识。"""
    from engine.config import get_project_root

    raw_path = Path(args.file)
    if not raw_path.exists():
        print(f"错误: 文件不存在 — {args.file}")
        return 1

    root = get_project_root()
    raw_dir = root / "raw"
    if not str(raw_path.resolve()).startswith(str(root.resolve())):
        import shutil
        dest = raw_dir / raw_path.name
        shutil.copy2(raw_path, dest)
        raw_path = dest
        print(f"已复制到 raw/: {raw_path.name}")

    print("正在处理...")
    print("注意: 当前版本需要 LLM 先整理内容。")
    print("请通过 kb-ingest skill 在 LLM 环境中完成导入。")
    print(f"源文件已就绪: {raw_path.relative_to(root)}")

    return 0


def cmd_search(args) -> int:
    """搜索知识库。"""
    from engine.search import search_as_json

    result = search_as_json(args.query, args.category)
    print(result)
    return 0


def cmd_check(args) -> int:
    """运行健康检查。"""
    from engine.quality import check_all, check_summary

    if args.id:
        from engine.config import get_project_root
        from engine.quality import check_entry

        root = get_project_root()
        found = None
        for cat_dir in (root / "wiki").iterdir():
            if cat_dir.is_dir():
                candidate = cat_dir / f"{args.id}.md"
                if candidate.exists():
                    found = candidate
                    break

        if not found:
            print(f"错误: 未找到知识条目 — {args.id}")
            return 1

        result = check_entry(found)
        print(check_summary([result]))
    else:
        results = check_all(args.category)
        print(check_summary(results))

    return 0


def cmd_serve(args) -> int:
    """启动 Web 服务。"""
    import uvicorn
    from engine.config import get_web_config

    web_config = get_web_config()
    host = args.host or web_config.get("host", "0.0.0.0")
    port = args.port or web_config.get("port", 8000)

    print(f"启动 Web 服务: http://{host}:{port}")
    uvicorn.run(
        "web.app:app",
        host=host,
        port=port,
        reload=True,
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="kb.py",
        description="DevOps & Infra 知识库管理工具",
    )
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    subparsers.add_parser("init", help="初始化知识库目录结构")

    ingest_parser = subparsers.add_parser("ingest", help="导入知识")
    ingest_parser.add_argument("file", help="原始文件路径")

    search_parser = subparsers.add_parser("search", help="搜索知识")
    search_parser.add_argument("query", help="搜索关键词")
    search_parser.add_argument("--category", "-c", help="限定分类")

    check_parser = subparsers.add_parser("check", help="健康检查")
    check_parser.add_argument("--id", help="检查指定 ID")
    check_parser.add_argument("--category", "-c", help="检查指定分类")

    serve_parser = subparsers.add_parser("serve", help="启动 Web 服务")
    serve_parser.add_argument("--host", help="主机地址")
    serve_parser.add_argument("--port", type=int, help="端口")

    args = parser.parse_args()

    if args.command == "init":
        return cmd_init()
    elif args.command == "ingest":
        return cmd_ingest(args)
    elif args.command == "search":
        return cmd_search(args)
    elif args.command == "check":
        return cmd_check(args)
    elif args.command == "serve":
        return cmd_serve(args)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
