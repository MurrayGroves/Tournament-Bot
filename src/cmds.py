import discord
import logging
from datetime import datetime, timezone
import pytz
import json
import aiofiles
import os
import util

# Add the command logger
logger = logging.getLogger("cmdLogger")

# Generate a dictionary of timezone abbreviations to full timezone names. E.g. "PST": "US/Pacific".
# This is because pytz.timezone() only takes full timezone names but we want users to be able to input tz names such as PST
timezoneLookup = dict([(pytz.timezone(x).localize(datetime.now()).tzname(), x) for x in pytz.all_timezones])


async def cmd_ping(client, message):
    await message.channel.send("pong")


async def cmd_create(client, message, name, date, time, tz, limit):
    global timezoneLookup

    # If user already owns 3 tournaments in this server, stop them making another.
    f = await aiofiles.open(f"../data/users/{message.author.id}.json")
    old = await f.read()
    await f.close()
    userOld = json.loads(old)
    tOwned = {}
    for tourney in userOld["tOwned"]:
        guildID = tourney.split("/")[0]
        if guildID in tOwned:
            tOwned[guildID] += 1

        else:
            tOwned[guildID] = 1

    for tourney in tOwned:
        if tOwned[tourney] >= 3:
            em = discord.Embed(title="Cannot create tournament, you can only have 3 active tournaments.", colour=16711680)
            await message.channel.send(embed=em)
            return

    dTime = date + time
    try:
        # Generate a timezone agnostic datetime object from the user's input
        dTimeObj = datetime.strptime(dTime, "%Y/%m/%d%H:%M")
        # Get a timezone object from the shortcode provided by the user
        oldTZ = pytz.timezone(timezoneLookup[tz])
        # Add a datetime to the timezone object
        oldTZ = oldTZ.localize(dTimeObj)
        # Convert the timezone/datetime object to a datetime object in UTC
        dTimeObj = oldTZ.astimezone(timezone.utc)

    except ValueError:
        logger.debug("Invalid datetime")
        em = discord.Embed(title="Error",
                           description="Invalid date/time. Please make sure it's in this format: YYYY/MM/DD HH:MM TZ",
                           colour=16711680)
        await message.channel.send(embed=em)
        return

    except KeyError:
        logger.debug("Invalid timezone")
        em = discord.Embed(title="Error", description="Invalid timezone.", colour=16711680)
        await message.channel.send(embed=em)
        return

    dTime = datetime.strftime(dTimeObj, "%Y/%m/%d %H:%M")

    os.makedirs(f"../data/servers/{message.guild.id}/", exist_ok=True)

    tourney = {"name": name, "dTime": dTime, "players": [], "limit": limit}

    em = discord.Embed(title="Tournament Created", colour=65280)
    em.add_field(name="Name", value=name, inline=False)
    em.add_field(name="Date", value=dTime.split(" ")[0], inline=False)
    em.add_field(name="Time", value=f"{dTime.split(' ')[1]} UTC", inline=False)

    await message.channel.send(embed=em)

    # Convert dictionary to json string
    tourney = json.dumps(tourney)

    # Find available ID
    tourneyList = sorted(os.listdir(f"../data/servers/{message.guild.id}/"))
    tourneyID = int(tourneyList[-2].replace(".json", "")) + 1

    upcoming = {tourneyID: dTime}
    if "upcoming.json" not in os.listdir(f"../data/servers/{message.guild.id}/"):
        upcoming = json.dumps(upcoming)
        f = await aiofiles.open(f"../data/servers/{message.guild.id}/upcoming.json", "w+")
        await f.write(upcoming)
        await f.close()

    else:
        f = await aiofiles.open(f"../data/servers/{message.guild.id}/upcoming.json")
        oldData = await f.read()
        await f.close()

        upcoming = {**upcoming, **json.loads(oldData)}
        upcoming = json.dumps(upcoming)

        f = await aiofiles.open(f"../data/servers/{message.guild.id}/upcoming.json", "w+")
        await f.write(upcoming)
        await f.close()

        await util.cleanUpcoming(message.guild.id)

    f = await aiofiles.open(f"../data/servers/{message.guild.id}/{tourneyID}.json", "w+")
    await f.write(tourney)
    await f.close()

    userOld["tOwned"].append(f"{message.guild.id}/{tourneyID}")

    f = await aiofiles.open(f"../data/users/{message.author.id}.json", "w+")
    await f.write(json.dumps(userOld))
    await f.close()


async def cmd_owned(client, message):
    em = await util.genOwnedPage(message.guild.id, message.author.id)
    em = em[0]
    msg = await message.reply(embed=em, mention_author=False)
    await msg.add_reaction("⬅️")
    await msg.add_reaction("➡️")
    for x in range(1, 4):
        await msg.add_reaction(await util.intToEmoji(x))

async def cmd_upcoming(client, message):
    await util.cleanUpcoming(message.guild.id)

    em = await util.genUpcomingPage(1, message.guild.id)
    em = em[0]

    msg = await message.reply(embed=em, mention_author=False)
    await msg.add_reaction("⬅️")
    await msg.add_reaction("➡️")
    for x in range(1, 6):
        await msg.add_reaction(await util.intToEmoji(x))
