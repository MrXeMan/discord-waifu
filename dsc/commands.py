import asyncio
import logging
from typing import Literal

from discord.abc import GuildChannel
from discord.app_commands import commands

from dsc.core import Core
from dsc.utils import *


class Utilities(commands.Group):
    def __init__(self, bot: Core.CustomBot, **kwargs) -> None:
        self.bot = bot
        self.logger: logging.Logger = self.bot.logger
        self.get_string = self.bot.core.get_string
        super().__init__(**kwargs)

    @app_commands.command(name="exit", description="Exits completely.")
    async def exit(self, interaction: discord.Interaction):
        self.logger.log(logging.INFO, f"{interaction.user.name} has executed \"{self.name} exit\",")
        from main.global_variables import cmds, terminate_signal
        await interaction.response.send_message(await self.get_string("utils_exit_response"))
        from main.exceptions import EndSignal
        try:
            await cmds["exit"].execute()
        except EndSignal:
            terminate_signal.set()

    @app_commands.command(name="list_logs", description="Lists every log file. Use /utils read_logs to read them.")
    async def list_logs(self, interaction: discord.Interaction):
        self.logger.log(logging.INFO, f"{interaction.user.name} has executed \"{self.name} list_logs\",")
        from main.global_variables import cmds
        await interaction.response.send_message(await self.get_string("utils_list_logs_first_response"))
        logs = await cmds["list_logs"].execute()
        await interaction.edit_original_response(
            content=await self.get_string(
                "utils_list_logs_end_response",
                log_files="\n    " + "\n    ".join(
                    log for log in logs)
            )
        )

    @app_commands.command(name="read_logs", description="Read the log file provided.")
    @app_commands.describe(log_file="Log file")
    @app_commands.autocomplete(log_file=log_file_autocomplete)
    async def read_logs(self, interaction: discord.Interaction, log_file: str):
        self.logger.log(logging.INFO, f"{interaction.user.name} has executed \"{self.name} read_logs\",")
        from main.global_variables import cmds
        await interaction.response.send_message(
            await self.get_string(
                "utils_read_logs_first_response",
                log_file=log_file
            )
        )
        logs: list[str] = await cmds["read_logs"].execute(log_file=log_file)
        if logs[0] == "failed":
            await interaction.edit_original_response(
                content=await self.get_string(
                    "utils_read_logs_failed_response"
                )
            )
        else:
            await interaction.edit_original_response(
                content=await self.get_string(
                    "utils_read_logs_end_response",
                    log_file=log_file
                )
            )
            from dsc import utils
            utils.READING_LOG = ReadingLogState.READING
            log = ""
            i = 0
            while i < len(logs) and utils.READING_LOG == ReadingLogState.READING:
                if len(log + logs[i]) < 2000:
                    log += logs[i]
                    i += 1
                else:
                    if len(log) == 0:
                        i += 1
                        continue
                    await interaction.channel.send(content=log)
                    log = ""
            if len(log) > 0:
                await interaction.channel.send(content=log)
            if utils.READING_LOG == ReadingLogState.STOP:
                await interaction.channel.send(
                    content=await self.get_string(
                        "utils_read_logs_force_stop_response"
                    )
                )
            if utils.READING_LOG in [ReadingLogState.READING, READING_LOG.STOP]:
                utils.READING_LOG = ReadingLogState.IDLE

    @app_commands.command(name="clear_logs", description="Deletes all logs.")
    async def clear_logs(self, interaction: discord.Interaction):
        self.logger.log(logging.INFO, f"{interaction.user.name} has executed \"{self.name} clear_logs\",")
        await interaction.response.send_message(
            await self.get_string(
                "utils_clear_logs_first_response"
            )
        )
        from main.global_variables import cmds
        await cmds["clear_logs"].execute()
        await interaction.edit_original_response(
            content=await self.get_string(
                "utils_clear_logs_end_response"
            )
        )

    @app_commands.command(name="enable_overwrite",
                          description="CAUTION: This enables bot to interact with everything in the guild.")
    async def enable_overwrite(self, interaction: discord.Interaction):
        self.logger.log(logging.INFO, f"{interaction.user.name} has executed \"{self.name} enable_overwrite\".")
        timer = 10
        await interaction.response.send_message(
            await self.get_string(
                "utils_enable_overwrite_first_response",
                timer=timer
            )
        )
        await asyncio.sleep(timer)
        reacted = False
        for reaction in (await interaction.original_response()).reactions:
            users = [user async for user in reaction.users()]
            if interaction.user in users:
                reacted = True
                break
        if reacted:
            await interaction.edit_original_response(
                content=await self.get_string(
                    "utils_enable_overwrite_success_response",
                    name=self.name
                )
            )
            from dsc import utils
            utils.BOT_OVERWRITE = True
        else:
            await interaction.edit_original_response(
                content=await self.get_string(
                    "utils_enable_overwrite_failed_response", timer=timer
                )
            )

    @app_commands.command(name="disable_overwrite",
                          description="This disables bot from interacting with every channel without having role permission.")
    async def disable_overwrite(self, interaction: discord.Interaction):
        self.logger.log(logging.INFO, f"{interaction.user.name} has executed \"{self.name} disable_overwrite\".")
        await interaction.response.send_message(
            await self.get_string(
                "utils_disable_overwrite_response"
            )
        )
        from dsc import utils
        utils.BOT_OVERWRITE = False


