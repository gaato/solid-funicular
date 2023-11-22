import os
import time

import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv

load_dotenv()
intents = discord.Intents.default()
intents.members = True

admin_only = discord.Permissions()
admin_only.administrator = True

bot = commands.Bot(intents=intents)


async def remove_manage_roles(member: discord.Member) -> None:
    for role in member.roles:
        p = role.permissions
        if (
            p.manage_channels
            or p.manage_messages
            or p.manage_roles
            or p.ban_members
            or p.kick_members
            or p.administrator
        ):
            await member.remove_roles(role)


@bot.event
async def on_ready() -> None:
    print(f"Logged in as {bot.user}")
    check.start()


@bot.event
async def on_member_update(before: discord.Member, after: discord.Member) -> None:
    admin_role = after.guild.get_role(int(os.environ["ADMIN_ROLE_ID"]))
    for role in after.roles:
        if role.name == "罰" and role > admin_role:
            if int(time.time()) // (24 * 60 * 60) - role.color.value >= 30:
                await role.delete()
            else:
                await remove_manage_roles(after)


@bot.user_command(name="Punish", default_member_permissions=admin_only)
async def punish(ctx: discord.ApplicationContext, member: discord.Member) -> None:
    admin_role = ctx.guild.get_role(int(os.environ["ADMIN_ROLE_ID"]))
    await remove_manage_roles(member)
    role = await ctx.guild.create_role(
        name="罰", color=discord.Color(int(time.time()) // (24 * 60 * 60))
    )
    await role.edit(position=admin_role.position + 1)
    await member.add_roles(role)
    await ctx.respond(f"{member.mention} has been punished!", ephemeral=True)


@bot.user_command(name="Forgive", default_member_permissions=admin_only)
async def forgive(ctx: discord.ApplicationContext, member: discord.Member) -> None:
    await member.remove_roles(discord.utils.get(ctx.guild.roles, name="罰"))
    await ctx.respond(f"{member.mention} has been forgiven!", ephemeral=True)


@tasks.loop(hours=1)
async def check() -> None:
    guild = bot.get_guild(int(os.environ["GUILD_ID"]))
    admin_role = guild.get_role(int(os.environ["ADMIN_ROLE_ID"]))
    for member in guild.members:
        for role in member.roles:
            if role.name == "罰" and role > admin_role:
                if int(time.time()) // (24 * 60 * 60) - role.color.value >= 30:
                    await role.delete()
                else:
                    await remove_manage_roles(member)


bot.run(os.environ["DISCORD_TOKEN"])
