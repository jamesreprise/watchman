# TODO:
#
# A 'network' contains a group of servers which all share information through some channel per server.
# 
# Networks can be open, closed, or private.
# 
# Closed networks require an invite code to join. 


import psycopg2
import discord
import toml
from psycopg2 import sql
from discord.ext import commands
from datetime import datetime, timedelta

connection = psycopg2.connect("dbname=watchman user=watchman")
cursor = connection.cursor()

config = toml.load("config.toml")

def is_watchman_channel():
    def predicate(ctx):
        if ctx.author.id == config['ids']['owner']:
            return True
        cursor.execute(sql.SQL("SELECT channel_id FROM wm_servers WHERE guild_id = %s;"),
        [str(ctx.guild.id)])
        if int(cursor.fetchone()[0]) == ctx.channel.id:
            return True
        return False
    return commands.check(predicate)


class Watchman(commands.Cog):
    def __init__(self, bot, connection):
        self.bot = bot
        self.connection = connection
        self.cursor = self.connection.cursor()
        self.colour = 0X9DD6F3
        self.create_tables_if_not_exist()


    def create_tables_if_not_exist(self):
        self.cursor.execute(sql.SQL("CREATE TABLE IF NOT EXISTS wm_networks (network_id SERIAL PRIMARY KEY, name TEXT, state TEXT);"))
        self.cursor.execute(sql.SQL("CREATE TABLE IF NOT EXISTS wm_servers (guild_id TEXT PRIMARY KEY, channel_id TEXT);"))
        self.cursor.execute(sql.SQL("CREATE TABLE IF NOT EXISTS wm_network_invites (invite_id SERIAL PRIMARY KEY, network_id TEXT REFERENCES wm_networks(network_id), invite_code TEXT, expiry DATE);"))
        self.cursor.execute(sql.SQL("CREATE TABLE IF NOT EXISTS wm_enrollments (enrollment_id SERIAL PRIMARY KEY, network_id INTEGER REFERENCES wm_networks(network_id), guild_id TEXT REFERENCES wm_servers(guild_id));"))
        self.cursor.execute(sql.SQL("CREATE TABLE IF NOT EXISTS wm_notes (note_id SERIAL PRIMARY KEY, author_id TEXT, guild_id TEXT REFERENCES wm_servers(guild_id), user_id TEXT, note TEXT, date TEXT);"))
        self.cursor.execute(sql.SQL("CREATE TABLE IF NOT EXISTS wm_bans (ban_id SERIAL PRIMARY KEY, author_id TEXT, guild_id TEXT REFERENCES wm_servers(guild_id), user_id TEXT, ban_reason TEXT, date TEXT);"))
        self.connection.commit()


    def watchman_embed(self, description):
        embed = discord.Embed(colour=self.colour, description=description)
        embed.set_author(name="Watchman", icon_url=self.bot.user.avatar_url)
        embed.set_footer(text=f"{self.bot.time_now()}")
        return embed


    async def get_ban_tuple(self, guild, user_banned):
        try:
            async for log in guild.audit_logs(action=discord.AuditLogAction.ban):
                if log.target == user_banned:
                    return (log.user, log.reason)
            return ("Unknown", "Unknown")
        except Exception as e:
            return ("Unknown", "Unknown")


    async def get_info(self, user):
        self.cursor.execute(sql.SQL("SELECT author_id, guild_id, ban_reason, date FROM wm_bans WHERE user_id = %s;"),
        [str(user.id)])
        bans = self.cursor.fetchall()
        ban_field_desc = ""
        if bans != []:
            for ban in bans:
                author = await self.bot.fetch_user(int(ban[0]))
                guild = [guild for guild in self.bot.guilds if guild.id == int(ban[1])][0]
                ban_field_desc += f"{ban[3]} - [{guild.name}] {author.name}#{author.discriminator}: \"{ban[2]}\"."
        self.cursor.execute(sql.SQL("SELECT author_id, guild_id, note, date FROM wm_notes WHERE user_id = %s;"),
        [str(user.id)])
        notes = self.cursor.fetchall()
        note_field_desc = ""
        if notes != []:
            for note in notes:
                author = await self.bot.fetch_user(int(note[0]))
                guild = [guild for guild in self.bot.guilds if guild.id == int(note[1])][0]
                note_field_desc += f"{note[3]} - [{guild.name}] {author.name}#{author.discriminator}: \"{note[2]}\"."
        if not bans and not notes:
            embed = self.watchman_embed("This user has no notes or bans.")
        else:
            embed = self.watchman_embed(f"Information for {user.name}#{user.discriminator}:")
            if ban_field_desc:
                embed.add_field(name="Bans", value=ban_field_desc)
            if note_field_desc:
                embed.add_field(name="Notes", value=note_field_desc)
        return embed


    def del_note(self, guild, user, author):
        self.cursor.execute(sql.SQL("SELECT note_id FROM wm_notes WHERE author_id = %s AND user_id = %s AND guild_id = %s;"),
        [str(author.id), str(user.id), str(guild.id)])

        result = self.cursor.fetchall()
        if result != []:
            self.cursor.execute(sql.SQL("DELETE FROM wm_notes WHERE author_id = %s AND user_id = %s AND guild_id = %s;"),
            [str(author.id), str(user.id), str(guild.id)])
            self.connection.commit()
            return True
        return False


    def add_note(self, guild, user, author, note):
        self.cursor.execute(sql.SQL("SELECT note_id FROM wm_notes WHERE author_id = %s AND user_id = %s AND guild_id = %s;"),
        [str(author.id), str(user.id), str(guild.id)])

        result = self.cursor.fetchall()
        if result != []:
            self.cursor.execute(sql.SQL("UPDATE wm_notes SET note = %s, date = %s WHERE author_id = %s AND user_id = %s AND guild_id = %s;"),
            [note, self.bot.time_now(), str(author.id), str(user.id), str(guild.id)])
            self.connection.commit()
        else:
            self.cursor.execute(sql.SQL("INSERT INTO wm_notes (guild_id, user_id, author_id, note, date) VALUES (%s, %s, %s, %s, %s);"),
            [str(guild.id), str(user.id), str(author.id), note, self.bot.time_now()])
            self.connection.commit()

    
    async def note_alert(self, initiating_guild, user, author, note):
        author_addressor = f"{author.name}#{author.discriminator}"
        
        embed = self.watchman_embed(f"User {user.name}#{user.discriminator} was given a note by {author_addressor} in {initiating_guild.name}.")
        embed.add_field(name="Note", value=note)
    
        shared_guilds = [guild for guild in self.bot.guilds if user in guild.members and guild != initiating_guild]
        for guild in shared_guilds:
            self.cursor.execute(sql.SQL("SELECT channel_id FROM wm_servers WHERE guild_id = %s;"),
            [str(guild.id)])

            channel_id = self.cursor.fetchone()[0]
            try:
                channel = self.bot.get_channel(int(channel_id))
                await channel.send(embed=embed)
            except Exception as e:
                print(e)

    async def ban_alert(self, initiating_guild, user, author, reason):
        try:
            author_addressor = f"{author.name}#{author.discriminator}"
        except Exception as e:
            author_addressor = "Unknown"

        embed = self.watchman_embed(f"User {user.name}#{user.discriminator} was banned by {author_addressor} in {initiating_guild.name}.")
        embed.add_field(name="Reason", value=reason)
        
        shared_guilds = [guild for guild in self.bot.guilds if user in guild.members and guild != initiating_guild]
        for guild in shared_guilds:
            self.cursor.execute(sql.SQL("SELECT channel_id FROM wm_servers WHERE guild_id = %s;"),
            [str(guild.id)])

            channel_id = self.cursor.fetchone()[0]
            try:
                channel = self.bot.get_channel(int(channel_id))
                await channel.send(embed=embed)
            except Exception as e:
                print(e)




    @commands.command()
    @is_watchman_channel()
    async def docs(self, ctx):
        """ Returns a link to the documentation

        Syntax: docs
        """
        
        await ctx.send(embed=self.watchman_embed("https://primetime.james.gg/watchman_docs"))

    @commands.command()
    @is_watchman_channel()
    async def note(self, ctx):
        """ Add a note about a user. Notes must be no more than 150 characters.

        Syntax: note [User/Name+Discriminator/ID] [Note]
        Example 1: note James#0304 won't stop talking about "death grips"
        Example 2: note James won't stop talking about "death grips"
        Example 3: note 402081103923380224 won't stop talking about "death grips"
        """
        if len(ctx.message.content.split(" ")) > 1:
            user = ctx.message.content.split(" ")[1]
            try: 
                user = await commands.UserConverter().convert(ctx, user)
                note = " ".join(ctx.message.content.split(" ")[2::])
                if len(note) > 150 and ctx.author.id != self.bot.config['ids']['owner']:
                    await ctx.send(embed=self.watchman_embed("Notes must be shorter than 150 characters."))
                else:
                    self.add_note(ctx.guild, user, ctx.author, note)
                    await self.note_alert(ctx.guild, user, ctx.author, note)
                    await ctx.send(embed=self.watchman_embed(f"Recorded note for {user.name}#{user.discriminator}: \"{note}\"."))
            except Exception as e:
                print(e)
                await ctx.send(embed=self.watchman_embed(f"Couldn't find user \"{user}\"."))
        else:
            await ctx.send(embed=self.watchman_embed("Syntax: note <User> <Note>"))
    

    @commands.command()
    @is_watchman_channel()
    async def unnote(self, ctx):
        """ Remove your note for this user for this server.

        Syntax: unnote [User/Name+Discriminator/ID]
        Example 1: unnote James#0304
        Example 2: unnote James
        Example 3: unnote 402081103923380224
        """
        if len(ctx.message.content.split(" ")) > 1:
            try:
                user = await commands.UserConverter().convert(ctx, ctx.message.content.split(" ")[1])
                if self.del_note(ctx.guild, user, ctx.author):
                    await ctx.send(embed=self.watchman_embed(f"Deleted note for {user.name}#{user.discriminator} by {ctx.author.name}#{ctx.author.discriminator} in {ctx.guild.name}."))
                else:
                    await ctx.send(embed=self.watchman_embed(f"No note found for {user.name}#{user.discriminator} by {ctx.author.name}#{ctx.author.discriminator} in {ctx.guild.name}."))
            except Exception as e:
                print(e)
                await ctx.send(embed=self.watchman_embed("User not found. Double check your case and try again."))
        else:
            await ctx.send(embed=self.watchman_embed("Syntax: unnote <User>"))
    

    @commands.command()
    @is_watchman_channel()
    async def info(self, ctx):
        """ Get all bans and notes for a user.

        Syntax: info [User/Name+Discriminator/ID]
        Example 1: info James#0304
        Example 2: info James
        Example 3: info 402081103923380224
        """
        if len(ctx.message.content.split(" ")) > 1:
            user = ctx.message.content.split(" ")[1]
            try:
                user = await commands.UserConverter().convert(ctx, user)
                embed = await self.get_info(user)
                await ctx.send(embed=embed)
            except Exception as e:
                await ctx.send(embed=self.watchman_embed("User not found. Double check your case and try again."))
            
        else:
            await ctx.send(embed=self.watchman_embed("Syntax: info <User>"))


    @commands.command()
    @commands.has_permissions(administrator=True)
    async def wm(self, ctx):
        """ Sets the watchman channel for the server.

        Syntax: wm
        """
        self.cursor.execute(sql.SQL("SELECT channel_id FROM wm_servers WHERE guild_id = %s;"),
        [str(ctx.guild.id)])
        if self.cursor.fetchall() == []:
            self.cursor.execute(sql.SQL("INSERT INTO wm_servers (guild_id, channel_id) VALUES (%s, %s);"),
            [str(ctx.guild.id), str(ctx.channel.id)])
            self.connection.commit()
            await ctx.send(embed=self.watchman_embed(f"Watchman channel has been set to {ctx.channel.name} (ID {ctx.channel.id})"))
        else:
            self.cursor.execute(sql.SQL("UPDATE wm_servers SET channel_id = %s WHERE guild_id = %s;"),
            [str(ctx.channel.id), str(ctx.guild.id)])
            self.connection.commit()
            await ctx.send(embed=self.watchman_embed(f"Watchman channel has been changed to {ctx.channel.name} (ID {ctx.channel.id})."))


    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        # We need to do some work to extract reason/audit log entry for who did it.
        (author, reason) = await self.get_ban_tuple(guild, user)
        if author == "Unknown":
            author_id = "Unknown"
        else:
            author_id = str(author.id)
        self.cursor.execute(sql.SQL("DELETE FROM wm_bans WHERE guild_id = %s AND user_id = %s;"),
        [str(guild.id), str(user.id)])
        self.cursor.execute(sql.SQL("INSERT INTO wm_bans (guild_id, user_id, author_id, ban_reason, date) VALUES (%s, %s, %s, %s, %s);"),
        [str(guild.id), str(user.id), author_id, reason, self.bot.time_now()])
        self.connection.commit()
        await self.ban_alert(guild, user, author, reason)


    @commands.Cog.listener()
    async def on_member_join(self, user):
        self.cursor.execute(sql.SQL("SELECT wm_bans.user_id, wm_notes.user_id FROM wm_bans, wm_notes WHERE wm_notes.user_id = %s OR wm_bans.user_id = %s;"),
        [str(user.id), str(user.id)])
        if self.cursor.fetchall() != []:
            self.cursor.execute(sql.SQL("SELECT channel_id FROM wm_servers WHERE guild_id = %s;"),
            [str(user.guild.id)])
            
            channel_id = self.cursor.fetchone()[0]
            channel = self.bot.get_channel(int(channel_id))

            await channel.send(embed=await self.get_info(user))


def setup(bot):
    bot.add_cog(Watchman(bot, connection))
