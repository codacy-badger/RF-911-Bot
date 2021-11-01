from nextcord import Embed, TextChannel, Colour
from nextcord.ext.commands import BucketType, Cog, Greedy, command, cooldown
from datetime import datetime

from . import del_user_msg


class Embedder(Cog):
    def __init__(self, bot):
        self.bot = bot


    @command(name="embedder", aliases=["embed"], description="Embed your message")
    @cooldown(3, 30, BucketType.user)
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

        await del_user_msg(ctx)
        await channel.send(embed=embedder)


    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
            self.bot.cogs_ready.ready_up("Embedder")


def setup(bot):
    bot.add_cog(Embedder(bot))
