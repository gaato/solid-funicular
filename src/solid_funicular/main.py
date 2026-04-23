import datetime
import itertools
import json
import os
import random
import re
import time
from io import BytesIO
from typing import Any, Optional

import discord
from discord.ext import commands, tasks
from discord.ui import Button, View
from dotenv import load_dotenv

# Only load .env if not running under systemd (for development)
if not os.environ.get('DISCORD_TOKEN'):
    load_dotenv()
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

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


users = FileDict("data/users.json")
punishment = FileDict("data/punishment.json")


yamanote_line_announces = itertools.cycle(
    [
        """この電車は、山手線内回り、上野・池袋方面行きです。

次は、神田、神田、お出口は左側です。

中央線、地下鉄銀座線はお乗り換えです。

This is the Yamanote Line train bound for Ueno and Ikebukuro.

The next station is Kanda(JY-02).

The doors on the left side will open.

Please change here the Chuo Line and the Ginza Subway Line.""",
        """次は、秋葉原、秋葉原、お出口は左側です。

総武線各駅停車、地下鉄日比谷線、つくばエクスプレス線はお乗り換えです。

The next station is Akihabara(JY-03).

The doors on the left side will open.

Please change here for the Sobu Line local service, the Hibiya Subway Line and the Tsukuba express Line.""",
        """次は、御徒町、御徒町、お出口は左側です。

都営地下鉄大江戸線はお乗り換えです

The next station is Okachimachi(JY-04).

The doors on the left side will open.

Please change here for the Oedo Subway Line.""",
        """次は、上野、上野、お出口は左側です。

新幹線、宇都宮線、高崎線、常磐線、地下鉄銀座線、地下鉄日比谷線、京成線はお乗り換えです。

The next station is Ueno(JY-05).

The doors on the left side will open.

Please change here for the Shinkansen, the Utsunomiya Line, the Takasaki Line, the Joban Line, the Ginza Subway Line, the Hibiya Subway Line and the Keisei Line.""",
        """この電車は、山手線内回り、池袋・新宿方面行きです。

次は、鶯谷、鶯谷、お出口は左側です。

This is the Yamanote Line train bound for Ikebukuro and Shinjuku.

The next station is Uguisudani(JY-06).

The doors on the left side will open.""",
        """次は、日暮里、日暮里、お出口は左側です。

常磐線、京成線と日暮里・舎人ライナーはお乗り換えです。

The next station is Nippori(JY-07).

The doors on the left side will open.

Please change here for the Joban Line, the Keisei Line and the Nippori-Toneri Liner.""",
        """次は、西日暮里、西日暮里、お出口は左側です。

地下鉄千代田線と日暮里・舎人ライナーはお乗り換えです。

The next station is Nishi-Nippori(JY-08).

The doors on the left side will open.

Please change here for the Chiyoda Subway Line and the Nippori-Toneri Liner.""",
        """次は、田端、田端、お出口は左側です。

京浜東北線はお乗り換えです。

The next station is Tabata(JY-09).

The doors on the left side will open.

Please change here for the Keihin-Tohoku Line.""",
        """次は、駒込、駒込、お出口は右側です。

地下鉄南北線はお乗り換えです。

この電車には優先席があります。優先席を必要とされるお客様がいらっしゃいましたら席をお譲りください。

The next station is Komagome(JY-10).

The doors on the right side will open.

Please change here for the Namboku Subway Line.

There are priority seats in most cars. Please offer seat to those who may need it.""",
        """次は、巣鴨、巣鴨、お出口は右側です。

都営地下鉄三田線はお乗り換えです。

The next station is Sugamo(JY-11).

The doors on the right side will open.

Please change here for the Mita Subway Line.""",
        """次は、大塚、大塚、お出口は右側です。

東京さくらトラム（都電荒川線）はお乗り換えです。

The next station is Otsuka(JY-12).

The doors on the right side will open.

Please change here for the Tokyo Sakura tram.""",
        """次は、池袋、池袋、お出口は左側です。

湘南新宿ライン、埼京線、東武東上線、西武池袋線、地下鉄丸ノ内線、地下鉄有楽町線、地下鉄副都心線はお乗り換えです。

The next station is Ikebukuro(JY-13).

The doors on the left side will open.

Please change here for the Shonan-Shinjuku Line, the Saikyo Line, the Tobu Tojo Line, the Seibu Ikebukuro Line, the Marunouchi Subway Line, the Yurakucho Subway Line and the Fukutoshin Subway Line.""",
        """この電車は、山手線内回り、新宿・渋谷方面行きです。

次は、目白、目白、お出口は左側です。

This is the Yamanote Line train bound for Shinjuku and Shibuya.

The next station is Mejiro(JY-14).

The doors on the right side will open.""",
        """次は、高田馬場、高田馬場、お出口は右側です。

西武新宿線、地下鉄東西線はお乗り換えです。

The next station is Takadanobaba(JY-15).

The doors on the right side will open.

Please change here the Seibu Shinjuku Line and the Tozai Subway Line.""",
        """次は、新大久保、新大久保、お出口は右側です。

お客様にお願い致します。車内では携帯電話をマナーモードに設定の上、通話はお控えください。ご協力をお願い致します。

The next station is Shin-Okubo(JY-16).

The doors on the right side will open.

Please set you mobile phone to silent mode and refrain talking on the phone.""",
        """次は、新宿、新宿、お出口は左側です。

中央線、湘南新宿ライン、埼京線、小田急線、京王線、地下鉄丸ノ内線、都営地下鉄新宿線、都営地下鉄大江戸線はお乗り換えです。

The next station is Shinjuku(JY-17).

The doors on the left side will open.

Please change here for the Chuo Line, the Shonan-Shinjuku Line, the Saikyo Line, the Odakyu Line, the Keio Line, the Marunouchi Subway Line, the Shinjuku Subway Line and the Oedo Subway Line.""",
        """この電車は、山手線内回り、渋谷・品川方面行きです。

次は、代々木、代々木、お出口は左側です。

都営地下鉄大江戸線はお乗り換えです。

This is the Yamanote Line train bound for Shibuya and Shinagawa.

The next station is Yoyogi(JY-18).

The doors on the left side will open.

Please change here for the Oedo Subway Line.""",
        """次は、原宿、原宿、お出口は右側です。

地下鉄千代田線と地下鉄副都心線はお乗り換えです。

The next station is Harajuku(JY-19).

The doors on the right side will open.

Please change here for the Chiyoda Subway Line and the Fukutoshin Subway Line.""",
        """次は、渋谷、渋谷、お出口は右側です。

東急東横線、東急田園都市線、京王井の頭線、地下鉄銀座線、地下鉄半蔵門線、地下鉄副都心線はお乗り換えです。

電車とホームの間が空いているところがありますので、足元にご注意ください。

The next station is Shibuya(JY-20).

The doors on the right side will open.

Please change here for the Tokyu Toyoko Line, the Tokyu Den-en-toshi Line, the Keio Inokashira Line, the Ginza Subway Line, the Hanzomon Subway Line and the fukutoshin Subway Line.

Please watch your step when you leave the train.""",
        """この電車は、山手線内回り、品川・東京方面行きです。

次は、恵比寿、恵比寿、お出口は右側です。

湘南新宿ラインと地下鉄日比谷線はお乗り換えです。

This is the Yamanote Line train bound for Shinagawa and Tokyo.

The next station is Ebisu(JY-21).

The doors on the right side will open.

Please change here for the Shonan-Shinjuku Line and the Hibiya Subway Line.""",
        """次は、目黒、目黒、お出口は右側です。

東急目黒線、地下鉄南北線、都営地下鉄三田線はお乗り換えです。

The next station is Meguro(JY-22).

The doors on the right side will open.

Please change here for the Tokyu Meguro Line, the Namboku Subway Line and the Mita Subway Line.""",
        """次は、五反田、五反田、お出口は右側です。

東急池上線、都営地下鉄浅草線はお乗り換えです。

The next station is Gotanda(JY-23).

The doors on the right side will open.

Please change here for the Tokyu Ikegami Line and the Asakusa Subway Line.""",
        """次は、大崎、大崎、お出口は右側です。

湘南新宿ライン、相鉄線直通列車と、東京臨海高速鉄道りんかい線はお乗り換えです。

The next station is Osaki(JY-24).

The doors on the right side will open.

Please change here for the Shonan-Shinjuku Line, through service to the Sotetsu Line and the Tokyo Rinkai Kosoku Tetsudo Rinkai Line.""",
        """次は、品川、品川、お出口は右側です。

新幹線、京浜東北線（大井町・蒲田方面）、東海道線、上野東京ライン、横須賀線、京急線はお乗り換えです。

この電車には優先席があります。優先席を必要とされるお客様がいらっしゃいましたら、席をお譲りください。

The next station is Shinagawa(JY-25).

The doors on the right side will open.

Please change here for the Shinkansen, the Keihin-Tohoku Line for Oimachi and Kamata, the Tokaido Line, the Ueno-Tokyo Line, the Yokosuka Line and the Keikyu Line.

There are priority seats in most cars. Please offer seat to those who may need it.""",
        """次は、高輪ゲートウェイ、高輪ゲートウェイ、お出口は右側です。

The next station is Takanawa Gateway(JY-26).

The doors on the right side will open.""",
        """次は、田町、田町、お出口は左側です。

京浜東北線はお乗り換えです。

The next station is Tamachi(JY-27).

The doors on the left side will open.

Please change here for the Kehin-Tohoku Line.""",
        """次は、浜松町、浜松町、お出口は左側です。

東京モノレール羽田空港線、都営地下鉄大江戸線はお乗り換えです。

The next station is Hamamatsucho(JY-28).

The doors on the left side will open.

Please change here for the Tokyo Monorail Haneda airport Line and the Oedo Subway Line.""",
        """次は、新橋、新橋、お出口は左側です。

地下鉄銀座線、都営地下鉄浅草線、ゆりかもめはお乗り換えです。

The next station is Shimbashi(JY-29).

The doors on the left side will open.

Please change here the Ginza Subway Line, the Asakusa Subway Line and the Yurikamome Line.""",
        """次は、有楽町、有楽町、お出口は左側です。

地下鉄日比谷線、地下鉄有楽町線はお乗り換えです。

The station is Yurakucho(JY-30).

The doors on the left side will open.

Please change here for the Hibiya Subway Line and the Yurakucho Subway Line.""",
        """次は、東京、東京、お出口は左側です。

新幹線、中央線、東海道線、上野東京ライン、横須賀線、総武快速線、京葉線、地下鉄丸ノ内線はお乗り換えです。

The next station is Tokyo(JY-01).

The doors on the left side will open.

Please change here the Shinkansen, the Chuo Line, the Tokaido Line,the Ueno-Tokyo Line, the Yokosuka Line, the Sobu Line rapid service the Keiyo Line and the Marunouchi Subway Line.""",
    ]
)


