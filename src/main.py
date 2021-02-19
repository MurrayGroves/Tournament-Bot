import discord
import sys
import asyncio
import aiofiles
import json

import util
import cmds

# Setup logging so discord.py can log
import logging
discordLogger = logging.getLogger("discord")
discordLogger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename="../logs/discord.log", encoding="utf-8", mode="w")
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
discordLogger.addHandler(handler)

# Setup a logger to log commands registered
logger = logging.getLogger("cmdLogger")
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler(sys.stdout))

# Read token from file
file = open("../token.dat")
token = file.read().strip()
file.close()

prefix = "t:"

client = discord.Client()

messageToTournamentIDMappings = {}
messageToUserIDMappings = {}

@client.event
async def on_ready():
    # Delete token out of memory, since the bot is already logged in. Just in case.
    global token
    del token

    logger.info(f"Logged in as {client.user.name}")


@client.event
async def on_message(message):
    global prefix

    # Prevents infinite loops caused by the bot triggering its own commands
    if message.author == client.user:
        return

    if message.reference:
        if message.reference.resolved.reference:
            userID = messageToUserIDMappings[message.reference.resolved.id]
            if message.author.id == userID and message.reference.resolved.embeds[0].title == "Owned Tournaments":
                args = message.content.strip().split(" ")
                desc = message.reference.resolved.embeds[0].description.splitlines()
                selected = [s for s in desc if "*" in s]
                selection = desc.index(selected[0]) - 2
                tournaments = await util.genOwnedPage(message.guild.id, userID)
                tournamentID = tournaments[1][selection]
                args.append(tournamentID)
                args.insert(0, message)
                await util.editTournament(*args)

    # If message doesn't start with the prefix, stop processing
    if not message.content.strip().startswith(prefix):
        return

    if " " in message.content.strip():
        # Separate the command and its parameters into different variables
        cmd, args = message.content.strip().split(" ", 1)
        args = args.split(" ")

    else:  # if command has no arguments, set args to an empty list
        cmd = message.content.strip()
        args = []

    cmd = cmd.replace(prefix, "")

    # If there's no corresponding command function, stop processing
    if f"cmd_{cmd}" not in vars(cmds):
        return

    # If the number of arguments is incorrect, send an error message and stop processing
    cmdFunc = vars(cmds)[f"cmd_{cmd}"]
    cmdArgCount = cmdFunc.__code__.co_argcount-2
    if cmdArgCount != len(args):
        em = discord.Embed(title="Incorrect number of arguments", description=f"Expected {cmdArgCount}, you gave {len(args)}", colour=16711680)
        await message.channel.send(embed=em)
        return

    # Register user if they're not already registered
    await util.registerUser(message.author.id)

    args.insert(0, message)
    args.insert(0, client)
    # Call the command function
    await cmdFunc(*args)

    logger.info(f"{message.author.name}({message.author.id}) -> {message.channel.name}({message.channel.id}): {message.content.strip()}")


