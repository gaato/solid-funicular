import asyncio
import json
import os
import time
from io import BytesIO
from typing import Any, Optional

import discord
from discord.ext import commands, tasks
from discord.ui import Button, View
from dotenv import load_dotenv

load_dotenv()
intents = discord.Intents.default()
intents.members = True

admin_only = discord.Permissions()
admin_only.administrator = True

bot = commands.Bot(intents=intents)


class FileDict(dict):
    def __init__(self, path: str) -> None:
        self.path = path
        if not os.path.exists(path):
            with open(path, "w") as f:
                json.dump({}, f)
        with open(path, "r") as f:
            self.update(json.load(f))

    def __setitem__(self, key: str, value: Any) -> None:
        super().__setitem__(key, value)
        with open(self.path, "w") as f:
            json.dump(self, f)

    def __delitem__(self, key: str) -> None:
        super().__delitem__(key)
        with open(self.path, "w") as f:
            json.dump(self, f)


sub_to_main = FileDict("data/sub-to-main.json")
punishment = FileDict("data/punishment.json")


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
    await bot.change_presence(
        activity=discord.Activity(type=discord.ActivityType.competing, name="がーと")
    )


@bot.event
async def on_member_update(before: discord.Member, after: discord.Member) -> None:
    if str(after.id) in sub_to_main:
        main = after.guild.get_member(sub_to_main[str(after.id)])
    else:
        main = after
    if str(main.id) in punishment:
        if punishment[str(main.id)] > time.time():
            await remove_manage_roles(after)
        else:
            del punishment[str(main.id)]


@bot.event
async def on_guild_role_update(before: discord.Role, after: discord.Role) -> None:
    await check()


@bot.slash_command(
    name="link-user",
    default_member_permissions=admin_only,
    guild_ids=[int(os.environ["GUILD_ID"])],
)
async def link_user(
    ctx: discord.ApplicationContext, main: discord.Member, sub: discord.Member
) -> None:
    if str(main.id) in sub_to_main:
        await ctx.respond(
            f"{main.mention} is already linked to {sub_to_main[str(main.id)]}!",
            ephemeral=True,
        )
        return
    sub_to_main[str(sub.id)] = main.id
    if str(main.id) in punishment:
        await remove_manage_roles(sub)
    await ctx.respond(f"{main.mention} is now linked to {sub.mention}!", ephemeral=True)


@bot.slash_command(
    name="unlink-user",
    default_member_permissions=admin_only,
    guild_ids=[int(os.environ["GUILD_ID"])],
)
async def unlink_user(
    ctx: discord.ApplicationContext, main: discord.Member, sub: discord.Member
) -> None:
    del sub_to_main[str(sub.id)]
    await ctx.respond(
        f"{main.mention} is now unlinked from {sub.mention}!", ephemeral=True
    )


@bot.user_command(
    name="Punish",
    default_member_permissions=admin_only,
    guild_ids=[int(os.environ["GUILD_ID"])],
)
async def punish(ctx: discord.ApplicationContext, member: discord.Member) -> None:
    await remove_manage_roles(member)
    punishment[str(member.id)] = time.time() + 24 * 60 * 60 * 30
    await ctx.respond(f"{member.mention} is now punished!", ephemeral=True)


@bot.user_command(
    name="Forgive",
    default_member_permissions=admin_only,
    guild_ids=[int(os.environ["GUILD_ID"])],
)
async def forgive(ctx: discord.ApplicationContext, member: discord.Member) -> None:
    del punishment[str(member.id)]
    await ctx.respond(f"{member.mention} is now forgiven!", ephemeral=True)


@bot.slash_command(
    name="list-punishments",
    guild_ids=[int(os.environ["GUILD_ID"])],
)
async def list_punishments(ctx: discord.ApplicationContext) -> None:
    await ctx.respond(
        "\n".join(
            f"{bot.get_user(int(k)).mention} is punished until <t:{int(v)}:F>"
            for k, v in punishment.items()
        ),
        ephemeral=True,
    )


