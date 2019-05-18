# discord-mod-mail

Simple mod-mail system for Discord. See `config.ini.example` for configuration, copy to `config.ini` to use. Python 3.6 or later is required (3.6.8 tested). (Windows Installer https://www.python.org/ftp/python/3.6.8/python-3.6.8-amd64.exe)
Discord.py (Windows Installer) [install.zip](https://github.com/ihaveamac/discord-mod-mail/files/3194508/install.zip)

Command usage to reply is only limited to the channel used for mod-mail, and not to users with specific roles. Don't allow everyone to send messages to the mod-mail channel because there is no role-check.

If you are adding a new bot to your server, you can use this link(replace client_id):
* `https://discordapp.com/oauth2/authorize?&client_id=<client_id>&scope=bot&permissions=11264`

This automatically selects Read Messages, Send Messages, and Manage Messages. You may want to manually add this bot to your mod-mail channel though, if it is private.

## Command usage
Assuming default prefix `?` is used.
* `?<userid> <message>` - send message to user with userid
* `?m` - @mention last user who contacted mod-mail
* `?ignore <userid> [reason]` - ignore messages from userid with optional reason
* `?qignore <userid>` - quiet ignore, don't notify user
* `?unignore <userid>` - don't ignore messages from userid

## License
MIT license
