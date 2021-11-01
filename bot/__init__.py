from asyncio import sleep
from os import getenv
from pathlib import Path

# from apscheduler.schedulers.asyncio import AsyncIOScheduler
# from apscheduler.triggers.cron import CronTrigger
from nextcord import (Activity, ActivityType, AuditLogAction, DMChannel, Embed,
                     Intents)
from nextcord.errors import Forbidden
from nextcord.ext.commands import BadArgument
from nextcord.ext.commands import Bot as BotBase
from nextcord.ext.commands import (CommandNotFound, CommandOnCooldown, Context,
                                  MissingRequiredArgument, when_mentioned_or)
from nextcord.ext.commands.errors import MissingPermissions
from dotenv import load_dotenv
from pymongo import MongoClient

OWNER_IDS = [188903265931362304] # 5 Councils
COGS = [p.stem for p in Path(".").glob("./cogs/*.py")]
IGNORE_EXCEPTIONS = (CommandNotFound, BadArgument)


class Ready(object):
    def __init__(self):
        for cog in COGS:
            setattr(self, cog, False)


    def ready_up(self, cog):
        setattr(self, cog, True)
        print(f"{cog.upper()} cog ready")


    def all_ready(self):
        return all([getattr(self, cog) for cog in COGS])


class Bot(BotBase):
    def __init__(self):
        self.ready = False
        self.cogs_ready = Ready()
        self.load_dotenv = load_dotenv()

        self.guild = None
        # self.scheduler = AsyncIOScheduler()

        self.MONGO_CLIENT =  MongoClient(getenv("DATABASE"))
        self.DB = self.MONGO_CLIENT["RF911"]
        self.GUILD_DB = self.DB['Guild']
        self.MUTE_DB = self.DB["Mute"]
        self.CASE_DB = self.DB["Case"]
        self.WARN_DB = self.DB["Warns"]
        self.BANNED_USER_DB = self.DB["Banned User"]

        super().__init__(command_prefix=self.prefix,
                         case_insensitive=True,
                         owner_ids=set(OWNER_IDS),
                         intents=Intents.all())


    def setup(self):
        print("---------- Setting up ----------")
        for cog in COGS:
            self.load_extension(f"cogs.{cog}")
            print(f"{cog.upper()} cog loaded")

        print("-------- Setup complete --------")


    def prefix(self, bot, msg):
        prefix = self.GUILD_DB.find_one({"_id": msg.guild.id})
        
        return when_mentioned_or(str(prefix["prefix"]))(bot, msg)


    def run(self, version):
        self.VERSION = version

        print("------- Running setup ... ------")
        self.setup()
        self.TOKEN = getenv("TOKEN")
        print("------ Running RF 911 ... ------")
        super().run(self.TOKEN, reconnect=True)


    async def on_guild_join(self, guild):
        def check(event):
            return event.target.id == self.user.id

        bot_entry = await guild.audit_logs(action=AuditLogAction.bot_add).find(check)
        await bot_entry.user.send(f'Hello {bot_entry.user.mention}, Thanks for inviting me! \nDefault prefix is "rf-" \nPlease use following commands to complete the setup: set-default-role, set-bounty-channel, set-lockdown-channel, set-log-channel, set-mute-role')

        self.GUILD_DB.insert_one({
                "_id": guild.id,
                "server name": guild.name,
                "prefix": "rf-",
                "Bounty submission": None,
                "Daily channel": None,
                "Log channel": None,
                "Mute role": None,
                "Default role": None,
            }
        )


    async def on_guild_remove(self, guild):
        self.GUILD_DB.delete_one({"_id": guild.id})
        self.WARN_DB.delete_many({"Guild ID": guild.id})
        self.CASE_DB.delete_many({"Guild ID": guild.id})
        self.MUTE_DB.delete_many({"Guild ID": guild.id})


    async def process_commands(self, message):
        ctx = await self.get_context(message, cls=Context)
        self.banlist_user = [user["_id"] for user in self.BANNED_USER_DB.find({"Guild ID": message.guild.id, "Type": 'user'})]
        self.banlist_channel = [channel["_id"] for channel in self.BANNED_USER_DB.find({"Guild ID": message.guild.id, "Type": 'channel'})]

        if ctx.command is not None and ctx.guild is not None:
            if message.author.id in self.banlist_user:
                await ctx.reply("You are banned from using commands.", delete_after=2)
            elif message.channel.id in self.banlist_channel:
                await ctx.reply("Commands are disabled in this channel.", delete_after=2)

            elif not self.ready:
                await ctx.send("I'm not ready to receive commands. Please wait a few seconds.", delete_after=5)

            else:
                await self.invoke(ctx)


    async def on_connect(self):
        print("------- RF 911 Connected -------")


    async def on_disconnect(self):
        print("------ RF 911 Disconnected -----")


    async def on_error(self, err, *args, **kwargs):
        if err == "on_command_error":
            await args[0].send(f"Something went wrong. \n{err}", delete_after=15)

        raise


    async def on_command_error(self, ctx, exc):
        if any([isinstance(exc, error) for error in IGNORE_EXCEPTIONS]):
            pass

        elif isinstance(exc, MissingRequiredArgument):
            await ctx.send("One or more required arguments are missing.")

        elif isinstance(exc, CommandOnCooldown):
            await ctx.send(f"That command is on {str(exc.cooldown.type).split('.')[-1]} cooldown. Try again in {exc.retry_after:,.2f} secs.")

        elif isinstance(exc, MissingPermissions):
            await ctx.send(exc)

        elif hasattr(exc, "original"):
            if isinstance(exc.original, Forbidden):
                await ctx.send("I do not have permission to do that.")

            else:
                raise exc.original

        else:
            raise exc


    async def on_ready(self):
        if not self.ready:
            while not self.cogs_ready.all_ready():
                await sleep(0.5)

            self.ready = True
            print('--------- Logged in as ---------')
            print(f'Name : {self.user}')
            print(f'IDs : {self.user.id}')
            print(f'Version: {self.VERSION}')
            print(f'Ping: {round(self.latency* 1000)} ms')
            print('--------------------------------')

            await self.change_presence(activity=Activity(type=ActivityType.watching, name="Raid Force 911")) 
            # meta = self.get_cog("Meta")
            # await meta.set()

        else:
            print("RF 911 reconnected")


    async def on_message(self, message):
        if not message.author.bot:
            if isinstance(message.channel, DMChannel):
                pass
            else:
                await self.process_commands(message)


bot = Bot()
