#!/bin/env python3

import argparse
import json
from pprint import pprint
import logging
from tools.logger import add_file_handler, logger
import random
import os
from auto_bot import AutoBot
from config.config import ConfigBot

logger.setLevel(logging.DEBUG)





if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.formatter_class = argparse.RawTextHelpFormatter
    parser.description = "A CLI interface for the OssFuzz-Auto"
    
    # Add global -config option
    parser.add_argument(
        "-c", "--config",
        help="path to configuration file",
        default="config.ini"
    )
    
    subparsers = parser.add_subparsers(
        dest="command", help="commands to run", required=True
    )

    # info subcommand
    info_parser = subparsers.add_parser(
        "info",
        help="print the info for special project"
    )
    info_parser.add_argument(
        "-n", "--project_name",
        help="project name",
        required=True
    )

    # reproduce subcommand
    repro_parser = subparsers.add_parser(
        "repro",
        help="reproduce the vulnerability for the target project"
    )
    repro_parser.add_argument(
        "-n", "--project_name",
        help="project name",
        required=True
    )
    repro_parser.add_argument(
        "-u", "--url",
        help="github url for the project",
        required=True
    )
    repro_parser.add_argument(
        "-v", "--vul_name",
        help="vulnerability name",
        required=True
    )


    # parse the args
    args = parser.parse_args()
    config = ConfigBot(args.config)
    config.print()

    autobot = AutoBot(config)
    autobot.build_env()
    logfile = os.path.join(config.logpath, f"{random.randint(1,100000)}.log")
    add_file_handler(logger, logfile)
    if  args.command == "info":
        logger.info("Get info...")
        try:
            autobot.info(args.project_name)
        except Exception as e:
            logger.error(f"Info error {e}")
    elif args.command == "repro":
        logger.info("Start reproducing...")
        try:
            autobot.reproduce(args.project_name, args.vul_name, args.url)
        except Exception as e:
            logger.error(f"Reproduce error {e}")
