import asyncio
import importlib.util
import inspect
import logging
import os.path
import pkgutil
import shutil
import sys
import threading
import time
import tracemalloc
import uuid
from collections.abc import Iterable
from datetime import datetime
from typing import Any

import yaml

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
    core_name = ""
    requestables = {}
    def __init__(self, terminate_signal: threading.Event, mode: str = "w", logger_name: str | None = None):
        """
        Common core for all the modules inside this program. This function is supposed to be overwritten by creating a subclass.
        It has 3 main functions to overwrite with passing to the super class: call, loop, stay_alive.
        It's a subclass of the Thread. It will not block the main thread.
        :param terminate_signal: Event that is given to each core to terminate the entire program if needed.
        :param mode: Mode for Log Handler. "w" means overwrite, while "a" applies it to the next log.

        :exception TerminateSignalMissing: raised when "terminate_signal" is None.
        :exception CoreNameMissing: raised when "name" is None or an empty string.
        """
        if terminate_signal is None:
            raise TerminateSignalMissing
        if self.core_name is None or len(self.core_name) == 0:
            raise CoreNameMissing
        tracemalloc.start()
        self.__terminate_signal = terminate_signal
        self.__ready: threading.Event = threading.Event()
        self.__logs_folder: str = f".logs/{self.core_name}"
        self.__log_handler: LogHandler = None
        self.__init_logs__(mode, logger_name)
        self.logger.log(logging.INFO, "Module has been initialized.")
        self.logger.log(logging.DEBUG, f"Parameters:")
        self.logger.log(logging.DEBUG, f"  Core Name: {self.core_name}")
        self.logger.log(logging.DEBUG, f"  Logs folder: {self.__logs_folder}")
        super().__init__(target=self.__start, daemon=True)


    def __start(self):
        asyncio.run(self.__call())


    async def __call(self) -> None:
        threading.Thread(target=self.__get_requests, daemon=True).start()
        await asyncio.create_task(self.call())
        await asyncio.create_task(self.__loop())
        await asyncio.create_task(self.stay_alive())

    async def __loop(self):
        while not self.killed():
            start_time = time.time()
            await asyncio.create_task(self.loop())
            await asyncio.sleep(1 - (time.time() - start_time))

    async def call(self) -> None:
        """
        Coroutine that is first called when the core is created.
        One time only.
        """
        self.logger.log(logging.INFO, "Module has started.")

    async def loop(self) -> None:
        """
        Coroutine that is run every second.
        """
        self.set()

    async def stay_alive(self) -> None:
        """
        Coroutine that makes the module stay alive until "terminale_signal" is set.
        Always pass it back to the super class.
        """
        while not self.killed():
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
        if self.is_set():
            return
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
            return
        while not self.is_set():
            await asyncio.sleep(1)

    def __init_logs__(self, mode: str, logger_name):
        if self.core_name not in list_dir(".logs"):
            os.mkdir(self.__logs_folder)
        if "current.log" in list_dir(self.__logs_folder) and mode is not None:
            if mode == "a":
                shutil.copyfile(f"{self.__logs_folder}/current.log",
                                f"{self.__logs_folder}/{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log")
            else:
                os.rename(f"{self.__logs_folder}/current.log",
                          f"{self.__logs_folder}/{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log")
        self.__log_handler = LogHandler(core_name=self.core_name, mode=mode if mode is not None else "a")
        self.logger = logging.getLogger(logger_name if logger_name is not None else str(uuid.uuid4()))
        if self.__log_handler not in self.logger.handlers:
            self.logger.setLevel(logging.DEBUG)
            self.logger.addHandler(self.__log_handler)

    async def get_locale(self):
        locale = os.path.join(os.path.dirname(os.path.realpath(inspect.getfile(self.__class__))), "locale_us.yaml")
        if not os.path.exists(locale):
            self.logger.log(logging.INFO, "Locale doesn't exists for this module.")
            self.logger.log(logging.DEBUG, f"Locale path: {locale}")
            self.logger.log(logging.DEBUG, f"Current directory: {os.curdir}")
            return {}
        with open(locale, "r") as file:
            return yaml.safe_load(file)

    async def get_string(self, target: str, **replaces):
        try:
            to_return = (await self.get_locale())[target]
        except KeyError:
            return target
        if type(to_return) is not str:
            return "THIS SHOULD NOT HAPPEN! PLEASE CONTANT HELP FOR THIS BOT ON WHAT HAPPENED!"
        for to_replace in replaces.keys():
            to_return = to_return.replace(f"%{to_replace}%", str(replaces[to_replace]))
        to_return = to_return.replace("\n ", "\n")
        return to_return

    async def unload(self):
        self.logger.log(logging.INFO, "Unloading extension.")
        self.__terminate_signal = threading.Event()
        self.__terminate_signal.set()
        from main import global_variables
        if self in global_variables.threads:
            global_variables.threads.remove(self)
        while self.is_alive():
            self.logger.log(logging.DEBUG, "Waiting for extension to be killed.")
            await asyncio.sleep(1)
        self.logger.log(logging.INFO, "Extension was killed!")

    def killed(self):
        return self.__terminate_signal.is_set()

    def kill(self):
        self.__terminate_signal.set()

    def __get_requests(self):
        while not self.killed():
            asyncio.run(self.get_requests())
            time.sleep(1)

    async def get_requests(self):
        from main import global_variables
        try:
            self.logger.log(logging.DEBUG, "Checking for new requests!")
            for request in global_variables.requests[self.core_name]:
                global_variables.requests.remove(request)
                if request.function_name in self.requestables.keys():
                    if "core" in inspect.getfullargspec(self.requestables[request.function_name][0]).annotations.keys():
                        request.arguments["core"] = self
                    if inspect.iscoroutinefunction(self.requestables[request.function_name][0]):
                        try:
                            request.response(await self.requestables[request.function_name][0](**request.arguments))
                        except Exception as e:
                            print(e)
                            self.logger.log(logging.ERROR, e, exc_info=e)
                        finally:
                            request.set()
                    elif inspect.isfunction(self.requestables[request.function_name][0]):
                        try:
                            request.response(self.requestables[request.function_name][0](**request.arguments))
                        except Exception as e:
                            print(e)
                            self.logger.log(logging.ERROR, e, exc_info=e)
                        finally:
                            request.set()
                else:
                    request.response(f"No function found by the name of {request.function_name}")
        except ValueError as e:
            print(e)

    @classmethod
    def requestable(cls, func):
        cls.requestables[func.__name__] = (func, True)
        return func

    @classmethod
    def not_toolable(cls, func):
        cls.requestables[func.__name__] = (func, False)
        return func

    @classmethod
    def get_requestable(cls):
        return cls.requestables


