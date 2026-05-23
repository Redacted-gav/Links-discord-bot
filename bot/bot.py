import os
import re
import random
import subprocess
from pathlib import Path
from collections import Counter

import discord
from discord.ext import commands, tasks
from discord import app_commands
from dotenv import load_dotenv


# =========================
# CONFIG
# =========================

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

VERIFIED_ROLE_ID = 1507541950121771028
HELPER_ROLE_ID = 1507774659498610776
SR_HELPER_ROLE_ID = 1507813599685513337

ADD_CHANNEL_ID = 1507752042272260187
BLOCKED_CHANNEL_ID = 1507772589265649934

BASE_DIR = Path("~/link-checker").expanduser()

UNCHECKED_FILE = BASE_DIR / "unchecked.txt"
APPROVED_FILE = BASE_DIR / "approved.txt"
BLOCK_FILE = BASE_DIR / "blocklist.txt"
URL_FILE = BASE_DIR / "urls.txt"
RESULT_FILE = BASE_DIR / "results.txt"
APPROVAL_LOG = BASE_DIR / "approval_log.txt"

LINK_REGEX = r"(https?://[^\s]+|www\.[^\s]+)"

# =========================
# BOT SETUP
# =========================

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# =========================
# FILE HELPERS
# =========================

def load_set(file_path: Path) -> set:
    if not file_path.exists():
        return set()
    return set(line.strip() for line in file_path.read_text().splitlines() if line.strip())


def save_set(file_path: Path, data: set):
    file_path.write_text("\n".join(sorted(data)) + "\n")


def load_list(file_path: Path) -> list:
    if not file_path.exists():
        return []
    return [line.strip() for line in file_path.read_text().splitlines() if line.strip()]


# =========================
# QUEUE SYSTEM
# =========================

def add_unchecked(link: str):
    approved = load_set(APPROVED_FILE)
    blocked = load_set(BLOCK_FILE)
    unchecked = load_set(UNCHECKED_FILE)

    # CLEANUP RULE: ignore anything already handled
    if link in approved:
        return
    if link in blocked:
        return
    if link in unchecked:
        return

    unchecked.add(link)
    save_set(UNCHECKED_FILE, unchecked)

def get_queue():
    return list(load_set(UNCHECKED_FILE))


def remove_from_queue(link: str):
    unchecked = load_set(UNCHECKED_FILE)
    unchecked.discard(link)
    save_set(UNCHECKED_FILE, unchecked)


# =========================
# CORE LOGIC
# =========================

def extract_links(text: str):
    return re.findall(LINK_REGEX, text)


def run_update():
    subprocess.run(["bash", str(Path("~/bin/links").expanduser()), "update"])


def generate_random_link():
    if not APPROVED_FILE.exists():
        return "No file found."

    links = load_list(APPROVED_FILE)
    if not links:
        return "No links found."

    return f"**Random Link:** {random.choice(links)}"


# =========================
# COMMANDS (USER)
# =========================

@tree.command(name="gen", description="Get a random approved link")
async def gen(interaction: discord.Interaction):
    if VERIFIED_ROLE_ID not in [role.id for role in interaction.user.roles]:
        await interaction.response.send_message("No permission.", ephemeral=True)
        return

    await interaction.response.send_message(generate_random_link())


@tree.command(name="update", description="Update link database")
async def update(interaction: discord.Interaction):
    if VERIFIED_ROLE_ID not in [role.id for role in interaction.user.roles]:
        await interaction.response.send_message("No permission.", ephemeral=True)
        return

    await interaction.response.send_message("Updating links...")
    run_update()
    await interaction.followup.send("Done.")


# =========================
# HELPER MODERATION SYSTEM
# =========================

