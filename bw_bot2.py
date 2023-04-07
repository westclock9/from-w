import google.auth
import os
import json
import discord
import re
import datetime
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from discord.ext import commands
from datetime import datetime, timezone, timedelta

TOKEN = 'MTA4ODAwODI4OTM4NTcyNjAwMg.GDXilR.TwJomQqKvKfdK0GpcjvnGy2oxlgaziylAavqy8'

file_dir = os.path.dirname(os.path.abspath(__file__))
creds_path = os.path.join(file_dir, 'client_secret.json')

intents = discord.Intents.default()
intents.members = True
intents.messages = True
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

# 수정한 부분: SCOPES를 전역변수로 추가
SCOPES = ['https://www.googleapis.com/auth/youtube.force-ssl']

@bot.command()
async def 전장(ctx):
    # 각 전장을 순서대로 저장
    battle_zones = [
        '```오늘은 외곽 유격지대(제압전)입니다.```',
        '```오늘은 봉인된 바위섬(봉바)입니다.```',
        '```오늘은 영광의 평원(쇄빙)입니다.```',
        '```오늘은 온살 하카이르입니다.```'
    ]

    start_date = datetime(2023, 3, 23)
    current_date = datetime.now()
    days_passed = (current_date - start_date).days
    current_battle_index = days_passed % len(battle_zones)
    current_battle = battle_zones[current_battle_index]

    await ctx.send(current_battle)

youtube_links = []
YOUTUBE_LINK_REGEX = r'(?:\+p\s)?((?:https?://)?(?:www\.)?(?:youtube\.com|youtu\.?be)/(?:watch\?v=)?[\w-]+)'


# 수정한 부분: 사용할 Google 계정 정보를 JSON 파일로 저장하여 경로를 지정
CREDENTIALS_FILE_PATH = 'google-credentials.json'

# 채널 ID를 이곳에 저장
TARGET_CHANNEL_ID = 1068994400778211428


def get_video_id(url):
    video_id_pattern = re.compile(r'(?:https?:\/\/)?(?:www\.)?(?:youtube\.com|youtu\.be)\/(?:watch\?v=)?([\w-]+)')
    match = video_id_pattern.match(url)
    return match.group(1) if match else None

# 수정한 부분: get_youtube_creds() 함수에서 계정 정보를 JSON 파일에서 불러오도록 변경
def get_youtube_creds():
    creds = None

    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                creds_path, SCOPES)
            creds = flow.run_local_server(port=8080)
            # Save the credentials for the next run
            with open('token.json', 'w') as token:
                token.write(creds.to_json())

    return creds



@bot.event
async def on_ready():
    print(f'{bot.user} is connected!')

@bot.event
async def on_message(message):
    # 봇 메시지는 무시
    if message.author == bot.user:
        return

    print("Checking channel ID...")
    # 메시지가 목표 채널에서 온 것인지 확인
    if message.channel.id == TARGET_CHANNEL_ID:
        print("Channel ID matched!")

        # 메시지 작성 시간이 오늘인지 확인
        if is_today(message.created_at):
            print("Message is from today!")
            youtube_link = re.search(YOUTUBE_LINK_REGEX, message.content)

            if youtube_link:
                print("YouTube link found!")
                youtube_links.append(youtube_link.group(1))

    await bot.process_commands(message)

@bot.command()
async def playlist(ctx):
    global youtube_links

    for channel in ctx.guild.text_channels:
        if str(channel.id) == str(TARGET_CHANNEL_ID):
            channel_youtube_links = []
            async for message in channel.history(limit=100):
                if is_today(message.created_at):
                    youtube_link = re.search(YOUTUBE_LINK_REGEX, message.content)
                    if youtube_link:
                        channel_youtube_links.append(youtube_link.group(1))
            youtube_links = channel_youtube_links
            break

    if youtube_links:
        today_str = datetime.now().strftime("%Y/%m/%d")
        playlist_name = f"{today_str} PLAYLIST"
        creds = get_youtube_creds()
        youtube = build('youtube', 'v3', credentials=creds)
        request = youtube.playlists().insert(
            part="snippet,status",
            body={
                "snippet": {
                    "title": playlist_name,
                    "description": "Today's YouTube playlist"
                },
                "status": {
                    "privacyStatus": "public"
                }
            }
        )
        response = request.execute()
        playlist_id = response['id']

        # 영상 ID를 사용하여 플레이리스트에 동영상 추가
        for link in youtube_links:
            video_id = get_video_id(link)
            if video_id:
                request = youtube.playlistItems().insert(
                    part="snippet",
                    body={
                        "snippet": {
                            "playlistId": playlist_id,
                            "position": 0,
                            "resourceId": {
                                "kind": "youtube#video",
                                "videoId": video_id
                            }
                        }
                    }
                )
                request.execute()

        playlist_url = f"https://www.youtube.com/playlist?list={playlist_id}"
        response = f"```{today_str} 플레이리스트‧₊˚(˘ᵕ˘)˚₊‧ : {playlist_url}```"
    else:
        response = "```오늘 올라온 YouTube 링크가 없습니다.```"
    await ctx.send(response)

@bot.command(name='date')
async def days_since_jan_21_2023(ctx):
    target_date = datetime(2023, 1, 21)
    current_date = datetime.now()
    days_passed = (current_date - target_date).days

    await ctx.send(f'```𝙀𝙩𝙚𝙧𝙣𝙖𝙡 𝙬𝙚𝙙𝙙𝙞𝙣𝙜 : +{days_passed}일```')

def is_today(message_date):
    today = datetime.now(timezone.utc)
    return message_date.day == today.day and message_date.month == today.month and message_date.year == today.year

@bot.command(name='remind')
async def remind(ctx):
    now = datetime.now()
    future = datetime(now.year, 1, 21)
    if future < now:
        future = datetime(now.year + 1, 1, 21)
    delta = future - now
    days = delta.days
    await ctx.send(f'``` 𝗡𝗲𝘅𝘁 𝗥𝗲𝗺𝗶𝗻𝗱 : D-{days} ( *˘╰╯˘*)```')
    
@bot.command(name='bb')
async def days_until_may_5(ctx):
    current_date = datetime.now()
    target_date = datetime(current_date.year, 5, 5)

    if current_date > target_date:
        target_date = datetime(current_date.year + 1, 5, 5)

    days_remaining = (target_date - current_date).days

    await ctx.send(f'``` ♡ 햄돼 생일 ♡ 까지 {days_remaining}일 남았습니다! ♡ ٩(´▽`)۶ ♡ ```')

bot.run(TOKEN)