@client.event
async def on_reaction_add(reaction, user):
    userID = reaction.message.reference.resolved.author.id
    messageToUserIDMappings[reaction.message.id] = userID
    if user.id != userID:
        return

    try:
        if "/" in reaction.message.embeds[0].footer.text:
            footerText = reaction.message.embeds[0].footer.text.split("/", 1)
            if " " in footerText[1]:
                footerText[1], _ = footerText[1].split(" ", 1)

            page = int(footerText[0])
            maxPage = int(footerText[1].split("\n")[0])

    except TypeError:
        pass

    if reaction.message.embeds[0].title == "Upcoming Tournaments" and reaction.emoji in ["➡️", "⬅️"]:
        await util.cleanUpcoming(reaction.message.guild.id)

        if reaction.emoji == "➡️" and page < maxPage:
            page += 1

        elif reaction.emoji == "⬅️" and page > 1:
            page -= 1

        else:
            return

        em = await util.genUpcomingPage(page, reaction.message.guild.id)
        em = em[0]
        em.set_footer(text=reaction.message.embeds[0].footer.text.replace(str(page-1), str(page), 1))

    elif reaction.message.embeds[0].title == "Owned Tournaments" and reaction.emoji in ["➡️", "⬅️"]:
        if reaction.emoji == "➡️" and page < maxPage:
            page += 1

        elif reaction.emoji == "⬅️" and page > 1:
            page -= 1

        else:
            return

        em = await util.genOwnedPage(page, reaction.message.guild.id, reaction.author.id)
        em = em[0]

    elif reaction.message.embeds[0].title == "Upcoming Tournaments" and reaction.emoji in ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]:
        selection = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"].index(reaction.emoji)
        tournament = await util.genUpcomingPage(page, reaction.message.guild.id)
        tournamentID = tournament[1][selection]
        result = await util.joinTournament(user.id, tournamentID, reaction.message.guild.id)

        em = await util.genUpcomingPage(page, reaction.message.guild.id)
        em = em[0]

        if result[0] == 0:
            em.colour = 16711680
            em.set_footer(text=f"{page}/{maxPage} This tournament is full!")

        elif result[0] == 1:
            em.colour = 65280
            em.set_footer(text=f"{page}/{maxPage} Joined: {result[1]}")

        elif result[0] == 2:
            em.colour = 16776960
            em.set_footer(text=f"{page}/{maxPage} Left: {result[1]}")

        em.set_footer(text=f"{page}/{maxPage}")
        await reaction.message.edit(embed=em, allowed_mentions=discord.AllowedMentions(replied_user=False))

        await asyncio.sleep(2)

    elif reaction.message.embeds[0].title == "Owned Tournaments" and reaction.emoji in ["1️⃣", "2️⃣", "3️⃣"]:
        await reaction.message.clear_reactions()
        await reaction.message.add_reaction("↩️")
        await reaction.message.add_reaction("❌")
        await reaction.message.add_reaction("✏️")

        selection = ["1️⃣", "2️⃣", "3️⃣"].index(reaction.emoji)
        tournament = await util.genOwnedPage(reaction.message.guild.id, user.id, selection=selection+1)
        tournamentID = tournament[1][selection]
        em = tournament[0]
        em.set_footer(text=f"{selection+1}/3")

    elif reaction.message.embeds[0].title == "Owned Tournaments" and reaction.emoji == "↩️":
        await reaction.message.clear_reactions()
        await reaction.message.add_reaction("⬅️")
        await reaction.message.add_reaction("➡️")
        for x in range(1, 4):
            await reaction.message.add_reaction(await util.intToEmoji(x))

        tournament = await util.genOwnedPage(reaction.message.guild.id, user.id)
        em = tournament[0]

    elif reaction.message.embeds[0].title == "Owned Tournaments" and reaction.emoji == "✏️":
        em = reaction.message.embeds[0]
        em.set_footer(text=em.footer.text + f" Please reply to this message with the new details in the same format as {prefix}create")

    elif reaction.message.embeds[0].title == "Owned Tournaments" and reaction.emoji == "❌":
        desc = reaction.message.embeds[0].description.splitlines()
        selected = [s for s in desc if "*" in s]
        selection = desc.index(selected[0]) - 2
        tournaments = await util.genOwnedPage(reaction.message.guild.id, user.id)
        tournamentID = tournaments[1][selection]
        f = await aiofiles.open(f"../data/servers/{reaction.message.guild.id}/{tournamentID}.json")
        tournament = await f.read()
        await f.close()
        tournament = json.loads(tournament)
        em = discord.Embed(title="Delete Tournament", description="Are you sure you want to delete this tournament? This is irreversible.")
        em.add_field(name="Name", value=tournament["name"])
        em.add_field(name="Date/Time", value=f"{tournament['dTime']} UTC")
        em.add_field(name="Players", value=f"{len(tournament['players'])}/{tournament['limit']}")

        await reaction.message.clear_reactions()
        await reaction.message.add_reaction("↩️")
        await reaction.message.add_reaction("✅")

        messageToTournamentIDMappings[reaction.message.id] = tournamentID

    elif reaction.message.embeds[0].title == "Delete Tournament" and reaction.emoji == "✅":
        tournamentID = messageToTournamentIDMappings[reaction.message.id]
        resp = await util.deleteTournament(user.id, tournamentID, reaction.message.guild.id)
        em = discord.Embed(title="Tournament Deleted", colour=65280)
        await reaction.message.edit(embed=em, allowed_mentions=discord.AllowedMentions(replied_user=False))

        await asyncio.sleep(2)
        em = await util.genOwnedPage(reaction.message.guild.id, user.id)
        em = em[0]

    # Emoji was not part of a command, so return
    else:
        return

    await reaction.remove(user)

    em.colour = 255
    await reaction.message.edit(embed=em, allowed_mentions=discord.AllowedMentions(replied_user=False))


# Run bot
client.run(token)
