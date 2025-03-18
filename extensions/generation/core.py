import logging
import os
import threading

from dotenv import load_dotenv
from ollama import AsyncClient

from extensions.generation.utils import *
from main import utils


class Core(utils.Core):
    core_name = "ollama"

    def __init__(self, terminate_signal: threading.Event, **kwargs):
        load_dotenv()
        self.__model_name = os.getenv("T2T_MODEL")
        self.__options = {
            "temperature": 0.7,
            "top_p": 0.9,
            "max_tokens": 300
        }
        self.messages = Messages(self)
        super().__init__(terminate_signal, **kwargs)
        self.__preload_model()
        self.__client = AsyncClient()

    async def call(self):
        await init_discord_commands(self)
        self.set()
        await super().call()

    def __preload_model(self, **kwargs):
        self.logger.log(logging.INFO, f"Preloading model: {self.__model_name}")
        ollama.generate(model=self.__model_name, prompt="", options=self.__options, **kwargs)
        self.logger.log(logging.INFO, f"Preloaded model: {self.__model_name}")

    async def chat_model(self, guild: discord.Guild, text: str,
                         role: Literal['user', 'assistant', 'system', 'tool'] = "user",
                         images: Optional[Sequence[Image]] = None) -> ollama.Message:
        self.messages.add_message_args(guild=guild, text=text, role=role, images=images)
        tools = utils.get_tools()
        response = await self.__client.chat(model=self.__model_name, messages=self.messages[guild], tools=tools, options=self.__options)
        while response.message.tool_calls:
            for tool in response.message.tool_calls:
                if function_call := self.requestables.get(tool.function.name)[0]:
                    output = function_call(**tool.function.arguments)
                    self.messages.add_message_args(guild=guild, text=str(output), role="tool")
            response = await AsyncClient().chat(model=self.__model_name, messages=self.messages[guild], tools=tools, options=self.__options)
        self.messages.add_message(guild, message=response.message)
        return response.message