# websocket

## Description
Simple async websocket server, using redis as broker.

## Requirements
- [python 3.4+](https://www.python.org/download/releases/3.4.0/)
- [redis](http://redis.io/download)

## Installation
```bash
$ git clone https://github.com/AHAPX/websocket
$ cd websocket
$ pip install -r requirements.txt
```

## Usage
```bash
$ python websocket.py -c ~/websocket.cfg
```

## Config file
Config has [ini format](https://en.wikipedia.org/wiki/INI_file), i.e.

```ini
[main]
host = localhost
port = 9998
debug = false

[redis]
host = localhost
port = 6379
db = 1
channel = ws-channel
```

## Command line arguments
- config - path to [config file](#config-file)
- host - host of websocket, default=localhost
- port - port of websocket, default=9999
- rhost - host of redis broker, default=locahost
- rport - port of redis broker, default=6379
- rdb - number of redis db, default=0
- rchannel - redis channel for subscription, default=ws-channel
- debug - debug mode

## Testing
```bash
$ python -m unittest
```

## API
### Server
Websocket server subscribes to channel and wait messages. Message must be valid JSON.
It should consist keys:
- message - required, text or JSON
- tags - list of tags, if it exists, websocket will send message only for clients with any tag from list

### Client
#### Test connection
Send "ping" and you will receive "pong", if connection is ok

#### Subscribe to tags
When connection is established client should send its tags, i.e.
```json
{
  "tags": ["tag1", "tag2"],
}
```
After that if server sends message to *tag1*, your client will receive it.
