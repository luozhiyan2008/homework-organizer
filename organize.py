#!/usr/bin/env python3
"""作业文件批量归档脚本 (pdd-03)

用法:
    python organize.py scan <文件夹> [--ext docx,pdf]
    python organize.py rename <文件夹>
    python organize.py archive <文件夹> --name 2025秋
    python organize.py undo <文件夹>
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

LOG_FILE = ".organize_log.json"
REPORT_FILE = "整理报告.txt"


def human_size(num):
    """把字节数转成人类可读的大小，如 1.2KB / 3.4MB"""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if num < 1024:
            return f"{num:.0f}{unit}" if unit == "B" else f"{num:.1f}{unit}"
        num /= 1024
    return f"{num:.1f}PB"


def parse_homework_name(name):
    """解析「学号_姓名_作业名.pdf」-> (学号, 姓名, 作业名)；不符合规则返回 None"""
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


def confirm(question):
    """统一的安全确认：返回 True 才继续执行"""
    return input(question).strip().lower() == "y"


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

    plan = []
    for f in sorted(folder.iterdir()):
        if not f.is_file() or f.name == LOG_FILE:
            continue
        parsed = parse_homework_name(f.name)
        if not parsed:
            continue
        sid, sname, homework = parsed
        plan.append((f, folder / f"{homework}_{sid}{f.suffix}"))

    if not plan:
        print("没有符合「学号_姓名_作业名」命名的文件，无需改名。")
        return

    print("===== 改名计划（尚未执行）=====")
    conflicts = 0
    for old, new in plan:
        tag = ""
        if new.exists():
            tag = "   [跳过: 目标已存在]"
            conflicts += 1
        print(f"  {old.name}  ->  {new.name}{tag}")
    print(f"共 {len(plan)} 项，其中 {conflicts} 项冲突将跳过")

    if not confirm("确认执行改名吗？(y = 执行 / 其他 = 取消): "):
        print("已取消，未做任何修改。")
        return

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


def cmd_archive(args):
    """需求3：按学期/类别把文件移动到子文件夹，生成整理报告，可通过 undo 撤销"""
    folder = Path(args.folder)
    if not folder.is_dir():
        print(f"[错误] {folder} 不是有效的文件夹")
        sys.exit(1)

    target = folder / args.name
    if target.exists() and not target.is_dir():
        print(f"[错误] {target} 已存在且不是文件夹")
        sys.exit(1)

    plan = []
    for f in sorted(folder.iterdir()):
        if not f.is_file() or f.name in (LOG_FILE, REPORT_FILE):
            continue
        plan.append((f, target / f.name))

    if not plan:
        print("没有可归档的文件。")
        return

    print("===== 归档计划（尚未执行）=====")
    print(f"目标子文件夹: {target}")
    conflicts = 0
    for old, new in plan:
        tag = ""
        if new.exists():
            tag = "   [跳过: 目标已存在]"
            conflicts += 1
        print(f"  {old.name}  ->  {args.name}/{new.name}{tag}")
    print(f"共 {len(plan)} 项，其中 {conflicts} 项冲突将跳过")

    if not confirm("确认执行归档吗？(y = 执行 / 其他 = 取消): "):
        print("已取消，未做任何修改。")
        return

    target.mkdir(exist_ok=True)

    batch = {"time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
             "type": "archive", "target": args.name, "actions": []}
    done = skipped = 0
    detail = []
    for old, new in plan:
        if new.exists():
            skipped += 1
            detail.append(f"  - {old.name}（原因: 目标已存在同名文件，为避免覆盖未移动）")
            batch["actions"].append({"src": old.name,
                                     "dst": f"{args.name}/{new.name}", "status": "skipped"})
            continue
        old.rename(new)
        done += 1
        detail.append(f"  - {old.name}（已移动到 {args.name}/）")
        batch["actions"].append({"src": old.name,
                                 "dst": f"{args.name}/{new.name}", "status": "done"})
        print(f"  已归档: {old.name} -> {args.name}/{new.name}")

    log = load_log(folder)
    log["batches"].append(batch)
    save_log(folder, log)

    report = folder / REPORT_FILE
    with open(report, "w", encoding="utf-8") as fp:
        fp.write("=" * 46 + "\n")
        fp.write("            作业文件整理报告\n")
        fp.write("=" * 46 + "\n")
        fp.write(f"时间: {batch['time']}\n")
        fp.write(f"原文件夹: {folder.resolve()}\n")
        fp.write(f"归档目标: {target.resolve()}\n")
        fp.write(f"处理文件: {done} 个（已移动）\n")
        fp.write(f"跳过文件: {skipped} 个\n")
        fp.write("-" * 46 + "\n")
        for line in detail:
            fp.write(line + "\n")
        fp.write("-" * 46 + "\n")
        fp.write("说明: 本报告由 organize.py archive 自动生成。\n")
        fp.write(f"如需撤销本次归档，运行: python organize.py undo {args.folder}\n")

    print(f"完成：归档 {done} 个，跳过 {skipped} 个。")
    print(f"整理报告已生成: {report}")


def cmd_undo(args):
    """需求3：撤销上一次操作（改名或归档），依据日志反向执行"""
    folder = Path(args.folder)
    log = load_log(folder)
    batches = [b for b in log["batches"] if not b.get("undone")]
    if not batches:
        print("没有可撤销的操作。")
        return

    last = batches[-1]
    print("===== 撤销计划（尚未执行）=====")
    print(f"将撤销: {last['time']} 的 {last['type']} 操作，共 {len(last['actions'])} 项")
    for a in last["actions"]:
        if a["status"] == "done":
            print(f"  {a['dst']}  还原为  {a['src']}")
        else:
            print(f"  {a['src']}（当时已跳过，无需处理）")

    if not confirm("确认撤销吗？(y = 撤销 / 其他 = 取消): "):
        print("已取消，未做任何修改。")
        return

    restored = 0
    for a in last["actions"]:
        if a["status"] != "done":
            continue
        dst = folder / a["dst"]
        src = folder / a["src"]
        if dst.exists() and not src.exists():
            dst.rename(src)
            restored += 1
            print(f"  已还原: {a['dst']} -> {a['src']}")
        else:
            print(f"  跳过: {a['dst']}（位置不符合预期，为安全起见不动）")

    last["undone"] = True
    save_log(folder, log)
    print(f"撤销完成: 还原 {restored} 个文件。")


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

    p_archive = sub.add_parser("archive", help="把文件归档到子文件夹并生成整理报告")
    p_archive.add_argument("folder", help="要归档的文件夹路径")
    p_archive.add_argument("--name", default="归档", help="归档子文件夹名，如: 2025秋")
    p_archive.set_defaults(func=cmd_archive)

    p_undo = sub.add_parser("undo", help="撤销上一次操作（依据操作日志）")
    p_undo.add_argument("folder", help="文件夹路径")
    p_undo.set_defaults(func=cmd_undo)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()