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
import parse
from webdriver_manager.chrome import ChromeDriverManager

import conf
from my_async import AsyncRequest, get_content

log = logging.getLogger(__name__)
mail_pattern = re.compile(r"[\w\d+._-]+\(?@\)?[\w\d+._-]+\.[a-zA-Z]+")
mailto_pattern = parse.Parser("mailto:{}\"")
url_parse = parse.Parser("/contact{}\"")


def extract_mail(string):
    """
    :param string: potential email string
    :return: formatted email if email found
    """
    if string.find("#&") or string.find("%"):  # mail is unicode-encoded or html-encoded
        string = html.unescape(string)
    if string.find("?"):  # mailto:{} sometimes returns mail?form=...
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


def get_website_contacts(url):
    mails = []
    website = AsyncRequest(get_content, url)
    if website.get():
        mailtos = mailto_pattern.search(website.get())
        mails.append(mailtos[0].lower()) if mailtos else None
        contact_url = url_parse.search(website.get())
        if contact_url and "css" not in contact_url[0]:
            # task.name is the requested website's url, at which we append /contact***/
            contact_url = contact_url[0].split("\"") if "\"" in contact_url[0] \
                else contact_url[0].split("\'") if "\'" in contact_url[0] \
                else contact_url
            contact_url = website.name[0] + ('/' if website.name[0][-1] != '/' else '') + "contact" + contact_url[0]
            contact_page = str(AsyncRequest(get_content, contact_url).get())
            if contact_page:
                try:
                    sub_mails = mail_pattern.findall(contact_page)
                    if sub_mails:
                        [mails.append(extract_mail(mail)) for mail in sub_mails]
                except ValueError:  # No email found via regex. Maybe it is encoded (may return unwanted values)
                    try:
                        sub_mailto = mailto_pattern.search(contact_page)
                        if sub_mailto:
                            [mails.append(extract_mail(mail)) if mail.lower() not in mails else None for mail in sub_mailto]
                    except ValueError:
                        pass
    log.info(f"{url} => extracted: {mails}")
    return mails


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
    try:
        with open("test_datas", "r") as fp:  # this file is a copy from browser's network analyser
            id_list = fp.readlines()
            if len(id_list) != 10:
                raise FileNotFoundError
    except FileNotFoundError:
        exit(print("Did you clone the repository ? It includes test_datas"))
    # Attempt to gather every website displayed
    results = [frozenset(get_website_contacts(extract_website(_id))) for _id in id_list]
    # save findings
    with open("findings", "w", 1024, "utf-8") as fp:
        for line in results:
            for elem in line:
                mail = extract_mail(elem)
                if mail:
                    print(mail, file=fp)