# yamanote_line_stations = itertools.cycle(
#     [
#         "東京",
#         "神田",
#         "秋葉原",
#         "御徒町",
#         "上野",
#         "鶯谷",
#         "日暮里",
#         "西日暮里",
#         "田端",
#         "駒込",
#         "巣鴨",
#         "大塚",
#         "池袋",
#         "目白",
#         "高田馬場",
#         "新大久保",
#         "新宿",
#         "代々木",
#         "原宿",
#         "渋谷",
#         "恵比寿",
#         "目黒",
#         "五反田",
#         "大崎",
#         "品川",
#         "高輪ゲートウェイ",
#         "田町",
#         "浜松町",
#         "新橋",
#         "有楽町",
#     ]
# )


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
    announce_station.start()
    # await bot.change_presence(
    #     activity=discord.Activity(
    #         type=discord.ActivityType.competing, name="がーとの脳内"
    #     )
    # )


@bot.event
async def on_message(message: discord.Message) -> None:
    if message.author.bot:
        return
    pattern = re.compile(r"(.)\1{99,}")
    if pattern.search(message.content):
        for _ in range(10):
            await message.channel.send(
                f"{message.author.mention} うるさい", delete_after=1.0
            )
            await message.author.send(message.content)


@bot.event
async def on_member_join(member: discord.Member) -> None:
    await check()


