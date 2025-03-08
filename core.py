import os
import threading
import time
import dsc.core
import generation.core
import utils
from utils import Command, EndSignal

threads: list[utils.Core] = []
cmds: dict[str, Command] = {}
terminate_signal: threading.Event = threading.Event()


async def start():
    await init()
    await run()
    await end()


async def init():
    threads.append(generation.core.Core(terminate_signal))
    threads.append(dsc.core.Core(terminate_signal))
    for thread in threads:
        thread.start()
    for file in os.listdir("./commands"):
        if ".py" not in file:
            continue
        cmd = Command(file)
        cmds[cmd.cmd] = cmd


async def run():
    while True:
        try:
            user_input = input("Command: ").lower()
            if user_input not in cmds.keys():
                print("No command found.")
                continue
            return_value = cmds[user_input].execute()
            if callable(return_value):
                return_value()
            elif type(return_value) is EndSignal:
                break
            else:
                print(return_value)
        except UnicodeDecodeError:
            break



async def end():
    alive = True
    print("Terminating process!")
    terminate_signal.set()
    while alive:
        for thread in threads:
            if thread.is_alive():
                alive = True
                break
            alive = False
        time.sleep(1)
    print("Terminated sub-processes!")