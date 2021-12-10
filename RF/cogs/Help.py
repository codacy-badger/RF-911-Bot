from pathlib import Path
from typing import Optional

from nextcord import Embed
from nextcord.ext.commands import Cog, Context, command, has_permissions
from nextcord.ext.menus import ListPageSource
from nextcord.utils import get

from ..bot import RF
from . import CustomButtonMenuPages, del_user_msg


async def syntax(command) -> str:
    params = []

    for key, value in command.params.items():
        if key not in ("self", "ctx"):
            params.append(f"[{key}]" if "None" in str(value) else f"<{key}>")

    return " ".join(params)


class HelpMenu(ListPageSource):
    def __init__(self, ctx, data, prefix) -> None:
        self.ctx = ctx
        self.guild_prefix = prefix

        super().__init__(data, per_page=1)


    async def write_page(self, menu, cog_name, fields=[]) -> Embed:
        offset = menu.current_page + 1
        len_data = len(self.entries)

        embed = Embed(title="Raid Force Help Menu", colour=0x2f3136, description=f"{cog_name} \n[ ] is optional arguments.\n< > is required arguments.")
        embed.set_thumbnail(url=self.ctx.guild.me.display_avatar)
        embed.set_footer(text=f"{offset:,} of {len_data:,} modules.")

        for name, value in fields:
            embed.add_field(name=name, value=value, inline=False)

        return embed


    async def format_page(self, menu, entries) -> Embed:
        fields = []
        cog_name = entries.qualified_name
        
        commandsList:list = sorted(list(filter(lambda c: not c.hidden, entries.walk_commands())), key=lambda c: c.name)

        for command in commandsList:
            aliases = f'| {", ".join(command.aliases)}' if command.aliases != [] else ''

            fields.append((f'{self.guild_prefix}{command.qualified_name} {aliases} {await syntax(command)}', 
                    command.description if command.description != '' else "This command have no description"))

        return await self.write_page(menu, cog_name, fields)


class Help(Cog):
    def __init__(self, bot: RF) -> None:
        self.bot = bot
        self.bot.help_command = None
        self.COGS = [p.stem for p in Path(".").glob("./RF/cogs/*.py")]


    async def cog_help(self, ctx: Context, cog: Cog) -> None:
        embed = Embed(title=f"Help with {cog.qualified_name}", color=0x2f3136)
        embed.set_author(name=ctx.author, icon_url=ctx.author.display_avatar)
        fields = []
        
        commandsList:list = sorted(list(filter(lambda c: not c.hidden, cog.walk_commands())), key=lambda c: c.name)

        for command in commandsList:
            aliases = f'| {", ".join(command.aliases)}' if command.aliases != [] else ''

            fields.append((f'{await self.get_guild_prefix(ctx)}{command.qualified_name} {aliases} {await syntax(command)}', 
                    command.description if command.description != '' else "This command have no description"))
        
        for name, value in fields:
            embed.add_field(name=name, value=value, inline=False)
        
        await ctx.send(embed=embed)


    async def cmd_help(self, ctx: Context, cmd: command) -> None:
        aliases = f' | {" | ".join(cmd.aliases)}' if cmd.aliases != [] else ''

        embed = Embed(title=f"Help with {cmd.qualified_name}", colour=0x2f3136)
        embed.set_author(name=ctx.author, icon_url=ctx.author.display_avatar)
        embed.add_field(name=f'{await self.get_guild_prefix(ctx)}{cmd.qualified_name} {aliases} {await syntax(cmd)}', 
                        value=cmd.description if cmd.description != '' else "This command have no description")

        await ctx.send(embed=embed)

    
    async def get_guild_prefix(self, ctx: Context) -> str:
        guild = self.bot.GUILD_DB.find_one({"_id": ctx.guild.id})

        return guild["prefix"]


    @command(name="help", description='Show help information.', hidden=True)
    @has_permissions(administrator=True)
    async def help_command(self, ctx: Context, cmds: Optional[str] = None) -> None:
        await del_user_msg(ctx)

        COGS = sorted([self.bot.get_cog(cog) for cog in self.COGS if len(list(filter(lambda c: not c.hidden, self.bot.get_cog(cog).walk_commands())))], key=lambda C: C.qualified_name)
        if cmds is not None:
            if (cmd := get(self.bot.commands, name=cmds)):
                await self.cmd_help(ctx, cmd)
            elif (cmd := get(COGS, qualified_name=cmds)):
                await self.cog_help(ctx, cmd)
            else:
                await ctx.send("That command does not exist.", delete_after=10)
                
        else:
            menu = CustomButtonMenuPages(source=HelpMenu(ctx, COGS, await self.get_guild_prefix(ctx)), timeout=30.0, ctx=ctx)
            await menu.start(ctx)


    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
            self.bot.cogs_ready.ready_up("Help")


def setup(bot):
    bot.add_cog(Help(bot))
