from config.config import ConfigBot
from tools.logger import logger
from tools import fetch_detail
from collections import defaultdict
from . import reproduce
import os
import re
import json
import subprocess


class ReproduceBot:
    def __init__(self, config: ConfigBot):
        self.config = config

    def setup(self, project_name, git_url, bug=""):
        # setup the environment for special project

        project_dir     = os.path.join(self.config.workdir,project_name)
        bug_dir         = os.path.join(self.config.workdir,"oss-fuzz-vulns/vulns",project_name)
        log_path        = f'{project_dir}/gitlog.txt'
        project_source  = f"{project_dir}/{project_name}"
        testcases_dir   = f"{project_dir}/testcases"
        data_dir        = f"{project_dir}/data"


        pattern_for_commit      = re.compile(r'[a-f0-9]{40}')
        pattern_for_introduced  = re.compile(r'introduced: [a-f0-9]{40}')
        pattern_for_fixed       = re.compile(r'fixed: [a-f0-9]{40}')
        pattrn_for_url          = re.compile(r"OSS-Fuzz report: (https?://[^\s]+)")


        # build the basic structure
        if not os.path.exists(project_dir):
            os.mkdir(project_dir)
        if not os.path.exists(testcases_dir):
            os.mkdir(testcases_dir)
        if not os.path.exists(data_dir):
            os.mkdir(data_dir)

        # clone the project source code
        if not os.path.exists(project_source):
            os.system(f"git clone {git_url} {project_source}")
        logger.debug(f"Finish cloning {project_name} and oss-fuzz")


        # exec git log to get all commit hashes and save to log_path
        content=os.popen(f"cd {project_source} && git log --format=%H ").read()
        with open(log_path, 'w', encoding='utf-8') as file:
            file.write(content)

        commit_hashes = re.findall(pattern_for_commit, content)
        # reverse commit_hashes
        commit_hashes.reverse()
        # only keep the last 40 characters of each commit hash
        commit_hashes = [commit_hash[-40:] for commit_hash in commit_hashes]
        logger.debug(f"Finish fetching commit hashes for {project_name}")

        # print all the commit
        # for commit_hash in commit_hashes:
        #     print(commit_hash)

        bug_map=defaultdict(dict)

        if os.path.exists(f"{project_dir}/bug_{project_name}.json"):
            with open(f"{project_dir}/bug_{project_name}.json", 'r', encoding='utf-8') as file:
                bug_map=json.load(file)

        # traverse all files in oss-fuzz-vulns/vulns/project_name and fetch the detail
        logger.debug(f"Start processing bugs in {bug_dir}")
        for root, dirs, files in os.walk(bug_dir):
            logger.info(f"Processing file: {files}")
            for file in files:
                if bug != "" and file.split(".")[0] != bug:
                    continue
                file_path = os.path.join(root, file)
                
                with open(file_path, 'r', encoding='utf-8') as file:
                    content = file.read()

                introduced = re.findall(pattern_for_introduced, content)[0][-40:]
                fixed      = re.findall(pattern_for_fixed, content)
                url        = re.findall(pattrn_for_url, content)[0]

                if fixed != []:
                    fixed = fixed[0][-40:]
                else :
                    fixed = commit_hashes[-1]

                file_name = file_path.split("/")[-1].split(".")[0]   
                logger.info(f"file: {file_name} introduced: {introduced} fixed: {fixed}")  
                #print(f"file: {file_name} introduced: {introduced} fixed: {fixed}")


                # fetch the detail for reproduce
                # check if file_name in bug_map's keys
                if file_name not in bug_map: 
                    try :            
                        detail = fetch_detail.get_details(issue_url=url)
                        logger.debug(f"Finish fetching details for {file_name}")
                    except Exception as e:
                        logger.debug(f"Fail to fetch details for {file_name} {e}") 
                        continue
                    bug_map[file_name] = {"introduced": introduced, "fixed": fixed, "url": url, "git": git_url}
                    bug_map[file_name]["reproduce"]=detail
                    with open(f"{project_dir}/bug_{project_name}.json", 'w', encoding='utf-8') as file:
                        json.dump(bug_map, file, ensure_ascii=False, indent=4)

                # download the testcase
                if not os.path.exists(f"{testcases_dir}/testcase-{file_name}"):
                    with open(f"{testcases_dir}/testcase-{file_name}","wb") as f :
                        try:
                            f.write(fetch_detail.get_testcase(detail["reproducer_testcase"]))
                            logger.debug(f"Finish downloading testcase for {file_name}")
                        except Exception as e:
                            logger.debug(f"Fail to download testcase for {file_name} {e}") 


        # save bug_map to json file     
        with open(f"{project_dir}/bug_{project_name}.json", 'w', encoding='utf-8') as file:
            json.dump(bug_map, file, ensure_ascii=False, indent=4)



    def reproduce(self, project_name, bug):

        # related path
        fuzz_dir       = os.path.join(self.config.workdir,"oss-fuzz")
        project_dir    = os.path.join(self.config.workdir,project_name)
        project_source = f"{project_dir}/{project_name}"
        testcases_dir  = f"{project_dir}/testcases"
        data_dir       = f"{project_dir}/data"

        # load bug map
        bug_map_path = f"{project_dir}/bug_{project_name}.json"
        with open(bug_map_path, 'r', encoding='utf-8') as file:
            bug_map = json.load(file)
        
        if bug not in bug_map:
            logger.warning(f"Bug {bug} not found")
            return

        # load message for reproduce
        fuzz_map      = reproduce.parse_git_log(reproduce.get_git_log(fuzz_dir),1)
        project_map   = reproduce.parse_git_log(reproduce.get_git_log(project_source),2)
        commit        = bug_map[bug]["introduced"]
        fuzz_commit   = reproduce.find_suite_commit(commit,fuzz_map,project_map)
        logger.info(f"commit: {commit}")
        logger.info(f"fuzz_commit: {fuzz_commit}")

        detail        = bug_map[bug]["reproduce"]
        git_url       = bug_map[bug]["git"]
        work_dir      = f"{project_dir}/work-rep"
        
        if not os.path.exists(work_dir):
            os.mkdir(work_dir)
        result = reproduce.reproduce_once(commit, fuzz_commit, detail, bug, testcases_dir, work_dir)
        logger.debug(f"result: {result}")
        if result["build"]:
            logger.info(f"reproduce success for {bug}")
            latest = bug_map[bug]["introduced"]
            oldest = bug_map[bug]["introduced"]
            oldest = self.get_parent_commit(oldest, project_name)
            logger.info(f"latest: {latest} oldest: {oldest}")
            # generate_task(project_name, git_url, commit, fuzz_commit, commit, oldest, [bug])
        else :
            logger.info(f"reproduce failed for {bug}")
        # save_task_build_info(project_name, commit, fuzz_commit, bug, result)
        return result

    def get_parent_commit(self, commit_hash, project_name):
        """
        获取指定提交的父提交。
        :param commit_hash: 提交的哈希值
        :return: 父提交的哈希值
        """
        dir_path = os.path.join(self.config.workdir, project_name, project_name)
        try:
            # 使用git log命令获取父提交
            check_command=f'''
            cd {dir_path} && git show --pretty=format:%H {commit_hash}^

            '''
            result = reproduce.run_command(check_command)
            
            parent_commit = result.strip().split('\n')[0]
            return parent_commit
        except subprocess.CalledProcessError as e:
            logger.error(f"Error getting parent commit for {commit_hash}: {e}")
            return None