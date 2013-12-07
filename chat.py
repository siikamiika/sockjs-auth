# -*- coding: utf-8 -*-
import tornado.ioloop
import tornado.web
import sockjs.tornado
import json


class IndexHandler(tornado.web.RequestHandler):
    """Regular HTTP handler to serve the chatroom page"""
    def get(self):
        self.render('index.html')


class ChatConnection(sockjs.tornado.SockJSConnection):
    """Chat connection implementation"""
    participants = set()

    def on_open(self, info):
        self.info = info
        self.auth = False
        #self.broadcast(self.participants, joininfo)
        #self.participants.add(self)

    def on_message(self, message):
        """
        Authenticate if not already authenticated.
        Otherwise broadcast message to participants.
        """
        self_set = set()
        self_set.add(self)
        try:
            message = json.loads(message)
        except:
            # :gconf:
            self.broadcast(self_set, 'That doesn\'t taste like JSON')
            return

        if not self.auth:
            # Authenticate
            try:
                if message['action'] == 'join':
                    self.nick = message['nick']
                    self.auth = True
                    self.broadcast(self.participants, json.dumps(message))
                    self.participants.add(self)
                    self.broadcast(self_set, '{"connected": true}')
            except: # TODO: gottacatchemall
                pass
            finally:
                if not self.auth:
                    print('auth@{} fail'.format(self.info.ip))
        elif message.get('body'):
            # Broadcast message
            tmp = set(self.participants)
            tmp.remove(self)
            msg = {'nick': self.nick, 'body': message.get('body')}
            self.broadcast(tmp, json.dumps(msg))
        else:
            self.broadcast(self_set, 'not a valid message')

    def on_close(self):
        # Remove client from the clients list and broadcast leave message
        self.participants.remove(self)
        partnotify = {'nick': self.nick, 'action': 'part'}
        self.broadcast(self.participants, json.dumps(partnotify))


if __name__ == "__main__":
    import logging
    logging.getLogger().setLevel(logging.DEBUG)

    # 1. Create chat router
    ChatRouter = sockjs.tornado.SockJSRouter(ChatConnection, '/chat')

    # 2. Create Tornado application
    app = tornado.web.Application(
            [(r"/", IndexHandler)] + ChatRouter.urls
    )

    # 3. Make Tornado app listen on port 8080
    app.listen(8000)

    # 4. Start IOLoop
    tornado.ioloop.IOLoop.instance().start()