@tree.command(name="queue", description="View unchecked link queue")
async def queue(interaction: discord.Interaction, page: int = 1):
    if HELPER_ROLE_ID not in [role.id for role in interaction.user.roles]:
        await interaction.response.send_message("No permission.", ephemeral=True)
        return

    queue = get_queue()

    if not queue:
        await interaction.response.send_message("Queue is empty.")
        return

    per_page = 5
    start = (page - 1) * per_page
    end = start + per_page

    chunk = queue[start:end]

    if not chunk:
        await interaction.response.send_message("No items on this page.")
        return

    msg = "\n".join([f"{i+start+1}. {link}" for i, link in enumerate(chunk)])

    await interaction.response.send_message(
        f"**Unchecked Queue (Page {page})**\n```{msg}```"
    )


@tree.command(name="approve", description="Approve a link from queue by index")
async def approve(interaction: discord.Interaction, index: int):
    if HELPER_ROLE_ID not in [role.id for role in interaction.user.roles]:
        await interaction.response.send_message("No permission.", ephemeral=True)
        return

    queue = get_queue()

    if index < 1 or index > len(queue):
        await interaction.response.send_message("Invalid index.")
        return

    link = queue[index - 1]

    approved = load_set(APPROVED_FILE)
    approved.add(link)
    save_set(APPROVED_FILE, approved)

    remove_from_queue(link)

    with open(APPROVAL_LOG, "a") as f:
        f.write(f"{interaction.user.id}|{interaction.user.name}|{link}\n")

    await interaction.response.send_message(f"Approved ✅\n{link}")

@tree.command(name="block", description="Block a link from queue by index")
async def block(interaction: discord.Interaction, index: int):
    if HELPER_ROLE_ID not in [role.id for role in interaction.user.roles]:
        await interaction.response.send_message("No permission.", ephemeral=True)
        return

    queue = get_queue()

    if index < 1 or index > len(queue):
        await interaction.response.send_message("Invalid index.")
        return

    link = queue[index - 1]

    blocked = load_set(BLOCK_FILE)
    blocked.add(link)
    save_set(BLOCK_FILE, blocked)

    remove_from_queue(link)

    await interaction.response.send_message(f"Blocked ❌\n{link}")

@tree.command(name="leaderboard", description="Shows top link approvers")
async def leaderboard(interaction: discord.Interaction):
    if SR_HELPER_ROLE_ID not in [role.id for role in interaction.user.roles]:
        await interaction.response.send_message("No permission.", ephemeral=True)
        return

    if not APPROVAL_LOG.exists():
        await interaction.response.send_message("No approvals yet.")
        return

    counts = Counter()

    with open(APPROVAL_LOG, "r") as f:
        for line in f:
            parts = line.strip().split("|")
            if len(parts) >= 2:
                user_id = parts[0]
                username = parts[1]
                counts[(user_id, username)] += 1

    if not counts:
        await interaction.response.send_message("No data.")
        return

    top = counts.most_common(10)

    msg = "\n".join(
        [f"{i+1}. <@{user_id}> — {count}" for i, ((_, name), count) in enumerate(top)]
    )

    await interaction.response.send_message(
        f"🏆 **Approval Leaderboard**\n```{msg}```"
    )

# =========================
# SCANNERS
# =========================

@tasks.loop(minutes=1)
async def scan_channel():
    channel = bot.get_channel(ADD_CHANNEL_ID)
    if not channel:
        return

    found = []

    async for message in channel.history(limit=200):
        found.extend(extract_links(message.content))

        try:
            await message.delete()
        except:
            pass

    for link in found:
        add_unchecked(link)


@tasks.loop(minutes=1)
async def scan_blocked_channel():
    channel = bot.get_channel(BLOCKED_CHANNEL_ID)
    if not channel:
        return

    blocked = load_set(BLOCK_FILE)
    new = 0

    async for message in channel.history(limit=200):
        links = extract_links(message.content)

        for link in links:
            blocked.add(link)
            new += 1

        try:
            await message.delete()
        except:
            pass

    if new:
        save_set(BLOCK_FILE, blocked)


@tasks.loop(minutes=60)
async def auto_update():
    run_update()


# =========================
# READY
# =========================

@bot.event
async def on_ready():
    await tree.sync()
    print(f"Logged in as {bot.user}")

    scan_channel.start()
    scan_blocked_channel.start()
    auto_update.start()


bot.run(TOKEN)

