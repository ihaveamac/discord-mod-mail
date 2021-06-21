# discord-mod-mail

Simple mod-mail system for Discord. See `config.ini.example` for configuration, copy to `config.ini` to use.

Python 3.6 or later is required. discord.py 1.5 or later is required.

Command usage to reply is only limited to the channel used for mod-mail, and not to users with specific roles. Don't allow everyone to send messages to the mod-mail channel because there is no role-check.

If you are adding a new bot to your server, you can use this link(replace client\_id):
* `https://discordapp.com/oauth2/authorize?&client_id=<client_id>&scope=bot`

Make sure to add the bot to your private mod-mail channel with Read Messages, Send Messages, and Manage Messages.

## Main features
* Works through DMs and a private mod-mail channel
* Simple permission setup: anyone who can send to the private channel can reply
* Easy replies: messages sent to the bot via DM have the user ID in the message to make it easy to copy, especially for mobile users
* Staff replies are anonymous (can be toggled in config)
* Replies posted to the channel are re-posted by the bot and deleted (intended to prevent staff from modifying them later)
* Supports attachments
* Supports ignoring users, and auto-ignoring spammers

## Command usage
Assuming default prefix `?` is used.
* `?<userid> <message>` - send message to user with userid (a space between the `?` and id is acceptable)
* `?r <message>` - reply to last user who contacted mod-mail
* `?m` - get @mention for the last user who contacted mod-mail
* `?ignore <userid> [reason]` - ignore messages from userid with optional reason, notifies user
* `?qignore <userid>` - quiet ignore, don't notify user
* `?unignore <userid>` - stop ignoring messages from userid

## Docker
A [Docker image](https://hub.docker.com/repository/docker/ianburgwin/discord-mod-mail) is provided for the latest release. To run, make sure to mount a path or volume to `/home/modmail/data`. `config.ini` must be placed in this directory, and must be writable for `modmail_data.sqlite` to be added. The uid of the container user is 3913.

Example:
```bash
docker run -v /opt/modmail-data:/home/modmail/data ianburgwin/discord-mod-mail:latest
```

## License
MIT license
