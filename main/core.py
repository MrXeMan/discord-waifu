import asyncio
import logging
import os
import time
from asyncio import CancelledError
from datetime import datetime

from inputimeout import inputimeout, TimeoutOccurred

import dsc.core
import generation.core
import main.exceptions
import removalScheduler.core
from main.global_variables import logger
from main.utils import Command, LogHandler


"""
TODO: Make modules be seperate from everything so I can load and unload them dynamically
TODO: Start implementing AI into this.
TODO: Make communication between modules. IP:port? idk
TODO: Create tools for channel/category creation (later after making the AI?)
"""


async def start():
    await init()
    await run()
    await end()


async def init():
    from main.global_variables import threads, terminate_signal, cmds
    main.global_variables.scheduler = removalScheduler.core.Core(terminate_signal)
    await create_logs()
    logger.log(logging.INFO, "Initializing the main core.")
    threads.append(generation.core.Core(terminate_signal))
    threads.append(dsc.core.Core(terminate_signal))
    threads.append(main.global_variables.scheduler)
    logger.log(logging.DEBUG, "Added all excepted modules.")
    from main import utils
    logger.log(logging.INFO, "Initializing commands.")
    for file in utils.list_dir("./commands"):
        if ".py" not in file:
            continue
        cmd = Command(file)
        cmds[cmd.cmd] = cmd
        logger.log(logging.DEBUG, f"Command loaded: {cmd.cmd}")
    logger.log(logging.INFO, f"Loaded all commands!")
    for thread in threads:
        thread.start()


async def create_logs():
    from main import utils
    if ".logs" not in utils.list_dir():
        os.mkdir(".logs")
    if "current.log" in utils.list_dir(".logs"):
        os.rename(f".logs/current.log",
                  f".logs/{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log")
    logger.addHandler(LogHandler())


async def run():
    try:
        from main.global_variables import cmds, terminate_signal, threads, console_enable
        for thread in threads:
            await thread.wait_until_ready()
        while not terminate_signal.is_set():
            try:
                if console_enable:
                    try:
                        user_input = inputimeout(prompt="Command: ", timeout=5)
                    except TimeoutOccurred:
                        user_input = None
                    if user_input is None or user_input == "":
                        continue
                    else:
                        user_input = user_input.lower()
                    if user_input not in cmds.keys():
                        print("No command found.")
                        continue
                    return_value = await cmds[user_input].execute()
                    if asyncio.iscoroutine(return_value):
                        await return_value()
                    elif callable(return_value):
                        return_value()
                    elif type(return_value) is list:
                        print('\n'.join(return_value))
                    else:
                        print(return_value)
                else:
                    await asyncio.sleep(1)
            except UnicodeDecodeError:
                break
            except main.exceptions.EndSignal:
                print("End signal received! Ending...")
                break
    except CancelledError:
        pass



async def end():
    from main.global_variables import terminate_signal, threads
    alive = True
    logger.log(logging.INFO, "Stopping all modules.")
    terminate_signal.set()
    while alive:
        for thread in threads:
            if thread.is_alive():
                alive = True
                break
            alive = False
        time.sleep(1)
    from main import utils
    await utils.clear_additional_logs(".logs")
    logger.log(logging.INFO, "All modules have been stopped.")