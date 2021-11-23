from datetime import datetime

from nextcord import Embed, Guild, Member, TextChannel
from nextcord.ext.commands import Cog
from pytz import timezone

from ..bot import RF
from .Bounty import Bounty


class Scheduler(Cog):
    def __init__(self, bot: RF) -> None:
        self.bot = bot


    async def get_hitlist(self, guild: Guild) -> TextChannel:
        HITLIST = self.bot.GUILD_DB.find_one({"_id": guild.id})

        if HITLIST is None:
            return None
        else:
            CHANNEL = self.bot.get_channel(HITLIST["Hitlist"])
            return CHANNEL


    async def log_send(self, guild:Guild, embed: Embed) -> None:
        Guild = self.bot.GUILD_DB.find_one({"_id": guild.id})
        logChannelID = Guild["Log channel"] if Guild is not None else None
        
        if logChannelID is not None:
            await self.bot.get_channel(logChannelID).send(embed=embed)


    async def unmutes_member(self, guild: Guild, member: Member, reason="Mute time expired.") -> None:
        userRolesID:list = self.bot.MUTE_DB.find_one({"Member ID": member.id, "Guild ID": guild.id})["Roles"]
        userRoles:list = [guild.get_role(id) for id in userRolesID]
        await member.edit(roles=userRoles, reason=f"Unmutes by {guild.me}, Reason: {reason}")
        
        self.bot.MUTE_DB.delete_one({"Member ID": member.id, "Guild ID": guild.id})
        self.bot.SCHEDULER.delete_one({"_id": f"{member.id}-Mute", "Guild ID": guild.id})
        
        embed = Embed(title=f"Unmutes | {member}", colour=0x43b582, timestamp=datetime.now(tz=timezone("Asia/Ho_Chi_Minh")))
        embed.set_footer(text=f"User ID: {member.id}")

        fields = [("Member: ", member.mention, True),
                    ("Moderator: ", guild.me.metion, True),
                    ("Reason: ", reason, False),]

        for name, value, inline in fields:
            embed.add_field(name=name, value=value, inline=inline)

        await self.log_send(guild, embed)


    @Cog.listener()
    async def on_ready(self) -> None:
        schedules = self.bot.SCHEDULER.find()

        for schedule in schedules:
            ids, scheduleType = schedule["_id"].split("-")

            expired_time = datetime(year=int(year), month=int(month), day=int(day), hour=int(hour), minute=int(minute), second=int(second))
            day, month, year, hour, minute, second = schedule["Expired"].split("-")
            guild = self.bot.get_guild(schedule["Guild ID"])

            if scheduleType == "Bounty":
                hitlist = await self.get_hitlist(guild)
                msg = await hitlist.fetch_message(int(ids))

                if expired_time > datetime.now():
                    self.bot.scheduler.add_job(Bounty.del_bounty, id=schedule["_id"], args=[msg], next_run_time=expired_time, replace_existing=True)
                else:
                    Bounty.del_bounty(msg)
                    schedules = self.bot.SCHEDULER.delete_one({"_id": f"{ids}-{scheduleType}"})

            elif scheduleType == "Mute":
                member = guild.get_member(int(ids))

                if expired_time > datetime.now():
                    self.bot.scheduler.add_job(self.unmutes_member, id=schedule["_id"], args=[guild, member], next_run_time=expired_time, replace_existing=True)
                else:
                    self.unmutes_member(guild, member)
                    schedules = self.bot.SCHEDULER.delete_one({"_id": f"{ids}-{scheduleType}"})
                    

        if not self.bot.ready:
            self.bot.cogs_ready.ready_up("Scheduler")


def setup(bot):
    bot.add_cog(Scheduler(bot))
