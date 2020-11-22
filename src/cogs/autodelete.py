from discord.ext import commands


class AutoDelete(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        message = message.channel.history(limit=1, after=message).flatten()[0]
        if message.author.id == self.bot.user.id:
            await message.delete()

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if after.content.startswith(self.bot.prefix(self.bot, after)):
            await self.bot.process_commands(after)


def setup(bot):
    bot.add_cog(AutoDelete(bot))