@bot.event
async def on_member_update(before: discord.Member, after: discord.Member) -> None:
    await check()


@bot.event
async def on_guild_role_update(before: discord.Role, after: discord.Role) -> None:
    await check()


@bot.slash_command(
    name="verify",
    default_member_permissions=admin_only,
    guild_ids=[int(os.environ["GUILD_ID"])],
)
async def verify_user(
    ctx: discord.ApplicationContext,
    target: discord.Member,
    main: Optional[discord.Member] = None,
) -> None:
    users[str(target.id)] = main.id if main is not None else None
    if main is not None and str(main.id) in punishment:
        await remove_manage_roles(target)
    await ctx.respond(f"{target.mention} is now verified!", ephemeral=True)


@bot.slash_command(
    name="unverify",
    default_member_permissions=admin_only,
    guild_ids=[int(os.environ["GUILD_ID"])],
)
async def unverify(ctx: discord.ApplicationContext, target: discord.Member) -> None:
    del users[str(target.id)]
    await ctx.respond(f"{target.mention} is now unverified!", ephemeral=True)


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
    for k, v in punishment.items():
        user = bot.get_user(int(k))
        assert user
        await ctx.respond(
            f"{user.mention} is punished until <t:{int(v)}:F>", ephemeral=True
        )


@bot.message_command(
    name="絵しりとり保管",
    guilds_ids=[int(os.environ["GUILD_ID"])],
)
async def store_eshiritori(
    ctx: discord.ApplicationContext, message: discord.Message
) -> None:
    eshiritori_channel = bot.get_channel(int(os.environ["ESHIRITORI_CHANNEL_ID"]))
    assert isinstance(eshiritori_channel, discord.TextChannel)
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
        self.archive_category_id = int(os.environ["ARCHIVE_CATEGORY_ID"])
        self.votes: dict[str, set[discord.User]] = {"👍": set(), "👎": set()}

    async def on_timeout(self):
        if len(self.votes["👍"]) > len(self.votes["👎"]):
            await self.archive_channel()
        else:
            await self.ctx.edit(
                content=f"反対 {len(self.votes['👎'])} 票のため投票が否決されました。",
                view=None,
            )

    async def handle_vote_update(self, interaction: discord.Interaction):
        if len(self.votes["👍"]) >= 5:
            await self.archive_channel()
        elif len(self.votes["👎"]) >= 3:
            await self.ctx.edit(
                content=f"反対 {len(self.votes['👎'])} 票のため投票が否決されました。",
                view=None,
            )

    @discord.ui.button(label="賛成", style=discord.ButtonStyle.green, emoji="👍")
    async def upvote_button(self, button: Button, interaction: discord.Interaction):
        assert isinstance(interaction.user, discord.Member)
        if str(interaction.user.id) not in users:
            await interaction.response.send_message(
                "あなたは認証されていません。", ephemeral=True
            )
            return
        if users[str(interaction.user.id)] is not None:
            user = self.ctx.guild.get_member(users[str(interaction.user.id)])
        else:
            user = interaction.user
        self.votes["👍"].add(user)
        self.votes["👎"].discard(user)
        await interaction.response.edit_message(embed=self.get_vote_embed(), view=self)
        await self.handle_vote_update(interaction)

    @discord.ui.button(label="反対", style=discord.ButtonStyle.red, emoji="👎")
    async def downvote_button(self, button: Button, interaction: discord.Interaction):
        assert isinstance(interaction.user, discord.Member)
        if str(interaction.user.id) not in users:
            await interaction.response.send_message(
                "あなたは認証されていません。", ephemeral=True
            )
            return
        if users[str(interaction.user.id)] is not None:
            user = self.ctx.guild.get_member(users[str(interaction.user.id)])
        else:
            user = interaction.user
        self.votes["👎"].add(user)
        self.votes["👍"].discard(user)
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
        await self.ctx.edit(
            content=f"賛成 {len(self.votes['👍'])} 票のため投票が可決されました。",
            view=None,
        )


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


