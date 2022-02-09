# This is a sample Python script.

# Press ⌃R to execute it or replace it with your code.
# Press Double ⇧ to search everywhere for classes, files, tool windows, actions, and settings.
import io
import json
import re
import os
import sys

# bash Shell 可执行路径
BATCH_PATH = ""
# 当前工具可用于缓存数据的目录
CACHE_DIR = ""
# svn 状态路径目录
SVN_STATUS_CACHE_PATH = ""
# 汇总报告路径
REPORT_PATH = ""
# svn 工作目录，即需要处理的项目路径
SVN_WORK_PATH = ""

print("tempFilePath:" + SVN_STATUS_CACHE_PATH)

is_dirty = True
report_cache = None


def report():
    global is_dirty
    is_dirty = False

    return report_cache


def output_report():
    global is_dirty
    if is_dirty:
        report()

    if report_cache is None:
        print("Nothing output")


def update():
    run_cmd("svn up")
    run_cmd("svn clean")

    global is_dirty
    is_dirty = True


def collect_status_info() -> dict:
    """
    整理 svn 状态，将冲突分为 tree 和 txt，并记录具体冲突类型和路径
    :return:
    dict = {
        "tree": [("conflictType", "conflictPath"), ...],
        ...
    }
    """
    info_dic = {
        'tree': [],
        'txt': [],
    }

    # 树冲突
    tree_conflict_pattern = r"[AD]\s+?\+\s*?C\s+?(\S+)"
    # 文本冲突
    txt_conflict_pattern = r"C\s+?(\S+)"

    run_cmd(f"svn st | tee {SVN_STATUS_CACHE_PATH}")

    file_obj = open(SVN_STATUS_CACHE_PATH, "r")
    file_list = file_obj.readlines()
    for line_str in file_list:
        match_item = re.match(tree_conflict_pattern, line_str)
        if match_item is not None:
            conflict_path = match_item.group(1)
            conflict_type = "tree" if conflict_path.find(".") == -1 else "txt"
            info_dic[conflict_type].append((match_item[0:1], conflict_path))
        else:
            match_item = re.match(txt_conflict_pattern, line_str)
            if match_item is not None:
                conflict_path = match_item.group(1)
                info_dic["txt"].append((match_item[0:1], conflict_path))

    return info_dic


def resolve_conflict(info):
    # 优先处理 tree conflict
    if len(info['tree']) > 0:
        for k, v in info['tree'].items():
            run_cmd(f"svn revert -R {v}")

    if len(info['txt']) > 0:
        run_cmd("svn resolve -R --accept theirs-full")

    # 重新获取冲突数据，如果仍有冲突残余，视为失败，退出处理
    recheck_info = collect_status_info()
    if len(recheck_info["tree"]) > 0 or len(recheck_info["txt"]) > 0:
        print("ERROR:Resolve conflict filed, please resolve manually.")
        return False

    return True


def run_cmd(cmd_str):
    os_cmd = f"{BATCH_PATH} -c {cmd_str}"
    print("running:" + os_cmd)


def load_cfg_by_dic(params):
    if params is None:
        return False

    global BATCH_PATH
    BATCH_PATH = params["BATCH_PATH"]

    global CACHE_DIR
    CACHE_DIR = params["CACHE_DIR"]

    global SVN_STATUS_CACHE_PATH
    SVN_STATUS_CACHE_PATH = os.path.join(CACHE_DIR, params["SVN_STATUS_FILE_NAME"])

    global REPORT_PATH
    REPORT_PATH = os.path.join(CACHE_DIR, params["REPORT_FILE_NAME"])

    return check_cfg()


def load_cfg_by_file(cfg_path):
    if not os.path.exists(cfg_path):
        cfg_path = "./config.txt"

    if not os.path.exists(cfg_path):
        return False

    cfg_file = open(cfg_path, "r")
    cfg_dic = json.loads(cfg_file.read())

    return load_cfg_by_dic(cfg_dic)


def check_cfg():
    result = True

    cfg_dic = {
        'BATCH_PATH': BATCH_PATH,
        'CACHE_DIR': CACHE_DIR,
        'SVN_STATUS_CACHE_PATH': SVN_STATUS_CACHE_PATH,
        'SVN_WORK_DIR': SVN_WORK_PATH,
    }

    for k, v in cfg_dic.items():
        if not os.path.exists(v):
            result = False
            print("cfg.{key} = {value} is not exists, please check.".format(key=k, value=v))

    return result


if __name__ == '__main__':
    if not load_cfg_by_file("./config.json"):
        print("Error:Load config filed, exit.")
        sys.exit()

    os.chdir(SVN_WORK_PATH)
    update()
    collect_status_info()

    if not resolve_conflict():
        sys.exit()

    out_put()