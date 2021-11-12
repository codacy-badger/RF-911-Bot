from nextcord import ButtonStyle, ui
from nextcord.ext.commands import Cog
from nextcord.ext.menus import ButtonMenuPages, MenuPaginationButton

from . import *


class CustomButtonMenuPages(ButtonMenuPages, inherit_buttons=False):
    """
    This class overrides the default ButtonMenuPages without inheriting the buttons
    by setting inherit_buttons to False.
    This allows us to add our own buttons with custom labels, styles, or even callbacks. 
    """

    def __init__(self, source, timeout):
        super().__init__(source, timeout=timeout, delete_message_after=True, clear_reactions_after=True)

        self.FIRST_PAGE = "<:end_back:906578658146254858>"
        self.LAST_PAGE = "<:end_next:906578658108522586>"
        self.PREVIOUS_PAGE = "<:previous:906578658062385192>"
        self.NEXT_PAGE = "<:next:906578657827512362>"
        self.STOP = "<:stop:906578657890418820>"

        # You can change the buttons to have custom labels and styles by setting
        # inherit_buttons=False above and adding them with self.add_item as shown below.
        # Note: None of the buttons are required you can leave any of them out
        self.add_item(MenuPaginationButton(emoji=self.FIRST_PAGE, label="First", style=ButtonStyle.success))
        self.add_item(MenuPaginationButton(emoji=self.NEXT_PAGE, label="Next", style=ButtonStyle.blurple))
        self.add_item(MenuPaginationButton(emoji=self.LAST_PAGE, label="Last", style=ButtonStyle.success))
        self.add_item(MenuPaginationButton(emoji=self.PREVIOUS_PAGE, label="Prev", style=ButtonStyle.blurple))
        
        # Reposition buttons
        self.children = [self.children[1], self.children[4], self.children[0], self.children[2], self.children[3]]
        
        # Disable buttons that are unavailable to be pressed at the start
        self._disable_unavailable_buttons()

    # To change the callback function, we can use the button decorator
    @ui.button(emoji='<:stop:906578657890418820>', label="Stop", style=ButtonStyle.red)
    async def stop_button(self, button, interaction):
        # await interaction.response.send_message("You pressed stop.", ephemeral=True)
        self.stop()


async def del_user_msg(ctx):
    delete_user_msg = await ctx.channel.fetch_message(ctx.message.id)
    await delete_user_msg.delete()


class __init__(Cog):
    def __init__(self, bot):
        self.bot = bot


    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
            self.bot.cogs_ready.ready_up("__init__")


def setup(bot):
    bot.add_cog(__init__(bot))
