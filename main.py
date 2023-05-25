import discord
import requests
import asyncio
import time

intents = discord.Intents.all()
intents.members = True
intents.messages = True
intents.message_content = True
client = discord.Client(intents=intents)

status_api_url = "https://status.cfx.re/api/v2/status.json"
ping_api_url = "https://status.cfx.re/metrics-display/1hck2mqcgq3h/day.json"

previous_status = None
config = {}
last_message_time = 0
message_cooldown = 20 * 60  

command_list = [
    "!help - Displays the list of available commands",
    "!set-channel <channel ID> - Configure the channel to receive status updates"
]


def create_embed(status_description, ping_last):
    if status_description == "All Systems Operational":
        color = discord.Color.green()
    else:
        color = discord.Color.red()

    embed = discord.Embed(title="Fivem Status",
                          description=status_description,
                          color=color)
    embed.set_thumbnail(
        url="https://logos-world.net/wp-content/uploads/2021/03/FiveM-Logo.png")
    embed.add_field(name="Ping", value=f"{ping_last} ms", inline=False)
    return embed


async def get_status_and_ping():
    try:
        status_response = await asyncio.get_event_loop().run_in_executor(
            None, requests.get, status_api_url)
        status_data = status_response.json()
        status_description = status_data["status"]["description"]
    except (requests.RequestException, ValueError, KeyError):
        status_description = "Error al obtener el estado"

    try:
        ping_response = await asyncio.get_event_loop().run_in_executor(
            None, requests.get, ping_api_url)
        ping_data = ping_response.json()
        ping_last = ping_data["summary"]["last"]
    except (requests.RequestException, ValueError, KeyError):
        ping_last = "Error al obtener el ping"

    return status_description, ping_last


async def check_status_and_ping():
    global last_message_time 

    await client.wait_until_ready()

    previous_status = None

    while not client.is_closed():
        status_description, ping_last = await get_status_and_ping()
        current_time = time.time()

        if current_time - last_message_time >= message_cooldown:
            for guild_id, guild_config in config.items():
                channel_id = guild_config.get("channel_id")
                if channel_id:
                    channel = client.get_channel(channel_id)
                    if channel:
                        mention_message = None

                        if status_description != previous_status:
                            if status_description != "All Systems Operational":
                                try:
                                    mention_message = await channel.send("@here")
                                    await asyncio.sleep(2)
                                except discord.Forbidden:
                                    print(
                                        f"El bot no tiene permisos para mencionar en el canal {channel.name}"
                                    )

                            embed = create_embed(status_description, ping_last)

                            message = None
                            async for msg in channel.history():
                                if msg.author == client.user:
                                    message = msg
                                    break

                            if message:
                                await message.edit(embed=embed)
                            else:
                                message = await channel.send(embed=embed)

                            previous_status = status_description
                            last_message_time = current_time

                            if mention_message:
                                await mention_message.delete()
                        else:
                            embed = create_embed(status_description, ping_last)

                            message = None
                            async for msg in channel.history():
                                if msg.author == client.user:
                                    message = msg
                                    break

                            if message:
                                await message.edit(embed=embed)

        await asyncio.sleep(5)


@client.event
async def on_ready():
    print("Bot conectado")
    activity = discord.Game(name="!help to see the commands")
    await client.change_presence(status=discord.Status.idle, activity=activity)
    await check_status_and_ping()


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content == "!help":
        help_message = "Available commands:\n" + "\n".join(command_list)
        await message.channel.send(help_message)

    if message.content.startswith("!set-channel"):
        guild_id = message.guild.id
        channel_id = int(message.content.split()[1])
        guild = client.get_guild(guild_id)
        channel = discord.utils.get(guild.text_channels, id=channel_id)
        if channel:
            config[guild_id] = {"channel_id": channel_id}
            await message.channel.send("The channel has been configured")
            status_description, ping_last = await get_status_and_ping()
            embed = create_embed(status_description, ping_last)
            await channel.send(embed=embed)
        else:
            await message.channel.send(
                "Channel not found. Be sure to provide a valid text channel ID.")


client.run("YOUR-DISCORD-BOT-TOKEN")
