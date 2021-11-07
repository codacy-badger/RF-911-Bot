from os import getenv
from typing import Optional

from nextcord import Embed, TextChannel, Member, ui, Interaction, ButtonStyle
from nextcord.ext.commands import (BucketType, Cog, Greedy, command, cooldown,
                                  has_permissions, has_role)
from nextcord.ext.commands.errors import MissingRole
from nextcord.ext.menus import ButtonMenu, Menu
from pymongo import MongoClient
from requests import get
from roblox import Client

from . import del_user_msg


class ButtonConfirm(ButtonMenu):
    def __init__(self, text):
        super().__init__(timeout=18000.0, delete_message_after=True)
        self.text = text
        self.result = None

    async def send_initial_message(self, ctx, channel):
        return await channel.send(embed=self.text, view=self)

    @ui.button(emoji='<:green_check_mark:882362735969579088>', style=ButtonStyle.success)
    async def do_confirm(self, button, interaction):
        if "Logistics" in [role.name for role in interaction.user.roles]:
            self.result = True
            self.stop()
        else:
            await interaction.response.send_message("You don't have permission to do this action.", ephemeral=True)

    @ui.button(emoji='<:cross_mark:906819264462348318>', style=ButtonStyle.danger)
    async def do_deny(self, button, interaction):
        if "Logistics" in [role.name for role in interaction.user.roles]:
            self.result = False
            self.stop()
        else:
            await interaction.response.send_message("You don't have permission to do this action.", ephemeral=True)

    async def prompt(self, ctx):
        await Menu.start(self, ctx, wait=True)
        return self.result


class Bounty(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.roblox = Client()

        self.MONGO_CLIENT =  MongoClient(getenv("DATABASE"))
        self.DB = self.MONGO_CLIENT["RF911"]
        self.GUILD_DB = self.DB['Guild']
        self.ROBLOX_DB = self.DB['Roblox']
        

    async def check_channel(self, ctx):
        BOUNTY_SUBMISSIONS = self.GUILD_DB.find_one({"_id": ctx.guild.id})['Bounty submission']

        if ctx.channel.id != BOUNTY_SUBMISSIONS and BOUNTY_SUBMISSIONS is not None:
            return False
        return True

    
    async def get_hitlist(self, ctx):
        HITLIST = self.GUILD_DB.find_one({"_id": ctx.guild.id})
        
        if HITLIST is None:
            return None
        else:
            CHANNEL = self.bot.get_channel(HITLIST["Hitlist"])
            return CHANNEL


    @command(name="set-hitlist-channel", aliases=["shc"], description="Set Hitlist Channel. Required administrator permissions.")
    @has_permissions(administrator=True)
    async def set_hitlist_command(self, ctx, channels : Greedy[TextChannel]):
        await del_user_msg(ctx)

        channel_id = (channel.id for channel in channels).__next__()
        self.GUILD_DB.update_one({"_id": ctx.guild.id}, {"$set": {"Hitlist": channel_id}})

        await ctx.send(f'Hitlist channel set/update to <#{channel_id}>', delete_after = 30)


    @command(name="set-bounty-channel", aliases=["sbc"], description="Set Bounty Submissions Channel. Required administrator permissions.")
    @has_permissions(administrator=True)
    async def set_bounty_command(self, ctx, channels : Greedy[TextChannel]):
        await del_user_msg(ctx)

        channel_id = (channel.id for channel in channels).__next__()
        self.GUILD_DB.update_one({"_id": ctx.guild.id}, {"$set": {"Bounty submission": channel_id}})

        await ctx.send(f'Bounty Submissions channel set/update to <#{channel_id}>', delete_after = 30)

    
    async def get_roblox_info(self, ctx, user):
        url = get(
                f"https://thumbnails.roblox.com/v1/users/avatar?format=Png&isCircular=false&size=420x420&userIds={user.id}").json()

        embed = Embed(title="Roblox User Info", colour= 0x2f3136, url=f"https://www.roblox.com/users/{user.id}/profile")
        embed.set_thumbnail(url=url["data"][0]["imageUrl"])

        description = "This user has no description." if user.description == '' else user.description.strip()

        fields = [("User Name: ", user.name, True),
                      ("Display Name: ", user.display_name, True),
                      ("ID: ", user.id, False),
                      ("Created at: ", str(user.created)[:10], True),
                      ("Is banned: ", user.is_banned, True),
                      ("Description: ", description, False)
            ]

        for name, value, inline in fields:
            embed.add_field(name=name, value=value, inline=inline)

        await ctx.send(embed= embed)


    @command(name="submit-bounty", aliases=['sb'], description="Submit bounty to bounty submission channel. \nRequire `Bounty Hunter` role.")
    @cooldown(rate=4, per=7200, type=BucketType.user)
    @has_role("Bounty Hunter")
    async def _bounty(self, ctx, target: Optional[str] = "Roblox",  *, reason: Optional[str] = "No reason provided."):
        CHECK_CHANNEL = await self.check_channel(ctx)
        await del_user_msg(ctx)

        if CHECK_CHANNEL:
            user_name = await self.roblox.get_user_by_username(target)

            if user_name == None:
                await ctx.send("No user found with that username.")
            else:
                user = await self.roblox.get_user(user_name.id)
                url = get(
                    f"https://thumbnails.roblox.com/v1/users/avatar?format=Png&isCircular=false&size=420x420&userIds={user_name.id}").json()

                embed = Embed(title="***TARGET INFO***", color=0x2f3136, url=f"https://www.roblox.com/users/{user.id}/profile")
                embed.set_author(name=f"Resquested by {ctx.author}", icon_url=f'{ctx.author.display_avatar}')
                embed.set_image(url=url["data"][0]["imageUrl"])

                fields = [("User Name: ", user.name, True),
                            ("Display Name: ", user.display_name, True),
                            ("Created at: ", str(user.created)[:10], True),
                            ("Reason: ", reason, False),]

                for name, value, inline in fields:
                    embed.add_field(name=name, value=value, inline=inline)

                answer = await ButtonConfirm(embed).prompt(ctx)
                if answer is True:
                    hitlist = await self.get_hitlist(ctx)
                    if hitlist is None:
                        await ctx.send("Hitlist channel haven't been specified.")
                    else:
                        await hitlist.send(embed=embed)
                else:
                    pass

        else:
            await ctx.send(f"Wrong channel to submit bounty {ctx.author.mention}", delete_after=5)


    @_bounty.error
    async def _load_error(self, ctx, exc):
        if isinstance(exc, MissingRole):
            await ctx.send(content=exc, delete_after = 20)


    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
            self.bot.cogs_ready.ready_up("Bounty")


def setup(bot):
    bot.add_cog(Bounty(bot))