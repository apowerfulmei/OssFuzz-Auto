from tools.logger import logger
from reproduce.reproducer import ReproduceBot
from config.config import ConfigBot
import os



class AutoBot:
    def __init__(self, config: ConfigBot):
        self.config = config
        self.reproducer = ReproduceBot(config)


    def build_env(self):
        # build the environment
        self.config.build()

    def fetch(self, project_name, project_url):
        print(f"Fetching data for project '{project_name}' from '{project_url}'")
        # Add logic to fetch data here

    def info(self, project_name):
        """
        print the info of the project
        """
        project_dir    = os.path.join(self.config.workdir,project_name)
        file_path      = f'{project_dir}/gitlog.txt'
        replog_path    =f'{project_dir}/reprolog.txt'
        project_source = f"{project_dir}/{project_name}"
        testcases_dir  = f"{project_dir}/testcases"
        data_dir       = f"{project_dir}/data"

        print(f"TestCases for project {project_name}: ")
        for file in os.listdir(testcases_dir):
            print(file)
        # bug_dir=f"./oss-fuzz-vulns/vulns/{project_name}"

    def reproduce(self, project_name, bug_name, git_url):
        self.reproducer.setup(project_name, git_url, bug_name)
        self.reproducer.reproduce(project_name, bug_name)

    def validate(self, CVE=None, kbug=None, app=None):
        print(f"Validating with CVE: {CVE}, kbug: {kbug}, app: {app}")
        # Add logic to validate here