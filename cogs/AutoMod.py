from asyncio import sleep
from datetime import datetime, timezone
from os import getenv
from typing import Optional

from better_profanity import profanity
from nextcord import (DMChannel, Embed, Member, Message, NotFound, Object,
                      Role, TextChannel)
from nextcord.ext.commands import (BadArgument, CheckFailure, Cog, Converter,
                                   Greedy, bot_has_permissions, command,
                                   has_permissions)
from nextcord.utils import get
from pymongo import MongoClient

from . import del_user_msg
from .Mod import Mod


class AutoMod(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.MOD = Mod(bot)

        self.MONGO_CLIENT =  MongoClient(getenv("DATABASE"))
        self.DB = self.MONGO_CLIENT["RF911"]
        self.BANNED_DB = self.DB['Banned']
        self.GUILD_DB = self.DB['Guild']
        self.SPIKE_DB = self.DB["Spike"]
        self.BANNED_WORDS_DB = self.DB["Banned Words"]


    def get_mute_role(self, ctx):
        get_mute = self.GUILD_DB.find_one({"_ids": ctx.guild.id})
        return get_mute["Mute role"] if get_mute is not None else None


    async def auto_muted(self, message, duration, reason, auto=True):
        unmutes = await self.MOD.mute_members(message, targets=[message.author], hours=duration, reason=reason, auto=auto)
        tempmute = self.MOD.time_converter(duration)

        if len(unmutes):
            await sleep(tempmute)
            await self.MOD.unmute_members(message, message.guild, [message.author], auto=auto)

    
    async def check_db(self, message):
        if self.SPIKE_DB.find_one({"_id": message.author.id}) is None:
            return False
        return True

    
    async def Spike_check(self, message, SPIKE_COUNT, SPIKE_INCREASE):
        spike_updating = await self.check_db(message)
        if not spike_updating:
            self.SPIKE_DB.insert_one({"_id": message.author.id, "Name": f"{message.author.name}#{message.author.discriminator}",  "Spike": 1})
        else:
            self.SPIKE_DB.update_one({"_id": message.author.id}, {"$set": {"Spike": SPIKE_COUNT + SPIKE_INCREASE}})


    @Cog.listener()
    async def on_message(self, message):
        def _check_mass_mention(m):
            return (m.author == message.author and len(m.mentions) >= 4 and (datetime.now(timezone.utc) - m.created_at).seconds <= 30)
        def _check_spam(m):
            return (m.author == message.author and (datetime.now(timezone.utc) - m.created_at).seconds < 5)

        BANNED_WORDS_ID = self.BANNED_WORDS_DB.find_one({"_id": message.guild.id})
        if BANNED_WORDS_ID is None:
            self.BANNED_WORDS_DB.insert_one({"_id": message.guild.id, "Words": ['nigga', 'fagot']})
            BANNED_WORDS = ['nigga', 'fagot']
        else:
            BANNED_WORDS = BANNED_WORDS_ID["Words"]
            
        profanity.load_censor_words(BANNED_WORDS)

        SPIKE = self.SPIKE_DB.find_one({"_id": message.author.id})
        SPIKE_COUNT = SPIKE["Spike"] if SPIKE is not None else 0
        MAXED_SPIKE = 2

        SPAM_MENTION = len(list(filter(lambda m: (m.author == message.author and len(m.mentions) and (datetime.now(timezone.utc) - m.created_at).seconds < 30) , self.bot.cached_messages)))
        SPAM = len(list(filter(lambda m: _check_spam(m), self.bot.cached_messages)))
        MASS_MENTION = len(list(filter(lambda m: _check_mass_mention(m), self.bot.cached_messages)))
        CONTAIN_BANNED = profanity.contains_profanity(message.content)

        is_admins = message.author.guild_permissions.administrator if type(message.author) == Member else get(message.guild.members, id=message.author.id)

        if not message.author.bot and not is_admins:
            if SPIKE_COUNT < MAXED_SPIKE:
                if  SPAM_MENTION >= 5:
                    await message.channel.purge(limit=SPAM_MENTION, check=lambda m: (m.author == message.author and (datetime.now(timezone.utc) - m.created_at).seconds < 30))
                    await self.Spike_check(message, SPIKE_COUNT, 1)
                    await message.channel.send(f"Don't spam mention. {MAXED_SPIKE - SPIKE_COUNT} spike before auto mute.", delete_after=2)

                if SPAM >= 5:
                    await message.channel.purge(limit=SPAM, check=lambda m: (m.author == message.author and (datetime.now(timezone.utc) - m.created_at).seconds < 30))
                    await message.channel.send(f"Don't spam. {MAXED_SPIKE - SPIKE_COUNT} spike before auto mute.", delete_after=2)
                    await self.Spike_check(message, SPIKE_COUNT, 1)

                if MASS_MENTION >= 2:
                    await message.channel.purge(limit=MASS_MENTION, check=lambda m: (m.author == message.author and (datetime.now(timezone.utc) - m.created_at).seconds < 5))
                    await message.channel.send(f"Do not mass mention again. {MAXED_SPIKE - SPIKE_COUNT} spike before auto mute.", delete_after = 2)
                    await self.Spike_check(message, SPIKE_COUNT, 3)

                if CONTAIN_BANNED:
                    await message.delete()
                    await message.channel.send(f"Watch your words {message.author}. {MAXED_SPIKE - SPIKE_COUNT} spike before auto mute.", delete_after = 2)
                    await self.Spike_check(message, SPIKE_COUNT, 1)

            else:
                self.SPIKE_DB.update_one({"_id": message.author.id}, {"$set": {"Spike": 0}})
                await self.auto_muted(message, '5h', "Auto mute", True)
                member = get(message.guild.members, id=message.author.id)
                await member.send(f"You have been muted in {message.guild}")


    @Cog.listener()
    async def on_ready(self):
        if not self.bot.ready:
            self.bot.cogs_ready.ready_up("AutoMod")


def setup(bot):
    bot.add_cog(AutoMod(bot))
