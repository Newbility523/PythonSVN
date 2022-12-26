import shutil
from functools import wraps
import os
import logging
import helper
from .svn_core import svn_core

# todo typer 接入
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
        """
        depth 支持的参数('empty', 'files', 'immediates', or 'infinity')
        path checkout到目标目录
        """
        if os.path.exists(path) and self.same_path(svn_path, once_cwd=path):
            self.update(once_cwd=path)
        else:
            self.run_svn_cmd(f"svn co --depth={depth} {svn_path} '{path}'")

    @svn_core.once_cwd_decorator
    def resolve_conflict_auto(self, once_cwd=None):
        output = self.collect_status_info()
        if not self.resolve_conflict(output):
            raise Exception("resolve_conflict_auto failed.")

    def resolve_conflict_prefer(self, accept=svn_core.ACCEPT_THEIRS_FULL, files=None):
        files_str = self.particular_files_str(files)
        self.run_svn_cmd(f"svn resolve --accept {accept} -R {files_str}")

    def resolve_conflict(self, info):
        tree_conflict_count = len(info['conflict']['tree'])
        logging.debug(f"tree conflict: {tree_conflict_count}")
        txt_conflict_count = len(info['conflict']['txt'])
        logging.debug(f"txt conflict: {txt_conflict_count}")

        # 优先处理 tree conflict
        if tree_conflict_count > 0:
            count = 0
            for item in info['conflict']['tree']:
                count += 1
                logging.log(level=1, msg=f"resolving ({count}/{tree_conflict_count})...")
                self.run_svn_cmd(f"svn revert -R '{item[1]}' --depth infinity")

        if txt_conflict_count > 0:
            logging.log(level=1, msg=f"resolving txt conflict together...")
            self.run_svn_cmd("svn resolve -R --accept theirs-full")

        # 重新获取冲突数据，如果仍有冲突残余，视为失败，退出处理
        logging.log(level=1, msg="recheck")
        recheck_info = self.collect_status_info()
        if len(recheck_info['conflict']["tree"]) > 0 or len(recheck_info['conflict']["txt"]) > 0:
            logging.error("ERROR:Resolve conflict filed, please resolve manually.")
            return False

        logging.log(level=1, msg="recheck success")

        return True

    def clean_unversioned(self):
        self.run_svn_cmd("svn cleanup --remove-unversioned")

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
        self.resolve_conflict_prefer(accept=svn_core.ACCEPT_WORKING)

        # 所有新增进行确认
        self.run_svn_cmd(f"svn add . --force")
        # 对所有删除进行确认
        if len(cur_info['missing']) > 0:
            for item in cur_info['missing']:
                self.run_svn_cmd(f"svn remove '{item}' --force ")

        self.commit(msg)

        if once_cwd is not None:
            self.working_cwd = self.cwd

    def commit_files(self, msg: str = None, once_cwd: str = None, files: list = None):
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
        self.resolve_conflict_prefer(accept=svn_core.ACCEPT_WORKING, files=files)

        self.run_svn_cmd(f"svn add {files_str} --force")

        self.commit(msg, files=files)

        if once_cwd is not None:
            self.working_cwd = self.cwd


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
