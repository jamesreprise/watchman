# TODO
# 
# MUST:
# [-] Networks are groups of servers which all share information through some channel per server.
# [/] Networks have owners - the person that created them. What about when the owner disappears?
# [/] Networks require an invite to join.
# [ ] Networks need to be able to exclude servers that have joined.
# 
# SHOULD:
# [-] Listeners for permission changes on the bots.
# [-] Preventing `wm` in channels that are too public.
# [-] Importing all bans from a server upon `wm`. 
# 
# MIGHT:
# [ ] Start using argument-based discord.py user resolution.

import psycopg2
import discord
import toml
import random
from psycopg2 import sql
from discord.ext import commands
from datetime import datetime, timedelta

config = toml.load("config.toml")

connection = psycopg2.connect(config['settings']['db_auth'])
cursor = connection.cursor()

def is_watchman_channel():
    def predicate(ctx):
        if not ctx.guild:
            return False

        cursor.execute(sql.SQL(
            "SELECT channel_id FROM wm_servers WHERE guild_id = %s; AND status = %s;"),
        [str(ctx.guild.id), "ACTIVE"])
        if int(cursor.fetchone()[0]) == ctx.channel.id:
            return True
        
        return False
    
    return commands.check(predicate)


class Watchman(commands.Cog):
    def __init__(self, bot, connection):
        self.bot = bot
        self.connection = connection
        self.cursor = self.connection.cursor()
        self.colour = self.bot.colour
        self.create_tables_if_not_exist()

    # HELPER FUNCTIONS

    def create_tables_if_not_exist(self):
        self.cursor.execute(sql.SQL(
            """CREATE TABLE IF NOT EXISTS wm_networks (
                network_id SERIAL, 
                name TEXT PRIMARY KEY, 
                creator TEXT, 
                state TEXT
                );"""))
        self.cursor.execute(sql.SQL(
            """CREATE TABLE IF NOT EXISTS wm_servers (
                guild_id TEXT PRIMARY KEY, 
                channel_id TEXT,
                status TEXT
                );"""))
        self.cursor.execute(sql.SQL(
            """CREATE TABLE IF NOT EXISTS wm_network_invites (
                invite_id SERIAL PRIMARY KEY, 
                network_id TEXT REFERENCES wm_networks(network_id), 
                invite_code TEXT, 
                expiry DATE
                );"""))
        self.cursor.execute(sql.SQL(
            """CREATE TABLE IF NOT EXISTS wm_memberships (
                membership_id SERIAL PRIMARY KEY, 
                network_id INTEGER REFERENCES wm_networks(network_id), 
                guild_id TEXT REFERENCES wm_servers(guild_id)
                );"""))
        self.cursor.execute(sql.SQL(
            """CREATE TABLE IF NOT EXISTS wm_notes (
                note_id SERIAL, 
                message_id TEXT PRIMARY KEY, 
                author_id TEXT, 
                guild_id TEXT REFERENCES wm_servers(guild_id), 
                user_id TEXT, 
                note TEXT, 
                date TEXT
                );"""))
        self.cursor.execute(sql.SQL(
            """CREATE TABLE IF NOT EXISTS wm_bans (
                ban_id SERIAL, 
                audit_entry_id TEXT PRIMARY KEY, 
                author_id TEXT, 
                guild_id TEXT REFERENCES wm_servers(guild_id), 
                user_id TEXT, 
                ban_reason TEXT, 
                date TEXT
                );"""))
        self.connection.commit()


    def watchman_embed(self, description):
        embed = discord.Embed(colour=self.colour, description=description)
        embed.set_author(name="Watchman", icon_url=self.bot.user.avatar_url)
        embed.set_footer(text=f"{self.bot.time_now()}")
        return embed


    def get_watchman_channel(self, guild):
        self.cursor.execute(sql.SQL("SELECT channel_id FROM wm_servers WHERE guild_id = %s;"),
        [str(guild.id)])

        channel_id = self.cursor.fetchone()[0]
        try:
            return self.bot.get_channel(int(channel_id))
        except Exception as e:
            print(e)
            return None

    
    async def alert_watchman_channel(self, guild, embed):
        self.cursor.execute(sql.SQL(
            "SELECT channel_id FROM wm_servers WHERE guild_id = %s AND status = ACTIVE;"),
            [str(guild.id)])
        channel_id = self.cursor.fetchone()
        if channel_id != []:
            channel = self.bot.get_channel(int(channel_id[0]))
            await channel.send(embed)


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


    def add_note(self, ctx, user, note):
        self.cursor.execute(sql.SQL("INSERT INTO wm_notes (message_id, author_id, user_id, guild_id, note, date) VALUES (%s, %s, %s, %s, %s) ON CONFLICT UPDATE;"),
        [str(ctx.message.id), str(ctx.author.id), str(user.id), str(ctx.guild.id), note, self.bot.time_now()])
        self.connection.commit()


    def has_info(self, member):
        self.cursor.execute(sql.SQL(
            """SELECT wm_bans.user_id, wm_notes.user_id 
            FROM wm_bans, wm_notes 
            WHERE wm_notes.user_id = %s OR wm_bans.user_id = %s;"""),
        [str(member.id), str(member.id)])
        return self.cursor.fetchall() != []

    
    def generate_invite_code(self, network_id):
        candidate_code = hex(random.randint(16 ** 5, (16 ** 6) - 1))
        self.cursor.execute(sql.SQL(
            "SELECT invite_id FROM wm_network_invites WHERE invite_code = %s;"),
            [candidate_code])
        while self.cursor.fetchall() != []:
            candidate_code = hex(random.randint(16 ** 5, (16 ** 6) - 1))
            self.cursor.execute(sql.SQL(
                "SELECT invite_id FROM wm_network_invites WHERE invite_code = %s;"),
                [candidate_code])
        self.cursor.execute(sql.SQL(
            """INSERT INTO wm_network_invites (network_id, expiry, invite_code)
            VALUES (%s, %s, %s)"""),
            [network_id, datetime.now() + datetime.timedelta(hours=24), candidate_code])
        return candidate_code


    def has_needed_permissions(self, guild):
        permissions = self.get_watchman_channel_permissions(guild)
        return (permissions.send_messages and permissions.embed_links
                and permissions.view_audit_log)


    def get_watchman_channel_permissions(self, guild):
        channel = self.get_watchman_channel(guild)
        return self.bot.user.permissions_in(channel)


    def permissions_sync(self, guild):
        status = self.get_watchman_status_for_guild(guild)
        invalid_permissions = self.has_needed_permissions()[0]
        if invalid_permissions and status == "ACTIVE":
            self.cursor.execute(sql.SQL(
                "UPDATE wm_servers (status) VALUES (%s) WHERE server_id = %s;"),
                ["DISABLED", str(guild.id)])
            self.connection.commit()
        elif not invalid_permissions and status == "DISABLED":
            self.cursor.execute(sql.SQL(
                "UPDATE wm_servers (status) VALUES (%s) WHERE server_id = %s;"),
                ["ACTIVE", str(guild.id)])
            self.connection.commit()


    async def prompt_for_needed_permissions(self, channel, initiating_member=None):
        permissions = self.get_watchman_channel_permissions(channel.guild)
        if not (permissions.send_messages and permissions.embed_links):
            if initiating_member:
                await initiating_member.send(embed=self.watchman_embed("""
                    Watchman needs a few permissions to get started.\n
                    First of all, permission to send messages and embed links
                    in the channel you just used `!wm` in.\n

                    After that, permission to view the audit log. If Watchman
                    has all of these it'll activate once you use `!wm` again!
                    """))
            else:
                await channel.guild.owner.send(embed=self.watchman_embed(f"""
                    Someone with permission to add bots to {channel.guild.name} added
                    Watchman.\n 

                    Watchman needs a few permissions to get started.\n
                    First of all, permission to send messages and embed links
                    in the channel someone just used `!wm` in.\n

                    After that, permission to view the audit log. If Watchman
                    has all of these it'll activate once you use `!wm` again.
                    """))
        elif not permissions.view_audit_log:
            
            await channel.send(embed=self.watchman_embed("""
                    We need permission to view the audit log to activate,
                    otherwise discord gives us no way of knowing who banned
                    someone and for what reason.

                    Once you've done this, use `!wm` again.
                    """))
        else:
            return True
        return False

    async def get_ban_tuple(self, guild, user_banned):
        try:
            async for log in guild.audit_logs(limit=500, action=discord.AuditLogAction.ban):
                if log.target == user_banned:
                    return (log.id, log.user, log.reason)
            return ("error", "Couldn't find user in log list.")
        except Exception as e:
            return ("error", e)


    async def catchup_audit_log_bans(self, guild):
        entries = await guild.audit_logs(limit=500, action=discord.AuditLogAction.ban).flatten()
        for log in entries:
            self.cursor.execute(sql.SQL("SELECT audit_entry_id FROM wm_bans WHERE audit_entry_id = %s;"),
            [str(log.id)])
            if self.cursor.fetchall() == []:
                self.cursor.execute(sql.SQL("INSERT INTO wm_bans (audit_entry_id, author_id, guild_id, user_id, ban_reason, date) VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING;"),
                [str(log.id), str(log.user.id), str(guild.id), str(log.target.id), log.reason, self.bot.time_now()])
            else:
                break
        self.connection.commit()


    async def get_info(self, user):
        self.cursor.execute(sql.SQL("SELECT author_id, guild_id, ban_reason, date FROM wm_bans WHERE user_id = %s;"),
        [str(user.id)])
        bans = self.cursor.fetchall()
        ban_field_desc = ""
        if bans != []:
            for ban in bans:
                author = await self.bot.fetch_user(int(ban[0]))
                guild = [guild for guild in self.bot.guilds if guild.id == int(ban[1])][0]
                ban_field_desc += f"{ban[3]} - [{guild.name}] {author.name}#{author.discriminator}: \"{ban[2]}\".\n"
        
        self.cursor.execute(sql.SQL("SELECT author_id, guild_id, note, date FROM wm_notes WHERE user_id = %s;"),
        [str(user.id)])
        notes = self.cursor.fetchall()
        note_field_desc = ""
        if notes != []:
            for note in notes:
                author = await self.bot.fetch_user(int(note[0]))
                guild = [guild for guild in self.bot.guilds if guild.id == int(note[1])][0]
                note_field_desc += f"{note[3]} - [{guild.name}] {author.name}#{author.discriminator}: \"{note[2]}\".\n"
        
        if not bans and not notes:
            embed = self.watchman_embed("This user has no notes or bans.")
        else:
            embed = self.watchman_embed(f"Information for {user.name}#{user.discriminator}:")
            if ban_field_desc:
                embed.add_field(name="Bans", value=ban_field_desc)
            if note_field_desc:
                embed.add_field(name="Notes", value=note_field_desc)
        return embed

    
    async def note_alert(self, initiating_guild, user, author, note):
        author_addressor = f"{author.name}#{author.discriminator}"
        
        embed = self.watchman_embed(f"""User {user.name}#{user.discriminator} was 
                given a note by {author_addressor} in {initiating_guild.name}.""")
        embed.add_field(name="Note", value=note)
    
        shared_guilds = [guild for guild in self.bot.guilds if user in guild.members and guild != initiating_guild]
        for guild in shared_guilds:
            await self.alert_watchman_channel(guild, embed)


    async def ban_alert(self, initiating_guild, user, author, reason):
        try:
            author_addressor = f"{author.name}#{author.discriminator}"
        except Exception as e:
            author_addressor = "Unknown"

        embed = self.watchman_embed(f"""User {user.name}#{user.discriminator} 
                was banned by {author_addressor} in {initiating_guild.name}.""")
        embed.add_field(name="Reason", value=reason)
        
        shared_guilds = [guild for guild in self.bot.guilds if user in guild.members and guild != initiating_guild]
        for guild in shared_guilds:
            await self.alert_watchman_channel(guild, embed)

    # COMMANDS 

    @commands.command()
    @commands.check_any(is_watchman_channel(), commands.is_owner())
    async def docs(self, ctx):
        """ Returns a link to the documentation

        Syntax: docs
        """
        
        await ctx.send(embed=self.watchman_embed("https://watchman.berserksystems.com"))


    @commands.command()
    @commands.check_any(is_watchman_channel(), commands.is_owner())
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
                    self.add_note(ctx, user, note)
                    await self.note_alert(ctx.guild, user, ctx.author, note)
                    await ctx.send(embed=self.watchman_embed(f"Recorded note for {user.name}#{user.discriminator}: \"{note}\"."))
            except Exception as e:
                print(e)
                await ctx.send(embed=self.watchman_embed(f"Couldn't find user \"{user}\"."))
        else:
            await ctx.send(embed=self.watchman_embed("Syntax: note <User> <Note>"))
    

    @commands.command()
    @commands.check_any(is_watchman_channel(), commands.is_owner())
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
                    await ctx.send(embed=self.watchman_embed(f"""Deleted note for
                        {user.name}#{user.discriminator} by 
                        {ctx.author.name}#{ctx.author.discriminator} 
                        in {ctx.guild.name}."""))
                else:
                    await ctx.send(embed=self.watchman_embed(f"""No note found 
                        for {user.name}#{user.discriminator} by 
                        {ctx.author.name}#{ctx.author.discriminator} 
                        in {ctx.guild.name}."""))
            except Exception as e:
                print(e)
                await ctx.send(embed=self.watchman_embed("User not found. Double check your case and try again."))
        else:
            await ctx.send(embed=self.watchman_embed("Syntax: unnote <User>"))


    @commands.command()
    @commands.check_any(is_watchman_channel(), commands.is_owner())
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
                await ctx.send(embed=self.watchman_embed("""User not found. 
                    Double check your case and try again."""))

        else:
            await ctx.send(embed=self.watchman_embed("Syntax: info <User>"))


    @commands.command()
    @commands.check_any(commands.has_permissions(administrator=True), commands.is_owner())
    async def wm(self, ctx):
        """ Sets the watchman channel for the server.

        Syntax: wm
        """
        if self.has_needed_permissions(ctx.guild) and (len(ctx.channel.members) < len(ctx.guild.members)):
            self.cursor.execute(sql.SQL(
                """INSERT INTO wm_servers (guild_id, channel_id, status) 
                VALUES (%s, %s, %s) ON CONFLICT UPDATE;"""),
            [str(ctx.guild.id), str(ctx.channel.id), "ACTIVE"])
            self.connection.commit()
            await ctx.send(embed=self.watchman_embed(f"Watchman channel has been set to {ctx.channel.name} (ID {ctx.channel.id})"))
        elif not self.has_needed_permissions(ctx.guild):
            await self.prompt_for_needed_permissions(ctx.channel, initiating_member=ctx.author)


    @commands.command()
    @commands.check_any(is_watchman_channel(), commands.is_owner())
    async def create(self, ctx):
        """ Creates a watchman network and adds the current server to the network.

        Syntax: create <Network Name>
        """
        if len(ctx.message.content.split(" ")) > 1:
            name = " ".join(ctx.message.content.split(" ")[1::])
            self.cursor.execute(sql.SQL(
                "SELECT network_id FROM wm_networks WHERE name = %s AND creator = %s;"),
                [name.upper(), str(ctx.author.id)])
            if self.cursor.fetchall() == []:
                self.cursor.execute(sql.SQL(
                    "INSERT INTO wm_networks (network_id, name, creator, state) VALUES (%s, %s, %s) RETURNING network_id;"),
                    [name.upper(), str(ctx.author.id), "OPEN"])
                network_id = self.cursor.fetchone()[0]
                self.cursor.execute(sql.SQL(
                    "INSERT INTO wm_memberships (network_id, guild_id);"),
                    [network_id, str(ctx.guild.id)])
                self.connection.commit()

                embed = self.watchman_embed("Watchman Network Created.")
                embed.add_field(name="Name", value=name)
                embed.add_field(name="State", value="Open")
                embed.add_field(name="Network ID", value=str(network_id))

                await ctx.send(embed=embed)
            else:
                await ctx.send(embed=self.watchman_embed("You've already created a network with that name!"))
        else:
            await ctx.send(embed=self.watchman_embed("Syntax: create <Network Name>"))

    # We need some method to list out and uniquely identify networks and 
    # servers if there is a collision.

    @commands.command()
    @is_watchman_channel()
    async def remove(self, ctx):
        """ Removes a server from your network.

        Syntax: remove <Server Name> """

    @commands.command()
    @is_watchman_channel()
    async def leave(self, ctx):
        """ Removes your server from a network.

        Syntax: leave <Network Name> """

    @commands.command()
    @is_watchman_channel()
    async def invite(self, ctx):
        """ Creates an invite code with which other users can join

        Syntax: invite <Network Name> """
        if len(ctx.message.content.split(" ")) > 1:
            name = " ".join(ctx.message.content.split(" ")[1::])
            self.cursor.execute(sql.SQL(
                "SELECT network_id FROM wm_networks WHERE name = %s AND creator = %s;"),
                [name.upper(), str(ctx.author.id)])
            result = self.cursor.fetchall()
            if result != []:
                invite_code = self.generate_invite_code()
                embed = self.watchman_embed(f"{name} Invite Code")
                embed.add_field(name="Code", value=invite_code)
                await ctx.send(embed=embed)
            else:
                await ctx.send(embed=self.watchman_embed("You don't have a network by that name.")) 
        else:
            await ctx.send(embed=self.watchman_embed("Syntax: invite <Network Name>"))

    @commands.command()
    @commands.check_any(is_watchman_channel(), commands.is_owner())
    async def join(self, ctx):
        """ Joins the current server to a watchman network with an invite code.
        Invite codes aren't case sensitive.

        Syntax: join <Invite Code>
        """
        if len(ctx.message.content.split(" ")) > 1:
            self.cursor.execute(sql.SQL(
                "SELECT network_id FROM wm_network_invites WHERE invite_code = %s;"),
                [ctx.message.content.split(" ")[1]])
            result = self.cursor.fetchall()
            if result != []:
                network_id = result[0][0]
                self.cursor.execute(sql.SQL(
                    "INSERT INTO wm_memberships (network_id, guild_id) VALUES (%s, %s);"),
                    [network_id, str(ctx.guild.id)])
                self.connection.commit()
                await ctx.send(embed=self.watchman_embed(f"Joined network."))
                # Show users with notes/bans and number of upon network join?
            else:
                await ctx.send(embed=self.watchman_embed("Invalid invite code."))
        else:
            await ctx.send(embed=self.watchman_embed("Syntax: join <Invite Code>"))

    # LISTENERS

    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        # We need to do some work to extract reason/audit log entry for who did it.
        audit_log_tuple = await self.get_ban_tuple(guild, user)
        if audit_log_tuple[0] != "error":
            (audit_entry_id, author, reason) = audit_log_tuple

            self.cursor.execute(sql.SQL(
                """INSERT INTO wm_bans 
                (audit_entry_id, guild_id, user_id, author_id, ban_reason, date) 
                VALUES (%s, %s, %s, %s, %s) ON CONFLICT UPDATE;"""),
            [str(audit_entry_id), str(guild.id), str(user.id), str(author.id),
                reason, self.bot.time_now()])

            self.connection.commit()
            await self.ban_alert(guild, user, author, reason)
        else:
            print(audit_log_tuple)            


    @commands.Cog.listener()
    async def on_member_join(self, member):
        if self.has_info(member):       
            channel = self.get_watchman_channel(member.guild)
            await channel.send(embed=await self.get_info(member))


    @commands.Cog.listener()
    async def on_guild_role_update(self, before, after):
        if self.get_watchman_channel(after.guild) != None:
            self.permissions_sync(after.guild)


    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if self.get_watchman_channel(after.guild) != None:
            self.permissions_sync(after.guild)


    @commands.Cog.listener()
    async def on_ready(self):
        for guild in self.bot.guilds:
            await self.catchup_audit_log_bans(guild)
            self.permissions_sync(guild)


def setup(bot):
    bot.add_cog(Watchman(bot, connection))
    
