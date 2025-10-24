import discord
from discord.ext import commands
import asyncio
import os
from dotenv import load_dotenv
import json
import re

# Load environment variables from .env file
load_dotenv()

# Get sensitive data from .env
BOT_TOKEN = os.getenv('BOT_TOKEN')
GUILD_ID = int(os.getenv('GUILD_ID'))  # Convert to int since IDs are numbers
USER_ID = int(os.getenv('USER_ID'))    # Convert to int
OUTPUT_FILE = 'user_messages.jsonl'

# Check if environment variables are loaded
if not all([BOT_TOKEN, GUILD_ID, USER_ID]):
    raise ValueError("Missing required environment variables. Check your .env file.")

def remove_links(text):
    """Remove URLs and links from text while preserving the rest of the content."""
    if not text:
        return text

    # Pattern to match Discord CDN attachment URLs specifically
    discord_cdn_pattern = r'https://cdn\.discordapp\.com/attachments/[^\s]+'
    # Pattern to match general URLs (http, https, www)
    url_pattern = r'https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:\w*))?)?'
    # Also match www. links without protocol
    www_pattern = r'www\.(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:\w*))?)?'

    # Remove Discord CDN URLs first (most specific)
    cleaned_text = re.sub(discord_cdn_pattern, '', text)
    # Remove general URLs
    cleaned_text = re.sub(url_pattern, '', cleaned_text)
    # Remove www links
    cleaned_text = re.sub(www_pattern, '', cleaned_text)

    # Remove attachment placeholder text that's left behind
    # Remove "Attachments:" lines
    cleaned_text = re.sub(r'\n?\s*Attachments:\s*\n?', '', cleaned_text)
    # Remove standalone "Attachments:" at start or end
    cleaned_text = re.sub(r'^\s*Attachments:\s*$', '', cleaned_text)

    # Clean up extra whitespace left by removed links and attachment text
    cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()

    return cleaned_text


def is_meaningful_message(text):
    """Check if a message has meaningful content."""
    if not text or not text.strip():
        return False

    return True

intents = discord.Intents.default()
intents.message_content = True
intents.messages = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    guild = bot.get_guild(GUILD_ID)
    if not guild:
        print(f'Guild with ID {GUILD_ID} not found.')
        await bot.close()
        return

    # Fetch the user to get their name for the system prompt
    user = await bot.fetch_user(USER_ID)
    if not user:
        print(f'User with ID {USER_ID} not found.')
        await bot.close()
        return

    # Define the system prompt (customize the description as needed)
    SYSTEM_PROMPT = f"[INST] System: You are mimicking {user.name}, a friendly and casual Discord user. Respond as they would in a group chat. \n\n[/INST]"

    messages = []
    for channel in guild.text_channels:
        if channel.permissions_for(guild.me).read_message_history:
            try:
                async for message in channel.history(limit=None):  # limit=None for all messages, but beware of rate limits
                    if message.author.id == USER_ID:
                        completion = message.content
                        if message.attachments:
                            urls = ", ".join([att.url for att in message.attachments])
                            completion += f'\nAttachments: {urls}'
                        completion = remove_links(completion)  # Remove links from final completion including attachments
                        if is_meaningful_message(completion):  # Skip messages that are just attachment placeholders
                            msg_dict = {
                                "prompt": SYSTEM_PROMPT,
                                "completion": completion
                            }
                            messages.append(msg_dict)
            except discord.Forbidden:
                print(f'No access to channel {channel.name}')
            except Exception as e:
                print(f'Error in channel {channel.name}: {e}')

    # Write to JSONL file (oldest first)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        for msg_dict in reversed(messages):
            f.write(json.dumps(msg_dict) + '\n')

    print(f'Exported {len(messages)} messages to {OUTPUT_FILE}')
    await bot.close()

bot.run(BOT_TOKEN)