import os
import tornado.httpserver
import tornado.websocket
import tornado.ioloop
import tornado.web
from motor.motor_tornado import MotorClient
from bson import json_util
from logzero import logger
import matplotlib.pyplot as plt
import mpld3


class WebpageHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("templates/index.html")


class ChangesHandler(tornado.websocket.WebSocketHandler):

    connected_clients = set()

    def check_origin(self, origin):
        return True

    def open(self):
        ChangesHandler.connected_clients.add(self)

    def on_close(self):
        ChangesHandler.connected_clients.remove(self)

    @classmethod
    def send_updates(cls, message):
        for connected_client in cls.connected_clients:
            connected_client.write_message(message)

    @classmethod
    def on_change(cls, change):
        logger.debug(change)
        print(change)
        message = f"{change['operationType']}: {change['fullDocument']['values']}"
        f = plt.figure()
        plt.plot(change['fullDocument']['values'])
        html = mpld3.fig_to_html(f)
        ChangesHandler.send_updates(html)


change_stream = None


async def watch(collection):
    global change_stream

    async with collection.watch(full_document='updateLookup') as change_stream:
        async for change in change_stream:
            ChangesHandler.on_change(change)


def main():
    client = MotorClient("mongodb://root:password@mongo:27017/?retryWrites=true&w=majority&uuidRepresentation=standard")
    collection = client["hub"]["dr"]

    app = tornado.web.Application(
        [(r"/socket", ChangesHandler), (r"/", WebpageHandler)]
    )

    app.listen(8006)

    loop = tornado.ioloop.IOLoop.current()
    loop.add_callback(watch, collection)
    try:
        loop.start()
    except KeyboardInterrupt:
        pass
    finally:
        if change_stream is not None:
            change_stream.close()


if __name__ == "__main__":
    main()