"""
JalebiJams - Discord Music Bot
A Discord bot that plays YouTube music in voice channels.
"""

import os
import re
import json
import platform
import discord
from discord.ext import commands
import yt_dlp
import asyncio
from dotenv import load_dotenv
import traceback
import itertools
import requests

# Load environment variables
load_dotenv()

# Bot configuration
TOKEN = os.getenv('DISCORD_TOKEN')
COMMAND_PREFIX = os.getenv('COMMAND_PREFIX', '!')

# Setup intents
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

# Create bot instance
bot = commands.Bot(command_prefix=COMMAND_PREFIX, intents=intents)

# YouTube DL options
import os.path

cookies_file = os.path.join(os.path.dirname(__file__), 'cookies.txt')
INVIDIOUS_HOST_ENV = os.getenv('INVIDIOUS_HOST')
_INVIDIOUS_DEFAULTS = [
    'https://invidious.jing.rocks',
    'https://invidious.flokinet.to',
    'https://invidious.privacydev.net',
]
INVIDIOUS_HOST = (INVIDIOUS_HOST_ENV or _INVIDIOUS_DEFAULTS[0]).rstrip('/')

USER_AGENT = os.getenv('YTDLP_USER_AGENT', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0 Safari/537.36')

VERBOSE_YTDLP = os.getenv('YTDLP_VERBOSE', '0') == '1'

ytdl_format_options = {
    'format': 'bestaudio*',  # More flexible format selection
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': False,  # Allow playlists
    'playlistend': 50,
    'nocheckcertificate': True,
    'ignoreerrors': True,
    'logtostderr': False,
    'quiet': not VERBOSE_YTDLP,
    'no_warnings': not VERBOSE_YTDLP,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
    'http_headers': {
        'User-Agent': USER_AGENT,
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept': '*/*',
        'Origin': 'https://www.youtube.com',
        'Referer': 'https://www.youtube.com/',
    },
    'extractor_args': {
        'youtube': {
            'player_client': ['android', 'web', 'ios'],
        }
    },
    'retries': 3,
}

# Add cookies if file exists
CRITICAL_COOKIE_NAMES = {'SID','HSID','SSID','SAPISID','__Secure-3PAPISID','__Secure-3PSID','__Secure-3PSIDCC','PREF','LOGIN_INFO'}
COOKIES_LOADED = False
COOKIE_MISSING_CRITICAL = True
if os.path.isfile(cookies_file):
    try:
        size_ok = os.path.getsize(cookies_file) > 64
        critical_found = set()
        if size_ok:
            with open(cookies_file, 'r', encoding='utf-8', errors='ignore') as cf:
                for line in cf:
                    if '\tyoutube.com\t' in line or '\tyoutube-nocookie.com\t' in line:
                        parts = line.strip().split('\t')
                        if len(parts) >= 7:
                            name = parts[5]
                            if name in CRITICAL_COOKIE_NAMES:
                                critical_found.add(name)
                if critical_found:
                    ytdl_format_options['cookiefile'] = cookies_file
                    COOKIES_LOADED = True
                    COOKIE_MISSING_CRITICAL = not (CRITICAL_COOKIE_NAMES & critical_found)
    except Exception:
        COOKIES_LOADED = False
        COOKIE_MISSING_CRITICAL = True

ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

# Configuration (can be overridden via environment variables)
MAX_PLAYLIST_ITEMS = int(os.getenv('MAX_PLAYLIST_ITEMS', '50'))
FAST_PLAYLIST_MODE = os.getenv('PLAYLIST_MODE', 'fast').lower() == 'fast'  # fast = don't prefetch full metadata


def _build_ytdl():
    """Rebuild YoutubeDL instance (used for fallback attempts when options change)."""
    return yt_dlp.YoutubeDL(ytdl_format_options)


async def extract_info_safe(url: str, *, download: bool = False, process: bool = True):
    """Extract info with layered fallbacks.

    Fallback strategy:
    1. Try with current options (stream mode)
    2. Retry with simpler player_client if formats missing
    3. Retry forcing default player client
    4. As last resort: download the file (slower) and use local filename
    """
    loop = asyncio.get_event_loop()

    async def _run(extractor_opts_override=None, force_download=False):
        opts = ytdl_format_options.copy()
        if extractor_opts_override:
            opts['extractor_args'] = extractor_opts_override
        ytdl_local = yt_dlp.YoutubeDL(opts)
        return await loop.run_in_executor(
            None,
            lambda: ytdl_local.extract_info(url, download=force_download or download, process=process)
        )

    try:
        data = await _run()
    except Exception as e1:
        print(f"[extract] primary failed: {e1}")
        try:
            data = await _run({'youtube': {'player_client': ['default']}})
        except Exception as e2:
            print(f"[extract] fallback client failed: {e2}")
            try:
                data = await _run({'youtube': {'player_client': ['default']}}, force_download=True)
            except Exception as final_err:
                print(f"[extract] force download failed: {final_err}")
                raise final_err
    return data


def select_playable_url(data: dict):
    """Return a playable audio URL (or local filename) from yt-dlp data."""
    if not data:
        return None
    # Direct/url field
    direct = data.get('url')
    if direct:
        return direct
    # Formats fallback
    formats = data.get('formats') or []
    audio = [f for f in formats if f.get('acodec') and f.get('acodec') != 'none' and f.get('url')]
    if audio:
        # Prefer highest abr
        audio.sort(key=lambda f: f.get('abr') or 0)
        return audio[-1]['url']
    # If downloaded
    if data.get('_filename'):
        return data['_filename']
    return None


async def enqueue_playlist_fast(entries, ctx, queue):
    """Enqueue playlist entries quickly without full metadata extraction.
    Only basic fields are stored. Full extraction happens when each track plays.
    """
    added = 0
    # Support both list-like and generator/iterable entries
    if hasattr(entries, '__getitem__'):
        iterable = entries[:MAX_PLAYLIST_ITEMS]
    else:
        iterable = itertools.islice(entries, MAX_PLAYLIST_ITEMS)

    for entry in iterable:
        if not entry:
            continue
        video_id = entry.get('id')
        if video_id and len(video_id) == 11:
            base_url = f"https://www.youtube.com/watch?v={video_id}"
        else:
            base_url = entry.get('webpage_url') or entry.get('url')
        if not base_url:
            continue
        queue.add({'url': base_url, 'title': entry.get('title') or 'Unknown', 'ctx': ctx})
        added += 1
    return added


def extract_video_id(url: str) -> str | None:
    """Extract YouTube video ID from multiple URL patterns."""
    patterns = [
        r"v=([A-Za-z0-9_-]{11})",
        r"youtu\.be/([A-Za-z0-9_-]{11})",
        r"youtube\.com/embed/([A-Za-z0-9_-]{11})"
    ]
    for p in patterns:
        m = re.search(p, url)
        if m:
            return m.group(1)
    if len(url) == 11 and re.match(r"^[A-Za-z0-9_-]{11}$", url):
        return url
    return None


def invidious_api_video(video_id: str) -> dict | None:
    """Fetch video information from Invidious as a fallback."""
    try:
        resp = requests.get(f"{INVIDIOUS_HOST}/api/v1/videos/{video_id}", timeout=10)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        return None
    return None


def pick_invidious_audio(data: dict) -> str | None:
    """Select an audio stream URL from Invidious API response."""
    if not data:
        return None
    adaptive = data.get('adaptiveFormats') or []
    audio = [f for f in adaptive if f.get('type', '').startswith('audio/') and f.get('url')]
    if not audio:
        # Try formatStreams fallback
        streams = data.get('formatStreams') or []
        audio = [f for f in streams if f.get('type', '').startswith('audio/') and f.get('url')]
    if audio:
        # Prefer highest bitrate
        audio.sort(key=lambda f: f.get('bitrate') or 0)
        return audio[-1]['url']
    return None


class YTDLSource(discord.PCMVolumeTransformer):
    """YouTube audio source for Discord voice client."""
    
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')
        self.duration = data.get('duration')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        """Create audio source from YouTube URL."""
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            # Take first item from a playlist
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)


class MusicQueue:
    """Simple music queue manager."""
    
    def __init__(self):
        self.queue = []
        self.current = None

    def add(self, song):
        """Add a song to the queue."""
        self.queue.append(song)

    def get_next(self):
        """Get the next song from the queue."""
        if self.queue:
            self.current = self.queue.pop(0)
            return self.current
        return None

    def clear(self):
        """Clear the queue."""
        self.queue.clear()
        self.current = None

    def is_empty(self):
        """Check if queue is empty."""
        return len(self.queue) == 0


# Store music queues per guild
music_queues = {}


def get_queue(guild_id):
    """Get or create a music queue for a guild."""
    if guild_id not in music_queues:
        music_queues[guild_id] = MusicQueue()
    return music_queues[guild_id]


@bot.event
async def on_ready():
    """Event handler for when the bot is ready."""
    print(f'{bot.user} has connected to Discord!')
    print(f'Bot is in {len(bot.guilds)} guilds')
    ytdlp_version = getattr(yt_dlp, '__version__', getattr(getattr(yt_dlp, 'version', None), '__version__', 'unknown'))
    print(f'yt-dlp version: {ytdlp_version} | Python: {platform.python_version()}')
    print(f'Cookies loaded: {COOKIES_LOADED} | Critical missing: {COOKIE_MISSING_CRITICAL}')
    print(f'Invidious host: {INVIDIOUS_HOST}')
    if not COOKIES_LOADED:
        print('WARNING: cookies.txt not fully loaded or missing — YouTube may trigger bot detection.')
    elif COOKIE_MISSING_CRITICAL:
        print('NOTICE: Some critical cookies missing; consider exporting with browser extension for full set.')


@bot.event
async def on_voice_state_update(member, before, after):
    """Event handler for voice state changes."""
    # Check if someone left a voice channel
    if before.channel is not None and after.channel != before.channel:
        # Get the bot's voice client for this guild
        voice_client = member.guild.voice_client
        
        # If bot is in a voice channel
        if voice_client and voice_client.channel:
            # Count non-bot members in the channel
            members = [m for m in voice_client.channel.members if not m.bot]
            
            # If bot is alone (only bots left), disconnect
            if len(members) == 0:
                queue = get_queue(member.guild.id)
                queue.clear()
                await voice_client.disconnect()
                print(f"Auto-disconnected from {voice_client.channel.name} - channel empty")



@bot.command(name='join', help='Makes the bot join the voice channel')
async def join(ctx):
    """Join the voice channel of the user."""
    if not ctx.message.author.voice:
        await ctx.send("You are not connected to a voice channel!")
        return

    channel = ctx.message.author.voice.channel
    
    if ctx.voice_client is not None:
        await ctx.voice_client.move_to(channel)
    else:
        await channel.connect()
    
    await ctx.send(f"Joined {channel.name}!")


@bot.command(name='leave', help='Makes the bot leave the voice channel')
async def leave(ctx):
    """Leave the voice channel."""
    if ctx.voice_client:
        queue = get_queue(ctx.guild.id)
        queue.clear()
        await ctx.voice_client.disconnect()
        await ctx.send("Left the voice channel!")
    else:
        await ctx.send("I'm not in a voice channel!")


@bot.command(name='play', help='Plays music from YouTube (URL or search query)')
async def play(ctx, *, url):
    """Play music from YouTube."""
    if not ctx.message.author.voice:
        await ctx.send("You need to be in a voice channel to play music!")
        return

    channel = ctx.message.author.voice.channel

    # Join the channel if not already connected
    if ctx.voice_client is None:
        await channel.connect()
    elif ctx.voice_client.channel != channel:
        await ctx.voice_client.move_to(channel)
    
    # Clean YouTube Music URLs - remove auto-playlist parameters
    if 'music.youtube.com' in url and '&list=' in url:
        # Extract just the video ID for single song playback
        url = url.split('&list=')[0]

    async with ctx.typing():
        try:
            loop = bot.loop or asyncio.get_event_loop()
            is_playlist_url = ('/playlist?' in url) or ('youtube.com/watch' in url and 'list=' in url and 'RDAMVM' not in url)

            if is_playlist_url:
                # Fetch playlist shell without processing full metadata
                data = await extract_info_safe(url, download=False, process=False)
                if data and 'entries' in data:
                    entries = data['entries']
                    playlist_title = data.get('title', 'playlist')
                    queue = get_queue(ctx.guild.id)
                    added = await enqueue_playlist_fast(entries, ctx, queue) if FAST_PLAYLIST_MODE else 0
                    if not FAST_PLAYLIST_MODE:
                        # Full metadata mode: extract each (slow)
                        for entry in entries[:MAX_PLAYLIST_ITEMS]:
                            if not entry:
                                continue
                            video_id = entry.get('id')
                            url_single = f"https://www.youtube.com/watch?v={video_id}" if video_id else entry.get('webpage_url')
                            queue.add({'url': url_single, 'title': entry.get('title') or 'Unknown', 'ctx': ctx})
                        added = min(len(entries), MAX_PLAYLIST_ITEMS)
                    await ctx.send(f"📝 Added **{added}** tracks from playlist: **{playlist_title}**")
                    if not ctx.voice_client.is_playing():
                        await play_next(ctx)
                    return
            # Single video or fallback
            data = None
            try:
                data = await extract_info_safe(url, download=False)
            except Exception as primary_err:
                print(f"[play] primary extraction failed: {primary_err}")
                # If cookies absent or primary failed with auth message -> try Invidious
                vid = extract_video_id(url)
                if vid:
                    inv = invidious_api_video(vid)
                    if inv:
                        playable = pick_invidious_audio(inv)
                        if playable:
                            fake_data = {
                                'title': inv.get('title', 'Unknown (Invidious)'),
                                'url': playable,
                                'duration': inv.get('lengthSeconds'),
                            }
                            player = YTDLSource(discord.FFmpegPCMAudio(playable, **ffmpeg_options), data=fake_data)
                            if ctx.voice_client.is_playing():
                                queue = get_queue(ctx.guild.id)
                                queue.add({'url': url, 'title': fake_data['title'], 'ctx': ctx})
                                await ctx.send(f'Added (fallback): **{fake_data['title']}**')
                            else:
                                ctx.voice_client.play(player, after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop))
                                await ctx.send(f'Now playing (fallback): **{fake_data['title']}**')
                            return
                await ctx.send(f"⚠️ Extraction failed: {str(primary_err)[:90]}")
                return
            if 'entries' in data:
                data = data['entries'][0]
            playable = select_playable_url(data)
            if not playable:
                raise Exception('No playable audio format found')
            player = YTDLSource(discord.FFmpegPCMAudio(playable, **ffmpeg_options), data=data)
            if ctx.voice_client.is_playing():
                queue = get_queue(ctx.guild.id)
                queue.add({'url': url, 'title': player.title, 'ctx': ctx})
                await ctx.send(f'Added to queue: **{player.title}**')
            else:
                ctx.voice_client.play(player, after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop))
                await ctx.send(f'Now playing: **{player.title}**')
        except Exception as e:
            await ctx.send(f'⚠️ Error: {str(e)[:120]}')
            traceback.print_exc()


async def play_next(ctx):
    """Play the next song in the queue."""
    queue = get_queue(ctx.guild.id)
    next_song = queue.get_next()
    
    if next_song and ctx.voice_client:
        try:
            data = None
            try:
                data = await extract_info_safe(next_song['url'], download=False)
            except Exception as primary_err:
                print(f"[next] primary extraction failed: {primary_err}")
                vid = extract_video_id(next_song['url'])
                if vid:
                    inv = invidious_api_video(vid)
                    if inv:
                        playable = pick_invidious_audio(inv)
                        if playable:
                            fake_data = {
                                'title': inv.get('title', 'Unknown (Invidious)'),
                                'url': playable,
                                'duration': inv.get('lengthSeconds'),
                            }
                            player = YTDLSource(discord.FFmpegPCMAudio(playable, **ffmpeg_options), data=fake_data)
                            ctx.voice_client.play(player, after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop))
                            await next_song['ctx'].send(f"Now playing (fallback): **{fake_data['title']}**")
                            return
                raise primary_err
            if 'entries' in data:
                data = data['entries'][0]
            playable = select_playable_url(data)
            if not playable:
                raise Exception('No playable format found')
            player = YTDLSource(discord.FFmpegPCMAudio(playable, **ffmpeg_options), data=data)
            ctx.voice_client.play(player, after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop))
            await next_song['ctx'].send(f"Now playing: **{data.get('title', 'Unknown')}**")
        except Exception as e:
            await next_song['ctx'].send(f"⚠️ Skipped: {next_song.get('title','Unknown')} - {str(e)[:90]}")
            await play_next(ctx)


@bot.command(name='pause', help='Pauses the current song')
async def pause(ctx):
    """Pause the current song."""
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        await ctx.send("⏸️ Paused the music!")
    else:
        await ctx.send("No music is currently playing!")


@bot.command(name='resume', help='Resumes the paused song')
async def resume(ctx):
    """Resume the paused song."""
    if ctx.voice_client and ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        await ctx.send("▶️ Resumed the music!")
    else:
        await ctx.send("The music is not paused!")


@bot.command(name='stop', help='Stops the music and clears the queue')
async def stop(ctx):
    """Stop the music and clear the queue."""
    if ctx.voice_client:
        queue = get_queue(ctx.guild.id)
        queue.clear()
        ctx.voice_client.stop()
        await ctx.send("⏹️ Stopped the music and cleared the queue!")
    else:
        await ctx.send("I'm not playing any music!")


@bot.command(name='skip', help='Skips the current song')
async def skip(ctx):
    """Skip the current song."""
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("⏭️ Skipped the current song!")
    else:
        await ctx.send("No music is currently playing!")


@bot.command(name='queue', help='Shows the current music queue')
async def show_queue(ctx):
    """Display the current music queue."""
    queue = get_queue(ctx.guild.id)
    
    if queue.is_empty() and not queue.current:
        await ctx.send("The queue is empty!")
        return

    message = "**Music Queue:**\n"
    
    if queue.current:
        message += f"Now playing: {queue.current.get('title', 'Unknown')}\n\n"
    
    if not queue.is_empty():
        message += "Up next:\n"
        for i, song in enumerate(queue.queue, 1):
            message += f"{i}. {song.get('title', 'Unknown')}\n"
    else:
        message += "No songs in queue."
    
    await ctx.send(message)


@bot.command(name='status', help='Shows bot playback and extraction status')
async def status(ctx):
    queue = get_queue(ctx.guild.id)
    pending = len(queue.queue)
    current = queue.current.get('title') if queue.current else None
    ytdlp_version = getattr(yt_dlp, '__version__', getattr(getattr(yt_dlp, 'version', None), '__version__', 'unknown'))
    report = [
        f"yt-dlp: {ytdlp_version}",
        f"Python: {platform.python_version()}",
        f"Cookies loaded: {COOKIES_LOADED}",
        f"Critical cookies missing: {COOKIE_MISSING_CRITICAL}",
        f"Invidious host: {INVIDIOUS_HOST}",
        f"Current track: {current or 'None'}",
        f"Queue length: {pending}",
        f"Playlist mode: {'fast' if FAST_PLAYLIST_MODE else 'full'}",
        f"Verbose yt-dlp: {VERBOSE_YTDLP}",
    ]
    await ctx.send("Status:\n" + '\n'.join(report))


@bot.command(name='volume', help='Changes the volume (0-100)')
async def volume(ctx, volume: int):
    """Change the player volume."""
    if not ctx.voice_client:
        await ctx.send("I'm not connected to a voice channel!")
        return

    if not 0 <= volume <= 100:
        await ctx.send("Volume must be between 0 and 100!")
        return

    if ctx.voice_client.source:
        ctx.voice_client.source.volume = volume / 100
        await ctx.send(f"🔊 Volume set to {volume}%")
    else:
        await ctx.send("No music is currently playing!")


@bot.event
async def on_command_error(ctx, error):
    """Handle command errors."""
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"Missing argument: {error.param.name}")
    elif isinstance(error, commands.CommandNotFound):
        await ctx.send("Unknown command! Use `!help` to see available commands.")
    else:
        await ctx.send(f"An error occurred: {str(error)}")
        print(f"Error: {error}")


if __name__ == "__main__":
    if not TOKEN:
        print("Error: DISCORD_TOKEN not found in environment variables!")
        print("Please create a .env file with your Discord bot token.")
    else:
        bot.run(TOKEN)
