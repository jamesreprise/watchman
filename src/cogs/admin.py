from discord.ext import commands


class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.check_any(commands.is_owner(), commands.has_permissions(administrator=True))
    async def prefix(self, ctx):
        """ Sets the prefix to the string given.

        Syntax: prefix [prefix string]"""
        self.bot.prefixes.update({ctx.guild.id: ctx.message.content.split(" ")[1]})

    @commands.is_owner()
    @commands.command()
    async def silence(self, ctx):
        """ Silence any users in the current guild except owner.

        Syntax: silence"""
        self.bot.silent_guilds.append(ctx.guild.id)

    @commands.is_owner()
    @commands.command()
    async def unsilence(self, ctx):
        """ Undo the silence action.

        Syntax: unsilence"""
        self.bot.silent_guilds.remove(ctx.guild.id)

    @commands.is_owner()
    @commands.command()
    async def leave(self, ctx):
        """ Makes the bot leave the server.

        Syntax: leave"""
        await ctx.guild.leave()

    @commands.bot_has_permissions(kick_members=True)
    @commands.is_owner()
    @commands.command()
    async def kick(self, ctx):
        """ Kicks all tagged users from the server.

        Syntax:  kick [User]"""
        for subject in ctx.message.mentions:
            await ctx.guild.kick(subject)

    @commands.bot_has_permissions(ban_members=True)
    @commands.is_owner()
    @commands.command()
    async def ban(self, ctx):
        """ Bans all tagged users from the server. 
        
        Syntax: ban [User]"""
        for subject in ctx.message.mentions:
            await ctx.guild.ban(subject)

    @commands.bot_has_permissions(mute_members=True)
    @commands.is_owner()
    @commands.command()
    async def mute(self, ctx):
        """ Voice mutes all tagged users.
        If no user is tagged, mute every user in the same channel as the command caller. 

        Syntax: mute <User>"""
        if ctx.message.mentions:
            for subject in ctx.message.mentions:
                await subject.edit(mute=True)
        else:
            if ctx.message.author.voice:
                for subject in ctx.message.author.voice.channel.members:
                    if subject.id != self.bot.owner_id:
                        await subject.edit(mute=True)

    @commands.bot_has_permissions(mute_members=True)
    @commands.is_owner()
    @commands.command()
    async def unmute(self, ctx):
        """ Voice unmutes all tagged users.
        If no user is tagged, unmute every user in the same channel as the command caller. 

        Syntax: unmute <User>"""
        if ctx.message.mentions:
            for subject in ctx.message.mentions:
                await subject.edit(mute=False)
        else:
            if ctx.message.author.voice:
                for subject in ctx.message.author.voice.channel.members:
                    if subject.id != self.bot.owner_id:
                        await subject.edit(mute=False)

    @commands.bot_has_permissions(manage_channels=True)
    @commands.is_owner()
    @commands.command()
    async def purge(self, ctx):
        """ Deletes the channel the command is called in and re-creates it. 

        Will result in loss of permissions or topic data. 

        Syntax: purge"""
        channel = ctx.channel
        await ctx.channel.delete()
        await channel.category.create_text_channel(channel.name)

    @commands.bot_has_permissions(manage_channels=True)
    @commands.is_owner()
    @commands.command()
    async def delete(self, ctx):
        """ Deletes the channel the command is called in. 

        Syntax: delete"""
        await ctx.channel.delete()


def setup(bot):
    bot.add_cog(Admin(bot))