@bot.slash_command(
    name="setup",
    default_member_permissions=admin_only,
    guild_ids=[int(os.environ["GUILD_ID"])],
)
async def setup(ctx: discord.ApplicationContext) -> None:
    member_role = ctx.guild.get_role(int(os.environ["MEMBER_ROLE_ID"]))
    for member in ctx.guild.members:
        if str(member.id) not in users:
            users[str(member.id)] = None
            await member.add_roles(member_role)


@tasks.loop(minutes=1)
async def check() -> None:
    guild = bot.get_guild(int(os.environ["GUILD_ID"]))
    assert guild
    for member in guild.members:
        if str(member.id) not in users:
            continue
        if users[str(member.id)] is not None:
            main = member.guild.get_member(users[str(member.id)])
        else:
            main = member
        assert main
        if str(main.id) in punishment:
            if punishment[str(main.id)] > time.time():
                await remove_manage_roles(member)
            else:
                del punishment[str(main.id)]


@tasks.loop(minutes=2)
async def announce_station() -> None:
    # 0:56 から 4:25 まではアナウンスしない
    now = datetime.datetime.now().time()
    if datetime.time(hour=0, minute=56) <= now <= datetime.time(hour=4, minute=25):
        return
    guild = bot.get_guild(1181575958730391642)
    if guild is None:
        return
    channel = guild.get_channel(1181589574993064007)
    if not isinstance(channel, discord.TextChannel):
        all_channels = filter(
            lambda c: isinstance(c, discord.TextChannel), await guild.fetch_channels()
        )
        channel = random.choice(list(all_channels))
        assert isinstance(channel, discord.TextChannel)
    assert bot.user
    bot_member = guild.get_member(bot.user.id)
    assert bot_member
    announce = next(yamanote_line_announces)
    if m := re.search(r"この電車は、山手線内回り、(.+?)方面行きです。", announce):
        await bot_member.edit(nick=f"山手線内回り {m.group(1)}方面行き")
    await channel.send("<@!600922778509770754>\n" + announce)


@bot.message_command(
    name="ピン留め",
    guilds_ids=[int(os.environ["GUILD_ID"])],
)
async def pin(ctx: discord.ApplicationContext, message: discord.Message) -> None:
    await message.pin()
    await ctx.respond("ピン留めしました。", ephemeral=True)


@bot.message_command(
    name="ピン留め解除",
    guilds_ids=[int(os.environ["GUILD_ID"])],
)
async def unpin(ctx: discord.ApplicationContext, message: discord.Message) -> None:
    await message.unpin()
    await ctx.respond("ピン留め解除しました。", ephemeral=True)


def main():
    """Main entry point for the bot."""
    bot.run(os.environ["DISCORD_TOKEN"])


if __name__ == "__main__":
    main()
