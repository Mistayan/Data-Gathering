# -*- coding: utf-8 -*-
"""
Created by: Mistayan
Project: Learning-Python
"""
import html
import time
import asyncio
import logging

from aiohttp import ClientOSError

import conf
import aiohttp
import yarl

log = logging.getLogger(__name__)


# ____________________________________________________ #
# __________________ ASYNC FUNCTIONS _________________ #
# ____________________________________________________ #
async def get_content(url: str, query: str = ''):
    """
    Generate an async session requesting url + query
    Returns a StreamReader, according to current response formatting
    """
    if not url or "css" in url:
        return
    target = yarl.URL(url + query)  # proper request formatting
    log.info(f"request : {target}")
    try:
        async with aiohttp.ClientSession() as session:

            try:
                async with session.get(target) as response:  # Get session's content
                    # if response.host != target.host and  response.host != "www." + target.host:
                    #     raise ValueError(f"{response.host} not {target.host}")
                    if not response.status == 200:
                        ret = await response.text()
                    else:
                        log.debug(response.content_type)
                        match response.content_type:
                            case 'application/json':
                                ret = await response.json()
                            case 'text/html':
                                ret = html.unescape(await response.text())
                            case _:
                                ret = html.unescape(await response.content.read())
                        log.debug(f"result for {target.human_repr()}: "
                                  f"{ret if not isinstance(ret, bytes) and len(ret) < 500 else 'bytes.'}")
            except ClientOSError as err:
                ret = err.strerror

    except aiohttp.ClientConnectorError as err:
        log.debug(f"Connection not established with {target.human_repr()}")
        ret = err.strerror
    return ret


# ____________________________________________________ #
# _____________________ EASY ASYNC ___________________ #
# ____________________________________________________ #
class AsyncRequest:
    """
    Start an asynchronous request when you call the class. \n
    You can retrieve results later on in your program without the pain to wait.

    How To Use:\n
    request = AsyncRequest(async_function, *args, **options)\n
    request2 = AsyncRequest(get_content, url, callback=print)  # print request2 as soon as possible\n
    # do stuff (like requesting more stuff ?)\n
    results = request.get()\n
    # do more stuff with the results
    """

    def __init__(self, func, *args, **kwargs):
        self.log = logging.getLogger(__name__ + str(func))
        self.start = time.perf_counter()
        self.name = [*args]
        self.__loop = None
        self.future = None
        # sanity checks
        try:
            self.__loop = asyncio.get_event_loop_policy().get_event_loop()
            self.future = asyncio.Task(func(*args), loop=self.__loop)  # initiate request as background task
            self.future.add_done_callback(self._set_result)
            asyncio.set_event_loop(self.__loop)
            self.result = None
        except RuntimeError or RuntimeWarning:  # multithread / multiprocess context
            self.result = asyncio.run(func(*args))
        self.end = time.perf_counter()

    def add_done_callback(self, callback):
        if callback\
                and isinstance(callback, staticmethod) and issubclass(callback, classmethod)\
                and self.future:
            self.future.add_done_callback(callback)

    def _set_result(self, cb):
        if isinstance(cb, Exception):
            self.log.debug(f"Exceptions raised as callback @{time.perf_counter() - self.start}\n{cb}s")
            raise cb
        else:
            self.log.debug(f"callback for {self.name} : {cb} received @{time.perf_counter() - self.start:0.4f}s")
            self.result = cb.result()[0] if isinstance(cb.result(), list) else cb.result()
        return self.result

    def get(self):
        """
        If internal callback is received (Thread raised an Error, or ended), skip freeze \n
        Will freeze calling process until result is available. \n
        When done, stop current loop after ensuring _Future \n
        Release newly created loop (if not main thread's loop)
        """
        try:
            if self.future and not (self.future.done() or self.result):
                loop = self.future.get_loop()
                if not loop.is_running():
                    loop.run_until_complete(self.future)
                if not self.result:
                    self.result = self.future.result()
                    self.future = None
        except Exception:
            pass
        return self.result

    def close(self, cb=None):
        # self.__await__()
        if isinstance(cb, Exception):
            return
        if self.__loop.is_running():
            self.log.debug(f"stopping loop {self.__loop}")
            self.__loop.stop()
        self.log.debug(f"closing loop {self.__loop}")
        self.__loop.close()

    def __str__(self):
        return self.get()

    def __repr__(self):
        return self.get()

    def __await__(self):
        if self.future:
            self.future.__await__()
