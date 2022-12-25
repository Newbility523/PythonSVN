import re
import shutil
from functools import wraps
import os
import logging

from .svn_core import svn_core


# todo typer 接入
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


class svn(svn_core):
    def __init__(self):
        super(svn_core, self).__init__()

    def same_path(self, svn_path: str, once_cwd: object = None) -> bool:
        """
        检查当前目录是否和指定的svn目录一致
        :param svn_path:
        :param once_cwd:
        :return:
        """
        url, _, _ = self.run_svn_cmd(f"svn info --show-item url")
        return svn_path == url.strip()

    def ensure_dir(self, svn_path: str, path, depth="infinity"):
        '''
        depth 支持的参数('empty', 'files', 'immediates', or 'infinity')
        path checkout到目标目录
        '''
        if os.path.exists(path) and same_path(svn_path, once_cwd=path):
            self.update(once_cwd=path)
        else:
            self.run_svn_cmd(f"svn co --depth={depth} {svn_path} '{path}'")


    @once_cwd_decorator
    def resolve_conflict_auto(self, once_cwd=None):
        output = self.collect_status_info()
        if not self.resolve_conflict(output):
            raise Exception("resolve_conflict_auto failed.")

    def resolve_conflict_prefer(self, accept=ACCEPT_THEIRS_FULL, files=None):
        files_str = self.particular_files_str(files)
        self.run_svn_cmd(f"svn resolve --accept {accept} -R {files_str}")

    def resolve_conflict(self, info):
        tree_conflict_count = len(info['conflict']['tree'])
        log(f"tree conflict: {tree_conflict_count}")
        txt_conflict_count = len(info['conflict']['txt'])
        log(f"txt conflict: {txt_conflict_count}")

        # 优先处理 tree conflict
        if tree_conflict_count > 0:
            count = 0
            for item in info['conflict']['tree']:
                count += 1
                log(f"resolving ({count}/{tree_conflict_count})...")
                self.run_svn_cmd(f"svn revert -R '{item[1]}' --depth infinity")

        if txt_conflict_count > 0:
            log(f"resolving txt conflict together...")
            self.run_svn_cmd("svn resolve -R --accept theirs-full")

        # 重新获取冲突数据，如果仍有冲突残余，视为失败，退出处理
        log("recheck")
        recheck_info = self.collect_status_info()
        if len(recheck_info['conflict']["tree"]) > 0 or len(recheck_info['conflict']["txt"]) > 0:
            log("ERROR:Resolve conflict filed, please resolve manually.")
            return False

        log("recheck success")

        return True

    def clean_unversioned(self):
        self.run_svn_cmd("svn cleanup --remove-unversioned")


if __name__ == '__main__':
    # if not load_cfg_by_file("./config.json"):
    #     log("Error:Load config filed, exit.")
    #     sys.exit()
    #
    # cwd = SVN_WORK_PATH
    # log(collect_status_info())

    # p = r"E:/SvnTest/clients/c1/project1/UI"
    # commit_replace(msg="replace", once_cwd=p)
    # log("中文")
    # # log(os.system("ping www.baidu.com"))
    # p = r"E:\SvnTest\clients\c2\project1\UI\Base"
    # log(os.system(f"svn info \"{p}\""))
    # commit_replace()
    # log("Done.")

    # test 1
    # set_cwd(r"D:\tempCheck\Util")
    # source_path = r"D:\tempCheck\Util"
    # output_path = r"D:\tempCheck\Util2"
    # source_path = source_path.replace("\\", "/").strip("/")
    # output_path = output_path.replace("\\", "/").strip("/")
    #
    # modify = []
    # remove = []
    #
    # diff_dict = diff("base", "head", once_cwd=source_path)
    # modify = diff_dict['modify'] + diff_dict['add']
    # remove = diff_dict['remove']
    #
    # delete_files(remove)
    # test 1 end

    # test 2
    svn = svn()
    svn.set_cwd(r"D:\tempCheck")
    # test_1()
    a = svn.diff(100, 101)
    print(a)
    # test 2 end
    pass
