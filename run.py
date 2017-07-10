#!/usr/bin/env python3

import asyncio
import configparser
import discord
import json
import random
import os

version = '1.0'

print('Starting discord-mod-mail {}!'.format(version))

client = discord.Client()

config = configparser.ConfigParser()
config.read('config.ini')

client.already_ready = False

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
    client.channel = client.get_channel(config['Main']['channel_id'])
    if not client.channel:
        print('Channel with ID {} not found.'.format(config['Main']['channel_id']))
        await client.close()
    await client.send_message(client.channel, '{0.user} is now ready.'.format(client))
    print('{0.user} is now ready.'.format(client))
    await client.change_presence(game=discord.Game(name=config['Main']['playing']))
    client.already_ready = True


def gen_color(user_id):
    random.seed(user_id)
    c_r = random.randint(0, 255)
    c_g = random.randint(0, 255)
    c_b = random.randint(0, 255)
    return discord.Color((c_r << 16) + (c_g << 8) + c_b)


anti_spam_check = {}


@client.event
async def on_message(message):
    if message.author == client.user:
        return
    if not client.already_ready:
        return
    if isinstance(message.channel, discord.PrivateChannel):
        if message.author.id in ignored_users:
            return
        if message.author.id not in anti_spam_check:
            anti_spam_check[message.author.id] = 0
        anti_spam_check[message.author.id] += 1
        if anti_spam_check[message.author.id] >= int(config['AntiSpam']['messages']):
            if message.author.id not in ignored_users:  # prevent duplicates
                ignored_users.append(message.author.id)
            with open('ignored.json', 'w') as f:
                json.dump(ignored_users, f)
            await client.send_message(client.channel, '{0.id} {0.mention} auto-ignored due to spam. Use `{1}unignore` to reverse.'.format(message.author, config['Main']['command_prefix']))
            return
        embed = discord.Embed(color=gen_color(int(message.author.id)), description=message.content)
        to_send = '{0.id} {0.mention}'.format(message.author)
        await client.send_message(client.channel, to_send, embed=embed)
        if message.attachments:
            attachment_urls = []
            for attachment in message.attachments:
                attachment_urls += "<{}>".format(attachment.url)
            attachment_msg = ", ".join(attachment.urls)
            await client.send_message(client.channel, "Attachments in above message: " + attachment_msg)
        await asyncio.sleep(int(config['AntiSpam']['seconds']))
        anti_spam_check[message.author.id] -= 1
    elif message.channel == client.channel:
        if message.content.startswith(config['Main']['command_prefix']):
            # this might be the wrong way
            command_split = message.content[len(config['Main']['command_prefix']):].strip().split(' ', maxsplit=1)
            command_name = command_split[0]
            command_contents = command_split[1]
            if command_name == 'ignore':
                user_id = command_contents.split(' ', maxsplit=1)[0]
                if user_id in ignored_users:
                    await client.send_message(client.channel, '{0.author.mention} {1} is already ignored.'.format(message, user_id))
                else:
                    ignored_users.append(user_id)
                    with open('ignored.json', 'w') as f:
                        json.dump(ignored_users, f)
                    await client.send_message(client.channel, '{0.author.mention} {1} is now ignored. Messages from this user will not appear. Use `{2}unignore` to reverse.'.format(message, user_id, config['Main']['command_prefix']))
            elif command_name == 'unignore':
                user_id = command_contents.split(' ', maxsplit=1)[0]
                if user_id not in ignored_users:
                    await client.send_message(client.channel, '{0.author.mention} {1} is not ignored.'.format(message, user_id))
                else:
                    ignored_users.remove(user_id)
                    with open('ignored.json', 'w') as f:
                        json.dump(ignored_users, f)
                    await client.send_message(client.channel, '{0.author.mention} {1} is no longer ignored. Messages from this user will appear again. Use `{2}ignore` to reverse.'.format(message, user_id, config['Main']['command_prefix']))
            else:
                for server in client.servers:
                    member = server.get_member(command_name)
                    if member:
                        embed = discord.Embed(color=gen_color(int(command_name)), description=command_contents)
                        if config['Main']['anonymous_staff']:
                            to_send = 'Staff reply: '
                        else:
                            to_send = '{}: '.format(message.author.mention)
                        to_send += command_contents
                        try:
                            await client.send_message(member, to_send)
                            header_message = '{0.author.mention} replying to {1.id} {1.mention}'.format(message, member)
                            if member.id in ignored_users:
                                header_message += ' (replies ignored)'
                            await client.send_message(client.channel, header_message, embed=embed)
                            await client.delete_message(message)
                        except discord.errors.Forbidden:
                            await client.send_message(client.channel, '{0.author.mention} {1.mention} has disabled DMs or is not in a shared server.'.format(message, member))
                        break


client.run(config['Main']['token'])
