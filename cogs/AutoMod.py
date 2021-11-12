from asyncio import sleep
from datetime import datetime, timedelta, timezone
from json import dump, load
from os import getenv
from os.path import exists

from apscheduler.jobstores.base import JobLookupError, ConflictingIdError
from better_profanity import profanity
from nextcord import Member
from nextcord.ext.commands import Cog
from nextcord.utils import get
from pymongo import MongoClient

from .Mod import Mod


class Automod(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.MOD = Mod(bot)
        self.first_times = True

        self.MONGO_CLIENT = MongoClient(getenv("DATABASE"))
        self.DB = self.MONGO_CLIENT["RF911"]
        self.BANNED_DB = self.DB["Banned"]
        self.GUILD_DB = self.DB["Guild"]
        self.BANNED_WORDS_DB = self.DB["Banned Words"]


    async def get_mute_role(self, ctx):
        get_mute = self.GUILD_DB.find_one({"_ids": ctx.guild.id})
        return get_mute["Mute role"] if get_mute is not None else None


    async def auto_muted(self, message, duration, reason, auto=True):
        unmutes = await self.MOD.mute_members(
            message,
            targets=[message.author],
            durations=duration,
            reason=reason,
            auto=auto,
        )
        tempmute = self.MOD.time_converter(duration)

        if len(unmutes):
            await sleep(tempmute)
            await self.MOD.unmute_members(
                message, message.guild, [message.author], auto=auto
            )


    @staticmethod
    async def create_user(message):
        user_info = {
            "User Name": f"{message.author}",
            "Spike": 0,
            "Spam Message": [],
            "Mention Message": [],
        }

        with open(f"./cogs/message/{message.guild.id}.json", "r+") as f:
            data = load(f)
            data[str(message.author.id)] = user_info
            f.seek(0)
            dump(data, f, indent=4)
            f.truncate()


    async def load_banned_words(self, message):
        BANNED_WORDS_ID = self.BANNED_WORDS_DB.find_one({"_id": message.guild.id})

        if BANNED_WORDS_ID is None:
            self.BANNED_WORDS_DB.insert_one(
                {"_id": message.guild.id, "Words": ["nigga", "fagot"]}
            )
            BANNED_WORDS = ["nigga", "fagot"]
        else:
            BANNED_WORDS = BANNED_WORDS_ID["Words"]

        profanity.load_censor_words(BANNED_WORDS)


    async def check_spike(self, message):
        def get_info():
            with open(f"./cogs/message/{message.guild.id}.json", "r") as f:
                user = load(f)
            return user[f"{message.author.id}"]

        try:
            userInfo = get_info()
        except KeyError:
            await self.create_user(message)
            userInfo = get_info()

        return userInfo["Spike"]


    @staticmethod
    async def write_file(message, position ,option, content = None):
        GUILD_INFO = f"./cogs/message/{message.guild.id}.json"
        
        with open(GUILD_INFO, 'r+') as f:
            user = load(f)

            if position == "Spike":
                if option:
                    user[str(message.author.id)]["Spike"] = user[str(message.author.id)]['Spike'] + 1
                else:
                    user[str(message.author.id)]['Spike'] = 0
            elif position == "Spam":
                if option:
                    user[str(message.author.id)]['Spam Message'].append(content)
                else:
                    user[str(message.author.id)]['Spam Message'] = []
            elif position == "Mention":
                if option:
                    user[str(message.author.id)]['Mention Message'].append(content)
                else:
                    user[str(message.author.id)]['Mention Message'] = []
            else:
                user[str(message.author.id)]['Spike'] = 0
                user[str(message.author.id)]['Spam Message'] = []
                user[str(message.author.id)]['Mention Message'] = []

            f.seek(0)
            dump(user, f, indent=4)
            f.truncate()


    @staticmethod
    async def reset_spike(message):
        GUILD_INFO = f"./cogs/message/{message.guild.id}.json"
        
        with open(GUILD_INFO, 'r+') as f:
            user = load(f)
            user[str(message.author.id)]['Spike'] = 0

            f.seek(0)
            dump(user, f, indent=4)
            f.truncate()


    @Cog.listener()
    async def on_message(self, message):
        if not exists(f"./cogs/message/{message.guild.id}.json"):
            with open(f"./cogs/message/{message.guild.id}.json", "w") as f:
                f.write("{}")

        if self.first_times:
            await self.load_banned_words(message)
            self.first_times = False
            
        MASS_MENTION = len(list(filter(lambda m: m.author == message.author and len(m.mentions) >= 5 and (datetime.now(timezone.utc) - m.created_at).seconds <= 10, self.bot.cached_messages,)))
        IS_ADMINS = (message.author.guild_permissions.administrator if type(message.author) == Member else get(message.guild.members, id=message.author.id))

        if not message.author.bot and not IS_ADMINS:
            SPIKE = await self.check_spike(message)

            if len(message.mentions):
                await self.write_file(message, "Mention", option=True, content=message.id)
                self.bot.scheduler.add_job(self.write_file, id=f"{message.author.id}-MENTION" ,args=[message, "Mention", False, None] , next_run_time=(datetime.now()+timedelta(seconds=1.5)), replace_existing=True)

            elif len(message.content):
                await self.write_file(message, "Spam", option=True, content=message.id)
                self.bot.scheduler.add_job(self.write_file, id=f"{message.author.id}-SPAM" ,args=[message, "Spam", False, None] , next_run_time=(datetime.now()+timedelta(seconds=1.5)), replace_existing=True)

            if SPIKE > 0:
                try:
                    self.bot.scheduler.add_job(self.reset_spike, id=f"{message.author.id}-SPIKE" ,args=[message], next_run_time=(datetime.now()+timedelta(seconds=30)))
                except ConflictingIdError:
                    pass

            if profanity.contains_profanity(message.content):
                    await message.delete()
                    await message.channel.send(f"Watch your word {message.author.mention}", delete_after=2)
                    await self.write_file(message, "Spike", option=True)
                    try:
                        self.bot.scheduler.add_job(self.reset_spike, id=f"{message.author.id}-SPIKE" ,args=[message], next_run_time=(datetime.now()+timedelta(seconds=30)), replace_existing=True)
                    except JobLookupError:
                        pass
            else:
                with open(f"./cogs/message/{message.guild.id}.json") as f:
                    user = load(f)

                if len(user[str(message.author.id)]["Mention Message"]) >= 3:
                    await self.write_file(message, "Mention", option=False)
                    await message.channel.purge(limit=10, check=lambda m: (m.author == message.author), after=(datetime.now(timezone.utc) - timedelta(seconds=2)))
                    await self.write_file(message, "Spike", option=True)
                    await message.channel.send(f"Don't spam mention {message.author.mention}", delete_after=2)


                elif len(user[str(message.author.id)]["Spam Message"]) >= 5:
                    await self.write_file(message, "Spam", option=False)
                    await message.channel.purge(limit=10, check=lambda m: (m.author == message.author), after=(datetime.now(timezone.utc) - timedelta(seconds=2)))
                    await self.write_file(message, "Spike", option=True)
                    await message.channel.send(f"A bit too fast there {message.author.mention}", delete_after=2)


            if SPIKE >= 2 or MASS_MENTION >= 3:
                await message.channel.purge(limit=10, check=lambda m: len(m.mentions) >= 5, after=(datetime.now(timezone.utc) - timedelta(seconds=10)))
                await self.write_file(message, "All", option=False)
                await self.auto_muted(message, "5h", "Auto Mute", auto=True)
                

    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
            self.bot.cogs_ready.ready_up("Automod")


def setup(bot):
    bot.add_cog(Automod(bot))
