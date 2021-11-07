from nextcord import Embed, TextChannel, Colour, ui, ButtonStyle
from nextcord.ext.commands import BucketType, Cog, Greedy, command, cooldown
from nextcord.ext.commands.core import has_permissions
from nextcord.ext.menus import Menu, ButtonMenu
from datetime import datetime, timezone

from . import del_user_msg


class ButtonConfirm(ButtonMenu):
    def __init__(self, ctx, text):
        super().__init__(timeout=18000.0, delete_message_after=True)
        self.text = text
        self.ctx = ctx
        self.result = None

    async def send_initial_message(self, ctx, channel):
        return await channel.send(content="Embed preview before send", embed=self.text, view=self)

    @ui.button(label="Post", style=ButtonStyle.success)
    async def do_confirm(self, button, interaction):
        if self.ctx.author == interaction.user:
            self.result = True
            self.stop()
        else:
            await interaction.response.send_message("You don't have permission to do this action.", ephemeral=True)

    @ui.button(label="Cancel", style=ButtonStyle.danger)
    async def do_deny(self, button, interaction):
        if self.ctx.author == interaction.user:
            self.result = False
            self.stop()
        else:
            await interaction.response.send_message("You don't have permission to do this action.", ephemeral=True)

    async def prompt(self, ctx):
        await Menu.start(self, ctx, wait=True)
        return self.result


class Embedder(Cog):
    def __init__(self, bot):
        self.bot = bot


    @command(name="embedder", aliases=["embed"], description="Custem Embedder. Required manage guild permissions.")
    @cooldown(3, 30, BucketType.user)
    @has_permissions(manage_guild=True)
    async def _msg_embedder(self, ctx, channels : Greedy[TextChannel]):

        channel_id = (channel.id for channel in channels).__next__()
        channel = self.bot.get_channel(channel_id)

        await ctx.send("Title for your embed: ")
        title = await self.bot.wait_for('message', check=lambda message: message.author == ctx.author and message.channel.id == ctx.channel.id)

        await ctx.send("Desciption for your embed: ")
        description = await self.bot.wait_for('message', check=lambda message: message.author == ctx.author and message.channel.id == ctx.channel.id)

        await ctx.send("Footer text for your embed: ")
        footer = await self.bot.wait_for('message', check=lambda message: message.author == ctx.author and message.channel.id == ctx.channel.id)

        await ctx.send("Color for your embed: ")
        color = await self.bot.wait_for('message', check=lambda message: message.author == ctx.author and message.channel.id == ctx.channel.id)

        if color.content.lower() == "none":
            r, g, b = 47, 49, 54
        else:
            r, g, b = int(color.content[0:2], 16), int(color.content[2:4], 16), int(color.content[4:6], 16)
        

        await ctx.send("Times text for your embed? y/n")
        times = await self.bot.wait_for('message', check=lambda message: message.author == ctx.author and message.channel.id == ctx.channel.id)

        if times.content.lower() in ["y", 'yes']:
            embedder = Embed(title=title.content if title.content.lower() != 'none' else Embed.Empty, colour=Colour.from_rgb(r, g, b), description=description.content  if description.content.lower() != 'none' else Embed.Empty, timestamp=datetime.utcnow())
        else:
            embedder = Embed(title=title.content if title.content.lower() != 'none' else Embed.Empty, colour=Colour.from_rgb(r, g, b), description=description.content  if description.content.lower() != 'none' else Embed.Empty)
        
        embedder.set_author(name=ctx.author, icon_url=ctx.author.display_avatar)
        embedder.set_footer(text=footer.content  if footer.content.lower() != 'none' else Embed.Empty)

        await ctx.send("Thumbnails text for your embed: ")
        thumbnails = await self.bot.wait_for('message', check=lambda message: message.author == ctx.author and message.channel.id == ctx.channel.id)
        embedder.set_thumbnail(url=thumbnails.content  if thumbnails.content.lower() != 'none' else Embed.Empty)

        await ctx.send("Image text for your embed: ")
        image = await self.bot.wait_for('message', check=lambda message: message.author == ctx.author and message.channel.id == ctx.channel.id)
        embedder.set_image(url=image.content if image.content.lower() != 'none' else Embed.Empty)


        await ctx.send("How many fields for your embed: ")
        number_fields = await self.bot.wait_for('message', check=lambda message: message.author == ctx.author and message.channel.id == ctx.channel.id)

        for i in range(int(number_fields.content)):
            await ctx.send(f"Field {i+1}: \nPlease enter your field like this: name, value, inline")
            field = await self.bot.wait_for('message', check=lambda message: message.author == ctx.author and message.channel.id == ctx.channel.id)

            for name, value, inline in [field.content.split(',')]:
                embedder.add_field(name=name, value=value, inline=False if inline.strip().lower() == "false" else True)

        answer = await ButtonConfirm(ctx, embedder).prompt(ctx)
        if answer is True:
            await channel.send(embed=embedder)
        else:
            await ctx.send("Action canceled.", delete_after=10)


    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
            self.bot.cogs_ready.ready_up("Embedder")


def setup(bot):
    bot.add_cog(Embedder(bot))
