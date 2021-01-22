import discord
import logging
import datetime
import json
import aiofiles
import os
import util

# Add the command logger
logger = logging.getLogger("cmdLogger")

async def cmd_ping(client, message):
    await message.channel.send("pong")

async def cmd_create(client, message, name, date, time, timezone):
    dTime = date + time + timezone
    try:
        dTimeObj = datetime.datetime.strptime(dTime, "%Y/%m/%d%H:%M%Z")

    except ValueError:
        em = discord.Embed(title="Error", description="Invalid date/time/timezone. Please make sure it's in this format: YYYY/MM/DD HH:MM TZ", colour=16711680)
        await message.channel.send(embed=em)
        return

    dTime = datetime.datetime.strftime(dTimeObj, "%Y/%m/%d %H:%M")

    os.makedirs(f"../data/servers/{message.guild.id}/", exist_ok=True)
    
    tourney = {"name": name, "dTime": dTime, "players": []}

    em = discord.Embed(title="Tournament Created", colour=65280)
    em.add_field(name="Name", value=name, inline=False)
    em.add_field(name="Date", value=dTime.split(" ")[0], inline=False)
    em.add_field(name="Time", value=dTime.split(" ")[1], inline=False)

    await message.channel.send(embed=em)

    # Convert dictionary to json string
    tourney = json.dumps(tourney)
    tourneyID = len(os.listdir(f"../data/servers/{message.guild.id}/"))

    upcoming = {tourneyID: dTime}
    if "upcoming.dat" not in os.listdir(f"../data/servers/{message.guild.id}/"):
        upcoming = json.dumps(upcoming)
        f = await aiofiles.open(f"../data/servers/{message.guild.id}/upcoming.dat", "w+")
        await f.write(upcoming)
        await f.close()

    else:
        f = await aiofiles.open(f"../data/servers/{message.guild.id}/upcoming.dat")
        oldData = await f.read()
        await f.close()

        upcoming = {**upcoming, **json.loads(oldData)}
        upcoming = json.dumps(upcoming)

        f = await aiofiles.open(f"../data/servers/{message.guild.id}/upcoming.dat", "w+")
        await f.write(upcoming)
        await f.close()

        await util.cleanUpcoming(message.guild.id)

    f = await aiofiles.open(f"../data/servers/{message.guild.id}/{tourneyID}.dat", "w+")
    await f.write(tourney)
    await f.close()
