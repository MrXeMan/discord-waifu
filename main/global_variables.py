import logging
import threading
import uuid
import removalScheduler

from main.utils import Cores, Command, Requests

threads: Cores = Cores()  # all modules
threads_to_start: dict[int, list[str]] = {}

cmds: dict[str, Command] = {}  # commands from "/commands" folder
terminate_signal: threading.Event = threading.Event()  # global terminate signal
scheduler: removalScheduler.core.Core | None = None

console_enable = False  # if python console should be enabled
no_delete = False  # if True then deletion is on hold and will not be deleted.

logger: logging.Logger = logging.getLogger(str(uuid.uuid4()))  # global logger
logger.setLevel(logging.DEBUG)  # level of logs to save

requests: Requests = Requests(logger)