#!/usr/bin/env python3

import asyncio
import configparser
import random
import sqlite3
from subprocess import check_output, CalledProcessError
from sys import version_info
from tempfile import TemporaryFile
from typing import TYPE_CHECKING

import discord

if TYPE_CHECKING:
    from typing import List, Optional, Tuple

DATABASE_FILE = 'modmail_data.sqlite'

version = '1.3b1'

pyver = '{0[0]}.{0[1]}.{0[2]}'.format(version_info)
if version_info[3] != 'final':
    pyver += '{0[3][0]}{0[4]}'.format(version_info)

try:
    commit = check_output(['git', 'rev-parse', 'HEAD']).decode('ascii')[:-1]
except CalledProcessError as e:
    print(f'Checking for git commit failed: {type(e).__name__} {e}')
    commit = '<unknown>'
except FileNotFoundError as e:
    print('git not found, not showing commit')
    commit = '<unknown>'

try:
    branch = check_output(['git', 'rev-parse', '--abbrev-ref', 'HEAD']).decode()[:-1]
except CalledProcessError as e:
    print(f'Checking for git branch failed: {type(e).__name__} {e}')
    branch = '<unknown>'
except FileNotFoundError as e:
    print('git not found, not showing branch')
    branch = '<unknown>'

print(f'Starting discord-mod-mail {version}!')

config = configparser.ConfigParser()
config.read('config.ini')

client = discord.Client(activity=discord.Game(name=config['Main']['playing']), max_messages=100)
client.channel: discord.TextChannel

client.already_ready = False

client.last_id = 'uninitialized'

db = sqlite3.connect(DATABASE_FILE)
with db:
    if db.execute('PRAGMA user_version').fetchone()[0] == 0:
        print('Setting up', DATABASE_FILE)
        db.execute('PRAGMA application_id = 0x4D6F644D')  # ModM
        db.execute('PRAGMA user_version = 1')
        with open('schema.sql', 'r', encoding='utf-8') as f:
            db.executescript(f.read())

        try:
            print('Converting ignored.json')
            with open('ignored.json', 'r') as f:
                # only importing json if needed
                import json
                ignored = json.load(f)
                del json

            db.executemany('INSERT INTO ignored VALUES (?, 1, NULL)', ((x,) for x in ignored))
            print('Done!')

        except FileNotFoundError:
            pass


def is_ignored(user_id: int) -> 'Optional[Tuple[int, Optional[str]]]':
    with db:
        return db.execute('SELECT quiet, reason FROM ignored WHERE user_id = ?', (user_id,)).fetchone()


def add_ignore(user_id: int, reason: str = None, is_quiet: bool = False) -> bool:
    try:
        with db:
            print(user_id)
            db.execute('INSERT INTO ignored VALUES (?, ?, ?)', (user_id, is_quiet, reason))
            return True
    except sqlite3.IntegrityError:
        return False


def remove_ignore(user_id: int) -> int:
    with db:
        return db.execute('DELETE FROM ignored WHERE user_id = ?', (user_id,)).rowcount


@client.event
async def on_ready():
    if client.already_ready:
        return
    client.channel = client.get_channel(int(config['Main']['channel_id']))
    if not client.channel:
        print(f'Channel with ID {config["Main"]["channel_id"]} not found.')
        await client.close()
    print('{0.user} is now ready.'.format(client))
    startup_message = (f'{client.user} is now ready. Version {version}, branch {branch}, commit {commit[0:7]}, '
                       f'Python {pyver}')
    await client.channel.send(startup_message)
    print(startup_message)
    client.already_ready = True


def gen_color(user_id):
    random.seed(user_id)
    c_r = random.randint(0, 255)
    c_g = random.randint(0, 255)
    c_b = random.randint(0, 255)
    return discord.Color((c_r << 16) + (c_g << 8) + c_b)


anti_spam_check = {}

anti_duplicate_replies = {}


@client.event
async def on_typing(channel, user, when):
    if isinstance(channel, discord.DMChannel):
        if not is_ignored(user.id):
            await client.channel.trigger_typing()


