import requests as rq
import json
# from selenium import webdriver
# from selenium.webdriver.common.by import By
# from selenium.common.exceptions import NoSuchElementException
import time
import re
import sys

TESTCASE_REGEX = re.compile(r"Reproducer Testcase: (https?://[^\s]+)")
import re


# 提取 Detailed Report 的 URL
DETAILED_REPORT_REGEX = re.compile(r"Detailed Report: (https?://[^\s]+)")
# 提取 Project 信息
PROJECT_REGEX = re.compile(r"Project: ([\w-]+)")
# 提取 Fuzzing Engine 信息
FUZZING_ENGINE_REGEX = re.compile(r"Fuzzing Engine: ([\w-]+)")
# 提取 Fuzz Target 信息
FUZZ_TARGET_REGEX = re.compile(r"Fuzz Target: ([\w-]+)")
FUZZ_TARGET_REGEX_2 = re.compile("Fuzz target binary: ([\w-]+)")
# 提取 Job Type 信息
JOB_TYPE_REGEX = re.compile(r"Job Type: ([\w-]+)")
# 提取 Platform Id 信息
PLATFORM_ID_REGEX = re.compile(r"Platform Id: ([\w-]+)")
# 提取 Crash Type 信息
CRASH_TYPE_REGEX = re.compile(r"Crash Type: ([\w-]+)")
# 提取 Crash Address 信息
CRASH_ADDRESS_REGEX = re.compile(r"Crash Address: ([^\n]+)")
# 提取 Crash State 信息，因为它是多行的，使用 re.DOTALL 来匹配多行
CRASH_STATE_REGEX = re.compile(r"Crash State:([\s\S]+?)(?=\n\n|\n$)")
# 提取 Sanitizer 信息
SANITIZER_REGEX = re.compile(r"Sanitizer: (.+)\n")
# 提取 Regressed 的 URL
REGRESSED_REGEX = re.compile(r"Regressed: (https?://[^\s]+)")
# 提取 Reproducer Testcase 的 URL
REPRODUCER_TESTCASE_REGEX = re.compile(r"Reproducer Testcase: (https?://[^\s]+)")

#const url = "https://issues.oss-fuzz.com/42486565"
ISSUE_OSS_URL_REGEX = re.compile(r"const url \= \"(https://issues.oss-fuzz.com/\d+)\"")
def search():
    url = "https://issues.chromium.org/action/issues/list"
    page_idx = 0
    while True:
        response = rq.post(url,headers={"Content-Type": "application/json"},data=f'[null,null,null,null,null,["391"],["project:libxml2",null,50,"start_index:{page_idx*50}"]]')
        res = json.loads(response.text[5:])
        ids = [x[1] for x in res[0][6][0]]
        for i in ids:
            yield i
        page_idx += 1
# 输入 issue_id，返回 issue 的详细信息
def get_details(issue_id=None, issue_url=None):
    if issue_id is None and issue_url is None:
        raise ValueError("issue_id and issue_url cannot be both None")
    if issue_url is not None:
        response = rq.get(issue_url, allow_redirects=False)
        real_url = ISSUE_OSS_URL_REGEX.search(response.text)
        if real_url:
            url = real_url.group(1)
        else:
            raise ValueError("Cannot find real issue url")
        issue_id = url.split('/')[-1]
        print("issue_id:", issue_id)
    url = f"https://issues.oss-fuzz.com/action/issues/{issue_id}/events?currentTrackerId=391"

    response = rq.get(url)
    res = json.loads(response.text[5:])
    issue_detail_text = res[0][2][0][2][0]
    project = PROJECT_REGEX.search(issue_detail_text)
    fuzzing_engine = FUZZING_ENGINE_REGEX.search(issue_detail_text)
    fuzz_target = FUZZ_TARGET_REGEX.search(issue_detail_text)
    if fuzz_target is None:
        fuzz_target = FUZZ_TARGET_REGEX_2.search(issue_detail_text)
    job_type = JOB_TYPE_REGEX.search(issue_detail_text)
    platform_id = PLATFORM_ID_REGEX.search(issue_detail_text)
    crash_type = CRASH_TYPE_REGEX.search(issue_detail_text)
    crash_address = CRASH_ADDRESS_REGEX.search(issue_detail_text)
    # crash_state = CRASH_STATE_REGEX.search(issue_detail_text)
    sanitizer = SANITIZER_REGEX.search(issue_detail_text)
    regressed = REGRESSED_REGEX.search(issue_detail_text)
    reproducer_testcase = REPRODUCER_TESTCASE_REGEX.search(issue_detail_text)
    details = {
        'issue_id': issue_id,
        # 'detail_text': issue_detail_text,
        'project': project.group(1) if project else None,
        'fuzzing_engine': fuzzing_engine.group(1) if fuzzing_engine else None,

        'fuzz_target': fuzz_target.group(1) if fuzz_target else None,
        'job_type': job_type.group(1) if job_type else None,
        'platform_id': platform_id.group(1) if platform_id else None,
        'crash_type': crash_type.group(1) if crash_type else None,
        'crash_address': crash_address.group(1) if crash_address else None,
        # 'crash_state': crash_state.group(1) if crash_state else None,
        'sanitizer': sanitizer.group(1) if sanitizer else None,
        'regressed': regressed.group(1) if regressed else None,
        'reproducer_testcase': reproducer_testcase.group(1) if reproducer_testcase else None
    }
    # if testcase:
        # print(testcase.group(1))
        # return testcase.group(1)
    return details
def get_testcase(url):
    response = rq.get(url, allow_redirects=False)
    redirect_url = response.headers['Location']
    if '/login?dest=https' in redirect_url:
        print("Need to login")
        return None
    response = rq.get(redirect_url)
    # return response.text
    return response.content
if __name__ == "__main__":
    # 爬libxml2所有的 issue_id
    # for issue_id in search():
    #   print(issue_id)
    #   detail = get_details(issue_id)
    #   print(get_testcase(detail['reproducer_testcase']))
        # exit(0)
    print(get_details(issue_url='https://bugs.chromium.org/p/oss-fuzz/issues/detail?id=24925'))
    # print(get_testcase("https://oss-fuzz.com/download?testcase_id=5376081376378880"))
    # print(get_testcase("https://oss-fuzz.com/download?testcase_id=5514320082436096"))
    # print(get_testcase("https://oss-fuzz.com/download?testcase_id=4897346556067840"))