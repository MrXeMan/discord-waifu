import os
from enum import Enum

import discord
from discord import app_commands, ChannelType
from dotenv import load_dotenv

import main.utils

"""
--------------------------------
   CHECKS FOR ROLE PERMISSION
--------------------------------
"""


def channel_has_role(channel: discord.TextChannel | discord.VoiceChannel, role: discord.Role) -> bool:
    """
    Checks if provided role has access to the provided channel.
    :param channel: Channel to check.
    :param role: Role to check.
    :return: Returns if provided role has access to the channel.
    """
    if BOT_OVERWRITE:
        return True
    if role not in channel.changed_roles:
        return False
    return channel.permissions_for(role).view_channel


def channels_has_role(guild: discord.Guild, role: discord.Role) -> list[
    tuple[discord.TextChannel | discord.VoiceChannel | discord.ForumChannel | discord.StageChannel, str]]:
    """
    Checks for every channel in the guild if the provided role has access to it.
    :param guild: Guild to get channels from.
    :param role: Role to check.
    :return: Returns list of tuple that has as first argument a channel that role has access to, as second argument a category in which it is.
    """
    channels = []
    for channel in guild.text_channels:
        if channel_has_role(channel, role):
            channels.append((channel, "text"))
    for channel in guild.voice_channels:
        if channel_has_role(channel, role):
            channels.append((channel, "voice"))
    for channel in guild.channels:
        if channel.type in [ChannelType.text, ChannelType.voice, ChannelType.category]:
            continue
        else:
            if channel_has_role(channel, role):
                channels.append((channel, "other"))
    return channels


def category_has_role(category: discord.CategoryChannel, role: discord.Role) -> bool:
    """
    Checks if provided role has access to the provided category.
    :param category: Category to check.
    :param role: Role to check.
    :return: Returns if provided role has access to the category.
    """
    if BOT_OVERWRITE:
        return True
    if role not in category.changed_roles:
        return False
    return category.permissions_for(role).view_channel


def categories_has_role(guild: discord.Guild, role: discord.Role) -> list[discord.CategoryChannel]:
    """
    Checks for every category in the guild if provided role has access to it.
    :param guild: Guild to get every category from.
    :param role: Role to check.
    :return: Returns list of categories that the role has access to.
    """
    categories = []
    for channel in guild.channels:
        if type(channel) is discord.CategoryChannel and \
                category_has_role(channel, role):
            categories.append(channel)
    return categories


"""
-----------------------------
    COMMAND AUTOCOMPLETES
-----------------------------
"""


async def log_file_autocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    from main.global_variables import cmds
    logs: list[str] = await cmds["list_logs"].execute()
    logs.sort(key=lambda log: log.rsplit("\\", maxsplit=1)[1], reverse=True)
    while len(logs) > 25:
        logs.pop(25)
    choices = [app_commands.Choice(name=log_file, value=log_file) for log_file in logs if
               current.lower() in log_file.lower()]
    return choices


async def loaded_extension_autocomplete(interaction: discord.Interaction, current: str) -> list[
    app_commands.Choice[str]]:
    from main import global_variables
    return [app_commands.Choice(name=extension.core_name, value=extension.core_name) for extension in
            global_variables.threads
            if current.lower() in extension.core_name.lower()]


async def unloaded_extension_autocomplete(interaction: discord.Interaction, current: str) -> list[
    app_commands.Choice[str]]:
    extensions = []
    for extension in os.listdir(os.path.join("extensions")):
        ext = await main.utils.get_extension(extension)
        if ext:
            core: str = ext.core.Core.core_name
            from main import global_variables
            if core not in [exts.core_name for exts in global_variables.threads]:
                extensions.append(core)
    return [app_commands.Choice(name=extension, value=extension) for extension in extensions
            if current.lower() in extension.lower()]


"""
-----------------
    UTILITIES
-----------------
"""


def get_self_role_from_interaction(interaction: discord.Interaction):
    """
    Gets role that the bot has in specific interaction.
    :param interaction: Interaction to get guild from.
    :return: Returns the role bot has.
    """
    return get_self_role_from_guild(interaction.guild)


def get_self_role_from_guild(guild: discord.Guild):
    """
    Gets role that the bot has in the guild.
    :param guild: Guild to check for role.
    :return: Returns the role bot has.
    """
    load_dotenv()
    return guild.get_role(int(os.getenv("ROLE_ID")))


async def get_extension_from_folder(extension: str) -> tuple[str, str] | None:
    for e in os.listdir(os.path.join("extensions")):
        ext = await main.utils.get_extension(e)
        if ext:
            core: str = ext.core.Core.core_name
            if core == extension:
                return extension, e
    return None


"""
----------------
    CLASSES    
----------------
"""


class Group(app_commands.Group):
    def __init__(self, bot, *args, **kwargs):
        self.bot = bot
        super().__init__(*args, **kwargs)


"""
-------------
    ENUMS    
-------------
"""


class ReadingLogState(Enum):
    IDLE = 0
    READING = 1
    STOP = 2


"""
-----------------
    VARIABLES
------------------
"""

# BE CAREFUL, THIS CAN CAUSE EXTREME DAMAGE IF NOT USED CORRECTLY!
BOT_OVERWRITE = False
READING_LOG: ReadingLogState = ReadingLogState.IDLE