class Cores(list[Core]):
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


class Request:
    def __init__(self, source: str, destination: str, function_name: str, arguments: dict[str, Any] | None):
        if source is None or destination is None or function_name is None:
            raise IncompleteRequest
        self.request_id = uuid.uuid4()
        self.source_name = source
        self.destination_name = destination
        self.function_name = function_name
        self.arguments = arguments
        self.__responded = threading.Event()
        self.__response = None
        from main import global_variables
        global_variables.requests.append(self)

    def __str__(self):
        return f"<{self.request_id}>: source: {self.source_name}, destination: {self.destination_name}, function_name:{self.function_name}, arguments: {self.arguments}"

    def set(self):
        self.__responded.set()

    def is_set(self):
        return self.__responded.is_set()

    def response(self, response):
        self.__response = response
        self.set()

    async def wait_for_response(self):
        while not self.is_set():
            await asyncio.sleep(1)

    def get_response(self):
        return self.__response


def get_tools():
    requestables = []
    for requestable in Core.get_requestable().keys():
        if Core.get_requestable()[requestable][1]:
            requestables.append(Core.get_requestable()[requestable][0])
    return requestables


class Requests(list[Request]):
    def __init__(self, logger: logging.Logger):
        logger.log(logging.INFO, "Created new Requests list.")
        super().__init__()

    def __getitem__(self, core_name: str) -> list[Request]:
        to_return = []
        for request in self:
            if request.destination_name == core_name:
                to_return.append(request)
        return to_return

    def __iadd__(self, other: Request | Iterable[Request]) -> None:
        if isinstance(other, Iterable):
            self.extend(other)
        else:
            self.append(other)

    def __str__(self):
        return f"<{self.__class__}>: [{', '.join(self.__iter__().__str__())}]"

    def append(self, request: Request):
        from main.global_variables import logger
        logger.log(logging.INFO, f"Added new request: {request}")
        super().append(request)

    def extend(self, requests: Iterable[Request]):
        for request in requests:
            self.append(request)


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


async def init_extension(extension: str,  **kwargs):
    from main.global_variables import threads, terminate_signal
    from main.global_variables import logger
    package = await get_extension(extension)
    if package is None:
        return
    try:
        core = package.core.Core(terminate_signal, **kwargs)
        threads.append(core)
        logger.log(logging.INFO, f"Loaded extension: {core.core_name}!")
        return core
    except Exception as e:
        logger.log(logging.ERROR, f"Couldn't load: {extension}!")
        logger.log(logging.ERROR, e, exc_info=e)
        return


async def get_extension(extension: str):
    from main.global_variables import logger
    if not os.path.isdir(os.path.join("extensions", extension)) or "__" in extension:
        return
    try:
        package_name = f"extensions.{extension}"
        if package_name in sys.modules:
            importlib.reload(sys.modules[package_name])
        package = importlib.import_module(package_name)
        for _, module_name, _ in pkgutil.walk_packages(package.__path__):
            if f"{package_name}.{module_name}" in sys.modules:
                importlib.reload(sys.modules[f"{package_name}.{module_name}"])
            importlib.import_module(f"{package_name}.{module_name}")
    except AttributeError as e:
        logger.log(logging.ERROR, "Failed to get the extension to load: %s", exc_info=e)
        return
    if not hasattr(package, "core"):
        logger.log(logging.ERROR, f"Couldn't load: {extension} - as it doesn't have a core file.")
        return
    core_module = importlib.import_module(f"{package_name}.core")
    if not hasattr(core_module, "Core"):
        logger.log(logging.ERROR, f"Couldn't load: {extension} - as the core file doesn't have a Core implemented.")
        return
    if not issubclass(getattr(core_module, "Core"), Core):
        logger.log(logging.ERROR,
                   f"Couldn't load: {extension} - as the core file doesn't use a subclass of Core from main.utils!")
        return
    return package


def add_thread_to_start(extension: str, time: int = 0):
    from main import global_variables
    if time < 0:
        time = 10
    if time not in global_variables.threads_to_start.keys():
        global_variables.threads_to_start[time] = []
    global_variables.threads_to_start[time].append(extension)
