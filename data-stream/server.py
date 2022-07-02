import os

import tornado.httpserver
import tornado.ioloop
import tornado.web
import tornado.websocket
from logzero import logger
from motor.motor_tornado import MotorClient


class DRChangesHandler(tornado.websocket.WebSocketHandler):

    connected_clients = set()

    def check_origin(self, origin):
        return True

    def open(self):
        DRChangesHandler.connected_clients.add(self)

    def on_close(self):
        DRChangesHandler.connected_clients.remove(self)

    @classmethod
    def send_updates(cls, message):
        for connected_client in cls.connected_clients:
            connected_client.write_message(message)

    @classmethod
    def on_change(cls, change):
        logger.debug(change)
        if 'fullDocument' in change:
            message = f"{change['operationType']}: {change['fullDocument']['values'][change['fullDocument']['counter']:]}"
            print(message)
            DRChangesHandler.send_updates(message)


class EDChangesHandler(tornado.websocket.WebSocketHandler):

    connected_clients = set()

    def check_origin(self, origin):
        return True

    def open(self):
        EDChangesHandler.connected_clients.add(self)

    def on_close(self):
        EDChangesHandler.connected_clients.remove(self)

    @classmethod
    def send_updates(cls, message):
        for connected_client in cls.connected_clients:
            connected_client.write_message(message)

    @classmethod
    def on_change(cls, change):
        logger.debug(change)
        if 'fullDocument' in change:
            message = change['fullDocument']
            EDChangesHandler.send_updates(message)


DRchange_stream = None
EDchange_stream = None


async def watchDR(collection):
    global DRchange_stream

    async with collection.watch(full_document='updateLookup') as DRchange_stream:
        async for change in DRchange_stream:
            DRChangesHandler.on_change(change)


async def watchED(collection):
    global EDchange_stream

    async with collection.watch(full_document='updateLookup') as EDchange_stream:
        async for change in EDchange_stream:
            EDChangesHandler.on_change(change)


def main():
    client = MotorClient("mongodb://root:password@" + os.environ.get("MONGO_HOST") +
                         ":27017/?retryWrites=true&w=majority&uuidRepresentation=standard")
    collectionDR = client["hub"]["dr"]
    collectionED = client["hub"]["energydata"]

    app = tornado.web.Application(
        handlers=[(r"/dr", DRChangesHandler),
                  (r"/ed", EDChangesHandler)]
    )

    app.listen(8060)

    loop = tornado.ioloop.IOLoop.current()
    loop.add_callback(watchDR, collectionDR)
    loop.add_callback(watchED, collectionED)
    try:
        loop.start()
    except KeyboardInterrupt:
        pass
    finally:
        if DRchange_stream is not None:
            DRchange_stream.close()
        if EDchange_stream is not None:
            EDchange_stream.close()


if __name__ == "__main__":
    main()
