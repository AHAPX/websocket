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
$ python websocket.py
```

## Command line arguments
- host - host of webserver, default=localhost
- port - port of webseerver, default=9999
- redis-host - host of redis broker, default=locahost
- redis-port - port of redis broker, default=6379
- redis-db - number of redis db, default=0
- channel - redis channel for subscription, default=ws-channel

## Testing
```bash
$ python -m unittest
```

## API
### Server
Webserver subscribes to channel and wait messages. Message must be valid JSON.
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
