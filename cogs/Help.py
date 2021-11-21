from os import getenv
from pathlib import Path
from typing import Optional

from nextcord import Embed
from nextcord.ext.commands import BucketType, Cog, Greedy, command, cooldown, has_permissions
from nextcord.ext.menus import ListPageSource
from nextcord.utils import get
from pymongo import MongoClient

from . import CustomButtonMenuPages, del_user_msg


async def syntax(command):
    params = []

    for key, value in command.params.items():
        if key not in ("self", "ctx"):
            params.append(f"[{key}]" if "None" in str(value) else f"<{key}>")

    params = " ".join(params)

    return params


class HelpMenu(ListPageSource):
    def __init__(self, ctx, data, prefix):
        self.ctx = ctx
        self.guild_prefix = prefix

        super().__init__(data, per_page=1)


    async def write_page(self, menu, cog_name, fields=[]):
        offset = (menu.current_page*self.per_page) + 1
        len_data = len(self.entries)

        embed = Embed(title="Raid Force Help Menu", colour=0x2f3136, description=f"{cog_name} \n[] is optional arguments.\n<> is required arguments.")
        embed.set_thumbnail(url=self.ctx.guild.me.display_avatar)
        embed.set_footer(text=f"{offset:,} of {len_data:,} modules.")

        for name, value in fields:
            embed.add_field(name=name, value=value, inline=False)

        return embed


    async def format_page(self, menu, entries):
        fields = []
        cog_name = entries.qualified_name

        for command in entries.walk_commands():
            aliases = f' | {", ".join(command.aliases)}' if command.aliases != [] else ''

            fields.append((f'{self.guild_prefix}{command.qualified_name} {aliases} {await syntax(command)}', 
                    command.description if command.description != '' else "This command have no description"))

        return await self.write_page(menu, cog_name, fields)


class Help(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.help_command = None
        self.COGS = [p.stem for p in Path(".").glob("./cogs/*.py")]

        self.MONGO_CLIENT =  MongoClient(getenv("DATABASE"))
        self.DB = self.MONGO_CLIENT["RF911"]
        self.GUILD_DB = self.DB['Guild']

    
    async def cmd_help(self, ctx, cmd):
        aliases = f' | {" | ".join(cmd.aliases)}' if cmd.aliases != [] else ''

        embed = Embed(title=f"Help with {cmd.qualified_name}", colour=0x2f3136)
        embed.set_author(name=ctx.author, icon_url=ctx.author.display_avatar)
        embed.add_field(name=f'{await self.get_guild_prefix(ctx)}{cmd.qualified_name} {aliases} {await syntax(cmd)}', 
                        value=cmd.description if cmd.description != '' else "This command have no description")

        await ctx.send(embed=embed)

    
    async def get_guild_prefix(self, ctx):
        guild = self.GUILD_DB.find_one({"_id": ctx.guild.id})

        return guild["prefix"]

    
    @command(name="help", description='Show help information.')
    @has_permissions(administrator=True)
    async def help_command(self, ctx, cmds: Optional[str] = None):
        await del_user_msg(ctx)

        if cmds is not None:
            if (cmd := get(self.bot.commands, name=cmds)):
                await self.cmd_help(ctx, cmd)

            else:
                await ctx.send("That command does not exist.", delete_after=10)
        else:
            COGS = [self.bot.get_cog(cog) for cog in self.COGS if len(list(self.bot.get_cog(cog).walk_commands()))]
            menu = CustomButtonMenuPages(source=HelpMenu(ctx, COGS, await self.get_guild_prefix(ctx)), timeout=120.0, ctx=ctx)
            await menu.start(ctx)


    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
            self.bot.cogs_ready.ready_up("Help")


def setup(bot):
    bot.add_cog(Help(bot))
