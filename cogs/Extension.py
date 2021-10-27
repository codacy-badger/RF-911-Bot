from pathlib import Path
from typing import Optional

from discord.ext.commands import Cog, CommandError, command, has_permissions


class ExtensionNotloaded(CommandError):
    pass


class ExtensionNotFound(CommandError):
    pass


class Extension(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.DELETE_AFTER = 45


    @staticmethod
    async def del_user_msg(ctx):
        delete_user_msg = await ctx.channel.fetch_message(ctx.message.id)
        await delete_user_msg.delete()


    @command(name= "load", description='Load extensions, required administrator permission')
    @has_permissions(administrator=True)
    async def _load(self, ctx, module: Optional[str]):

        await self.del_user_msg(ctx)

        try:
            self.bot.load_extension(f'bot.cogs.{module.lower()}')
            await ctx.send(f'Loaded `{module.lower()}`', delete_after = self.DELETE_AFTER)
        except:
            raise ExtensionNotloaded


    @command(name= 'unload', description='Unload extensions, required administrator permission')
    @has_permissions(administrator=True)
    async def _unload(self, ctx, module: Optional[str]):

        await self.del_user_msg(ctx)

        try:
            self.bot.unload_extension(f'bot.cogs.{module.upper()}')
            await ctx.send(f'UnLoaded `{module.upper()}`', delete_after = self.DELETE_AFTER)
        except:
            raise ExtensionNotloaded


    @command(name= 'reload', description='Reload extensions, required administrator permission')
    @has_permissions(administrator=True)
    async def _reload(self, ctx, module: Optional[str] = "all"):

        await self.del_user_msg(ctx)

        self._COGS = [p.stem for p in Path(".").glob("./cogs/*.py")]

        try:
            if "all" in module:
                for cog in self._COGS:
                    self.bot.reload_extension(f"cogs.{cog}")
                    
                await ctx.send(f"Reloaded all cogs successfully", delete_after = self.DELETE_AFTER)
            else:
                self.bot.reload_extension(f'cogs.{module.upper()}')
                await ctx.send(f'Reloaded `{module.upper()}`', delete_after = self.DELETE_AFTER)
        except:
            raise ExtensionNotloaded

    # Loading extensions errors
    @_load.error
    async def _load_error(self, ctx, exc):
        if isinstance(exc, ExtensionNotloaded):
            await ctx.send("Unable to load this extension", delete_after = self.DELETE_AFTER)


    @_unload.error
    async def _unload_error(self, ctx, exc):
        if isinstance(exc, ExtensionNotloaded):
            await ctx.send("Unable to unload this extension", delete_after = self.DELETE_AFTER)


    @_reload.error
    async def _reload_error(self, ctx, exc):
        if isinstance(exc, ExtensionNotloaded):
            await ctx.send("Unable to reload this extension", delete_after = self.DELETE_AFTER)


    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
            self.bot.cogs_ready.ready_up("Extension")


def setup(bot):
    bot.add_cog(Extension(bot))
