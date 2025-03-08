import asyncio
import importlib.util
import os.path
import threading


class Core(threading.Thread):
    def __init__(self, terminate_signal: threading.Event, name: str):
        self.terminate_signal = terminate_signal
        self.name = name
        super().__init__(target=asyncio.run, daemon=True, args=(self.call(), ))

    async def call(self):
        await asyncio.create_task(self.__loop())
        await asyncio.create_task(self.stay_alive())

    async def stay_alive(self):
        while not self.terminate_signal.is_set():
            await asyncio.sleep(1)
            print("STAY ALIVE!")

    async def __loop(self):
        while not self.terminate_signal.is_set():
            await self.loop()
            await asyncio.sleep(1)

    async def loop(self):
        pass


class Command:
    def __init__(self, file: str):
        self.cmd = file.removesuffix(".py")
        self.spec = importlib.util.spec_from_file_location(self.cmd, os.path.join("commands", file))
        self.module = importlib.util.module_from_spec(self.spec)

    def execute(self):
        self.spec.loader.exec_module(self.module)
        if hasattr(self.module, "call"):
            return self.module.call()


class EndSignal:
    def __int__(self):
        return -1