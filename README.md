# discord-mod-mail

Simple mod-mail system for Discord. See `config.ini.example` for configuration, copy to `config.ini` to use.

Python 3.6 or later is required. discord.py 1.5 or later is required.

Command usage to reply is only limited to the channel used for mod-mail, and not to users with specific roles. Don't allow everyone to send messages to the mod-mail channel because there is no role-check.

If you are adding a new bot to your server, you can use this link(replace client_id):
* `https://discordapp.com/oauth2/authorize?&client_id=<client_id>&scope=bot`

Make sure to add the bot to your private mod-mail channel with Read Messages, Send Messages, and Manage Messages.

## Command usage
Assuming default prefix `?` is used.
* `?<userid> <message>` - send message to user with userid
* `?r <message>` - reply to last user who contacted mod-mail
* `?m` - get @mention for the last user who contacted mod-mail
* `?ignore <userid> [reason]` - ignore messages from userid with optional reason
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
