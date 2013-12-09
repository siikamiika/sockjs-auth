# -*- coding: utf-8 -*-
import tornado.ioloop
import tornado.web
import sockjs.tornado
import json
import time
import datetime


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
        self.action = self.message.get('action')
        if verifiednick is None:
            self.nick = self.message.get('nick')
        else:
            self.nick = verifiednick
        if self.action is not None:
            if self.action == 'join':
                self.message = {
                'action': self.action,
                'nick': self.nick,
                'passwd': self.passwd
                }
            if self.action == 'getroster':
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
    participants = set()

    def on_open(self, info):
        """"""
        self.info = info
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
                for participant in self.participants:
                    if participant.nick == self.nick:
                        print('auth@{0} fail: nick collision ({1})'.format(self.info.ip, self.nick))
                        return
                print('auth@{} success'.format(self.info.ip))
                self.auth = True
                self.broadcast(self.participants, msgobj.send())
                self.participants.add(self)
                self.broadcast(self_set, Message().connectnotify())
            else:
                print('auth@{} fail: invalid password'.format(self.info.ip))
        else:
            msgobj = Message(message=message, verifiednick=self.nick)
            if msgobj.type == 'chat':
                self.broadcast(self.participants, msgobj.send())
            elif msgobj.type == 'control' and msgobj.action == 'getroster':
                roster = [participant.nick for participant in self.participants]
                self.broadcast(self_set, Message().sendroster(roster))
            else:
                self.broadcast(self_set, 'not a valid message')

    def on_close(self):
        """"""
        try:
            self.participants.remove(self)
            self.broadcast(self.participants,
                Message(verifiednick=self.nick).partnotify())
        except KeyError:
            pass


if __name__ == "__main__":
    import logging
    logging.getLogger().setLevel(logging.DEBUG)
    ChatRouter = sockjs.tornado.SockJSRouter(ChatConnection, '/chat')
    app = tornado.web.Application(
            [(r"/", IndexHandler)] + ChatRouter.urls
    )
    app.listen(8000)
    tornado.ioloop.IOLoop.instance().start()
