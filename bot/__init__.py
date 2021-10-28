from asyncio import sleep
from os import getenv
from pathlib import Path

# from apscheduler.schedulers.asyncio import AsyncIOScheduler
# from apscheduler.triggers.cron import CronTrigger
from discord import Activity, ActivityType, DMChannel, Embed, Intents, AuditLogAction
from discord.errors import Forbidden
from discord.ext.commands import BadArgument
from discord.ext.commands import Bot as BotBase
from discord.ext.commands import (CommandNotFound, CommandOnCooldown, Context,
                                  MissingRequiredArgument, when_mentioned_or)
from dotenv import load_dotenv
from pymongo import MongoClient

OWNER_IDS = [759385760071155783, 188903265931362304, 801344820757004328, 454886359354703882, 342418762152280076] # 5 Councils
COGS = [p.stem for p in Path(".").glob("./cogs/*.py")]
IGNORE_EXCEPTIONS = (CommandNotFound, BadArgument)
VERSION = 0.4


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

        super().__init__(command_prefix=self.prefix,
                         case_insensitive=True,
                         owner_ids=set(OWNER_IDS),
                         intents=Intents.all()
                        )


    def setup(self):
        print("---------- Setting up ----------")
        for cog in COGS:
            self.load_extension(f"cogs.{cog}")
            print(f"{cog.upper()} cog loaded")

        print("-------- Setup complete --------")


    def prefix(self, bot, msg):
        prefix = self.GUILD_DB.find_one({"_id": msg.guild.id})
        
        return when_mentioned_or(str(prefix["prefix"]))(bot, msg)


    def run(self):
        print("------- Running setup ... ------")
        self.setup()
        self.TOKEN = getenv("TOKEN")
        print("------ Running RF 911 ... ------")
        super().run(self.TOKEN, reconnect=True)

    
    async def on_guild_join(self, guild):
        def check(event):
            return event.target.id == self.user.id

        bot_entry = await guild.audit_logs(action=AuditLogAction.bot_add).find(check)
        await bot_entry.user.send(f'Hello {bot_entry.user.mention}, Thanks for inviting me! \nDefault prefix is "rf-"')

        self.GUILD_DB.insert_one({
                "_id": guild.id,
                "server name": guild.name,
                "prefix": "rf-",
                "Bounty submission": None,
                "Daily channel": None,
                "Log channel": None,
                "Mute role": None,
            }
        )


    async def on_guild_remove(self, guild):
        self.GUILD_DB.delete_one({"_id": guild.id})


    async def process_commands(self, message):
        ctx = await self.get_context(message, cls=Context)

        if ctx.command is not None and ctx.guild is not None:
            # if message.author.id in self.banlist:
            #     await ctx.send("You are banned from using commands.")

            if not self.ready:
                await ctx.send("I'm not ready to receive commands. Please wait a few seconds.")

            else:
                await self.invoke(ctx)


    # async def rules_reminder(self):
    #     await self.stdout.send("Remember to adhere to the rules!")


    async def on_connect(self):
        print("------- RF 911 Connected -------")


    async def on_disconnect(self):
        print("------ RF 911 Disconnected -----")


    async def on_error(self, err, *args, **kwargs):
        if err == "on_command_error":
            await args[0].send("Something went wrong.", delete_after=15)

        # await self.stdout.send("An error occured.")
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
            print('--------- Logged in as ---------')
            print(f'Name : {self.user}')
            print(f'IDs : {self.user.id}')
            print(f"Ping: {round(self.latency* 1000)} ms")
            print('--------------------------------')

            await self.change_presence(activity=Activity(type=ActivityType.watching, name="Raid Force 911")) 
            # meta = self.get_cog("Meta")
            # await meta.set()

        else:
            print("RF 911 reconnected")


    # async def on_message(self, message):
    #     if not message.author.bot:
    #         if isinstance(message.channel, DMChannel):
    #             if len(message.content) < 50:
    #                 await message.channel.send("Your message should be at least 50 characters in length.")

    #             else:
    #                 member = self.guild.get_member(message.author.id)
    #                 embed = Embed(title="Modmail",
    #                               colour=member.colour,
    #                               timestamp=datetime.utcnow())

    #                 embed.set_thumbnail(url=member.avatar_url)

    #                 fields = [("Member", member.display_name, False),
    #                           ("Message", message.content, False)]

    #                 for name, value, inline in fields:
    #                     embed.add_field(name=name, value=value, inline=inline)
                    
    #                 mod = self.get_cog("Mod")
    #                 await mod.log_channel.send(embed=embed)
    #                 await message.channel.send("Message relayed to moderators.")

    #         else:
    #             await self.process_commands(message)


bot = Bot()
