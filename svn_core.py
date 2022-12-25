import re
import shutil
import time
from functools import wraps
import os
import logging

import helper

# accept params
ACCEPT_BASE = "base"
ACCEPT_WORKING = "working"
ACCEPT_MINE_CONFLICT = "mine-conflict"
ACCEPT_THEIRS_CONFLICT = "theirs-conflict"
ACCEPT_MINE_FULL = "mine-full"
ACCEPT_THEIRS_FULL = "theirs-full"

def once_cwd_decorator(func):
    @wraps(func)
    def wrapFunction(*args, **kwargs):
        once_cwd = kwargs.get("once_cwd")
        print(func.__name__, "called, once_cwd", once_cwd)
        if once_cwd is not None:
            global working_cwd
            working_cwd = once_cwd
        result = func(*args, **kwargs)
        # outStr, stderr, returnCode = func(*args, **kwargs)
        if once_cwd is not None:
            global cwd
            working_cwd = cwd
        return result

    return wrapFunction


def log(*args):
    global enable_log

    if not enable_log:
        return

    print(args)


class svn_core:
    # svn 账号
    user_name = ""
    # svn 密码
    passwords = ""

    is_dirty = True
    report_cache = None

    cwd = ""
    working_cwd = ""
    enable_log = False

    def __init__(self):
        log_file_path = time.strftime("./logs/log_%Y-%m-%d-%H-%M-%S.log", time.localtime())
        logging.basicConfig(filename=log_file_path, level=logging.DEBUG)
        logging.debug("svn core init success.")

    def set_cwd(self, cwd_str: str) -> None:
        """
        设置工作目录
        """
        self.cwd = cwd_str
        self.working_cwd = cwd

    @once_cwd_decorator
    def get_url(self):
        """
        获取当前目录的svn目录
        """
        url, _, _ = self.run_svn_cmd(f"svn info --show-item url")
        return url.strip()

    def identify(self, user_name: str, passwords: str):
        """
        设置 svn 的账号密码
        :param user_name: 用户名
        :param passwords: 密码
        :return: None
        """
        if user_name is not None:
            self.user_name = user_name

        if passwords is not None:
            self.passwords = passwords

    def particular_files_str(self, files=None):
        """
        不要多次传递files。不要将 particular_files_str 的返回值再作为 particular_files_str 的参数
        """
        files_str = ""
        if files is not None:
            if isinstance(files, str):
                if not files_str.startswith("'") and not files_str.startswith("\""):
                    files_str = "'" + files + "'"
                else:
                    files_str = files
            elif isinstance(files, list):
                for item in files:
                    files_str += ("'" + item + "' ")

        return files_str

    def commit(self, msg=None, once_cwd=None, files=None):
        """
        提交当前所有修改
        :param msg: 提交消息
        :param once_cwd: 本次运行目录
        :param files:
        :return:
        """
        if not helper.is_string(msg):
            raise Exception("commit failed. msg can not empty!")

        if once_cwd is not None:
            self.working_cwd = once_cwd

        files_str = self.particular_files_str(files)

        self.run_svn_cmd(f"svn commit -m \"{msg}\" {files_str}")

        if once_cwd is not None:
            self.working_cwd = self.cwd

    def commit_files(self, msg=None, once_cwd=None, files=None):
        """
        强制提交文件，无视他人修改。
        :param msg: 提交消息
        :param once_cwd: 临时工作目录
        :param files: 文件
            str: 字符串，包含一个或个文件的字符串，注意以空格区分
            list: 文件路径数组，可以绝对路径，或是相对于工作区路径
        :return:
        """
        if not helper.is_string(msg):
            logging.debug("commit msg is empty, exit!")
            return

        if once_cwd is not None:
            self.working_cwd = once_cwd

        files_str = self.particular_files_str(files)
        self.update(files=files)
        self.resolve_conflict_prefer(accept=ACCEPT_WORKING, files=files)

        self.run_svn_cmd(f"svn add {files_str} --force")

        self.commit(msg, files=files)

        if once_cwd is not None:
            self.working_cwd = self.cwd

    def commit_replace(self, msg=None, once_cwd=None):
        """
        完全将指定目录作为版本内容，无视其他人的修改，只以本地为准
        :param msg: 提交信息
        :param once_cwd: 本次命令执行路径
        :return: None
        """

        if not helper.is_string(msg):
            logging.log("commit msg is empty, exit!")
            return

        if once_cwd is not None:
            self.working_cwd = once_cwd

        if not os.path.isdir(self.working_cwd):
            logging.log("working_cwd is invalid, exit!")
            return

        (up_dir, name) = os.path.split(self.working_cwd)
        temp_dir = os.path.join(up_dir, name + "_temp")

        if os.path.isdir(temp_dir):
            shutil.rmtree(temp_dir, True)

        shutil.copytree(self.working_cwd, temp_dir, dirs_exist_ok=False)

        self.update()

        shutil.rmtree(self.working_cwd, True)
        shutil.copytree(temp_dir, self.working_cwd, dirs_exist_ok=False)
        shutil.rmtree(temp_dir, True)

        cur_info = self.collect_status_info()
        self.resolve_conflict_prefer(accept=ACCEPT_WORKING)

        # 所有新增进行确认
        self.run_svn_cmd(f"svn add . --force")
        # 对所有删除进行确认
        if len(cur_info['missing']) > 0:
            for item in cur_info['missing']:
                self.run_svn_cmd(f"svn remove '{item}' --force ")

        self.commit(msg)

        if once_cwd is not None:
            self.working_cwd = self.cwd

    def info(self, path=None, vision=None):
        output = self.run_svn_cmd(f"svn info '{path}'")

    # 检查svn路径是否正确
    def check_path(self, path: str) -> bool:
        """
        path 可以是 working-copy path 或 URL
        """
        out_str, std_err, return_code = self.run_svn_cmd(f"svn info '{path}'")
        if return_code == 0:
            return True

        return False

    def fill_info(self):
        return None

    def repos_url(self) -> str:
        """

        :return:
        """
        output = self.run_svn_cmd(f"svn info --show-item repos-root-url")[0]
        return output

    def author(self, target: str, revision="BASE") -> str:
        if helper.is_string(target):
            output = self.run_svn_cmd(f"svn info '{target}' -r {revision} --show-item last-changed-author")[0]
        else:
            output = self.run_svn_cmd(f"svn info --show-item {revision} revision")[0]

        return output.strip()

    def revision(self, target, once_cwd=None) -> int:
        if once_cwd is not None:
            self.working_cwd = once_cwd

        if helper.is_string(target):
            output = self.run_svn_cmd(f"svn info -r '{target}' --show-item revision")[0]
        else:
            output = self.run_svn_cmd(f"svn info --show-item revision")[0]

        try:
            output = int(output)
        except IndentationError:
            logging.error("Error:Can't get version")
            output = -1
        finally:
            if once_cwd is not None:
                self.working_cwd = self.cwd

        return output

    def diff(self, r_from="base", r_to="head", once_cwd=None):
        if once_cwd is not None:
            self.working_cwd = once_cwd

        output = self.run_svn_cmd(f"svn diff -r {r_from}:{r_to} --summarize")[0]
        pattern = r"\s*?([AMD])\s+?(\S+)"
        result = {
            "modify": [],
            "add": [],
            "remove": [],
        }

        for item in output.splitlines():
            match_item = re.match(pattern, item)
            if match_item is not None:
                if match_item.group(2) != ".":
                    short_tag = match_item.group(1)
                    full_tag = self.get_tag(short_tag)
                    if full_tag is not None:
                        result[full_tag].append(match_item.group(2).replace('\\', '/'))

        if once_cwd is not None:
            self.working_cwd = self.cwd

        return result

    @once_cwd_decorator
    def checkout(self, svn_path: str, depth="infinity", path="", once_cwd=None):
        """
        depth 支持的参数('empty', 'files', 'immediates', or 'infinity')
        path checkout到目标目录
        """
        self.run_svn_cmd(f"svn co --depth={depth} {svn_path} '{path}'")

    @once_cwd_decorator
    def switch(self, svn_path: str, once_cwd=None):
        self.run_svn_cmd(f"svn sw {svn_path}")

    @once_cwd_decorator
    def revert(self, once_cwd=None):
        self.run_svn_cmd("svn revert . -R")

    @once_cwd_decorator
    def update(self, files=None, once_cwd=None):
        """
        更新当前工作区
        :return:
        """
        self.run_svn_cmd("svn cleanup")

        files_str = self.particular_files_str(files)

        # --non-interactive 可取消将可能出现的冲突处理交互请求
        self.run_svn_cmd(f"svn update {files_str}  --non-interactive")
        # run_svn_cmd("svn clean")

    def update_dir(self, dir_path, depth="infinity"):
        # --non-interactive 可取消将可能出现的冲突处理交互请求
        # --parents 用于checkout(path:str, depth="empty")时，父文件夹不存在的情况
        self.run_svn_cmd(f"svn update '{dir_path}' --non-interactive --parents --set-depth {depth}")

    def get_tag(self, info_str):
        temp_tag = info_str[0:1]
        if temp_tag == "!":
            return "missing"
        elif temp_tag == "?":
            return "unversion"
        elif temp_tag == "D":
            return "remove"
        elif temp_tag == "A":
            return "add"
        elif temp_tag == "M":
            return "modify"
        elif temp_tag == "C":
            return "conflict"

        return None

    def collect_status_info(self) -> dict:
        """
        整理 svn 状态，将冲突分为 tree 和 txt，并记录具体冲突类型和路径
        :return:
        dict = {
            "tree": [("conflictType", "conflictPath"), ...],
            ...
        }
        """
        info_dic = {
            'conflict': {
                'tree': [],
                'txt': [],
            },
            'missing': [],
            'unversion': [],
            'remove': [],
            'add': [],
            'modify': [],
        }

        # 树冲突
        tree_conflict_pattern = r"[!ARD](\s+?\+\s+?|\s+?)C\s+?(.*)"
        # 文本冲突
        txt_conflict_pattern = r"C\s+?(.*)"
        # other
        normal_pattern = r"^(\S)\s+(.*)"

        # 暂时不支持管道
        # run_svn_cmd(f"svn st | tee {SVN_STATUS_CACHE_PATH}")
        # file_obj = open(SVN_STATUS_CACHE_PATH, "r")
        # file_list = file_obj.readlines()

        output = self.run_svn_cmd(f"svn st")[0]
        file_list = output.splitlines()
        for line_str in file_list:
            match_item = re.match(tree_conflict_pattern, line_str)
            if match_item is not None:
                # conflict_type = "tree" if conflict_path.find(".") == -1 else "txt"
                info_dic['conflict']["tree"].append((match_item.group(0)[0:1], match_item.group(2).replace('\\', '/')))
            else:
                match_item = re.match(txt_conflict_pattern, line_str)
                if match_item is not None:
                    conflict_path = match_item.group(1)
                    info_dic['conflict']["txt"].append((match_item.group(0)[0:1], conflict_path.replace('\\', '/')))
                else:
                    match_item = re.match(normal_pattern, line_str)
                    if match_item is not None:
                        tag = self.get_tag(match_item.group(0))
                        if tag is not None:
                            info_dic[tag].append(match_item.group(2).replace('\\', '/'))

        return info_dic

    def run_svn_cmd(self, svn_command: str, timeout: int = None) -> object:
        return self.run_cmd(svn_command, timeout=timeout)

    def run_cmd(self, cmd_str, timeout=None):
        return self.commonUtil.run_cmd(cmd_str, timeout, self.working_cwd)


if __name__ == '__main__':
    # test 2
    svn = svn_core()
    svn.set_cwd(r"D:\tempCheck")
    # test_1()
    a = svn.diff(100, 101)
    print(a)
    # test 2 end
    pass
