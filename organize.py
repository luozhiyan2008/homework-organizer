#!/usr/bin/env python3
"""作业文件批量归档脚本 (pdd-03)

用法:
    python organize.py scan <文件夹> [--ext docx,pdf]
"""
import argparse
import sys
from datetime import datetime
from pathlib import Path


def human_size(num):
    """把字节数转成人类可读的大小，如 1.2KB / 3.4MB"""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if num < 1024:
            return f"{num:.0f}{unit}" if unit == "B" else f"{num:.1f}{unit}"
        num /= 1024
    return f"{num:.1f}PB"


def cmd_scan(args):
    """需求1：扫描文件夹，列出文件的大小与修改时间，支持按扩展名过滤"""
    folder = Path(args.folder)
    if not folder.is_dir():
        print(f"[错误] {folder} 不是有效的文件夹")
        sys.exit(1)

    files = [f for f in folder.iterdir() if f.is_file()]

    # 按扩展名过滤（--ext docx,pdf）
    if args.ext:
        wanted = {e.strip().lstrip(".").lower() for e in args.ext.split(",") if e.strip()}
        files = [f for f in files if f.suffix.lstrip(".").lower() in wanted]

    files.sort(key=lambda f: f.name)

    print(f"扫描文件夹: {folder.resolve()}")
    if args.ext:
        print(f"扩展名过滤: {args.ext}")
    print(f"符合条件: {len(files)} 个文件")
    print("-" * 70)
    for f in files:
        st = f.stat()
        mtime = datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M")
        print(f"  {f.name}  |  {human_size(st.st_size):>8}  |  {mtime}")
    print("-" * 70)
    if not files:
        print("  (没有匹配的文件)")


def main():
    parser = argparse.ArgumentParser(description="作业文件批量归档脚本")
    sub = parser.add_subparsers(dest="command", required=True)

    # 子命令 scan
    p_scan = sub.add_parser("scan", help="扫描文件夹并列出文件")
    p_scan.add_argument("folder", help="要扫描的文件夹路径")
    p_scan.add_argument("--ext", default="", help="按扩展名过滤，如: docx,pdf")
    p_scan.set_defaults(func=cmd_scan)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()