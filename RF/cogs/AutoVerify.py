from nextcord import Embed, Guild, Member, Message, Role, Forbidden
from nextcord.ext.commands import (Cog, Context, Greedy, command,
                                   has_permissions)
from nextcord.utils import get

from ..bot import RF
from . import del_user_msg


class AutoVerify(Cog):
    def __init__(self, bot: RF):
        self.bot = bot

        self.DELETE_AFTER = 300


    async def getDefaultRole(self, guild: Guild) -> Role:
        server = self.bot.GUILD_DB.find_one({"_id": guild.id})
        return guild.get_role(server["Default role"])


    @command(name="sign-in", description='Link your roblox account to your discord account.')
    async def sign_in_command(self, ctx: Context):
        default_role = await self.getDefaultRole(ctx.guild)

        if self.bot.ROBLOX_DB.find_one({"_id": ctx.author.id}) is None:
            await ctx.author.send(f'Hello {ctx.author.mention}, welcome to {ctx.guild.name}.\nPlease tell me your roblox account name', delete_after=self.DELETE_AFTER)
            await self.check_username(ctx.author, default_role, isNew=False)
        else:
            await ctx.author.send("You're already verified")


    @command(name="set-default-role", aliases=['sdr'], description='Set the default role for new member after join.\nRequired `Administrator` permissions.')
    @has_permissions(administrator=True)
    async def set_default_role_command(self, ctx: Context, roles: Greedy[Role]):
        await del_user_msg(ctx)

        role_id = (role.id for role in roles).__next__()
        self.bot.GUILD_DB.update_one({"_id": ctx.guild.id}, {"$set": {"Default role": role_id}})

        await ctx.send(content=f"Default have been set/update to <@&{role_id}>", delete_after = self.DELETE_AFTER)


    async def check_username(self, member: Member, defaultRole: Role, isNew: bool =True):
        while True:
            msg: Message = await self.bot.wait_for('message', check=lambda message: message.author == member)
            user = await self.bot.roblox.get_user_by_username(msg.content)

            if user == None:
                await member.send("No user found with that username.")
            else:
                check_user_db = self.bot.ROBLOX_DB.find_one({"Roblox ID": user.id})
                if check_user_db is None:

                    thumbnail = await self.bot.roblox.thumbnails.get_user_avatars([user.id], size="720x720")
                    thumbnail_url = thumbnail[0].image_url if thumbnail[0].image_url is not None else Embed.Empty

                    user = await self.bot.roblox.get_user(user.id)
                    embed = Embed(colour=0x2f3136, url=f"https://www.roblox.com/users/{user.id}/profile")
                    embed.set_thumbnail(url=thumbnail_url)
                    
                    description = "This user has no description." if user.description == '' else str(user.description).strip()

                    fields = [("User Name: ", user.name, True),
                              ("Display Name: ", user.display_name, True),
                              ("ID: ", user.id, False),
                              ("Created at: ", str(user.created)[:10], True),
                              ("Description: ", description, False)]

                    for name, value, inline in fields:
                        embed.add_field(name=name, value=value, inline=inline)

                    await member.send(content="Is this your roblox account? y/n", embed=embed, delete_after=self.DELETE_AFTER)
                    confirm_msg = await self.bot.wait_for('message', check=lambda message: message.author == member)
                    if confirm_msg.content.lower() in ["yes", "y"]:
                        await member.send("Congratulation, you have been verified.")

                        userRoles = member.roles
                        userRoles.append(defaultRole)

                        if isNew:
                            await member.edit(roles=userRoles)

                        self.bot.ROBLOX_DB.insert_one({"_id": member.id, "User Name": f"{member}", "Roblox ID": user.id, "Joined at": member.joined_at.strftime("%b %d %Y")})
                        break

                    elif confirm_msg.content.lower() in ["no", 'n']:
                        await member.send("Please tell me your roblox account name again", delete_after=self.DELETE_AFTER)

                else:
                    await member.send("Sorry but that account already been used.\nDM Council to report if someone using your account.", delete_after=self.DELETE_AFTER)


    @Cog.listener()
    async def on_member_join(self, member: Member) -> None:
        defaultRole = await self.getDefaultRole(member.guild)

        if self.bot.ROBLOX_DB.find_one({"_id": member.id}) is None:
            try:
                await member.send(f'Hello {member.mention}, welcome to {member.guild.name}. \nBefore you can access any chat in server you need to verify yourself. \nPlease tell me your roblox account name', delete_after=self.DELETE_AFTER)
                await self.check_username(member, defaultRole)
            except Forbidden:
                channel = get(member.guild.text_channels, id=808318831240019970)
                await channel.send(f"Unable to verify {member} due to unable to dms.")
        else:
            userRoles = member.roles
            userRoles.append(defaultRole)

            await member.edit(roles=userRoles)
            await member.send(f'Hello {member.mention}, welcome back to {member.guild.name}', delete_after=self.DELETE_AFTER)


    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
            self.bot.cogs_ready.ready_up("AutoVerify")


def setup(bot):
    bot.add_cog(AutoVerify(bot))