class Channels(commands.Group):
    def __init__(self, bot: Core.CustomBot, **kwargs) -> None:
        self.bot = bot
        self.logger: logging.Logger = self.bot.logger
        self.get_string = self.bot.core.get_string
        super().__init__(**kwargs)

    @app_commands.command(name="list", description="Lists all channel that the bot can access.")
    async def list(self, interaction: discord.Interaction):
        self.logger.log(logging.INFO, f"{interaction.user.name} has executed \"{self.name} list\",")
        self_role = get_self_role_from_interaction(interaction)
        await interaction.response.send_message(await self.get_string("channels_list_first_response"))
        if self_role is None:
            await interaction.edit_original_response(
                content=await self.get_string(
                    "channels_list_role_fail"
                )
            )
            return
        text_channels: list[discord.TextChannel] = []
        voice_channels: list[discord.VoiceChannel] = []
        other_channels: list[discord.ForumChannel | discord.StageChannel] = []
        for channel, channel_type in channels_has_role(interaction.guild, self_role):
            match channel_type:
                case "text":
                    text_channels.append(channel)
                case "voice":
                    voice_channels.append(channel)
                case "other":
                    other_channels.append(channel)
        await interaction.edit_original_response(
            content=await self.get_string(
                "channels_list_success_response",
                text_channels=', '.join(
                    channel.name for channel in
                    text_channels) if len(
                    text_channels) > 0 else await self.get_string(
                    "no_channels_found"),
                voice_channels=(', '.join(
                    channel.name for channel in
                    voice_channels)) if len(
                    voice_channels) > 0 else await self.get_string(
                    "no_channels_found"),
                other_channels=(', '.join(
                    channel.name for channel in
                    other_channels)) if len(
                    other_channels) > 0 else await self.get_string(
                    "no_channels_found")
            )
        )

    @app_commands.command(name="add", description="Gives permission for the bot to interact with the channel.")
    @app_commands.describe(channel="Channel you want to add.")
    async def add(self, interaction: discord.Interaction, channel: discord.TextChannel | discord.VoiceChannel):
        self.logger.log(logging.INFO, f"{interaction.user.name} has executed \"{self.name} add\".")
        self_role = get_self_role_from_interaction(interaction)
        await interaction.response.send_message(
            await self.get_string(
                "channels_add_first_response"
            )
        )
        if self_role is None:
            await interaction.edit_original_response(
                content=await self.get_string(
                    "channels_add_role_fail"
                )
            )
            return
        await channel.set_permissions(self_role, view_channel=True)
        await interaction.edit_original_response(
            content=await self.get_string(
                "channels_add_success_response",
                name=self.name
            )
        )

    @app_commands.command(name="remove", description="Removes permission for the bot to interact with the channel.")
    @app_commands.describe(channel="Channel you want to remove.")
    async def remove(self, interaction: discord.Interaction, channel: discord.TextChannel | discord.VoiceChannel):
        self.logger.log(logging.INFO, f"{interaction.user.name} has executed \"{self.name} remove\".")
        self_role = get_self_role_from_interaction(interaction)
        await interaction.response.send_message(
            await self.get_string(
                "channels_remove_first_response"
            )
        )
        if self_role is None:
            await interaction.edit_original_response(
                content=await self.get_string(
                    "channels_remove_role_fail"
                )
            )
            return
        await channel.set_permissions(self_role, view_channel=False)
        await interaction.edit_original_response(
            content=await self.get_string(
                "channels_remove_success_response",
                name=self.name
            )
        )

    @app_commands.command(name="create", description="Creates a channel in the specified category.")
    @app_commands.describe(category="Category in which you want the channel.")
    @app_commands.describe(channel_name="Name you want the channel to have.")
    @app_commands.describe(channel_type="Type you want the channel to be. Default: Text")
    async def create(self, interaction: discord.Interaction, category: discord.CategoryChannel, channel_name: str,
                     channel_type: Literal["text", "voice", "forum", "stage"] = "text"):
        self.logger.log(logging.INFO, f"{interaction.user.name} has executed \"{self.name} create\".")
        self_role = get_self_role_from_interaction(interaction)
        await interaction.response.send_message(
            await self.get_string(
                "channels_create_first_response",
                channel_name=channel_name,
                channel_type=channel_type,
                category_name=category.name
            )
        )
        if self_role is None:
            await interaction.edit_original_response(
                content=await self.get_string(
                    "channels_create_role_fail"
                )
            )
            return
        if not category_has_role(category, self_role):
            await interaction.edit_original_response(
                content=await self.get_string(
                    "channels_create_category_failed",
                    name=self.name
                )
            )
            return
        else:
            for channel in category.channels:
                if channel.name == channel_name:
                    await interaction.edit_original_response(
                        content=await self.get_string(
                            "channels_create_channel_exists"
                        )
                    )
                    return
            channel = None
            match channel_type:
                case "text":
                    channel: GuildChannel = await category.create_text_channel(channel_name)
                case "voice":
                    channel: GuildChannel = await category.create_voice_channel(channel_name)
                case "forum":
                    channel: GuildChannel = await category.create_forum(channel_name)
                case "stage":
                    channel: GuildChannel = await category.create_stage_channel(channel_name)
            await channel.set_permissions(self_role, view_channel=True)
            await interaction.edit_original_response(
                content=await self.get_string(
                    "channels_create_success_response",
                    channel_url=channel.jump_url
                )
            )

    @app_commands.command(name="delete", description="Deletes a channel from specified category.")
    @app_commands.describe(channel="Channel you want to delete.")
    async def delete(self, interaction: discord.Interaction,
                     channel: discord.TextChannel | discord.VoiceChannel | discord.ForumChannel | discord.StageChannel):
        self.logger.log(logging.INFO, f"{interaction.user.name} has executed \"{self.name} delete\".")
        self_role = get_self_role_from_interaction(interaction)
        await interaction.response.send_message(
            await self.get_string(
                "channels_delete_first_response",
                channel_url=channel.jump_url,
                category_name=channel.category.name
            )
        )
        if self_role is None:
            await interaction.edit_original_response(
                content=await self.get_string(
                    "channels_delete_role_fail"
                )
            )
            return
        if category_has_role(channel.category, self_role) and \
                channel_has_role(channel, self_role):
            await channel.delete(reason=f"Deteled by: {interaction.user.name}")
            await interaction.edit_original_response(
                content=await self.get_string(
                    "channels_delete_success_response"
                )
            )
        else:
            await interaction.edit_original_response(
                content=await self.get_string(
                    "channels_delete_category_failed"
                )
            )


