from discord.ext import commands


class AutoDelete(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_raw_message_delete(self, ctx):
        """ Checks if a user removed a command call, removes the response. """
        info = await self.bot.application_info()

        if ctx.cached_message:
            messages = await self.bot.get_channel(ctx.channel_id).history(limit=1, after=ctx.cached_message).flatten()
            for message in messages:
                if message.author.id == info.id:
                    await message.delete()
        else:
            messages = await self.bot.get_channel(ctx.channel_id).history(limit=1).flatten()
            for message in messages:
                if message.author.id == info.id:
                    before_messages = await self.bot.get_channel(ctx.channel_id).history(limit=1, before=message).flatten()
                    await message.delete()


def setup(bot):
    bot.add_cog(AutoDelete(bot))
