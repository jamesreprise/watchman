from discord.ext import commands
import traceback


class ErrorHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        #if not isinstance(error, commands.errors.CheckFailure) or not isinstance(error, commands.errors.CommandNotFound):
            #await ctx.send("I'm sorry {}, I'm afraid I can't do that.".format(ctx.message.author.nick if ctx.message.author.nick else ctx.message.author.name))
        print(error)

def setup(bot):
    bot.add_cog(ErrorHandler(bot))
