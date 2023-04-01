# -*- coding: utf-8 -*-
"""
Created by: Mistayan
Project: navigate-and-gather
IDE: PyCharm
Creation-date: 08/03/22
"""
import re
import json
import logging
from multiprocessing.pool import Pool

import yarl
from selenium.webdriver import Proxy
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from urllib3.exceptions import MaxRetryError
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

import conf
from main import extract_website, extract_mail

log = logging.getLogger(__name__)


def omail_get_mails(url):
    domain = re.sub("www.", "", yarl.URL(url).host)
    log.info(f"extract: {domain}")
    service = Service(ChromeDriverManager().install())
    options = Options()
    options.headless = True
    options.proxy = Proxy()
    options.accept_insecure_certs = True
    try:
        with webdriver.Chrome(options=options, service=service) as driver:
                driver.get(f"https://omail.io/leads/{domain}")
                mails = WebDriverWait(driver, 5).until(
                    EC.presence_of_all_elements_located((By.CLASS_NAME, "domain_text")))
                if mails and "None" not in mails[0].text:
                    log.info(f"found intel on {domain}")
                    return [mail.text for mail in mails]
                return []
    except (ConnectionRefusedError, MaxRetryError):
        return []


def omail_it():
    with open("websites") as fp:
        use_list = fp.readlines()
    # Attempt to gather every website displayed
    with Pool(processes=conf.MAX_WORKERS) as pool:
        sites = pool.map_async(omail_get_mail, [url for url in use_list]).get()
    # save findings
    print(sites)
    with open("sites", "w", 1024, "utf-8") as fp:
        for mails in sites:
            for mail in mails:
                line = extract_mail(mail)
                if line:
                    print(line, file=fp)


def get_websites():
    with open("datas.json") as fp:
        use_list = json.load(fp)
    # Attempt to gather every website displayed
    with Pool(processes=conf.MAX_WORKERS) as pool:
        sites = pool.map_async(extract_website, [url for url in use_list]).get()
    # save findings
    print(sites)
    with open("websites", "w", 1024, "utf-8") as fp:
        for line in sites:
            if line:
                print(line, file=fp)


# ______________________________________________________________________________________________ #
if __name__ == '__main__':
    # Attempt to gather json sent when loading the map
    # try:
    #     with open("datas.json", "r") as fp:  # this file is a copy from browser's network analyser
    #         _json: list = json.load(fp)
    #         use_list = []
    #         for i in range(10):
    #             use_list.append(_json[i])
    # except FileNotFoundError:
    #     exit(print("Please, copy website's json containing targets IDs in datas.json"))
    # except json.JSONDecodeError:
    #     exit(print("Invalid datas.json formatting. Please repair before you can use this script."))
    omail_it()

