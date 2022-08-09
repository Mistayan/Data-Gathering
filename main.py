# -*- coding: utf-8 -*-
"""
Created by: Mistayan
Project: navigate-and-gather
IDE: PyCharm
Creation-date: 08/03/22
"""
import re
import logging
import html

from selenium import webdriver
from selenium.webdriver import Proxy
from selenium.webdriver.chrome.options import Options
from urllib3.exceptions import MaxRetryError
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

import conf
from my_async import AsyncRequest, get_content

log = logging.getLogger(__name__)
mail_pattern = re.compile(r"[\w\d+._-]+\(?@\)?[\w\d+._-]+\.[a-zA-Z]+")
contact_pattern = re.compile(r"/.?contact+[\w\d+_/-]+")


def extract_mail(string):
    """
    :param string: potential email string
    :return: formatted email if email found
    """
    if string.find("#&") or string.find("%"):  # mail is unicode-encoded or html-encoded
        string = html.unescape(string)
    if string.find("?"):
        string = string.split("?")[0]
    if re.match(r" ?[&?'\"\'\\<(){]+.+", html.unescape(string)):  # mail from mailto: {} sometimes returns extra
        string = re.sub(r" ?[&?'/\"\'\\<(){]+.+", "", html.unescape(string))  # remove potential junk after email
    # some mails match urls img@xyz.png
    try:
        string = mail_pattern.match(string.lower())[0]
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
        [ret.append(mailto) for mailto in mails] if mails else None
        contact = contact_pattern.search(website.get())
        print(contact)
        if contact and "css" not in contact[0]:
            # task.name is the requested website's url, at which we append /*contact*/
            contact = website.name[0] + (contact[0][1:] if website.name[0][-1] == '/' else contact[0])
            contact_page = str(AsyncRequest(get_content, contact).get())
            if contact_page:
                try:
                    mails = mail_pattern.findall(contact_page)
                    [ret.append(mail) for mail in mails] if mails else None
                except ValueError:  # No email found via regex. Maybe it is encoded (may return unwanted values)
                    pass
    log.info(f"{url} => extracted: {ret}")
    return ret


def extract_website(_id):
    log.info(f"extract: {_id}")
    try:
        options = Options()
        options.headless = True
        options.proxy = Proxy()
        options.accept_insecure_certs = True
        with webdriver.Chrome(ChromeDriverManager().install(), options=options) as driver:
            driver.get(f"https://www.touslesgolfs.com/?post_type=golf&p={_id}")
            url = WebDriverWait(driver, 1).until(EC.presence_of_element_located((By.CLASS_NAME, "url_block")))
            if url:
                log.info(url.text)
                return url.text
    except ConnectionRefusedError:
        return
    except MaxRetryError:
        return


# ______________________________________________________________________________________________ #
if __name__ == '__main__':
    # Attempt to gather json sent when loading the map
    print("""Data-Gathering  Copyright (C) 2022  Mistayan
    This program comes with ABSOLUTELY NO WARRANTY; for details type `show w'.
    This is free software, and you are welcome to redistribute it
    under certain conditions; type `show c' for details.""")
          
    try:
        with open("test_datas", "r") as fp:  # this file is a copy from browser's network analyser
            id_list = fp.readlines()
            if len(id_list) != 10:
                raise FileNotFoundError
    except FileNotFoundError:
        exit(print("Did you clone the repository ? It includes test_datas"))
    # Attempt to gather every website displayed
    results = [frozenset(get_website_mails(extract_website(_id))) for _id in id_list]
    # save findings
    with open("findings", "w", 1024, "utf-8") as fp:
        for line in results:
            for elem in line:
                mail = extract_mail(elem)
                if mail:
                    print(mail, file=fp)
