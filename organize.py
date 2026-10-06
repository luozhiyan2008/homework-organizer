#!/usr/bin/env python3
"""作业文件批量归档脚本 (pdd-03)

用法:
    python organize.py scan <文件夹> [--ext docx,pdf]
    python organize.py rename <文件夹>
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

LOG_FILE = ".organize_log.json"


def human_size(num):
    """把字节数转成人类可读的大小，如 1.2KB / 3.4MB"""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if num < 1024:
            return f"{num:.0f}{unit}" if unit == "B" else f"{num:.1f}{unit}"
        num /= 1024
    return f"{num:.1f}PB"


def parse_homework_name(name):
    """解析「学号_姓名_作业名.pdf」→ (学号, 姓名, 作业名)；不符合规则返回 None"""
    parts = Path(name).stem.split("_")
    if len(parts) < 3:
        return None
    sid, sname = parts[0], parts[1]
    homework = "_".join(parts[2:])
    return sid, sname, homework


def load_log(folder):
    """读取操作日志（用于撤销）"""
    p = Path(folder) / LOG_FILE
    if p.exists():
        with open(p, encoding="utf-8") as fp:
            return json.load(fp)
    return {"batches": []}


def save_log(folder, log):
    p = Path(folder) / LOG_FILE
    with open(p, "w", encoding="utf-8") as fp:
        json.dump(log, fp, ensure_ascii=False, indent=2)


def cmd_scan(args):
    """需求1：扫描文件夹，列出文件的大小与修改时间，支持按扩展名过滤"""
    folder = Path(args.folder)
    if not folder.is_dir():
        print(f"[错误] {folder} 不是有效的文件夹")
        sys.exit(1)

    files = [f for f in folder.iterdir() if f.is_file()]

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


def cmd_rename(args):
    """需求2：按规则批量改名。先打印计划、确认后才执行；目标已存在则跳过，绝不覆盖"""
    folder = Path(args.folder)
    if not folder.is_dir():
        print(f"[错误] {folder} 不是有效的文件夹")
        sys.exit(1)

    # 1) 先收集改名计划：学号_姓名_作业名 -> 作业名_学号
    plan = []
    for f in sorted(folder.iterdir()):
        if not f.is_file() or f.name == LOG_FILE:
            continue
        parsed = parse_homework_name(f.name)
        if not parsed:
            continue  # 不符合命名规则的文件（如 随手记.txt）自动跳过
        sid, sname, homework = parsed
        plan.append((f, folder / f"{homework}_{sid}{f.suffix}"))

    if not plan:
        print("没有符合「学号_姓名_作业名」命名的文件，无需改名。")
        return

    # 2) 先打印计划——此刻还没有动任何文件
    print("===== 改名计划（尚未执行）=====")
    conflicts = 0
    for old, new in plan:
        tag = ""
        if new.exists():
            tag = "   [跳过: 目标已存在]"
            conflicts += 1
        print(f"  {old.name}  ->  {new.name}{tag}")
    print(f"共 {len(plan)} 项，其中 {conflicts} 项冲突将跳过")

    # 3) 确认后才真的执行
    answer = input("确认执行改名吗？(y = 执行 / 其他 = 取消): ").strip().lower()
    if answer != "y":
        print("已取消，未做任何修改。")
        return

    # 4) 执行并写日志（供需求3的撤销使用）
    batch = {"time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
             "type": "rename", "actions": []}
    done = skipped = 0
    for old, new in plan:
        if new.exists():
            skipped += 1
            batch["actions"].append({"src": old.name, "dst": new.name, "status": "skipped"})
            continue
        old.rename(new)
        done += 1
        batch["actions"].append({"src": old.name, "dst": new.name, "status": "done"})
        print(f"  已改名: {old.name} -> {new.name}")

    log = load_log(folder)
    log["batches"].append(batch)
    save_log(folder, log)
    print(f"完成：改名 {done} 个，跳过 {skipped} 个（绝不覆盖已有文件）。")


def main():
    parser = argparse.ArgumentParser(description="作业文件批量归档脚本")
    sub = parser.add_subparsers(dest="command", required=True)

    p_scan = sub.add_parser("scan", help="扫描文件夹并列出文件")
    p_scan.add_argument("folder", help="要扫描的文件夹路径")
    p_scan.add_argument("--ext", default="", help="按扩展名过滤，如: docx,pdf")
    p_scan.set_defaults(func=cmd_scan)

    p_rename = sub.add_parser("rename", help="按「学号_姓名_作业名」->「作业名_学号」批量改名")
    p_rename.add_argument("folder", help="要改名的文件夹路径")
    p_rename.set_defaults(func=cmd_rename)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()