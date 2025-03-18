import asyncio
import logging
import os
import threading

import discord
from discord.ext import commands
from dotenv import load_dotenv

from main import utils


class Core(utils.Core):
    core_name = "discord"
    class CustomBot(commands.Bot):
        def __init__(self, core: utils.Core):
            self.bg_task = None
            self.core = core
            self.logger = core.logger
            super().__init__(command_prefix=">>", intents=discord.Intents.all())

        async def setup_hook(self) -> None:
            await self.load_extension(self.__module__.rsplit(".", maxsplit=1)[0]+".commands")
            self.bg_task = self.loop.create_task(self.self_close())

        async def on_ready(self):
            self.logger.log(logging.INFO, f"Logged on as {self.user}")

            guild_id = os.getenv("GUILD_ID")
            self.tree.copy_global_to(guild=discord.Object(id=guild_id))
            await self.tree.sync(guild=discord.Object(id=guild_id))

            self.core.set()

        async def on_message(self, message: discord.Message):
            if message.author == self.user:
                return
            print(
                f"""New message:
        Author: {message.author.display_name}
        Channel: {message.channel.name}
        Content: {message.content}
    """)
            await self.process_commands(message)

        async def self_close(self):
            await self.wait_until_ready()
            while not self.core.killed():
                await asyncio.sleep(1)
            await self.close()

    def __init__(self, terminate_signal: threading.Event, **kwargs):
        super().__init__(terminate_signal, logger_name="discord",  **kwargs)
        self.bot: Core.CustomBot = None

    async def call(self):
        self.bot: Core.CustomBot = Core.CustomBot(self)
        from dotenv import load_dotenv
        load_dotenv()
        bot_token = os.getenv("BOT_TOKEN")
        await super().call()
        await self.bot.start(token=bot_token)

    async def stay_alive(self):
        await super().stay_alive()
        await self.bot.close()

