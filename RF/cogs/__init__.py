from os import getenv

from nextcord import ButtonStyle, Interaction, ui
from nextcord.ext.commands import Cog, Context
from nextcord.ext.menus import ButtonMenuPages, MenuPaginationButton
from nextcord.ext.menus.utils import _cast_emoji
from pymongo.mongo_client import MongoClient
from RF.utils.Moderation import ResponseError

from ..bot import RF
from . import *


class CustomMenuPaginationButton(ui.Button['MenuPaginationButton']):
    """
    A custom button for pagination that will be disabled when unavailable.
    """

    def __init__(self, ctx, **kwargs):
        self.ctx = ctx
        super().__init__(**kwargs)
        emoji = kwargs.get("emoji", None)
        self._emoji = _cast_emoji(emoji) if emoji else None


    async def callback(self, interaction: Interaction):
        """
        Callback for when this button is pressed
        """
        if self._emoji is None:
            return

        assert self.view is not None
        view: ButtonMenuPages = self.view
        
        if self.ctx.author.id == interaction.user.id:
            # change the current page
            if str(self._emoji) == view.FIRST_PAGE:
                await view.go_to_first_page()
            elif str(self._emoji) == view.PREVIOUS_PAGE:
                await view.go_to_previous_page()
            elif str(self._emoji) == view.NEXT_PAGE:
                await view.go_to_next_page()
            elif str(self._emoji) == view.LAST_PAGE:
                await view.go_to_last_page()

            # disable buttons that are unavailable
            view._disable_unavailable_buttons()

            # disable all buttons if stop is pressed
            if str(self._emoji) == view.STOP:
                return view.stop()

            # update the view
            await interaction.response.edit_message(view=view)
        else:
            await interaction.response.send_message("You don't have permission to do this action.", ephemeral=True)


class CustomButtonMenuPages(ButtonMenuPages, inherit_buttons=False):
    """
    This class overrides the default ButtonMenuPages without inheriting the buttons
    by setting inherit_buttons to False.
    This allows us to add our own buttons with custom labels, styles, or even callbacks. 
    """

    def __init__(self, source, timeout, ctx: Context):
        super().__init__(source, timeout=timeout, delete_message_after=True, clear_reactions_after=True)

        self.FIRST_PAGE = "<:end_first:906578658146254858>"
        self.LAST_PAGE = "<:end_final:906578658108522586>"
        self.PREVIOUS_PAGE = "<:previous:906578658062385192>"
        self.NEXT_PAGE = "<:next:906578657827512362>"
        self.STOP = "<:stop:906578657890418820>"

        # You can change the buttons to have custom labels and styles by setting
        # inherit_buttons=False above and adding them with self.add_item as shown below.
        # Note: None of the buttons are required you can leave any of them out
        self.add_item(CustomMenuPaginationButton(ctx=ctx, emoji=self.FIRST_PAGE, label="First", style=ButtonStyle.success))
        self.add_item(CustomMenuPaginationButton(ctx=ctx, emoji=self.PREVIOUS_PAGE, label="Prev", style=ButtonStyle.blurple))
        self.add_item(CustomMenuPaginationButton(ctx=ctx, emoji=self.STOP, label="Stop", style=ButtonStyle.red))
        self.add_item(CustomMenuPaginationButton(ctx=ctx, emoji=self.NEXT_PAGE, label="Next", style=ButtonStyle.blurple))        
        self.add_item(CustomMenuPaginationButton(ctx=ctx, emoji=self.LAST_PAGE, label="Last", style=ButtonStyle.success))

        # Disable buttons that are unavailable to be pressed at the start
        self._disable_unavailable_buttons()


def isModerator(ctx: Context):
    MONGO_CLIENT = MongoClient(getenv("DATABASE"))
    DB = MONGO_CLIENT["RF911"]
    GUILD_DB = DB["Guild"]
    GUILD = GUILD_DB.find_one({"_id": ctx.guild.id})
    try:
        roleID = GUILD["Moderator Role"]
    except KeyError:
        raise ResponseError("No Moderator have been assigned.")

    if roleID not in [role.id for role in ctx.author.roles] and not ctx.author.guild_permissions.administrator and ctx.guild.owner_id != ctx.author.id:
        raise ResponseError("You're not moderator.")
    return True


async def delUserMsg(ctx):
    delete_user_msg = await ctx.channel.fetch_message(ctx.message.id)
    await delete_user_msg.delete()


class __init__(Cog):
    def __init__(self, bot: RF):
        self.bot = bot


    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
            self.bot.cogs_ready.ready_up("__init__")


def setup(bot):
    bot.add_cog(__init__(bot))
