from datetime import datetime, timedelta
from typing import Union

from nextcord import (ButtonStyle, Embed, Interaction, Member, Message,
                      TextChannel, ui)
from nextcord.ext.commands import (BucketType, Cog, Context, command, cooldown,
                                   has_permissions, has_role)
from nextcord.ext.menus import ButtonMenu, Menu
from roblox import Client

from ..bot import RF
from . import del_user_msg


class ButtonConfirm(ButtonMenu):
    def __init__(self, text):
        super().__init__(timeout=36000.0, delete_message_after=True)
        self.text = text
        self.result = None
        self.host = None

    async def send_initial_message(self, ctx, channel: TextChannel):
        return await channel.send(embed=self.text, view=self)

    @ui.button(emoji='<:green_check_mark:882362735969579088>', style=ButtonStyle.success)
    async def do_confirm(self, button, interaction: Interaction):
        if "Logistics" in [role.name for role in interaction.user.roles]:
            self.result:bool = True
            self.host: Member = interaction.user
            self.stop()
        else:
            await interaction.response.send_message("You don't have permission to do this action.", ephemeral=True)

    @ui.button(emoji='<:cross_mark:906819264462348318>', style=ButtonStyle.danger)
    async def do_deny(self, button, interaction: Interaction):
        if "Logistics" in [role.name for role in interaction.user.roles]:
            self.result:bool = False
            self.stop()
        else:
            await interaction.response.send_message("You don't have permission to do this action.", ephemeral=True)

    async def prompt(self, ctx) -> Union[bool, Member]:
        await Menu.start(self, ctx, wait=True)
        return self.result, self.host


class Bounty(Cog):
    def __init__(self, bot: RF) -> None:
        self.bot = bot
        self.roblox = Client()


    async def check_channel(self, ctx) -> bool:
        BOUNTY_SUBMISSIONS = self.bot.GUILD_DB.find_one({"_id": ctx.guild.id})['Bounty submission']

        if ctx.channel.id != BOUNTY_SUBMISSIONS and BOUNTY_SUBMISSIONS is not None:
            return False
        return True

    
    async def get_hitlist(self, ctx) -> TextChannel:
        HITLIST = self.bot.GUILD_DB.find_one({"_id": ctx.guild.id})
        
        if HITLIST is None:
            return None
        else:
            CHANNEL = self.bot.get_channel(HITLIST["Hitlist"])
            return CHANNEL


    @command(name="set-hitlist-channel", aliases=["shc"], description="Set Hitlist Channel.\nRequired `administrator` permissions.")
    @has_permissions(administrator=True)
    async def set_hitlist_command(self, ctx: Context, channels : TextChannel) -> None:
        await del_user_msg(ctx)
        
        self.bot.GUILD_DB.update_one({"_id": ctx.guild.id}, {"$set": {"Hitlist": channels.id}})
        await ctx.send(f'Hitlist channel set/update to {channels.mention}', delete_after = 5)


    @command(name="set-bounty-channel", aliases=["sbc"], description="Set Bounty Submissions Channel.\nRequired `administrator` permissions.")
    @has_permissions(administrator=True)
    async def set_bounty_command(self, ctx: Context, channels : TextChannel) -> None:
        await del_user_msg(ctx)
        
        self.bot.GUILD_DB.update_one({"_id": ctx.guild.id}, {"$set": {"Bounty submission": channels.id}})
        await ctx.send(f'Bounty Submissions channel set/update to {channels.mention}', delete_after = 5)


    @staticmethod  
    async def del_bounty(msg: Message) -> None:
        await msg.edit(content="Expired")


    @command(name="submit-bounty", aliases=['sb'], description="Submit bounty to bounty submission channel.\nRequire `Bounty Hunter` role.")
    @cooldown(rate=4, per=7200, type=BucketType.user)
    @has_role("Bounty Hunter")
    async def _bounty(self, ctx: Context, target: str,  *, reason: str) -> None:
        CHECK_CHANNEL = await self.check_channel(ctx)
        await del_user_msg(ctx)

        if CHECK_CHANNEL:
            user_name = await self.roblox.get_user_by_username(target)
            if user_name == None:
                await ctx.send("No user found with that username.")
            else:
                user = await self.roblox.get_user(user_name.id)
                thumbnail = await self.roblox.thumbnails.get_user_avatars([user.id], size="720x720")
                thumbnail_url = thumbnail[0].image_url if thumbnail[0].image_url is not None else Embed.Empty
                expired_time = datetime.now() + timedelta(days=7)

                embed = Embed(title=f"{user.name} profiles", color=0x2f3136, url=f"https://www.roblox.com/users/{user.id}/profile")
                embed.set_image(url=thumbnail_url)

                fields = [("User Name: ", user.name, True),
                            ("Display Name: ", user.display_name, True),
                            ("Request by: ", ctx.author, False),
                            ("Expired: ", f"<t:{str(expired_time.timestamp()).split('.')[0]}:R>", True),
                            ("Reason: ", reason, False),]

                for name, value, inline in fields:
                    embed.add_field(name=name, value=value, inline=inline)

                answer, host = await ButtonConfirm(embed).prompt(ctx)
                if answer is True:
                    hitlist = await self.get_hitlist(ctx)
                    if hitlist is None:
                        await ctx.send("Hitlist channel haven't been specified.", delete_after=5)
                    else:
                        embed.set_author(name=f"Host by {host}", icon_url=host.display_avatar)
                        msg: Message = await hitlist.send(content="<@&878261620311220225>", embed=embed)

                        self.bot.scheduler.add_job(self.del_bounty, id=f"{msg.id}-Bounty", args=[msg], next_run_time=expired_time)
                        self.bot.SCHEDULER.insert_one({"_id": f"{msg.id}-Bounty", "Guild ID": ctx.guild.id,
                                                   "Expired": (datetime.now() + timedelta(days=7)).strftime('%d-%m-%Y-%H-%M-%S'),})
                else:
                    pass
        else:
            await ctx.send(f"Wrong channel to submit bounty {ctx.author.mention}", delete_after=5)


    @Cog.listener()
    async def on_ready(self) -> None:
        if not self.bot.ready:
            self.bot.cogs_ready.ready_up("Bounty")


def setup(bot):
    bot.add_cog(Bounty(bot))
