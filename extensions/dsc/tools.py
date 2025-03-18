import logging
import os

import discord.app_commands
from extensions.dsc.utils import Group

from extensions.dsc.core import Core


@Core.requestable
def dummy_function():
    """
    Function that returns a basic string.
    """
    return "This is requestable dummy function from discord extension."


@Core.not_toolable
async def create_command(core: Core, category_name: str, command: discord.app_commands.Command):
    guild_id = os.getenv("GUILD_ID")
    core.logger.log(logging.DEBUG, f"Adding new command: {command.name} to category: {category_name}")
    for group in core.bot.tree.get_commands():
        if not isinstance(group, discord.app_commands.Group):
            continue
        if group.name == category_name:
            core.logger.log(logging.DEBUG, f"Successfully found the group. Adding...")
            group.add_command(command)
            await core.bot.tree.sync(guild=discord.Object(id=guild_id))
            return
    core.logger.log(logging.DEBUG, f"No group found, creating new and adding.")
    group = Group(bot=core.bot, name=category_name, description=f"Special made category by {category_name} extension.")
    group.add_command(command)
    core.bot.tree.add_command(group)
    try:
        synced = await core.bot.tree.sync(guild=discord.Object(id=guild_id))
    except Exception:
        synced = None
    core.logger.log(logging.DEBUG, f"Created the group and added it to synced: {synced}")


@Core.not_toolable
async def create_group(core: Core, group: Group):
    guild_id = os.getenv("GUILD_ID")
    core.bot.tree.add_command(group)
    await core.bot.tree.sync(guild=discord.Object(id=guild_id))