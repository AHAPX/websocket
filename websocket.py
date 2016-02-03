import sys
import traceback
import asyncio
import json
import logging
from functools import partial
import argparse
import configparser

import websockets
import asyncio_redis


logger = logging.getLogger(__name__)


class Client():
    _socket = None
    _tags = []

    def __init__(self, socket):
        self._socket = socket

    def send(self, message):
        if self.is_active():
            if not isinstance(message, str):
                try:
                    message = json.dumps(message)
                except:
                    message = str(message)
            yield from self._socket.send(message)

    def init_tags(self, tags):
        self._tags = tags

    def is_active(self):
        return self._socket and self._socket.open

    def is_tag(self, tag):
        return tag in self._tags

    @property
    def name(self):
        return ', '.join(self._tags)


class Clients():
    _clients = []

    def add_client(self, client):
        if client.is_active():
            self._clients.append(client)

    def send(self, message, tags=[]):
        if tags:
            clients = []
            for client in self._clients:
                for tag in tags:
                    if client.is_tag(tag):
                        clients.append(client)
                        break
        else:
            clients = self._clients
        for client in clients:
            if not client.is_active():
                self._clients.remove(client)
            yield from client.send(message)


class WebSocketServer():
    server_handler, broker_handler = None, None

    def __init__(self, server_handler, broker_handler, redis_host, redis_port, redis_db, channel):
        self.clients = Clients()
        self.server_handler = server_handler
        self.broker_handler = broker_handler
        self.channel = channel
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.redis_db = redis_db

    def run(self, host, port):
        start_server = websockets.serve(
            partial(self.server_handler, self), host, port
        )
        logger.info('websocket server started')
        asyncio.async(self.broker_handler(self))
        loop = asyncio.get_event_loop()
        loop.run_until_complete(start_server)
        loop.run_forever()

    def receiver(self, client, message):
        try:
            msg = json.loads(message)
        except ValueError:
            msg = {'message': message}
        tags = msg.get('tags')
        if tags:
            if not isinstance(tags, (list, tuple)):
                tags = [tags]
            client.init_tags(tags)


@asyncio.coroutine
def server_handler(server, websocket, path):
    client = Client(websocket)
    server.clients.add_client(client)
    while client.is_active():
        try:
            message = yield from websocket.recv()
            if message == 'ping':
                logger.debug('ping from {}'.format(client.name))
                yield from client.send('pong')
            else:
                logger.info('received: {}'.format(message))
            if message is None:
                break
            yield server.receiver(client, message)
        except websockets.ConnectionClosed:
            break
        except Exception as exc:
            logger.error('\n'.join(traceback.format_tb(sys.exc_info()[2])))


@asyncio.coroutine
def redis_handler(server):
    connection = yield from asyncio_redis.Connection.create(
        host=server.redis_host,
        port=server.redis_port,
        db=server.redis_db
    )
    subscriber = yield from connection.start_subscribe()
    yield from subscriber.subscribe([server.channel])
    while True:
        try:
            pub = yield from subscriber.next_published()
            message = json.loads(pub.value)
            logger.info('send: {} - "{}"'.format(', '.join(message['tags']) if 'tags' in message else 'ALL', message['message']))
            tags = message['tags'] if 'tags' in message else []
            yield from server.clients.send(message['message'], tags)
        except Exception as exc:
            logger.error('\n'.join(traceback.format_tb(sys.exc_info()[2])))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='simple websocket server', add_help=False)
    parser.add_argument('--help', action='help', help='show this help message and exit')
    parser.add_argument('--config', '-c', type=str, help='config file')
    parser.add_argument('--host', '-h', type=str, help='host', default='localhost')
    parser.add_argument('--port', '-p', type=int, help='port', default=9999)
    parser.add_argument('--redis-host', type=str, help='redis host', default='localhost')
    parser.add_argument('--redis-port', type=int, help='redis port', default=6379)
    parser.add_argument('--redis-db', type=int, help='redis db', default=0)
    parser.add_argument('--channel', type=str, help='redis channel', default='ws-channel')
    args = parser.parse_args()

    settings = vars(args)
    if args.config:
        config = configparser.ConfigParser()
        config.read(args.config)
        settings['host'] = config.get('main', 'host', fallback=settings['host'])
        settings['port'] = config.getint('main', 'port', fallback=settings['port'])
        settings['redis_host'] = config.get('redis', 'host', fallback=settings['redis_host'])
        settings['redis_port'] = config.getint('redis', 'port', fallback=settings['redis_port'])
        settings['redis_db'] = config.getint('redis', 'db', fallback=settings['redis_db'])
        settings['channel'] = config.get('redis', 'channel', fallback=settings['channel'])

    WebSocketServer(
        server_handler=server_handler,
        broker_handler=redis_handler,
        redis_host=settings['redis_host'],
        redis_port=settings['redis_port'],
        redis_db=settings['redis_db'],
        channel=settings['channel'],
    ).run(settings['host'], settings['port'])
