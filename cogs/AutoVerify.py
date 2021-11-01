import random
import string
from os import getenv

from nextcord import DMChannel, Embed, Member, Role
from nextcord.ext.commands import Cog, Greedy, command, is_owner, has_permissions
from nextcord.ext.commands.core import check
from pymongo import MongoClient
from requests import get
from roblox import Client
from asyncio import sleep

from . import del_user_msg


class AutoVerify(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.roblox = Client()

        self.MONGO_CLIENT =  MongoClient(getenv("DATABASE"))
        self.DB = self.MONGO_CLIENT["RF911"]
        self.GUILD_DB = self.DB['Guild']
        self.ROBLOX_DB = self.DB['Roblox']

        self.DELETE_AFTER = 300

    
    @command(name="display-roblox-name", description="Change all members name in server into their roblox name, if they already sign in")
    @has_permissions(administrator=True)
    async def display_roblox_name_command(self, ctx, targets :Greedy[Member] = None):
        if targets is None:
            for member in ctx.guild.members:
                if self.ROBLOX_DB.find_one({"_id": ctx.author.id}) is None:
                    pass
                else:
                    user = self.ROBLOX_DB.find_one({"_id": member.id})
                    userID = user["Roblox ID"]
                    roblox = await self.roblox.get_user(userID)

                    old_nickname = member.display_name if '|' not in member.display_name else member.display_name.split("|")[1]
                    await member.edit(nick=f"{old_nickname.strip()} | [{roblox.name}]")


    @command(name="sign-in")
    async def sign_in_command(self, ctx):
        default_role = self.get_default_role(ctx.guild)

        if self.ROBLOX_DB.find_one({"_id": ctx.author.id}) is None:
            await ctx.author.send(f'Hello {ctx.author.mention}, welcome to {ctx.guild.name}. \nPlease tell me your roblox account name', delete_after=self.DELETE_AFTER)
            await self.check_username(ctx.author, default_role)

        else:
            await ctx.author.send("You're already verified")

    @command(name="set-default-role")
    async def set_default_role_command(self, ctx, roles: Greedy[Role]):
        await del_user_msg(ctx)

        role_id = (role.id for role in roles).__next__()
        self.GUILD_DB.update_one({"_id": ctx.guild.id}, {"$set": {"Default role": role_id}})

        await ctx.send(content=f"Default have been set/update to <@&{role_id}>", delete_after = self.DELETE_AFTER)


    async def check_username(self, member, default_role):
        random_string_to_confirm = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10)).strip()

        while True:
            msg = await self.bot.wait_for('message', check=lambda message: message.author == member)
            user = await self.roblox.get_user_by_username(msg.content)
            if user == None:
                await member.send("No user found with that username.")
            else:
                check_user_db = self.ROBLOX_DB.find_one({"Roblox ID": user.id})
                if check_user_db is None:
                    url = get(
                        f"https://thumbnails.roblox.com/v1/users/avatar?format=Png&isCircular=false&size=420x420&userIds={user.id}").json()

                    user = await self.roblox.get_user(user.id)
                    embed = Embed(title="This is your roblox profile?", colour= 0x2f3136, url=f"https://www.roblox.com/users/{user.id}/profile")
                    embed.set_thumbnail(url=url["data"][0]["imageUrl"])

                    description = "This user has no description." if user.description == '' else str(user.description).strip()

                    fields = [("User Name: ", user.name, True),
                            ("Display Name: ", user.display_name, True),
                            ("ID: ", user.id, False),
                            ("Created at: ", str(user.created)[:10], True),
                            ("Is banned: ", user.is_banned, True),
                            ("Description: ", description, False)
                    ]

                    for name, value, inline in fields:
                        embed.add_field(name=name, value=value, inline=inline)

                    await member.send(embed=embed, delete_after=self.DELETE_AFTER)
                    await member.send(content="Is this your roblox account? ", delete_after=self.DELETE_AFTER)

                    confirm_msg = await self.bot.wait_for('message', check=lambda message: message.author == member)

                    if confirm_msg.content.lower() in ["yes", "y"]:
                        await member.send(f"Please set this to your description to confirm: \n{random_string_to_confirm}")
                        user_description, timeout = None, 0
                        while user_description != random_string_to_confirm or timeout < 600:
                            rbuser = await self.roblox.get_user(user.id)
                            user_description = rbuser.description
                            timeout += 1
                            sleep(0.5)
                            
                        await member.send("Congratulation, you have been verified.")
                        guild = self.bot.get_guild(member.guild.id)
                        role = guild.get_role(default_role)
                        old_nickname = member.display_name if '|' not in member.display_name else member.display_name.split("|")[1]
                        await guild.get_member(member.id).edit(roles=[role], nick=f"{old_nickname.strip()} | [{user.name}]")
                        
                        self.ROBLOX_DB.insert_one({"_id": member.id, "User Name": f"{member.name}#{member.discriminator}", "Roblox ID": user.id, "Joined at": member.joined_at.strftime("%b %d %Y")})
                        break

                    elif confirm_msg.content.lower() in ["no", 'n']:
                        await member.send("Please tell me your roblox account name again", delete_after=self.DELETE_AFTER)
                        
                else:
                    await member.send("Sorry but that account already been used.", delete_after=self.DELETE_AFTER)

    
    def get_default_role(self, guild):
        server = self.GUILD_DB.find_one({"_id": guild.id})
        return server["Default role"]


    @Cog.listener()
    async def on_member_join(self, member):
        default_role = self.get_default_role(member.guild)

        if self.ROBLOX_DB.find_one({"_id": member.id}) is None:
            await member.send(f'Hello {member.mention}, welcome to {member.guild.name}. \nBefore you can access any chat in server you need to verify yourself. \nPlease tell me your roblox account name', delete_after=self.DELETE_AFTER)
            await self.check_username(member, default_role)

        else:
            user = self.ROBLOX_DB.find_one({"_id": member.id})
            userID = user["Roblox ID"]
            roblox = await self.roblox.get_user(userID)
            
            guild = self.bot.get_guild(member.guild.id)
            role = guild.get_role(default_role)
            old_nickname = member.display_name if '|' not in member.display_name else member.display_name.split("|")[1]
            await guild.get_member(member.id).edit(roles=[role], nick=f"{old_nickname.strip()} | [{roblox.name}]")
            
            await member.send(f'Hello {member.mention}, welcome back to {member.guild.name}', delete_after=self.DELETE_AFTER)

            
    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
            self.bot.cogs_ready.ready_up("AutoVerify")


def setup(bot):
    bot.add_cog(AutoVerify(bot))