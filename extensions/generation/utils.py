import logging
from typing import Literal, Optional, Sequence

import discord
import ollama
from ollama import Image

import extensions.dsc.core
from main.utils import Request


class Messages(dict[discord.Guild, list[ollama.Message]]):
    def __init__(self, core):
        super().__init__()
        self.core = core

    def add_guilds(self, guilds: list[discord.Guild]):
        for guild in guilds:
            self.add_guild(guild)

    def add_guild(self, guild: discord.Guild):
        if guild not in self.keys():
            self.core.logger.log(logging.DEBUG, f"Adding new Messages subsection for guild: {guild.name}")
            self[guild] = []

    def add_message(self, guild: discord.Guild, message: ollama.Message):
        self.core.logger.log(logging.DEBUG, f"Adding new message to Messages subsection: {guild.name} - {str(message)}")
        self.add_guild(guild)
        if len(message.content) > 0:
            self[guild].append(message)

    def add_message_args(self, guild: discord.Guild, text: str, role: Literal['user', 'assistant', 'system', 'tool'] = "user", images: Optional[Sequence[Image]] = None):
        self.add_message(guild, ollama.Message(role=role, content=text, images=images))


async def init_discord_commands(core: extensions.dsc.core.Core):
    core.logger.log(logging.DEBUG, f"Initializing commands for discord.")

    async def chat(interaction: discord.Interaction, text: str):
        from extensions.generation import tools
        await interaction.response.send_message(
            content="Trying to send a message to AI..."
        )
        response = (await tools.chat_with_model(core, interaction.guild, text)).content
        await interaction.edit_original_response(
            content=str(response)
        )

    from discord.app_commands import Command
    Request(
        source=core.core_name,
        destination="discord",
        function_name="create_command",
        arguments={
            "category_name": "ollama",
            "command": Command(name=chat.__name__, description="Custom ollama command.", callback=chat)
        }
    )