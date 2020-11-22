import discord
import aiohttp
import toml
from discord.ext import commands, tasks


class LastFM(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.LASTFM_LIMIT = 200
        self.session = aiohttp.ClientSession()
        self.lastfm_username = "VPVD"
        self.spotify_icon = "https://primetime.james.gg/images/spotify.png"
        self.lastfm_icon = "https://primetime.james.gg/images/lastfm.png"
        self.last_fm_api_key = self.bot.config['keys']['last_fm_api_key']
        self.lastfm_url_pattern = "https://ws.audioscrobbler.com/2.0/?method=user.getrecenttracks&user={user}&api_key=" + self.last_fm_api_key + "&limit=" + str(self.LASTFM_LIMIT) + "&format=json"
        self.lastfm_info_url_pattern = "https://ws.audioscrobbler.com/2.0/?method=user.getinfo&user={user}&api_key=" + self.last_fm_api_key + "&format=json"

    @commands.command()
    @commands.is_owner()
    async def np(self, ctx):
        """ Displays what the user is currently listening to.

        Syntax: np """

        await ctx.send(embed=await self.music_embed(ctx.message.author))

    async def music_embed(self, member):
        for activity in member.activities:
            if isinstance(activity, discord.Spotify):
                embed = await self.spotify_embed(member, activity)
                return embed

        embed = await self.lastfm_embed(member)
        return embed

    async def spotify_embed(self, member, spotify):
        addressor = member.nick if member.nick else member.name
        embed = discord.Embed(title="{} is listening to {}".format(
            addressor, spotify.artists[0]), colour=spotify.color)
        embed.add_field(name = "Song", 
            value = "[{}](https://open.spotify.com/track/{})".format(spotify.title, spotify.track_id))
        embed.add_field(name="Album", value="{}".format(spotify.album), inline=False)
        embed.set_image(url=spotify.album_cover_url)
        embed.set_footer(text=f"via Spotify.", icon_url=self.spotify_icon)
        return embed

    async def lastfm_embed(self, member):
        addressor = member.nick if member.nick else member.name

        async with self.session.get(self.lastfm_url_pattern.format(user=self.lastfm_username)) as r:
            last_fm_response_json = await r.json()
        async with self.session.get(self.lastfm_info_url_pattern.format(user=self.lastfm_username)) as s:
            last_fm_icon_json = await s.json()

        if 'recenttracks' in last_fm_response_json:
            streak_track = last_fm_response_json['recenttracks']['track'][0]['mbid']
            streak_count = 0
            while streak_count < self.LASTFM_LIMIT and streak_track == last_fm_response_json['recenttracks']['track'][streak_count]['mbid']:
                streak_count += 1
            
            liveNow = "is currently" if '@attr' in last_fm_response_json[
                'recenttracks']['track'][0] else "was"
            embed = discord.Embed(title="{} {} listening to {}".format(
                addressor, liveNow, last_fm_response_json['recenttracks']['track'][0]['artist']['#text']), colour=0XC3000D)
            if last_fm_response_json['recenttracks']['track'][0]['image'][3]['#text'] != "https://lastfm-img2.akamaized.net/i/u/300x300/2a96cbd8b46e442fc41c2b86b821562f.png":
                embed.set_image(
                    url=last_fm_response_json['recenttracks']['track'][0]['image'][3]['#text'])
            embed.add_field(name="Song", value="{}".format(
                last_fm_response_json['recenttracks']['track'][0]['name']))
            embed.add_field(
                name="Album", value=last_fm_response_json['recenttracks']['track'][0]['album']['#text'], inline=False)
            embed.set_footer(text="{} via last.fm. Total tracks played: {}.".format(
                self.lastfm_username, last_fm_icon_json['user']['playcount']), icon_url=last_fm_icon_json['user']['image'][2]['#text'])
            
            return embed

def setup(bot):
    bot.add_cog(LastFM(bot))
