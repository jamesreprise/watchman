#!/usr/bin/env python3
import discord
import toml
from discord.ext import commands
from datetime import datetime, timedelta, timezone


class Watchman(commands.Bot):
    def __init__(self, config):
        self.config = config
        super().__init__(command_prefix = self.prefix, owner_id = config['settings']['owner_id'])
        self.token = self.config['keys']['discord_bot_token']
        self.colour = self.config['settings']['colour']
        # TODO persist prefixes and silent_guilds.
        self.prefixes = {}
        self.silent_guilds = []
        self.max_messages = self.config['settings']['max_messages']

    def time_now(self):
        return datetime.utcnow().replace(microsecond=0, tzinfo=timezone.utc).isoformat()

    def prefix(self, bot, message):
        config_prefix = self.config['settings']['prefix']
        if message.author == self.owner_id or not message.guild:
            return config_prefix
        else:
            return self.prefixes.get(message.guild.id, config_prefix)

config = toml.load("config.toml")
bot = Watchman(config)


extensions = [
    "cogs.admin",
    "cogs.metacog",
    "cogs.watchman",
    "cogs.autodelete",
    "cogs.panopticon",
    "cogs.errorhandler"]
map(bot.load_extension, extensions)

# Global check on every command.
@bot.check
def exclude_silent_guilds(ctx):
    if not ctx.guild:
        return True
    else:
        return (not ctx.guild.id in ctx.bot.silent_guilds) or (ctx.author.id == ctx.bot.owner_id)

@bot.event
async def on_ready():
    print(f"[{bot.time_now()}] Ready. Logged in as {bot.user}.")
    server_list = [guild.name for guild in bot.guilds]
    print(f"[{bot.time_now()}] Present on {len(server_list)} servers: {server_list}.")
    await bot.change_presence(status=discord.Status.do_not_disturb, activity=discord.Streaming(name="another ultimate weapon.", url="https://www.youtube.com/watch?v=F4fQhHBuvc0"))

bot.run(bot.token)
