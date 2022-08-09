# -*- coding: utf-8 -*-
"""
Created by: Mistayan
Project: navigate-and-gather
IDE: PyCharm
Creation-date: 08/03/22
"""
import json
import re
import logging
import html
from multiprocessing import Pool

import yarl
from selenium import webdriver
from selenium.common import TimeoutException
from selenium.webdriver import Proxy
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from urllib3.exceptions import MaxRetryError
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

import conf
from my_async import AsyncRequest, get_content
log = logging.getLogger(__name__)
mail_pattern = re.compile(r"[\w\d+._-]+\(?@\)?[\w\d+._-]+\.[a-zA-Z]+")
contact_pattern = re.compile(r"\/[\w-]+?contact+[\w\d+_/-]+")
service = Service(ChromeDriverManager().install())
options = Options()
options.headless = True
options.proxy = Proxy()
options.accept_insecure_certs = True


def omail_get_mails(url):
    domain = re.sub("www.", "", yarl.URL(url).host)
    log.debug(f"extract: {domain}")
    try:
        with webdriver.Chrome(options=options, service=service) as driver:
            driver.get(f"https://omail.io/leads/{domain}")
            found = WebDriverWait(driver, 5).until(
                EC.presence_of_all_elements_located((By.CLASS_NAME, "domain_text")))
            if found and "None" not in found[0].text:
                mails = [mail.text for mail in found]
                log.info(f"found intel on {domain} : {mails}")
                return mails
            return []
    except (ConnectionRefusedError, MaxRetryError):
        return []


def extract_mail(string):
    """
    :param string: potential email string
    :return: formatted email if email found
    """
    if not string:
        return
    string = str(string)
    if re.match(r" ?[&?\\<(){]+.+", html.unescape(string)):  # mail from mailto: {} sometimes returns extra
        string = re.sub(r" ?[&?\\<(){]+.+", "", html.unescape(string))  # remove potential junk after email
    # some mails match urls img@xyz.png
    try:
        string = mail_pattern.match(html.unescape(string).lower())[0]
        if string and string[-3:] not in ("png", "gif", "svg"):
            return string
    except IndexError:
        log.error(f"MatchError : {string}")
    except TypeError:
        return


def get_website_mails(url):
    ret = []
    website = AsyncRequest(get_content, url)
    if website.get():
        mails = mail_pattern.findall(website.get())
        [ret.append(mail) if mail else None for mail in mails] if mails else None
        contact = contact_pattern.search(website.get())
        log.debug(contact)
        if contact and "css" not in contact[0]:
            # task.name is the requested website's url, at which we append /*contact*/
            contact = website.name[0] + (contact[0][1:] if website.name[0][-1] == '/' else contact[0])
            contact_page = str(AsyncRequest(get_content, contact).get())
            if contact_page:
                try:
                    mails = mail_pattern.findall(contact_page)
                    [ret.append(mail) if mail else None for mail in mails] if mails else None
                except ValueError:  # No email found via regex. Maybe it is encoded (may return unwanted values)
                    pass
    log.info(f"{url} => extracted: {ret}")
    if ret:
        ret += omail_get_mails(url)
        return ret
    return omail_get_mails(url)


def extract_website(_id):
    log.debug(f"extract: {_id}")
    try:
        with webdriver.Chrome(options=options, service=service) as driver:
            driver.get(f"https://www.touslesgolfs.com/?post_type=golf&p={_id}")
            try:
                url = WebDriverWait(driver, 1).until(EC.presence_of_element_located((By.CLASS_NAME, "url_block")))
                if url:
                    log.info(url.text)
                    return url.text
            except TimeoutException:
                log.warning(f"couldn't load https://www.touslesgolfs.com/?post_type=golf&p={_id}")
                return
    except (ConnectionRefusedError, MaxRetryError):
        return


# ______________________________________________________________________________________________ #
if __name__ == '__main__':
    # Attempt to gather json sent when loading the map
    print("""Data-Gathering  Copyright (C) 2022  Mistayan
    This program comes with ABSOLUTELY NO WARRANTY; for details type `show w'.
    This is free software, and you are welcome to redistribute it
    under certain conditions; type `show c' for details.""")

    try:
        print("reading file...")
        with open("test_datas", "r") as fp:  # this file is a copy from browser's network analyser
            id_list = fp.readlines()
            if len(id_list) != 10:
                raise FileNotFoundError
    except FileNotFoundError:
        exit(print("Did you clone the repository ? It includes test_datas"))
    # Attempt to gather every website displayed
    print("searching datas... (this can take a moment)")
    with Pool(conf.MAX_WORKERS) as pool:
        log.info("gathering websites from id_list")
        websites: list = pool.map_async(extract_website, id_list).get()
        log.info("gathering mails from websites:")
        with open("websites", "w") as fp:
            json.dump(websites, fp=fp, indent=2)
        mails: list[list] = pool.map_async(get_website_mails, websites).get()
        log.debug(mails)
    unique_set = set()
    for group in mails:
        [unique_set.add(elem) for elem in group]
    print("Saving findings...")
    with open("findings", "w", 1024, "utf-8") as fp:
        for elem in unique_set:
            mail = extract_mail(elem)
            if mail:
                print(mail, file=fp)
    print("Done.")