@bot.message_command(
    name="絵しりとり保管",
    guilds_ids=[int(os.environ["GUILD_ID"])],
)
async def store_eshiritori(
    ctx: discord.ApplicationContext, message: discord.Message
) -> None:
    eshiritori_channel = bot.get_channel(int(os.environ["ESHIRITORI_CHANNEL_ID"]))
    if eshiritori_channel is None:
        await ctx.respond("絵しりとり保管庫が見つかりませんでした。", ephemeral=True)
        return
    files = []
    for attachment in message.attachments:
        file_bytes = BytesIO(await attachment.read())
        file = discord.File(file_bytes, filename=attachment.filename)
        files.append(file)
    if len(files) == 0:
        await ctx.respond("画像が見つかりませんでした。", ephemeral=True)
        return
    embed = discord.Embed(
        description=message.content,
        timestamp=message.created_at,
    )
    embed.set_author(
        name=message.author.display_name,
        icon_url=message.author.display_avatar.url,
    )
    embed.add_field(
        name="メッセージリンク",
        value=message.jump_url,
    )
    await eshiritori_channel.send(
        embed=embed,
        files=files,
    )
    await ctx.respond("絵しりとり保管庫に保管しました。", ephemeral=True)


# @bot.slash_command(
#     name="pin-to-eshiritori",
#     default_member_permissions=admin_only,
#     guild_ids=[int(os.environ["GUILD_ID"])],
# )
# async def pin_to_eshiritori(ctx: discord.ApplicationContext):
#     pinned_messages = await ctx.channel.pins()
#     pinned_messages.reverse()
#     for message in pinned_messages:
#         await store_eshiritori(ctx, message)


class VotingView(View):
    def __init__(
        self,
        ctx: discord.ApplicationContext,
        channel: discord.TextChannel,
        timeout: float,
    ):
        super().__init__(timeout=timeout)
        self.ctx = ctx
        self.channel = channel
        self.archive_category_id = os.environ["ARCHIVE_CATEGORY_ID"]
        self.votes: dict[str, list[discord.User]] = {"👍": set(), "👎": set()}

    async def on_timeout(self):
        await self.ctx.edit(content="投票はタイムアウトしました。", view=None)

    async def handle_vote_update(self, interaction: discord.Interaction):
        if len(self.votes["👍"]) >= 3:
            await self.archive_channel()
        elif len(self.votes["👎"]) >= 3:
            await self.ctx.edit(content="投票が否決されました。", view=None)

    @discord.ui.button(label="賛成", style=discord.ButtonStyle.green, emoji="👍")
    async def upvote_button(self, button: Button, interaction: discord.Interaction):
        if str(interaction.user.id) in sub_to_main:
            user = self.ctx.guild.get_member(sub_to_main[str(interaction.user.id)])
        else:
            user = interaction.user
        self.votes["👍"].add(user)
        await interaction.response.edit_message(embed=self.get_vote_embed(), view=self)
        await self.handle_vote_update(interaction)

    @discord.ui.button(label="反対", style=discord.ButtonStyle.red, emoji="👎")
    async def downvote_button(self, button: Button, interaction: discord.Interaction):
        if str(interaction.user.id) in sub_to_main:
            user = self.ctx.guild.get_member(sub_to_main[str(interaction.user.id)])
        else:
            user = interaction.user
        self.votes["👎"].add(user)
        await interaction.response.edit_message(embed=self.get_vote_embed(), view=self)
        await self.handle_vote_update(interaction)

    def get_vote_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title="アーカイブ投票",
            description=f"{self.channel.name} ({self.channel.mention}) をアーカイブしますか？",
        )
        embed.add_field(
            name="賛成",
            value="\n".join(
                f"{user.mention} ({user.name})" for user in self.votes["👍"]
            ),
        )
        embed.add_field(
            name="反対",
            value="\n".join(
                f"{user.mention} ({user.name})" for user in self.votes["👎"]
            ),
        )
        return embed

    async def archive_channel(self):
        category = self.ctx.guild.get_channel(self.archive_category_id)
        await self.channel.edit(category=category, sync_permissions=True)
        await self.ctx.edit(content="投票が可決されました。", view=None)


@bot.slash_command(
    name="archive",
    guild_ids=[int(os.environ["GUILD_ID"])],
    description="チャンネルを投票でアーカイブする",
)
async def archive_vote(ctx: discord.ApplicationContext, channel: discord.TextChannel):
    embed = discord.Embed(
        title="アーカイブ投票",
        description=f"{channel.name} ({channel.mention}) をアーカイブしますか？",
    )
    view = VotingView(ctx, channel, 24 * 60 * 60)
    await ctx.respond(embed=embed, view=view)


@tasks.loop(hours=1)
async def check() -> None:
    for member in bot.get_guild(int(os.environ["GUILD_ID"])).members:
        if str(member.id) in sub_to_main:
            main = member.guild.get_member(sub_to_main[str(member.id)])
        else:
            main = member
        if str(main.id) in punishment:
            if punishment[str(main.id)] > time.time():
                await remove_manage_roles(member)
            else:
                del punishment[str(main.id)]


bot.run(os.environ["DISCORD_TOKEN"])
