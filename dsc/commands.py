import logging
import os

import discord
from discord import app_commands
from discord.app_commands import commands

from dsc import core


def channel_has_role(channel: discord.TextChannel | discord.VoiceChannel, role: discord.Role) -> bool:
    if role not in channel.changed_roles:
        return False
    return channel.permissions_for(role).view_channel


def channels_has_role(guild: discord.Guild, role: discord.Role) -> list[tuple[discord.TextChannel | discord.VoiceChannel, str]]:
    channels = []
    for channel in guild.text_channels:
        if channel_has_role(channel, role):
            channels.append((channel, "text"))
    for channel in guild.voice_channels:
        if channel_has_role(channel, role):
            channels.append((channel, "voice"))
    return channels


async def log_file_autocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    from main.global_variables import cmds
    logs: list[str] = await cmds["list_logs"].execute()
    return [app_commands.Choice(name=log_file, value=log_file) for log_file in logs if current.lower() in log_file.lower()]


class Commands(commands.Group):
    def __init__(self, bot: core.CustomBot, **kwargs) -> None:
        self.bot = bot
        self.logger: logging.Logger = self.bot.logger
        super().__init__(**kwargs)

    @app_commands.command(name="exit", description="Exits completely.")
    async def exit(self, interaction: discord.Interaction):
        self.logger.log(logging.INFO, f"{interaction.user.name} has executed \"utils exit\",")
        from main.global_variables import cmds, terminate_signal
        await interaction.response.send_message("Exit signal sent. Shutting down!")
        from main.exceptions import EndSignal
        try:
            await cmds["exit"].execute()
        except EndSignal:
            terminate_signal.set()

    @app_commands.command(name="list", description="Lists all channel that the bot can access.")
    async def list(self, interaction: discord.Interaction):
        self.logger.log(logging.INFO, f"{interaction.user.name} has executed \"utils list\",")
        from dotenv import load_dotenv
        load_dotenv()
        self_role = interaction.guild.get_role(int(os.getenv("ROLE_ID")))
        await interaction.response.send_message("Listing all accessable channels...")
        if self_role is not None:
            text_channels: list[discord.TextChannel] = []
            voice_channels: list[discord.VoiceChannel] = []
            for channel, channel_type in channels_has_role(interaction.guild, self_role):
                if channel_type == "text":
                    text_channels.append(channel)
                else:
                    voice_channels.append(channel)
            await interaction.edit_original_response(content=
                                                     f"""
Text channels: {', '.join(channel.name for channel in text_channels)}
Voice channels: {', '.join(channel.name for channel in voice_channels)}
-# Bot will automatically reply only on these channels. Bot will only respond to commands on other channels.
-# If you want bot to respond elsewhere too, add it's role to the channel with \"View channel\" permission.
"""
                                                     )
        else:
            await interaction.edit_original_response(content="Can't listen the channels. INVALID_ROLE")


    @app_commands.command(name="add", description="Gives permission for the bot to interact with the channel.")
    @app_commands.describe(channel="Channel you want to add.")
    async def add(self, interaction: discord.Interaction, channel: discord.TextChannel | discord.VoiceChannel):
        self.logger.log(logging.INFO, f"{interaction.user.name} has executed \"utils add\",")
        if channel is None:
            await interaction.response.send_message("Invalid channel.")
            return
        from dotenv import load_dotenv
        load_dotenv()
        self_role = interaction.guild.get_role(int(os.getenv("ROLE_ID")))
        if self_role is not None:
            await interaction.response.send_message("Editing permission for the channel...")
            await channel.set_permissions(self_role, view_channel=True)
            await interaction.edit_original_response(content="Edited the permission for the channel. You can check using /utils list")

    @app_commands.command(name="list_logs", description="Lists every log file. Use /utils read_logs to read them.")
    async def list_logs(self, interaction: discord.Interaction):
        self.logger.log(logging.INFO, f"{interaction.user.name} has executed \"utils list_logs\",")
        from main.global_variables import cmds
        await interaction.response.send_message("Getting all the logs...")
        logs = await cmds["list_logs"].execute()
        await interaction.edit_original_response(content=f"Here are all the log files:\n    " + "\n    ".join(log for log in logs))

    @app_commands.command(name="read_logs", description="Read the log file provided.")
    @app_commands.describe(log_file="Log file")
    @app_commands.autocomplete(log_file=log_file_autocomplete)
    async def read_logs(self, interaction: discord.Interaction, log_file: str):
        self.logger.log(logging.INFO, f"{interaction.user.name} has executed \"utils read_logs\",")
        from main.global_variables import cmds
        await interaction.response.send_message("Reading provided log file...")
        logs = await cmds["read_logs"].execute(log_file=log_file)
        if logs[0] == "failed":
            await interaction.edit_original_response(content=logs[1])
        else:
            await interaction.edit_original_response(content="Here are all the logs:\n    " + "    ".join(log for log in logs))

    @app_commands.command(name="clear_logs", description="Deletes all logs.")
    async def clear_logs(self, interaction: discord.Interaction):
        self.logger.log(logging.INFO, f"{interaction.user.name} has executed \"utils clear_logs\",")
        await interaction.response.send_message("Deleting all logs...")
        from main.global_variables import cmds
        await cmds["clear_logs"].execute()
        await interaction.edit_original_response(content="All logs successfully deleted.")


async def setup(bot: core.CustomBot):
    bot.tree.add_command(Commands(bot=bot, name="utils", description="Utility commands."))
