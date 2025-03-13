import asyncio
import importlib.util
import logging
import os.path
import shutil
import sys
import threading
import time
import tracemalloc
import uuid
from datetime import datetime

from main.exceptions import *


def list_dir(folder: str = "."):
    to_return = []
    for file in os.listdir(folder):
        if file.endswith(".deleted"):
            pass
        else:
            to_return.append(file)
    return to_return


async def clear_additional_logs(logs_folder):
    logs = []
    for file in list_dir(logs_folder):
        if ".log" in file:
            logs.append(f"{logs_folder}/{file}")
    from main.global_variables import scheduler
    while len(logs) > 5:
        from removalScheduler.core import DeletionReason
        scheduler.delete_file(logs[0], DeletionReason.AUTOMATIC)
        logs.pop(0)
    await scheduler.clear_scheduler()


class LogHandler(logging.FileHandler):
    def __init__(self, core_name: str | None = None, mode: str = "w", log_level: int = logging.DEBUG):
        if core_name is not None:
            super().__init__(filename=f".logs/{core_name}/current.log", encoding='utf-8', mode=mode)
        else:
            super().__init__(filename=f".logs/current.log", encoding='utf-8', mode=mode)
        self.setLevel(log_level)
        self.setFormatter(CustomFormatter())


class CustomFormatter(logging.Formatter):
    format = "[%(asctime)s: %(levelname)s] - %(message)s (%(filename)s:%(lineno)d)"

    FORMATS = {
        logging.DEBUG: format,
        logging.INFO: format,
        logging.WARNING: format,
        logging.ERROR: format,
        logging.CRITICAL: format
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


class Core(threading.Thread):
    def __init__(self, terminate_signal: threading.Event, name: str, loop_enabled: bool = True, mode: str = None):
        """
        Common core for all the modules inside this program. This function is supposed to be overwritten by creating a subclass.
        It has 3 main functions to overwrite with passing to the super class: call, loop, stay_alive.
        It's a subclass of the Thread. It will not block the main thread.
        :param terminate_signal: Event that is given to each core to terminate the entire program if needed.
        :param name: Name of the core file. Overwrite in the subclass or give it a name while initializing. Used in creating log folder etc.
        :param loop_enabled: Decides whether the loop should be activated. Will automatically be set to false if loop() is not overwritten.
        :param mode: Mode for Log Handler. "w" means overwrite, while "a" applies it to the next log.

        :exception TerminateSignalMissing: raised when "terminate_signal" is None.
        :exception CoreNameMissing: raised when "name" is None or an empty string.
        """
        if terminate_signal is None:
            raise TerminateSignalMissing
        if name is None or len(name) == 0:
            raise CoreNameMissing
        self.terminate_signal = terminate_signal
        self.core_name = name
        self.loop_enabled = loop_enabled
        self.__ready: threading.Event = threading.Event()
        self.__logs_folder: str = f".logs/{self.core_name}"
        self.__log_handler: LogHandler = None
        self.__init_logs__(mode if mode is not None else "w")
        tracemalloc.start()
        self.logger.log(logging.INFO, "Module has been initialized.")
        self.logger.log(logging.DEBUG, f"Parameters:")
        self.logger.log(logging.DEBUG, f"  Core Name: {self.core_name}")
        self.logger.log(logging.DEBUG, f"  Loop enabled: {self.loop_enabled}")
        self.logger.log(logging.DEBUG, f"  Logs folder: {self.__logs_folder}")
        super().__init__(target=asyncio.run, daemon=True, args=(self.__call(), ))


    async def __call(self) -> None:
        await asyncio.create_task(self.call())
        await asyncio.create_task(self.__loop())
        await asyncio.create_task(self.stay_alive())

    async def __loop(self):
        while self.loop_enabled and not self.terminate_signal.is_set():
            start_time = time.time()
            await asyncio.create_task(self.loop())
            await asyncio.sleep(1 - time.time() - start_time)

    async def call(self) -> None:
        """
        Coroutine that is first called when the core is created.
        One time only.
        """
        self.logger.log(logging.INFO, "Module has started.")

    async def loop(self) -> None:
        """
        Coroutine that is run every second.
        If not overwritten completely it will disable "loop_enabled" and ultimately disable itself.
        """
        self.loop_enabled = False
        self.set()

    async def stay_alive(self) -> None:
        """
        Coroutine that makes the module stay alive until "terminale_signal" is set.
        Always pass it back to the super class.
        """
        while not self.terminate_signal.is_set():
            await asyncio.sleep(1)

        self.logger.log(logging.INFO, "Clearing all additional logs.")
        try:
            await clear_additional_logs(self.__logs_folder)
        except Exception as e:
            self.logger.log(logging.ERROR, e)

    def set(self) -> None:
        """
        Sets if the module is ready.
        Call the function when module is ready to unlock the main thread.
        """
        self.logger.log(logging.DEBUG, "Module is ready!")
        self.__ready.set()

    def is_set(self) -> bool:
        """
        Returns if the module is ready.
        """
        return self.__ready.is_set()

    async def wait_until_ready(self) -> None:
        """
        It will wait for the current module to send a signal that it is ready.
        Use this coroutine in the main module to wait for the modules to start.
        :return:
        """
        if not self.is_set():
            self.logger.log(logging.DEBUG, "Waiting for the module to be ready.")
        while not self.is_set():
            await asyncio.sleep(1)



    def __init_logs__(self, mode: str):
        if self.core_name not in list_dir(".logs"):
            os.mkdir(self.__logs_folder)
        if "current.log" in list_dir(self.__logs_folder):
            if mode == "a":
                shutil.copyfile(f"{self.__logs_folder}/current.log",
                                f"{self.__logs_folder}/{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log")
            else:
                os.rename(f"{self.__logs_folder}/current.log",
                          f"{self.__logs_folder}/{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log")
        self.__log_handler = LogHandler(core_name=self.core_name, mode=mode)
        self.logger = logging.getLogger(str(uuid.uuid4()))
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(self.__log_handler)


class Cores(list):
    def append(self, core: Core):
        from main.global_variables import logger
        logger.log(logging.INFO, f"Core {core.core_name} has been added to known modules.")
        super().append(core)




class Command:
    """
    Class that allows for python files in the "commands" folder to be executed.
    Other modules too can run this.
    Every file in the commands folder is supposed to have call() function that will be run.
    """
    def __init__(self, file: str):
        """
        Class that allows for python files in the "commands" folder to be executed.
        Other modules too can run this.
        Every file in the commands folder is supposed to have call() function that will be run.
        :param file: File in the commands folder to be run.
        """
        self.cmd = file.removesuffix(".py")
        self.spec = importlib.util.spec_from_file_location(self.cmd, os.path.join("commands", file))
        self.module = importlib.util.module_from_spec(self.spec)

    async def execute(self, **kwargs):
        """
        Runs the python file in the "commands" folder.
        :param kwargs: Parameters to pass down to the call function.
        :return: It will return whatever the call returns.
        """
        self.spec.loader.exec_module(self.module)
        if hasattr(self.module, "call"):
            return self.module.call(**kwargs)
        elif hasattr(self.module, "call_async"):
            return await self.module.call_async(**kwargs)


def worker_input(prompt, output):
    """
    Worker function that handles the blocking input call and puts the result into a queue.
    """
    try:
        # Print prompt and flush output
        sys.stdout.write(prompt)
        sys.stdout.flush()
        # Read input (this call will block until input is given)
        user_input = sys.stdin.readline().rstrip('\n')
        output.put(user_input)
    except Exception:
        output.put(None)