class Categories(commands.Group):
    def __init__(self, bot: Core.CustomBot, **kwargs) -> None:
        self.bot = bot
        self.logger: logging.Logger = self.bot.logger
        self.get_string = self.bot.core.get_string
        super().__init__(**kwargs)

    @app_commands.command(name="list", description="Lists all categories that the bot can access.")
    async def list(self, interaction: discord.Interaction):
        self.logger.log(logging.INFO, f"{interaction.user.name} has executed \"{self.name} list\",")
        self_role = get_self_role_from_interaction(interaction)
        await interaction.response.send_message(
            await self.get_string("categories_list_first_response")
        )
        if self_role is None:
            await interaction.edit_original_response(
                content=await self.get_string(
                    "categories_list_role_fail"
                )
            )
            return
        categories: list[discord.CategoryChannel] = categories_has_role(interaction.guild, self_role)
        await interaction.edit_original_response(
            content=await self.get_string(
                "categories_list_success_response",
                categories=(', '.join(category.name for category in categories)) if len(categories) > 0 else await self.get_string("no_categories_found")
            )
        )

    @app_commands.command(name="add",
                          description="Gives permission for the bot to create and delete channels in a category.")
    @app_commands.describe(category="Category you want to add.")
    async def add(self, interaction: discord.Interaction, category: discord.CategoryChannel):
        self.logger.log(logging.INFO, f"{interaction.user.name} has executed \"{self.name} add\",")
        self_role = get_self_role_from_interaction(interaction)
        await interaction.response.send_message(
            await self.get_string("categories_add_first_response")
        )
        if self_role is None:
            await interaction.edit_original_response(
                content=await self.get_string(
                    "categories_add_role_fail"
                )
            )
            return
        await category.set_permissions(self_role, view_channel=True)
        await interaction.edit_original_response(
            content=await self.get_string(
                "categories_add_success_response",
                name=self.name
            )
        )

    @app_commands.command(name="remove",
                          description="Removes permission for the bot to create and delete channels in a category.")
    @app_commands.describe(category="Category you want to remove.")
    async def remove(self, interaction: discord.Interaction, category: discord.CategoryChannel):
        self.logger.log(logging.INFO, f"{interaction.user.name} has executed \"{self.name} remove\",")
        self_role = get_self_role_from_interaction(interaction)
        await interaction.response.send_message(
            await self.get_string(
                "categories_remove_first_response"
            )
        )
        if self_role is None:
            await interaction.edit_original_response(
                content=await self.get_string(
                    "categories_remove_role_fail"
                )
            )
            return
        await category.set_permissions(self_role, view_channel=False)
        await interaction.edit_original_response(
            content=await self.get_string(
                "categories_remove_success_response",
                name=self.name
            )
        )


async def setup(bot: Core.CustomBot):
    bot.tree.add_command(Utilities(bot=bot, name="utils", description="Utility commands."))
    bot.tree.add_command(Channels(bot=bot, name="channel", description="Channel commands."))
    bot.tree.add_command(Categories(bot=bot, name="category", description="Category commands."))
