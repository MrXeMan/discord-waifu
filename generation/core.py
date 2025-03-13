import logging
import threading

from main import utils


class Core(utils.Core):

    def __init__(self, terminate_signal: threading.Event):
        super().__init__(terminate_signal, "ollama")

    async def call(self):
        self.set()
        await super().call()

    async def loop(self):
        await super().loop()

    async def stay_alive(self):
        await super().stay_alive()
