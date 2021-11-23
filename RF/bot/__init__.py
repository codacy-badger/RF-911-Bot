from asyncio import sleep
from datetime import datetime
from os import getenv
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv
from nextcord import (Activity, ActivityType, DMChannel, Embed,
                      Intents)
from nextcord.errors import Forbidden
from nextcord.ext.commands import BadArgument
from nextcord.ext.commands import Bot as BotBase
from nextcord.ext.commands import (CommandNotFound, CommandOnCooldown, Context,
                                   MissingRequiredArgument, when_mentioned_or)
from nextcord.ext.commands.errors import MissingPermissions
from pymongo import MongoClient
from pytz import timezone

OWNER_IDS = [188903265931362304]
COGS = [p.stem for p in Path(".").glob("./RF/cogs/*.py")]
IGNORE_EXCEPTIONS = (CommandNotFound, BadArgument, MissingPermissions)


class Ready(object):
    def __init__(self):
        for cog in COGS:
            setattr(self, cog, False)

    def ready_up(self, cog):
        setattr(self, cog, True)
        print(f"{cog.upper()} cog ready")

    def all_ready(self):
        return all([getattr(self, cog) for cog in COGS])


class RF(BotBase):
    def __init__(self):
        self.ready = False
        self.guild = None
        self.cogs_ready = Ready()
        self.load_dotenv = load_dotenv()

        self.MONGO_CLIENT = MongoClient(getenv("DATABASE"))
        self.DB = self.MONGO_CLIENT["RF911"]
        self.GUILD_DB = self.DB["Guild"]
        self.MUTE_DB = self.DB["Mute"]
        self.CASE_DB = self.DB["Case"]
        self.WARN_DB = self.DB["Warns"]
        self.ROBLOX_DB = self.DB["Roblox"]
        self.BANNED_USER_DB = self.DB["Banned User"]
        self.SCHEDULER = self.DB['Scheduler']
        
        self.scheduler = AsyncIOScheduler(timezone=timezone("Asia/Ho_Chi_Minh"),)
        
        super().__init__(command_prefix=self.prefix,
                         case_insensitive=True,
                         owner_ids=set(OWNER_IDS),
                         intents=Intents.all(),)


    def setup(self):
        print("--------- Setting up -----------")
        for cog in COGS:
            self.load_extension(f"RF.cogs.{cog}")
            print(f"{cog.upper()} cog loaded")

        print("--------- Setup complete -------")


    def prefix(self, bot, msg):
        prefix = self.GUILD_DB.find_one({"_id": msg.guild.id})

        return when_mentioned_or(str(prefix["prefix"]))(bot, msg)


    def run(self, version):
        self.VERSION = version

        print("--------- Running setup ... ----")
        self.setup()
        self.TOKEN = getenv("TOKEN")
        print("--------- Running RF ... -------")
        super().run(self.TOKEN, reconnect=True)


    async def on_guild_join(self, guild):
        self.GUILD_DB.insert_one({"_id": guild.id, 
                                  "server name": guild.name,
                                  "prefix": "rf-",
                                  "Bounty submission": None,
                                  "Daily channel": None,
                                  "Log channel": None,
                                  "Mute role": None,
                                  "Default role": None,})


    async def on_guild_remove(self, guild):
        self.GUILD_DB.delete_one({"_id": guild.id})
        self.WARN_DB.delete_many({"Guild ID": guild.id})
        self.CASE_DB.delete_many({"Guild ID": guild.id})
        self.MUTE_DB.delete_many({"Guild ID": guild.id})


    async def process_commands(self, message):
        ctx = await self.get_context(message, cls=Context)
        self.banlist_user = [
            user["_id"]
            for user in self.BANNED_USER_DB.find({"Guild ID": message.guild.id, "Type": "user"})]
        self.banlist_channel = [channel["_id"] for channel in self.BANNED_USER_DB.find({"Guild ID": message.guild.id, "Type": "channel"})]

        if ctx.command is not None and ctx.guild is not None:
            if message.author.id in self.banlist_user:
                await ctx.reply("You are banned from using commands.", delete_after=2)
                
            elif message.channel.id in self.banlist_channel:
                await ctx.reply("Commands are disabled in this channel.", delete_after=2)

            elif not self.ready:
                await ctx.send(
                    "I'm not ready to receive commands. Please wait a few seconds.",
                    delete_after=5,
                )

            else:
                await self.invoke(ctx)


    async def on_connect(self):
        print("--------- RF Connected ---------")


    async def on_disconnect(self):
        print("--------- RF Disconnected ------")


    async def on_error(self, err, *args, **kwargs):
        if err == "on_command_error":
            await args[0].send(f"Something went wrong: {args[1]}", delete_after=3)
            embed = Embed(
                title="Errors occurred", colour=0x2F3136, timestamp=datetime.now(tz=timezone("Asia/Ho_Chi_Minh"))
            )

            fields = [
                ("In Server: ", args[0].guild, False),
                ("In Channel: ", args[0].channel, False),
                ("Command Trigger By:", args[0].author, False),
                ("Command Error: ", args[1], False),
            ]

            [embed.add_field(name=name, value=value, inline=inline) for name, value, inline in fields]

            await self.error_channel.send(embed=embed)
        raise


    async def on_command_error(self, ctx, exc):
        if any([isinstance(exc, error) for error in IGNORE_EXCEPTIONS]):
            pass

        elif isinstance(exc, MissingRequiredArgument):
            await ctx.send(
                "One or more required arguments are missing.", delete_after=3
            )

        elif isinstance(exc, CommandOnCooldown):
            await ctx.send(
                f"That command is on {str(exc.cooldown.type).split('.')[-1]} cooldown. Try again in {exc.retry_after:,.2f} secs.",
                delete_after=3,
            )

        elif isinstance(exc, MissingPermissions):
            await ctx.send(exc)

        elif hasattr(exc, "original"):
            if isinstance(exc.original, Forbidden):
                await ctx.send("I do not have permission to do that.", delete_after=3)

            else:
                raise exc.original

        else:
            raise exc


    async def on_ready(self):
        if not self.ready:
            while not self.cogs_ready.all_ready():
                await sleep(0.5)

            self.ready = True
            print("--------- Logged in as ---------")
            print(f"Name: {self.user}")
            print(f"ID: {self.user.id}")
            print(f"Version: {self.VERSION}")
            print(f"Ping: {round(self.latency* 1000)} ms")
            print("--------------------------------")

            await self.change_presence(activity=Activity(type=ActivityType.watching, name="Raid Force"))
            self.scheduler.start()
            self.error_channel = self.get_channel(906829491756732456)

        else:
            print("--------- RF Reconnected -------")


    async def on_message(self, message):
        if isinstance(message.channel, DMChannel):
            pass
        else:
            await self.process_commands(message)


bot = RF()