@client.event
async def on_message(message):
    if client.channel.guild.me.activity is None or client.channel.guild.me.activity.name != config['Main']['playing']:
        await client.change_presence(activity=discord.Game(name=config['Main']['playing']))
    author = message.author
    if author == client.user:
        return
    if not client.already_ready:
        return

    if type(message.channel) is discord.DMChannel:
        if is_ignored(author.id):
            return
        if author.id not in anti_spam_check:
            anti_spam_check[author.id] = 0

        anti_spam_check[author.id] += 1
        if anti_spam_check[author.id] >= int(config['AntiSpam']['messages']):
            add_ignore(author.id, 'Automatic anti-spam ignore')
            await client.channel.send(
                f'{author.id} {author.mention} auto-ignored due to spam. '
                f'Use `{config["Main"]["command_prefix"]}unignore` to reverse.')
            return

        # for the purpose of nicknames, if anys
        for server in client.guilds:
            member = server.get_member(author.id)
            if member:
                author = member
            break

        embed = discord.Embed(color=gen_color(int(author.id)), description=message.content)
        if isinstance(author, discord.Member) and author.nick:
            author_name = f'{author.nick} ({author})'
        else:
            author_name = str(author)
        embed.set_author(name=author_name, icon_url=author.avatar_url if author.avatar else author.default_avatar_url)

        to_send = f'{author.id}'
        if message.attachments:
            attachment_urls = []
            for attachment in message.attachments:
                attachment_urls.append(f'[{attachment.filename}]({attachment.url}) '
                                       f'({attachment.size} bytes)')
            attachment_msg = '\N{BULLET} ' + '\n\N{BULLET} '.join(attachment_urls)
            embed.add_field(name='Attachments', value=attachment_msg, inline=False)
        await client.channel.send(to_send, embed=embed)
        client.last_id = author.id
        await asyncio.sleep(int(config['AntiSpam']['seconds']))
        anti_spam_check[author.id] -= 1

    elif message.channel == client.channel:
        if message.content.startswith(config['Main']['command_prefix']):
            # this might be the wrong way
            command_split = message.content[len(config['Main']['command_prefix']):].strip().split(' ', maxsplit=1)
            command_name = command_split[0]
            try:
                command_contents = command_split[1]
            except IndexError:
                command_contents = ''

            if command_name == 'ignore' or command_name == 'qignore':
                if not command_contents:
                    await client.channel.send('Did you forget to enter an ID?')
                else:
                    try:
                        command_args = command_contents.split(' ', maxsplit=1)
                        user_id = int(command_args[0])
                        try:
                            reason = command_args[1]
                        except IndexError:
                            reason = None
                    except ValueError:
                        await client.channel.send('Could not convert to int.')
                        return
                    is_quiet = command_name == 'qignore'
                    if add_ignore(user_id, reason, is_quiet):
                        if not is_quiet:
                            to_send = 'Your messages are being ignored by staff.'
                            if reason:
                                to_send += ' Reason: ' + reason
                            for server in client.guilds:
                                member = server.get_member(user_id)
                                if member:
                                    try:
                                        await member.send(to_send)
                                    except discord.errors.Forbidden:
                                        await client.channel.send(f'{member.mention} has disabled DMs or is not in a '
                                                                  f'shared server, not sending reason.')
                                    break
                            else:
                                await client.channel.send('Failed to find user with ID, not sending reason.')
                        await client.channel.send(
                            f'{author.mention} {user_id} is now ignored. Messages from this user will not appear. '
                            f'Use `{config["Main"]["command_prefix"]}unignore` to reverse.')
                    else:
                        await client.channel.send(f'{author.mention} {user_id} is already ignored.')

            elif command_name == 'unignore':
                if not command_contents:
                    await client.channel.send('Did you forget to enter an ID?')
                else:
                    try:
                        user_id = int(command_contents.split(' ', maxsplit=1)[0])
                    except ValueError:
                        await client.channel.send('Could not convert to int.')
                        return
                    ignored = is_ignored(user_id)
                    if ignored:
                        is_quiet = ignored[0]
                        if not is_quiet:
                            to_send = 'Your messages are no longer being ignored by staff.'
                            for server in client.guilds:
                                member = server.get_member(user_id)
                                if member:
                                    try:
                                        await member.send(to_send)
                                    except discord.errors.Forbidden:
                                        await client.channel.send(f'{member.mention} has disabled DMs or is not in '
                                                                  f'a shared server, not sending notification.')
                                    break
                            else:
                                await client.channel.send('Failed to find user with ID, not sending notification.')
                    if remove_ignore(user_id):
                        await client.channel.send(
                            f'{author.mention} {user_id} is no longer ignored. Messages from this user will appear '
                            f'again. Use `{config["Main"]["command_prefix"]}ignore` to reverse.')
                    else:
                        await client.channel.send(f'{author.mention} {user_id} is not ignored.')

            elif command_name == 'fixgame':
                await client.change_presence(activity=None)
                await client.change_presence(activity=discord.Game(name=config['Main']['playing']))
                await client.channel.send('Game presence re-set.')

            elif command_name == 'm':
                await client.channel.send(f'{client.last_id} <@!{client.last_id}>')
            
            elif command_name == 'r':
                if command_name not in anti_duplicate_replies:
                    anti_duplicate_replies[command_name] = False
                elif anti_duplicate_replies[command_name]:
                    await client.channel.send(
                                              f'{author.mention} Your message was not sent to prevent multiple replies '
                                              f'to the same person within 2 seconds.')
                    return
                anti_duplicate_replies[command_name] = True
                if not command_contents:
                    await client.channel.send('Did you forget to enter a message?')
                else:
                    for server in client.guilds:
                        member = server.get_member(client.last_id)
                        if member:
                            attachments = []
                            try:
                                progress_msg = None
                                if message.attachments:
                                    size_limit = 0x800000
                                    size_diff = 0x800

                                    # first check the size of all attachments
                                    # the 0x800 number is arbitrary, just in case
                                    # in reality, the file size needs to be like 0x200 smaller than the supposed limit
                                    error_messages = []
                                    warning_messages = []
                                    for a in message.attachments:
                                        if a.size > size_limit:
                                            error_messages.append(f'`{discord.utils.escape_markdown(a.filename)}` '
                                                                  f'is too large to send in a direct message.')
                                        elif a.size > size_limit - 0x1000:
                                            warning_messages.append(f'`{discord.utils.escape_markdown(a.filename)}` '
                                                                    f'is very close to the file size limit of the '
                                                                    f'destination. It may fail to send.')

                                    if error_messages:
                                        final = '\n'.join(error_messages)
                                        final += f'\nLimit: {size_limit} bytes ({size_limit / (1024 * 1024):.02f} MiB)'
                                        final += f'\nRecommended Maximum: {size_limit - size_diff} bytes ' \
                                                 f'({(size_limit - size_diff) / (1024 * 1024):.02f} MiB)'
                                        await client.channel.send(final)
                                        break

                                    if warning_messages:
                                        final = '\n'.join(warning_messages)
                                        final += f'\nLimit: {size_limit} bytes ({size_limit / (1024 * 1024):.02f} MiB)'
                                        final += f'\nRecommended Maximum: {size_limit - size_diff} bytes ' \
                                                 f'({(size_limit - size_diff) / (1024 * 1024):.02f} MiB)'
                                        await client.channel.send(final)

                                    count = len(message.attachments)
                                    progress_msg = await client.channel.send(f'Downloading attachments... 0/{count}')
                                    for idx, a in enumerate(message.attachments, 1):
                                        tf = TemporaryFile()
                                        await a.save(tf, seek_begin=True)
                                        attachments.append(discord.File(tf, a.filename))
                                        await progress_msg.edit(content=f'Downloading attachments... {idx}/{count}')

                                embed = discord.Embed(color=gen_color(int(client.last_id)), description=command_contents)
                                if config['Main']['anonymous_staff']:
                                    to_send = 'Staff reply: '
                                else:
                                    to_send = f'{author.mention}: '
                                to_send += command_contents
                                try:
                                    if progress_msg:
                                        await progress_msg.edit(content=f'Sending message with {len(attachments)} '
                                                                        f'attachments...')
                                    staff_msg = await member.send(to_send, files=attachments)
                                    header_message = f'{author.mention} replying to {member.id} {member.mention}'
                                    if is_ignored(member.id):
                                        header_message += ' (replies ignored)'

                                    # add attachment links to mod-mail message
                                    if staff_msg.attachments:
                                        attachment_urls = []
                                        for attachment in staff_msg.attachments:
                                            attachment_urls.append(f'[{attachment.filename}]({attachment.url}) '
                                                                   f'({attachment.size} bytes)')
                                        attachment_msg = '\N{BULLET} ' + '\n\N{BULLET} '.join(attachment_urls)
                                        embed.add_field(name='Attachments', value=attachment_msg, inline=False)

                                    await client.channel.send(header_message, embed=embed)
                                    if progress_msg:
                                        await progress_msg.delete()
                                    await message.delete()

                                except discord.errors.Forbidden:
                                    await client.channel.send(f'{author.mention} {member.mention} has disabled DMs '
                                                              f'or is not in a shared server.')
                                break
                            finally:
                                for attach in attachments:
                                    attach.close()
                    else:
                        await client.channel.send(f'Failed to find user with ID {client.last_id}')
                await asyncio.sleep(2)
                anti_duplicate_replies[command_name] = False

            else:
                if command_name not in anti_duplicate_replies:
                    anti_duplicate_replies[command_name] = False
                elif anti_duplicate_replies[command_name]:
                    await client.channel.send(
                                              f'{author.mention} Your message was not sent to prevent multiple replies '
                                              f'to the same person within 2 seconds.')
                    return
                anti_duplicate_replies[command_name] = True
                if not command_contents:
                    await client.channel.send('Did you forget to enter a message?')
                else:
                    for server in client.guilds:
                        member = server.get_member(int(command_name))
                        if member:
                            attachments = []
                            try:
                                progress_msg = None
                                if message.attachments:
                                    size_limit = 0x800000
                                    size_diff = 0x800

                                    # first check the size of all attachments
                                    # the 0x800 number is arbitrary, just in case
                                    # in reality, the file size needs to be like 0x200 smaller than the supposed limit
                                    error_messages = []
                                    warning_messages = []
                                    for a in message.attachments:
                                        if a.size > size_limit:
                                            error_messages.append(f'`{discord.utils.escape_markdown(a.filename)}` '
                                                                  f'is too large to send in a direct message.')
                                        elif a.size > size_limit - 0x1000:
                                            warning_messages.append(f'`{discord.utils.escape_markdown(a.filename)}` '
                                                                    f'is very close to the file size limit of the '
                                                                    f'destination. It may fail to send.')

                                    if error_messages:
                                        final = '\n'.join(error_messages)
                                        final += f'\nLimit: {size_limit} bytes ({size_limit / (1024 * 1024):.02f} MiB)'
                                        final += f'\nRecommended Maximum: {size_limit - size_diff} bytes ' \
                                                 f'({(size_limit - size_diff) / (1024 * 1024):.02f} MiB)'
                                        await client.channel.send(final)
                                        break

                                    if warning_messages:
                                        final = '\n'.join(warning_messages)
                                        final += f'\nLimit: {size_limit} bytes ({size_limit / (1024 * 1024):.02f} MiB)'
                                        final += f'\nRecommended Maximum: {size_limit - size_diff} bytes ' \
                                                 f'({(size_limit - size_diff) / (1024 * 1024):.02f} MiB)'
                                        await client.channel.send(final)

                                    count = len(message.attachments)
                                    progress_msg = await client.channel.send(f'Downloading attachments... 0/{count}')
                                    for idx, a in enumerate(message.attachments, 1):
                                        tf = TemporaryFile()
                                        await a.save(tf, seek_begin=True)
                                        attachments.append(discord.File(tf, a.filename))
                                        await progress_msg.edit(content=f'Downloading attachments... {idx}/{count}')

                                embed = discord.Embed(color=gen_color(int(command_name)), description=command_contents)
                                if config['Main']['anonymous_staff']:
                                    to_send = 'Staff reply: '
                                else:
                                    to_send = f'{author.mention}: '
                                to_send += command_contents
                                try:
                                    if progress_msg:
                                        await progress_msg.edit(content=f'Sending message with {len(attachments)} '
                                                                        f'attachments...')
                                    staff_msg = await member.send(to_send, files=attachments)
                                    header_message = f'{author.mention} replying to {member.id} {member.mention}'
                                    if is_ignored(member.id):
                                        header_message += ' (replies ignored)'

                                    # add attachment links to mod-mail message
                                    if staff_msg.attachments:
                                        attachment_urls = []
                                        for attachment in staff_msg.attachments:
                                            attachment_urls.append(f'[{attachment.filename}]({attachment.url}) '
                                                                   f'({attachment.size} bytes)')
                                        attachment_msg = '\N{BULLET} ' + '\n\N{BULLET} '.join(attachment_urls)
                                        embed.add_field(name='Attachments', value=attachment_msg, inline=False)

                                    await client.channel.send(header_message, embed=embed)
                                    if progress_msg:
                                        await progress_msg.delete()
                                    await message.delete()

                                except discord.errors.Forbidden:
                                    await client.channel.send(f'{author.mention} {member.mention} has disabled DMs '
                                                              f'or is not in a shared server.')
                                break
                            finally:
                                for attach in attachments:
                                    attach.close()
                    else:
                        await client.channel.send(f'Failed to find user with ID {command_name}')
                await asyncio.sleep(2)
                anti_duplicate_replies[command_name] = False

client.run(config['Main']['token'])
