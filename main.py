# This is a sample Python script.

# Press ⌃R to execute it or replace it with your code.
# Press Double ⇧ to search everywhere for classes, files, tool windows, actions, and settings.
import re
import os

global_batchPath = "/ect/bin/bash"
global_workDir = "abc/abc1"
tempFilePath = os.path.join(global_workDir, "log.txt")

print("tempFilePath:" + tempFilePath)
def print_hi(name):
    # Use a breakpoint in the code line below to debug your script.
    print(f'Hi, {name}')  # Press ⌘F8 to toggle the breakpoint.
    str = "hello world!, 2l" \
          "abllo" \
          "loogb"
    output = re.search("(\S)l", str)
    print(output)
    print(output.group())
    print(output.group(1))
    print(len(output.groups()))

def update(svnPath):
    if not os.path.exists(svnPath):
        print(f"svnPath: {svnPath} is not exists, exit.")

    os.chdir(svnPath)
    run_cmd("svn up")
    run_cmd("svn clean")

def collect_status_info():
    run_cmd(f"svn st | tee {tempFilePath}")
    infoDic = {
        'dir':"",
        'tree':{},
        'txt':{},
    }
    # todo

    return infoDic

def resolve_conflict(info):
    # 优先处理 tree conflict
    if len(info['tree']) > 0:
        for k, v in info['tree'].items():
            run_cmd(f"svn revert -R {v}")
    elif len(info['txt']) > 0:
        run_cmd("svn resolve -R --accept theirs-full")

    # recheck
    if collect_status_info(info.dir) != None:
        print("ERROR:Resolve conflict filed, please resolve manually.")
        return

    return

def run_cmd(cmdStr):
    osCmd = "{bashPath} -c {cmd}".format(bashPath=global_batchPath, cmd=cmdStr)
    print("running:" + osCmd)

def load_cfg():
    cfgDic = {
        'global_batchPath':global_batchPath,
        'global_workDir':global_workDir,
        'tempFilePath': tempFilePath,
    }

    result = True
    for k, v in cfgDic.items():
        if not os.path.exists(v):
            result = False
            print("cfg.{key} = {value} is not exists, please check.".format(key = k, value = v))

    return result

# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    if load_cfg():
        print_hi('PyCharm')
        run_cmd("grep -ho 'abc' *")
