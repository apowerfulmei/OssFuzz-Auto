# 漏洞复现
import os
import subprocess
from collections import defaultdict
from datetime import datetime
import subprocess
import re
from tools.logger import logger






def get_git_log(repo_path):
    """
    获取指定仓库的git log信息。
    """
    try:
        # 获取所有提交的哈希和时间
        result = subprocess.run(['git', 'log', '--format=%H %ci'], cwd=repo_path, check=True, capture_output=True, text=True)
        return result.stdout.strip().split('\n')
    except subprocess.CalledProcessError as e:
        print(f'Error: {e}')
        return []

def parse_git_log(log_entries, flag):
    """
    解析git log输出，提取每个提交的哈希和时间。
    """
    oss_fuzz_map=defaultdict(dict)
    for entry in log_entries:
        commit_hash, commit_time = entry.split(maxsplit=1)
        commit_time = datetime.strptime(commit_time.split()[0], '%Y-%m-%d')
        #print(commit_hash,"xxx",commit_time)
        year_month = commit_time.strftime('%Y-%m-%d')
        #print(year_month)
        if flag==1:
            if not oss_fuzz_map[year_month] or commit_time > datetime.strptime(str(oss_fuzz_map[year_month][1]).split()[0], '%Y-%m-%d'):
                oss_fuzz_map[year_month] = (commit_hash, commit_time)
        else :
            oss_fuzz_map[commit_hash]=year_month
        # print(oss_fuzz_map)
        # x=input()
    # return {year_month: commit[0] for year_month, commit in oss_fuzz_map.items()}
    return oss_fuzz_map


def find_suite_commit(commit, time_map, commit_map):
    time=commit_map[commit]
    logger.debug(f"This is time: {time}")
    if time_map[time]:
        logger.debug(f"Find the suite commit: time_map[time][0]")
        return time_map[time][0]
    else :
        # 找到最近的时间，从最大到最小遍历所有时间，找到第一个比当前时间小的时间
        for key in sorted(time_map.keys(),reverse=True):
            if key < time:
                logger.debug(f"Find the suite commit: time_map[time][0]")
                return time_map[key][0]


def run_command(command):
    logger.debug(f"run command: {command}")
    message=""
    try:
        result = subprocess.run(command, timeout=25, check=True, capture_output=True, text=True, shell=True)
        message+=result.stdout
        message+=result.stderr
    except subprocess.TimeoutExpired as e:
        message+=f'命令超时: {e}'
        message+=str(e.stdout)
        message+=str(e.stderr)
    except subprocess.CalledProcessError as e:
        message+=f'命令执行失败: {e}'
        message+=e.stdout
        message+=e.stderr
    except Exception as e:
        message+=f'发生错误: {e}'
        message+=e.stdout
        message+=e.stderr
    return message

def reproduce_once(commit, fuzz_commit, detail, bug_name, testcase_dir, work_dir):
    result={"build":False,"reproduce":False}
    workdir=f"rep_{bug_name}"
    project_name=detail['project']
    # 如果fuzz_engine字段为空，则默认为libfuzzer
    fuzz_engine=detail['fuzzing_engine'] if detail['fuzzing_engine'] else 'libfuzzer'
    fuzz_target=detail['fuzz_target']
    sanitizer=detail['sanitizer']
    logger.debug(f"fuzz_target: {testcase_dir}")
    testcase=f"{testcase_dir}/testcase-{bug_name}"
    print("testcase path:",testcase)
    logger.debug(f"testcase: {testcase}")
    origin_dir = os.getcwd()
    os.chdir(work_dir)

    # 下载源码
    if os.path.exists(f"./{project_name}"):
        #使用git clone下载
        os.system(f"echo 'TDQ530' | sudo -S rm -rf ./{project_name}")
        #os.system(f"git clone {git_url}")
    os.system(f"cp -r ../{project_name} ./")
    if os.path.exists(f"./oss-fuzz"):
        os.system(f"echo 'TDQ530' | sudo -S  rm -rf ./oss-fuzz")
    os.system(f"cp -r ../../oss-fuzz ./")

    build_command=f'''
        cd {project_name} && git checkout {commit}
        cd ../oss-fuzz && git checkout {fuzz_commit}
        python infra/helper.py build_fuzzers --engine {fuzz_engine.lower()} --sanitizer {sanitizer.split()[0]} {project_name} ../{project_name}
        
    '''
    build_message=run_command(build_command).lower().strip()
    #print(build_message)
    if "failed" in build_message.split('\n')[-1] or "cannot use local checkout" in build_message.split('\n')[-1] :
        result["build"]=False
        print(build_message)
        os.chdir(origin_dir)
        return result
    else :
        result["build"]=True
    # #build_message+=os.popen(build_command).read()
    # os.system(build_command)
    reproduce_command=f'''
        cd oss-fuzz && python infra/helper.py reproduce {project_name} {fuzz_target} {testcase}
    '''

    message="reprduce message:\n"
    repro_message = run_command(reproduce_command)

    # 将这部分信息保存为log
    with open(f"../{bug_name}-{commit}.txt","w") as f:
        f.write(build_message+repro_message)
    # 进行内容匹配，判断是否成功复现
    # 当message中包含"==ERROR:","==WARNING:"等关键字时，说明复现成功
    flag=False

    if "==ERROR:" in repro_message or "==WARNING:" in repro_message:
        result["reproduce"]=True
        flag=True
    with open(f"../reprolog.txt","w") as f:
        f.write(
            f"bug_name:{bug_name}\n"
            f"commit:{commit}\n fuzz_commit:{fuzz_commit}\n"
            f"reproduce success:{flag}\n"
            f"build_command:{build_command}\n reproduce_command:{reproduce_command}\n"
            
        )
    os.chdir(origin_dir)
    return result


