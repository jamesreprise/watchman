import psycopg2
from psycopg2 import sql
from discord.ext import commands
from datetime import datetime, timedelta


class Panopticon(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def log(self, message):
        print("[" + self.bot.time_now() + "] " + message)

    @commands.Cog.listener()
    async def on_message(self, ctx):
        if not ctx.author.bot:
            if ctx.attachments:
                self.log(f"({ctx.guild.name} - #{ctx.channel.name}) {ctx.author.name}#{ctx.author.discriminator} [WITH ATTACHMENTS]: {ctx.content}")
            else:
                self.log(f"({ctx.guild.name} - #{ctx.channel.name}) {ctx.author.name}#{ctx.author.discriminator}: {ctx.content}")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if before.channel and not after.channel:
            self.log(f"({member.guild.name} - {before.channel.name}) {member.name}#{member.discriminator} left the voice channel.")
        if not before.channel and after.channel:
            self.log(f"({member.guild.name} - {after.channel.name}) {member.name}#{member.discriminator} joined the voice channel.")
        if before.channel and after.channel and before.channel != after.channel:
            self.log(f"({member.guild.name} - {before.channel.name} -> {after.channel.name}) {member.name}#{member.discriminator} moved voice channels.")
        if before.mute != after.mute and after.mute:
            self.log(f"({member.guild.name} - {after.channel.name}) {member.name}#{member.discriminator} was muted.")
        if before.deaf != after.deaf and after.deaf:
            self.log(f"({member.guild.name} - {after.channel.name}) {member.name}#{member.discriminator} was deafened.")
        if before.self_mute != after.self_mute and after.self_mute:
            self.log(f"({member.guild.name} - {after.channel.name}) {member.name}#{member.discriminator} muted.")
        if before.self_deaf != after.self_deaf and after.self_deaf:
            self.log(f"({member.guild.name} - {after.channel.name}) {member.name}#{member.discriminator} defeaned.")
        if before.self_video != after.self_video and after.self_video:
            self.log(f"({member.guild.name} - {after.channel.name}) {member.name}#{member.discriminator} enabled video.")
        if before.mute != after.mute and not after.mute:
            self.log(f"({member.guild.name} - {after.channel.name}) {member.name}#{member.discriminator} was unmuted.")
        if before.deaf != after.deaf and not after.deaf:
            self.log(f"({member.guild.name} - {after.channel.name}) {member.name}#{member.discriminator} was undeafened.")
        if before.self_mute != after.self_mute and not after.self_mute:
            self.log(f"({member.guild.name} - {after.channel.name}) {member.name}#{member.discriminator} unmuted.")
        if before.self_deaf != after.self_deaf and not after.self_deaf:
            self.log(f"({member.guild.name} - {after.channel.name}) {member.name}#{member.discriminator} undeafened.")
        if before.self_video != after.self_video and not after.self_video:
            self.log(f"({member.guild.name} - {after.channel.name}) {member.name}#{member.discriminator} disabled video.")


    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        self.log(f"({guild.name}) {user.name}#{user.discriminator} was banned.")

    @commands.Cog.listener()
    async def on_member_unban(self, guild, user):
        self.log(f"({guild.name}) {user.name}#{user.discriminator} was unbanned.")

    @commands.Cog.listener()
    async def on_member_join(self, user):
        self.log(f"({user.guild.name}) {user.name}#{user.discriminator} joined the server.")
        self.add_guild_user_if_not_exists(user)

    @commands.Cog.listener()
    async def on_member_remove(self, user):
        self.log(f"({user.guild.name}) {user.name}#{user.discriminator} left the server.")

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        self.log(f"({message.guild.name} - #{message.channel.name}) {message.author.name}#{message.author.discriminator}'s message was deleted: \"{message.content}\".")
    
    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if before.content != after.content:
            self.log(f"({before.guild.name} - #{before.channel.name}) {before.author.name}#{before.author.discriminator}'s message was edited:\n \"{before.content}\" \n -> \n \"{after.content}\".")
    
    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        self.log(f"({reaction.message.guild.name} - #{reaction.message.channel.name}) {user.name}#{user.discriminator} reacted with {str(reaction.emoji)} to \"{reaction.message.content[:20]}[...]\".")

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        self.log(f"({channel.guild.name}) #{channel.name} was created.")

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        self.log(f"({channel.guild.name}) #{channel.name} was deleted.")
    
    @commands.Cog.listener()
    async def on_guild_role_create(self, role):
        self.log(f"({role.guild.name}) Role {role.name} was created.")
    
    @commands.Cog.listener()
    async def on_guild_role_delete(self, role):
        self.log(f"({role.guild.name}) Role {role.name} was deleted.")

    @commands.Cog.listener()
    async def on_guild_role_update(self, before, after):
        if before.name != after.name:
            self.log(f"({after.guild.name}) Role {before.name}'s name was changed to {after.name}.")
        if before.permissions != after.permissions:
            b_perms = list(iter(before.permissions))
            a_perms = list(iter(after.permissions))
            modified_permissions = list(filter(lambda permission: permission not in b_perms, a_perms))
            if modified_permissions:
                self.log(f"({after.guild.name}) Role {after.name} had permissions modified: {modified_permissions}.")

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if before.nick != after.nick:
            if before.nick and after.nick:
                self.log(f"({after.guild.name} - {after.name}) {after.name}#{after.discriminator}'s nickname was changed from \"{before.nick}\" to \"{after.nick}\".")
            elif after.nick:
                self.log(f"({after.guild.name} - {after.name}) {after.name}#{after.discriminator}'s nickname was set to \"{after.nick}\".")
            else:
                self.log(f"({after.guild.name} - {after.name}) {after.name}#{after.discriminator}'s nickname was removed.")
        if before.roles != after.roles:
            added_roles = list(filter(lambda role: role not in before.roles, after.roles))
            removed_roles = list(filter(lambda role: role not in after.roles, before.roles))
            if added_roles:
                self.log(f"({after.guild.name} - {after.name}) {after.name}#{after.discriminator} was added to {added_roles}.")
            elif removed_roles:
                self.log(f"({after.guild.name} - {after.name}) {after.name}#{after.discriminator} was removed from {removed_roles}.")
        
    @commands.Cog.listener()
    async def on_user_update(self, before, after):
        if before.avatar_url != after.avatar_url and not before.bot:
            self.log(f"{after.name}#{after.discriminator} changed their avatar.")
        if before.name != after.name:
            self.log(f"{after.name}#{after.discriminator} changed their name: {before.name} -> {after.name}.")
        if before.discriminator != after.discriminator:
            self.log(f"{after.name}#{after.discriminator} changed their discriminator: {before.discriminator} -> {after.discriminator}.")
        
    @commands.Cog.listener()
    async def on_guild_update(self, before, after):
        if before.region != after.region:
            self.log(f"{after.name} region changed: {before.region} -> {after.region}.")

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        self.log(f"Joined {guild.name}.")
    
    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        self.log(f"Left {guild.name}.")


def setup(bot):
    bot.add_cog(Panopticon(bot))
