from pathlib import Path
from typing import Optional

from nextcord import Embed
from nextcord.ext.commands import (Cog, CommandError, Context, DisabledCommand,
                                   command, is_owner)

from ..bot import RF
from . import del_user_msg


class ExtensionNotloaded(CommandError):
    pass


class Owner(Cog):
    def __init__(self, bot: RF) -> None:
        self.bot = bot
        self._COGS = [p.stem for p in Path(".").glob("./RF/cogs/*.py")]
        self.DELETE_AFTER = 5

    
    @command(name="toggle", description="Toggle on/off commands.\n`Owner` only command", hidden=True)
    @is_owner()
    async def _toggle(self, ctx: Context, command: command) -> None:

        command = self.bot.get_command(command)
        if command is None:
            await ctx.send("Invalid command", delete_after= self.DELETE_AFTER)
        elif ctx.command == command:
            await ctx.send("Unable to disable this command", delete_after= self.DELETE_AFTER)
        else:
            command.enabled = not command.enabled
            ternary = "enabled" if command.enabled else "disabled"
            await ctx.send(f'Command `{command.qualified_name}` has been {ternary}', delete_after= self.DELETE_AFTER)


    @command(name="load", description='Load extensions.\n`Owner` only command', hidden=True)
    @is_owner()
    async def _load(self, ctx: Context, module: Optional[str]) -> None:
        await del_user_msg(ctx)

        try:
            self.bot.load_extension(f'RF.cogs.{module.capitalize()}')
            await ctx.send(f'Loaded `{module.upper()}`', delete_after = self.DELETE_AFTER)
        except:
            raise ExtensionNotloaded


    @command(name='unload', description='Unload extensions.\n`Owner` only command', hidden=True)
    @is_owner()
    async def _unload(self, ctx: Context, module: Optional[str]) -> None:
        await del_user_msg(ctx)

        try:
            self.bot.unload_extension(f'RF.cogs.{module.capitalize()}')
            await ctx.send(f'Unloaded `{module.upper()}`', delete_after = self.DELETE_AFTER)
        except:
            raise ExtensionNotloaded


    @command(name='reload', description='Reload extensions.\n`Owner` only command', hidden=True)
    @is_owner()
    async def _reload(self, ctx: Context, module: Optional[str] = "all") -> None:
        await del_user_msg(ctx)

        try:
            if "all" in module:
                for cog in self._COGS:
                    self.bot.reload_extension(f"RF.cogs.{cog}")
                    
                await ctx.send(f"Reloaded all cogs successfully", delete_after = self.DELETE_AFTER)
            else:
                self.bot.reload_extension(f'RF.cogs.{module.capitalize()}')
                await ctx.send(f'Reloaded `{module.upper()}`', delete_after = self.DELETE_AFTER)
        except:
            raise ExtensionNotloaded


    @command(name='cogs', description = 'List all extensions.\n`Owner` only command', hidden=True)
    @is_owner()
    async def _list_all_extensions(self, ctx: Context) -> None:
        await del_user_msg(ctx)

        embed = Embed(title="List of extensions: ", colour= 0x2f3136, description="\n".join(self._COGS))
        await ctx.send(embed=embed, delete_after = self.DELETE_AFTER)


    @Cog.listener()
    async def on_command_error(self, ctx: Context, exc) -> None:
        if isinstance(exc, ExtensionNotloaded):
            await ctx.send("Unable to unload this extension", delete_after = self.DELETE_AFTER)
        elif isinstance(exc, DisabledCommand):
            await ctx.send("This command have been disabled", delete_after = self.DELETE_AFTER)


    @Cog.listener()
    async def on_ready(self) -> None:
        if not self.bot.ready:
            self.bot.cogs_ready.ready_up("Owner")


def setup(bot):
    bot.add_cog(Owner(bot))
