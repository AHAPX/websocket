import sys
import traceback
import asyncio
import json
import logging
from functools import partial
import argparse
import configparser

import websockets
from subscriber import add_params, handlers


logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)
logger.addHandler(logging.StreamHandler())


class Client():
    socket = None
    tags = []

    def __init__(self, socket):
        self.socket = socket

    def send(self, message):
        if self.is_active():
            if not isinstance(message, str):
                try:
                    message = json.dumps(message)
                except TypeError:
                    message = str(message)
            yield from self.socket.send(message)

    def init_tags(self, tags):
        self.tags = tags
        logger.info('set tags "{}"'.format(tags))

    def is_active(self):
        return self.socket and self.socket.open

    def is_tag(self, tag):
        return tag in self.tags

    @property
    def name(self):
        return ', '.join(self.tags) if self.tags else 'unknown'


class Clients():
    clients = []

    def add_client(self, client):
        if client.is_active():
            self.clients.append(client)
            logger.debug('new client connected')

    def send(self, message, tags=[]):
        if tags:
            clients = []
            for client in self.clients:
                for tag in tags:
                    if client.is_tag(tag):
                        clients.append(client)
                        break
        else:
            clients = self.clients
        for client in clients:
            if not client.is_active():
                self.clients.remove(client)
            yield from client.send(message)


class WebSocketServer():

    def __init__(self):
        self.clients = Clients()

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


def redis_receiver(message, server):
    try:
        msg = json.loads(message)
    except ValueError:
        logger.warning('"{}" is not valid json'.format(message))
    else:
        logger.info('send: {} - "{}"'.format(', '.join(msg.get('tags') or ['ALL']), msg['message']))
        yield from server.clients.send(msg.get('message'), msg.get('tags', []))
    yield


def run(server_handler, redis_handler, host, port, rhost, rport, rdb, rchannel):
    server = WebSocketServer()
    start_server = websockets.serve(
        partial(server_handler, server), host, port
    )
    logger.info('websocket server started')
    asyncio.async(redis_handler(add_params(server)(redis_receiver),
        host=rhost, port=rport, db=rdb, channel=rchannel))
    loop = asyncio.get_event_loop()
    loop.run_until_complete(start_server)
    loop.run_forever()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='simple websocket server', add_help=False)
    parser.add_argument('--help', action='help', help='show this help message and exit')
    parser.add_argument('--config', '-c', type=str, help='config file')
    parser.add_argument('--host', '-h', type=str, help='host', default='localhost')
    parser.add_argument('--port', '-p', type=int, help='port', default=9999)
    parser.add_argument('--rhost', type=str, help='redis host', default='localhost')
    parser.add_argument('--rport', type=int, help='redis port', default=6379)
    parser.add_argument('--rdb', type=int, help='redis db', default=0)
    parser.add_argument('--rchannel', type=str, help='redis channel', default='ws-channel')
    parser.add_argument('--debug', '-D', help='debug mode', action='store_true', default=False)

    args = parser.parse_args()

    settings = vars(args)
    if args.config:
        config = configparser.ConfigParser()
        config.read(args.config)
        settings['host'] = config.get('main', 'host', fallback=settings['host'])
        settings['port'] = config.getint('main', 'port', fallback=settings['port'])
        settings['debug'] = config.get('main', 'debug', fallback=settings['debug'])
        settings['rhost'] = config.get('redis', 'host', fallback=settings['rhost'])
        settings['rport'] = config.getint('redis', 'port', fallback=settings['rport'])
        settings['rdb'] = config.getint('redis', 'db', fallback=settings['rdb'])
        settings['rchannel'] = config.get('redis', 'channel', fallback=settings['rchannel'])

    if settings['debug']:
        logger.setLevel(logging.DEBUG)

    run(server_handler=server_handler,
        redis_handler=handlers.redis,
        host=settings['host'],
        port=settings['port'],
        rhost=settings['rhost'],
        rport=settings['rport'],
        rdb=settings['rdb'],
        rchannel=settings['rchannel'])
