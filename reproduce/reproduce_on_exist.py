# 在已经generate好的数据上进行reproduce
import os
import subprocess
import sys
from collections import defaultdict
import pandas as pd

result_all=defaultdict(dict)
def load_commands(file_path):
    """
文件示例内容：

        # reproducing bug OSV-2023-1239
        cd ./fuzz-tooling
        python infra/helper.py build_fuzzers --engine libfuzzer --sanitizer address jq 
        cd ./fuzz-tooling && python infra/helper.py reproduce jq jq_fuzz_parse_extended ../testcases/testcase-OSV-2023-1239  

    
        # reproducing bug OSV-2024-396
        cd ./fuzz-tooling
        python infra/helper.py build_fuzzers --engine libfuzzer --sanitizer undefined jq 
        cd ./fuzz-tooling && python infra/helper.py reproduce jq jq_fuzz_fixed ../testcases/testcase-OSV-2024-396  

    
        # reproducing bug OSV-2024-831
        cd ./fuzz-tooling
        python infra/helper.py build_fuzzers --engine libfuzzer --sanitizer address jq 
        cd ./fuzz-tooling && python infra/helper.py reproduce jq jq_fuzz_execute ../testcases/testcase-OSV-2024-831  

    
        # reproducing bug OSV-2024-440
        cd ./fuzz-tooling
        python infra/helper.py build_fuzzers --engine libfuzzer --sanitizer undefined jq 
        cd ./fuzz-tooling && python infra/helper.py reproduce jq jq_fuzz_fixed ../testcases/testcase-OSV-2024-440  
命令之间以#注释行隔开，每个命令包含三行，将其摘出来保存在list中
    """
    commands = []
    if not os.path.exists(file_path):
        return []
    with open(file_path, 'r') as file:
        command_block = []
        for line in file:
            
            line = line.strip()
            if line.startswith("*"):
                return []
            if line.startswith("#") and not command_block:

                bug_name = line.split(" ")[-1]
                command_block.append(bug_name)

            elif line.startswith("#") and command_block:
                
                
                commands.append(command_block)
                command_block = []
                bug_name = line.split(" ")[-1]
                command_block.append(bug_name)
            if line and not line.startswith("#"):
                command_block.append(line)
        if command_block:
            commands.append(command_block)
    print(commands)
    return commands
    
def execute_commands(commands,project_name)->list:
    """
    执行命令
    """
    os.system(f"tar -xvf {project_name}.tar.gz")
    os.system("tar -xvf fuzz-tooling.tar.gz")
    result_b=[]
    for command_block in commands:
        bug_name = command_block[0]
        print(bug_name)
        build_command=f"{command_block[1]} && {command_block[2]}"
        reproduce_command=command_block[3]
        os.system(build_command)
        message=""
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

        if "==ERROR:" in message or "==WARNING:" in message:
            result_b.append(bug_name)
            print("Finished executing block.")
    return result_b

def save_to_excel(result, file_path):
    """
    将结果保存到excel文件中
    """
    df = pd.DataFrame(result).T
    df.to_excel(file_path)


def task_pro(project_name):
    for task in os.listdir(f"/root/tasks/{project_name}"):
        if os.path.isdir(f"/root/tasks/{project_name}/{task}"):
            save_to_excel(result_all, f"/root/tasks/repx.xlsx")
            os.chdir(f"/root/tasks/{project_name}/{task}")
            commands = load_commands("log_rep.txt")
            if commands==[]:
                result_all[task]["project_name"]=project_name
                result_all[task]["result"]="command error"
                print(f"{project_name}/{task} command error")
                continue
            mm=execute_commands(commands,project_name)
            result_all[task]["project_name"]=project_name
            result_all[task]["result"]=mm

            os.system(f"rm -rf {project_name}")
            os.system(f"rm -rf fuzz-tooling")



# 使用线程池处理任务

# import concurrent.futures
# with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:




for project_name in list(reversed(os.listdir("/root/tasks"))):
    print(project_name)
    if os.path.isdir(f"/root/tasks/{project_name}"):
        #task_pro(project_name)
        for task in os.listdir(f"/root/tasks/{project_name}"):
            if os.path.isdir(f"/root/tasks/{project_name}/{task}"):
                save_to_excel(result_all, f"/root/tasks/repxx.xlsx")
                os.chdir(f"/root/tasks/{project_name}/{task}")
                commands = load_commands("log_rep.txt")
                if commands==[]:
                    result_all[task]["project_name"]=project_name
                    result_all[task]["result"]="command error"
                    print(f"{project_name}/{task} command error")
                    continue
                mm=execute_commands(commands,project_name)
                result_all[task]["project_name"]=project_name
                result_all[task]["result"]=mm

                os.system(f"rm -rf {project_name}")
                os.system(f"rm -rf fuzz-tooling")
        os.system(f"docker rmi gcr.io/oss-fuzz/{project_name}")
        os.system("docker rm -f $(docker ps -a -q --filter ancestor=gcr.io/oss-fuzz-base/base-runner)")
        os.system('docker rmi $(docker images -f "dangling=true" -q)')
       
