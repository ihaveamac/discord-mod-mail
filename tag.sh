#!/bin/sh
for f in 1 1.3 1.3.13
do
	echo "Tagging latest -> $f"
	docker tag ianburgwin/discord-mod-mail:latest ianburgwin/discord-mod-mail:$f
done
