from asyncio import sleep
from datetime import datetime
from glob import glob
from os import getenv

# from apscheduler.schedulers.asyncio import AsyncIOScheduler
# from apscheduler.triggers.cron import CronTrigger
from discord import DMChannel, Embed, File
from discord.errors import Forbidden, HTTPException
from discord.ext.commands import BadArgument
from discord.ext.commands import Bot as BotBase
from discord.ext.commands import (CommandNotFound, CommandOnCooldown, Context,
                                  MissingRequiredArgument, when_mentioned_or)
from dotenv import load_dotenvgit
from pymongo import MongoClient

OWNER_IDS = [759385760071155783, 188903265931362304, 801344820757004328, 454886359354703882, 342418762152280076] # 5 Councils
COGS = [path.split("\\")[-1][:-3] for path in glob("./cogs/*.py")]
IGNORE_EXCEPTIONS = (CommandNotFound, BadArgument)

class Ready(object):
    def __init__(self):
        for cog in COGS:
            setattr(self, cog, False)

    def ready_up(self, cog):
        
        setattr(self, cog, True)
        print(f" {cog} cog ready")

    def all_ready(self):
        return all([getattr(self, cog) for cog in COGS])


class Bot(BotBase):
    def __init__(self):
        self.ready = False
        self.cogs_ready = Ready()

        self.guild = None
        # self.scheduler = AsyncIOScheduler()

        self.MONGO_CLIENT =  MongoClient(getenv("DATABASE"))
        self.DB = self.MONGO_CLIENT["Daily_DB"]
        self.GUILD_DB = self.DB['Guild']

        super().__init__(command_prefix=self.prefix, owner_ids=OWNER_IDS)


    def setup(self):
        load_dotenv()
        for cog in COGS:
            self.load_extension(f"cogs.{cog}")
            print(f" {cog} cog loaded")

        print("Setup complete")


    def prefix(self, bot, msg):
        prefix = self.GUILD_DB.find_one({"_id": f'{msg.guild.id}'})
        
        return when_mentioned_or(str(prefix["prefix"]))(bot, msg)


    def run(self):

        print("Running setup ...")
        self.setup()
        self.TOKEN = getenv("TOKEN")

        print("Running RF 911 ...")
        super().run(self.TOKEN, reconnect=True)


    async def process_commands(self, message):
        ctx = await self.get_context(message, cls=Context)

        if ctx.command is not None and ctx.guild is not None:
            if message.author.id in self.banlist:
                await ctx.send("You are banned from using commands.")

            elif not self.ready:
                await ctx.send("I'm not ready to receive commands. Please wait a few seconds.")

            else:
                await self.invoke(ctx)


    # async def rules_reminder(self):
    #     await self.stdout.send("Remember to adhere to the rules!")


    async def on_connect(self):
        print("RF 911 connected")


    async def on_disconnect(self):
        print("RF 911 disconnected")


    async def on_error(self, err, *args, **kwargs):
        if err == "on_command_error":
            await args[0].send("Something went wrong.")

        await self.stdout.send("An error occured.")
        raise


    async def on_command_error(self, ctx, exc):
        if any([isinstance(exc, error) for error in IGNORE_EXCEPTIONS]):
            pass

        elif isinstance(exc, MissingRequiredArgument):
            await ctx.send("One or more required arguments are missing.")

        elif isinstance(exc, CommandOnCooldown):
            await ctx.send(f"That command is on {str(exc.cooldown.type).split('.')[-1]} cooldown. Try again in {exc.retry_after:,.2f} secs.")

        elif hasattr(exc, "original"):
            # if isinstance(exc.original, HTTPException):
            # 	await ctx.send("Unable to send message.")

            if isinstance(exc.original, Forbidden):
                await ctx.send("I do not have permission to do that.")

            else:
                raise exc.original

        else:
            raise exc


    async def on_ready(self):
        if not self.ready:
            # self.guild = self.get_guild(806551631754690611)
            # self.stdout = self.get_channel(803112623951970314)
            # self.scheduler.add_job(self.rules_reminder, CronTrigger(day_of_week=0, hour=12, minute=0, second=0))
            # self.scheduler.start()

            while not self.cogs_ready.all_ready():
                await sleep(0.5)

            # await self.stdout.send("Now online!")
            self.ready = True
            print("RF 911 ready")

            # meta = self.get_cog("Meta")
            # await meta.set()

        else:
            print("RF 911 reconnected")


    async def on_message(self, message):
        if not message.author.bot:
            if isinstance(message.channel, DMChannel):
                if len(message.content) < 50:
                    await message.channel.send("Your message should be at least 50 characters in length.")

                else:
                    member = self.guild.get_member(message.author.id)
                    embed = Embed(title="Modmail",
                                  colour=member.colour,
                                  timestamp=datetime.utcnow())

                    embed.set_thumbnail(url=member.avatar_url)

                    fields = [("Member", member.display_name, False),
                              ("Message", message.content, False)]

                    for name, value, inline in fields:
                        embed.add_field(name=name, value=value, inline=inline)
                    
                    mod = self.get_cog("Mod")
                    await mod.log_channel.send(embed=embed)
                    await message.channel.send("Message relayed to moderators.")

            else:
                await self.process_commands(message)


bot = Bot()
