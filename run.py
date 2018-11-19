#!/usr/bin/env python3

import asyncio
import configparser
import json
import random
import os
from subprocess import check_output, CalledProcessError
from sys import version_info

import discord

version = '1.2.dev0'

pyver = '{0[0]}.{0[1]}.{0[2]}'.format(version_info)
if version_info[3] != 'final':
    pyver += '{0[3][0]}{0[4]}'.format(version_info)

try:
    commit = check_output(['git', 'rev-parse', 'HEAD']).decode('ascii')[:-1]
except CalledProcessError as e:
    print(f'Checking for git commit failed: {type(e).__name__} {e}')
    commit = '<unknown>'

try:
    branch = check_output(['git', 'rev-parse', '--abbrev-ref', 'HEAD']).decode()[:-1]
except CalledProcessError as e:
    print(f'Checking for git branch failed: {type(e).__name__} {e}')
    branch = '<unknown>'

print(f'Starting discord-mod-mail {version}!')

config = configparser.ConfigParser()
config.read('config.ini')

client = discord.Client(activity=discord.Game(name=config['Main']['playing']))

client.already_ready = False

client.last_id = 'uninitialized'

# to be filled from ignored.json later
ignored_users = []

if os.path.isfile('ignored.json'):
    with open('ignored.json', 'r') as f:
        ignored_users = json.load(f)
else:
    with open('ignored.json', 'w') as f:
        json.dump(ignored_users, f)


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
async def on_message(message):
    if client.channel.guild.me.activity is None or client.channel.guild.me.activity.name != config['Main']['playing']:
        await client.change_presence(activity=discord.Game(name=config['Main']['playing']))
    author = message.author
    if author == client.user:
        return
    if not client.already_ready:
        return

    if type(message.channel) is discord.DMChannel:
        if author.id in ignored_users:
            return
        if author.id not in anti_spam_check:
            anti_spam_check[author.id] = 0

        anti_spam_check[author.id] += 1
        if anti_spam_check[author.id] >= int(config['AntiSpam']['messages']):
            if author.id not in ignored_users:  # prevent duplicates
                ignored_users.append(author.id)
            with open('ignored.json', 'w') as f:
                json.dump(ignored_users, f)
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
                attachment_urls.append(f'[{attachment.filename}]({attachment.url})')
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

            if command_name == 'ignore':
                if not command_contents:
                    await client.channel.send('Did you forget to enter an ID?')
                else:
                    user_id = command_contents.split(' ', maxsplit=1)[0]
                    if user_id in ignored_users:
                        await client.channel.send(f'{author.mention} {user_id} is already ignored.')
                    else:
                        ignored_users.append(user_id)
                        with open('ignored.json', 'w') as f:
                            json.dump(ignored_users, f)
                        await client.channel.send(
                            f'{author.mention} {user_id} is now ignored. Messages from this user will not appear. '
                            f'Use `{config["Main"]["command_prefix"]}unignore` to reverse.')

            elif command_name == 'unignore':
                if not command_contents:
                    await client.channel.send('Did you forget to enter an ID?')
                else:
                    user_id = command_contents.split(' ', maxsplit=1)[0]
                    if user_id not in ignored_users:
                        await client.channel.send(f'{author.mention} {user_id} is not ignored.')
                    else:
                        ignored_users.remove(user_id)
                        with open('ignored.json', 'w') as f:
                            json.dump(ignored_users, f)
                        await client.channel.send(
                            f'{author.mention} {user_id} is no longer ignored. Messages from this user will appear '
                            f'again. Use `{config["Main"]["command_prefix"]}ignore` to reverse.')

            elif command_name == 'fixgame':
                await client.change_presence(activity=None)
                await client.change_presence(activity=discord.Game(name=config['Main']['playing']))
                await client.channel.send('Game presence re-set.')

            elif command_name == 'm':
                await client.channel.send(f'{client.last_id} <@!{client.last_id}>')

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
                            embed = discord.Embed(color=gen_color(int(command_name)), description=command_contents)
                            if config['Main']['anonymous_staff']:
                                to_send = 'Staff reply: '
                            else:
                                to_send = f'{author.mention}: '
                            to_send += command_contents
                            try:
                                await member.send(to_send)
                                header_message = f'{author.mention} replying to {member.id} {member.mention}'
                                if member.id in ignored_users:
                                    header_message += ' (replies ignored)'
                                await client.channel.send(header_message, embed=embed)
                                await message.delete()
                            except discord.errors.Forbidden:
                                await client.channel.send(
                                    f'{author.mention} {member.mention} has disabled DMs or is not in a shared server.')
                            break
                    else:
                        await client.channel.send(f'Failed to find user with ID {command_name}')
                await asyncio.sleep(2)
                anti_duplicate_replies[command_name] = False

client.run(config['Main']['token'])
