# This is a sample Python script.

# Press ⌃R to execute it or replace it with your code.
# Press Double ⇧ to search everywhere for classes, files, tool windows, actions, and settings.
import io
import json
import platform
import re
import os
import subprocess
import sys
import types

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
# svn 账号
USER_NAME = ""
# svn 密码
PASSWORD = ""

is_dirty = True
report_cache = None


def report():
    global is_dirty
    is_dirty = False

    return report_cache


def update_identify(user_name, password):
    global USER_NAME
    USER_NAME = user_name
    global PASSWORD
    PASSWORD = password


def output_report():
    global is_dirty
    if is_dirty:
        report()

    if report_cache is None:
        print("Nothing output")


def is_string(content):
    if content is None:
        return False

    if len(content) == 0:
        return False

    return not content.isspace()


def commit(msg):
    if not is_string(msg):
        print("commit msg is empty, exit.")
        return

    run_svn_cmd(f"svn ci -m {msg}")


def info(path=None, vision=None):
    output = run_svn_cmd(f"svn info {path}")


def fill_info(content):
    return None


def revision(target):
    output = -1
    if is_string(target):
        output = run_svn_cmd(f"svn info -r {target} --show-item revision")
    else:
        output = run_svn_cmd(f"svn info --show-item revision")

    try:
        output = int(output)
    except IndentationError:
        print("Error:Can't get version")
        output = -1
    finally:
        return output


def diff(r_from="base", r_to="head"):
    output = run_cmd(f"svn diff -r {r_from}:{r_to} --summarize")
    pattern = r"\s*?([AMD])\s+?(\S+)"
    result = {
        "M": [],
        "A": [],
        "D": [],
    }

    for item in output.splitlines():
        match_item = re.match(pattern, item)
        if match_item is not None:
            if match_item.group(2) != ".":
                tag = match_item.group(1)
                result[tag].append(match_item.group(2))

    print(result)
    return result


def revert():
    run_cmd("svn revert . -R")


def update():
    run_cmd("svn up")
    # run_cmd("svn clean")

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
    tree_conflict_pattern = r"[AD](\s+?\+\s+?|\s+?)C\s+?(\S+)"
    # 文本冲突
    txt_conflict_pattern = r"C\s+?(\S+)"

    # 暂时不支持管道
    # run_cmd(f"svn st | tee {SVN_STATUS_CACHE_PATH}")
    # file_obj = open(SVN_STATUS_CACHE_PATH, "r")
    # file_list = file_obj.readlines()

    output = run_cmd(f"svn st")
    file_list = output.splitlines()
    for line_str in file_list:
        match_item = re.match(tree_conflict_pattern, line_str)
        if match_item is not None:
            # conflict_type = "tree" if conflict_path.find(".") == -1 else "txt"
            info_dic["tree"].append((match_item.group(0)[0:1], match_item.group(2)))
        else:
            match_item = re.match(txt_conflict_pattern, line_str)
            if match_item is not None:
                conflict_path = match_item.group(1)
                info_dic["txt"].append((match_item.group(0)[0:1], conflict_path))

    return info_dic


def resolve_conflict(info):
    # 优先处理 tree conflict
    tree_conflict_count = len(info['tree'])
    if tree_conflict_count > 0:
        print(f"tree conflict: {tree_conflict_count}")
        count = 0
        for item in info['tree']:
            count += 1
            print(f"resolving ({count}/{tree_conflict_count})...")
            run_cmd(f"svn revert -R {item[1]}")

    txt_conflict_count = len(info['txt'])
    if txt_conflict_count > 0:
        print(f"txt conflict: {txt_conflict_count}")
        print(f"resolving txt conflict together...")
        run_cmd("svn resolve -R --accept theirs-full")

    # 重新获取冲突数据，如果仍有冲突残余，视为失败，退出处理
    print("recheck")
    recheck_info = collect_status_info()
    if len(recheck_info["tree"]) > 0 or len(recheck_info["txt"]) > 0:
        print("ERROR:Resolve conflict filed, please resolve manually.")
        return False

    print("recheck success")

    return True


def run_svn_cmd(svn_command):
    return run_cmd(svn_command)


def run_cmd(cmd_str):
    print(f"running cmd:{cmd_str}")
    pipe = subprocess.Popen(
        cmd_str,
        shell=False,
        stdout=subprocess.PIPE,
        cwd=SVN_WORK_PATH,
    )

    c1, c2 = None, None
    try:
        c1, c2 = pipe.communicate(timeout=20)
    except subprocess.TimeoutExpired:
        print("Exception:Command timeout, Kill.")
        pipe.kill()
    finally:
        c1, c2 = pipe.communicate()
        is_win = platform.system() == "Windows"
        return c1.decode(encoding=("gbk" if is_win else "utf8"))


def load_cfg_by_dic(params):
    if params is None:
        return False

    global BATCH_PATH
    BATCH_PATH = params["BATCH_PATH"]

    global CACHE_DIR
    CACHE_DIR = params["CACHE_DIR"]

    global SVN_WORK_PATH
    SVN_WORK_PATH = params["SVN_WORK_PATH"]

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
        # 'SVN_STATUS_CACHE_PATH': SVN_STATUS_CACHE_PATH,
        'SVN_WORK_PATH': SVN_WORK_PATH,
    }

    for k, v in cfg_dic.items():
        if not os.path.exists(v):
            result = False
            print("cfg.{key} = {value} is not exists, please check.".format(key=k, value=v))

    return result


def generate_todoabname():
    diff_dic = diff()
    content = ""
    for item in diff_dic["A"]:
        p = item.replace("\\", "/")
        content = content + f"{p}\n"

    fo = open(os.path.join(SVN_WORK_PATH, "ToDoABName.txt"), "w")
    fo.write(content)
    fo.flush()
    fo.close()


def init(params):
    if params is None:
        print("Error:Init failed.")
        return

    if type(params) is dict:
        load_cfg_by_dic(params)
    elif type(params) is str:
        load_cfg_by_file(params)
    else:
        print("Error:Init failed.")
        return


if __name__ == '__main__':
    if not load_cfg_by_file("./config.json"):
        print("Error:Load config filed, exit.")
        sys.exit()

    # generate_todoabname()

    update()
    output = collect_status_info()

    if not resolve_conflict(output):
        sys.exit()

    print("Done.")





