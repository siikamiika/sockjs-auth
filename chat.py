# -*- coding: utf-8 -*-
import tornado.ioloop
import tornado.web
import sockjs.tornado
import json
import time
import datetime
from collections import deque


class IndexHandler(tornado.web.RequestHandler):
    """Regular HTTP handler to serve the chatroom page"""
    def get(self):
        self.render('index.html')

class Message(object):
    """Forms a JSON string from data"""
    def __init__(self, message={}, verifiednick=None):
        """Parse message"""
        try:
            self.message = json.loads(message)
        except (ValueError, TypeError):
            # Handle invalid JSON
            self.message = {}
        self.body = self.message.get('body')
        self.passwd = self.message.get('passwd')
        self.room = self.message.get('room')
        self.action = self.message.get('action')
        if verifiednick is None:
            self.nick = self.message.get('nick')
        else:
            self.nick = verifiednick
        if self.action is not None:
            if self.action == 'join':
                self.message = {
                'action': self.action,
                'room': self.room,
                'nick': self.nick,
                'passwd': self.passwd
                }
            if self.action == ('getroster' or 'getbacklog'):
                self.message = {'action': self.action}
            self.type = 'control'
        elif self.body is not None:
            self.message = {
            'nick': self.nick,
            'body': self.body,
            'time': time.time()
            }
            self.type = 'chat'
        else:
            self.type = None

    def authorized(self, passwd):
        """"""
        if self.passwd == passwd:
            return True
        else:
            return False

    def connectnotify(self):
        """"""
        return json.dumps({"connected": True})

    def partnotify(self):
        """"""
        return json.dumps({'nick': self.nick, 'action': 'part'})

    def sendroster(self, roster):
        """"""
        return json.dumps({'roster': roster})

    def send(self):
        """"""
        return json.dumps(self.message)


class ChatConnection(sockjs.tornado.SockJSConnection):
    """Chat connection implementation"""
    participants = {}
    backlog = {}

    def on_open(self, info):
        """"""
        self.ip = info.headers['X-Real-Ip']
        self.auth = False

    def on_message(self, message):
        """
        Authenticate if not already authenticated.
        Otherwise broadcast message to participants.
        """
        self_set = set()
        self_set.add(self)

        if not self.auth:
            # Authenticate
            msgobj = Message(message=message)
            if msgobj.authorized('testing') and msgobj.nick is not None:
                self.nick = msgobj.nick
                self.room = msgobj.room
                try:
                    self.participants[self.room]
                except KeyError:
                    self.participants[self.room] = set()
                for participant in self.participants[self.room]:
                    if participant.nick == self.nick:
                        print('auth@{0} fail: nick collision ({1})'.format(
                            self.ip, self.nick))
                        return
                print('auth@{} success'.format(self.ip))
                self.auth = True
                msg = msgobj.send()
                self.broadcast(self.participants[self.room], msg)
                #self.backlog.append(msg)
                self.participants[self.room].add(self)
                self.broadcast(self_set, Message().connectnotify())

        else:
            msgobj = Message(message=message, verifiednick=self.nick)
            try:
                self.backlog[self.room]
            except KeyError:
                self.backlog[self.room] = deque(maxlen=30)
            if msgobj.type == 'chat':
                msg = msgobj.send()
                self.broadcast(self.participants[self.room], msg)
                self.backlog[self.room].append(msg)
            elif msgobj.type == 'control':
                if msgobj.action == 'getroster':
                    roster = [participant.nick for participant in self.participants[self.room]]
                    self.broadcast(self_set, Message().sendroster(roster))
                if msgobj.action == 'getbacklog':
                    for msg in self.backlog[self.room]:
                        self.broadcast(self_set, msg)
            else:
                self.broadcast(self_set, 'not a valid message')

    def on_close(self):
        """"""
        try:
            self.participants[self.room].remove(self)
            msg = Message(verifiednick=self.nick).partnotify()
            self.broadcast(self.participants[self.room], msg)
            #self.backlog.append(msg)
        except KeyError:
            pass


if __name__ == "__main__":
    import logging
    logging.getLogger().setLevel(logging.DEBUG)
    ChatRouter = sockjs.tornado.SockJSRouter(ChatConnection, '/chat')
    app = tornado.web.Application(
        [(r"/chat/", IndexHandler)] + ChatRouter.urls
    )
    app.listen(9002)
    tornado.ioloop.IOLoop.instance().start()
