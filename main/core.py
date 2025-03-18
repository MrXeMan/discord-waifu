import asyncio
import logging
import os
import time
from asyncio import CancelledError
from datetime import datetime

# from inputimeout import inputimeout, TimeoutOccurred

import main.exceptions
import removalScheduler.core
from main.global_variables import logger, threads_to_start
from main.utils import Command, LogHandler

"""
TODO: ollama chat
TODO: Start implementing AI into this.
TODO: Create tools for AI to interact with discord.
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
    logger.log(logging.INFO, "Initializing all extensions...")
    await init_extensions()
    logger.log(logging.INFO, "All extensions loaded.")
    from main import utils
    logger.log(logging.INFO, "Initializing commands.")
    for file in utils.list_dir("./commands"):
        if ".py" not in file:
            continue
        cmd = Command(file)
        cmds[cmd.cmd] = cmd
        logger.log(logging.DEBUG, f"Command loaded: {cmd.cmd}")
    logger.log(logging.INFO, f"Loaded all commands!")
    logger.log(logging.INFO, "Initialized the main core.")
    logger.log(logging.INFO, "Starting every extension.")
    for thread in threads:
        logger.log(logging.INFO, f"Starting extension: {thread.core_name}")
        thread.start()
    logger.log(logging.INFO, "Started all extensions!")


async def init_extensions():
    from main.utils import init_extension
    for extension in os.listdir(os.path.join("extensions")):
        await init_extension(extension)


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
        logger.log(logging.INFO, "Waiting for extensions to be ready...")
        for thread in threads:
            logger.log(logging.DEBUG, f"Waiting for extension: {thread.core_name}")
            await thread.wait_until_ready()
        while not terminate_signal.is_set():
            logger.log(logging.DEBUG, "Main loop has advanced!")
            try:
                if console_enable:
                    # try:
                    #     user_input = inputimeout(prompt="Command: ", timeout=5)
                    # except TimeoutOccurred:
                    #     user_input = None
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
                for left in sorted(threads_to_start.keys()):
                    if left == 0:
                        logger.log(logging.DEBUG, f"Starting threads...")
                        for extension in threads_to_start[left]:
                            core: main.utils.Core = await main.utils.init_extension(extension, mode=None)
                            if core is not None:
                                core.start()
                        threads_to_start[left].clear()
                    else:
                        from main import global_variables
                        if (left - 1) not in threads_to_start.keys():
                            global_variables.threads_to_start[left - 1] = []
                        global_variables.threads_to_start[left - 1].extend(threads_to_start[left])
                        threads_to_start[left].clear()
            except UnicodeDecodeError:
                break
            except main.exceptions.EndSignal:
                print("End signal received! Ending...")
                break
    except CancelledError:
        pass



async def end():
    from main.global_variables import terminate_signal, threads
    logger.log(logging.DEBUG, f"Stopping everything...")
    alive = True
    logger.log(logging.INFO, "Stopping all extensions.")
    terminate_signal.set()
    while alive:
        logger.log(logging.DEBUG, f"Extensions are still alive.")
        for thread in threads:
            if thread.is_alive():
                logger.log(logging.DEBUG, f"Extension: {thread.core_name} is confirmed to be alive. Waiting...")
                alive = True
                break
            alive = False
        time.sleep(1)
    logger.log(logging.DEBUG, f"Every extention confirmed killed.")

    logger.log(logging.DEBUG, f"Requesting logs clearing.")
    from main import utils
    await utils.clear_additional_logs(".logs")
    logger.log(logging.DEBUG, f"Request for logs clearing completed.")
    logger.log(logging.DEBUG, "Stopping deletion scheduler.")
    main.global_variables.scheduler.kill()
    while main.global_variables.scheduler.is_alive():
        logger.log(logging.DEBUG, f"Scheduler is confirmed to be alive. Waiting...")
        time.sleep(1)
    logger.log(logging.DEBUG, "Scheduler was stopped.")
    logger.log(logging.INFO, "All extensions have been stopped.")