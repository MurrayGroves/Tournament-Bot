import discord
import sys
import asyncio


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
    if user.id != userID:
        return

    if "/" in reaction.message.embeds[0].footer.text:
        footerText = reaction.message.embeds[0].footer.text.split("/", 1)
        if " " in footerText[1]:
            footerText[1], _ = footerText[1].split(" ", 1)

        page = int(footerText[0])
        maxPage = int(footerText[1])

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

    elif reaction.message.embeds[0].title == "Owned Tournaments" and reaction.emoji in ["➡️", "⬅️"]:
        await util.cleanUpcoming(reaction.message.guild.id)

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

        await reaction.message.edit(embed=em, allowed_mentions=discord.AllowedMentions(replied_user=False))

        await asyncio.sleep(2)

    elif reaction.message.embeds[0].title == "Owned Tournaments" and reaction.emoji in ["1️⃣", "2️⃣", "3️⃣", "4️⃣","5️⃣"]:
        await reaction.message.clear_reactions()
        await reaction.message.add_reaction("↩️")
        await reaction.message.add_reaction("❌")
        await reaction.message.add_reaction("✏️")

        selection = ["1️⃣", "2️⃣", "3️⃣"].index(reaction.emoji)
        tournament = await util.genOwnedPage(page, reaction.message.guild.id, user.id, selection=selection+1)
        tournamentID = tournament[1][selection]

        em = tournament[0]

    elif reaction.message.embeds[0].title == "Owned Tournaments" and reaction.emoji == "↩️":
        await reaction.message.clear_reactions()
        await reaction.message.add_reaction("⬅️")
        await reaction.message.add_reaction("➡️")
        for x in range(1, 6):
            await reaction.message.add_reaction(await util.intToEmoji(x))

        tournament = await util.genOwnedPage(page, reaction.message.guild.id, user.id)
        em = tournament[0]

    # Emoji was not part of a command, so return
    else:
        return

    await reaction.remove(user)

    em.colour = 255
    em.set_footer(text=f"{page}/{maxPage}")
    await reaction.message.edit(embed=em, allowed_mentions=discord.AllowedMentions(replied_user=False))


# Run bot
client.run(token)
