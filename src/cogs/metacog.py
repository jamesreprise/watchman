from discord.ext import commands


class MetaCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.is_owner()
    @commands.command()
    async def load(self, ctx):
        """ Loads a cog. 

        Syntax: load [Cog]"""
        self.bot.load_extension("cogs.{}".format(ctx.message.content[6::]))
        await ctx.send("Cog '{}' has been loaded.".format(ctx.message.content[6::]))

    @commands.is_owner()
    @commands.command()
    async def unload(self, ctx):
        """ Unloads a cog. 

        Syntax: unload [Cog]"""
        self.bot.unload_extension("cogs.{}".format(ctx.message.content[8::]))
        await ctx.send("Cog '{}' has been unloaded.".format(ctx.message.content[8::]))

    @commands.is_owner()
    @commands.command()
    async def reload(self, ctx):
        """ Reloads a cog. 

        Syntax: reload <Cog>"""
        if len(ctx.message.content) < 8:
            for extension in self.bot.extensions:
                self.bot.reload_extension(extension)
            await ctx.send("All cogs reloaded.")
        else:
            self.bot.reload_extension(
                "cogs.{}".format(ctx.message.content[8::]))
            await ctx.send("Cog '{}' has been reloaded.".format(ctx.message.content[8::]))


def setup(bot):
    bot.add_cog(MetaCog(bot))
