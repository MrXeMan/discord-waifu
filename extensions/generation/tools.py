import discord

from extensions.generation.core import Core


@Core.not_toolable
async def chat_with_model(core: Core, guild: discord.Guild, text: str):
    return await core.chat_model(guild=guild, text=text)