def reproduce_once_d(commit, fuzz_commit, detail, bug_name, git_url, testcase_dir, work_dir):
    
    workdir=f"rep_{bug_name}"
    project_name=detail['project']
    # 如果fuzz_engine字段为空，则默认为libfuzzer
    fuzz_engine=detail['fuzzing_engine'] if detail['fuzzing_engine'] else 'libfuzzer'
    fuzz_target=detail['fuzz_target']
    sanitizer=detail['sanitizer']
    testcase=f"{testcase_dir}/testcase-{bug_name}"
    origin_dir = os.getcwd()
    os.chdir(work_dir)

    # 下载源码
    if os.path.exists(f"./{project_name}"):
        #使用git clone下载
        os.system(f"echo 'TDQ530' | sudo -S rm -rf ./{project_name}")
        #os.system(f"git clone {git_url}")
    os.system(f"cp -r ../{project_name} ./")
    if os.path.exists(f"./oss-fuzz"):
        os.system(f"echo 'TDQ530' | sudo -S  rm -rf ./oss-fuzz")
    os.system(f"cp -r ../../oss-fuzz ./")

    os.system(f"cd ./oss-fuzz && git checkout {fuzz_commit}")
    # 读取./oss-fuzz/projects/{project_name}/Dockerfile文件
    # 匹配并更换其中的RUN git clone命令


    # 读取Dockerfile文件
    with open(f"./oss-fuzz/projects/{project_name}/Dockerfile") as f:
        lines=f.readlines()
    # 匹配并更换其中包含了参数git_url的github链接的命令
    pattern=re.compile(r"RUN git clone.*{}.*".format(git_url))
    for i in range(len(lines)):
        if pattern.match(lines[i]):
            #x=input()
            lines[i]=f"RUN git clone {git_url} {project_name} && cd {project_name} && git checkout {commit}\n"
            break

    # 将修改后的内容写入文件
    with open(f"./oss-fuzz/projects/{project_name}/Dockerfile","w") as f:
        f.writelines(lines)
    
    # print(git_url)
    # print(lines)
    # x=input()




    build_command=f'''
        cd ./oss-fuzz && python infra/helper.py build_fuzzers  --engine {fuzz_engine.lower()} --sanitizer {sanitizer.split()[0]} {project_name} 
        
    '''

    

    build_message=build_command
    #build_message+=os.popen(build_command).read()
    os.system(build_command)
    reproduce_command=f'''
        cd oss-fuzz && python infra/helper.py reproduce {project_name} {fuzz_target} {testcase}
    '''
    message="reprduce message:\n"
    try:
        result = subprocess.run(reproduce_command, timeout=25, check=True, capture_output=True, text=True, shell=True)
        message+=result.stdout
    except subprocess.TimeoutExpired as e:
        message+=f'命令超时: {e}'
        message+=str(e.stdout)
        message+=str(e.stderr)
    except subprocess.CalledProcessError as e:
        message+=f'命令执行失败: {e}'
        message+=e.stdout
        message+=e.stderr
    except Exception as e:
        message+=f'发生错误: {e}'
        message+=e.stdout
        message+=e.stderr



    # 将这部分信息保存为log
    with open(f"./log-{commit}.txt","a") as f:
        f.write(build_message+message)
    # 进行内容匹配，判断是否成功复现
    # 当message中包含"==ERROR:","==WARNING:"等关键字时，说明复现成功
    flag=False

    if "==ERROR:" in message or "==WARNING:" in message:
        flag=True
    with open(f"../reprolog.txt","a") as f:
        f.write(
            f"bug_name:{bug_name}\n"
            f"commit:{commit}\n fuzz_commit:{fuzz_commit}\n"
            f"reproduce success:{flag}\n"
            f"build_command:{build_command}\n reproduce_command:{reproduce_command}\n"
            
        )

    return flag

def test():
    command='''
    ls
    touch hello.txt
    echo cc >> hello.txt
'''
    xx=os.popen(command).read()
    print(f"hellllllllllll {xx}")



# commit="577e2516d0ed3669c7e9879ba9f04214658bfd1b"
# detail={"project":"libxml2","fuzzing_engine":"libfuzzer","fuzz_target":"api","sanitizer":"address"}
# bug_name="OSV-2024-1209"
# url="https://github.com/GNOME/libxml2.git"


# if reproduce_once(commit,detail,bug_name,url):
#     print("reproduce successs!!!")
# else :
#     print("reproduce failed!!!")