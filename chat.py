# -*- coding: utf-8 -*-
import tornado.ioloop
import tornado.web

import sockjs.tornado


class IndexHandler(tornado.web.RequestHandler):
    """Regular HTTP handler to serve the chatroom page"""
    def get(self):
        self.render('index.html')


class ChatConnection(sockjs.tornado.SockJSConnection):
    """Chat connection implementation"""
    # Tähän tallennetaan paikallaolijat
    participants = set()

    def on_open(self, info):
        #raise tornado.web.HTTPError(403)
        self.info = info
        self.broadcast(self.participants, self.info.ip+' joined')

        # Add client to the clients list
        self.participants.add(self)

    def on_message(self, message):
        # Broadcast message
        tmp = set(self.participants)
        tmp.remove(self)
        self.broadcast(tmp, '{0}: {1}'.format(self.info.ip, message))

    def on_close(self):
        # Remove client from the clients list and broadcast leave message
        try:
            self.participants.remove(self)
            self.broadcast(self.participants, self.info.ip+' left')
        except KeyError:
            pass

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
