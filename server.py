#!/usr/bin/env python3

import configparser
import threading
import socket
import argparse
import os
import json
import random
import time

TITLES = [
    "Python",
    "3",
    "JavaScript",
    "Hamburger",
    "Wieloryb",
    "Szkoła",
    "Uniwersytet",
    "Remiza",
    "Pomidor",
    "Radość",
    "Młot",
    "Baran",
    "Hiacynt",
    "Jedzenie w samolocie",
    "Rozpacz",
    "Ciasto",
    "Słońce",
    "Pantofel",
    "Widmo",
    "Dama",
    "Krawędź",
    "Japonki",
    "Zamek",
    "Szmalcownik",
    "Bazy danych",
    "Szarada",
    "Głaz",
    "Piwnica",
    "Pióro",
    "Rachunek prawdopodobieństwa",
    "Jabłko",
    "Granat",
    "Przystań",
    "Sumo",
    "Baba",
    "Tygrys",
    "Staw",
    "Oliwa",
    "Grzebień",
    "Kuba",
    "Piła",
    "Polka",
    "Warta",
    "Róża",
    "Kosa",
    "Narcyz",
    "Zebra",
    "Kapelusz",
    "Kule",
    "Mars",
    "Kiwi",
    "Mysz"
]


class Server(threading.Thread):
    def __init__(self, host, port):
        super().__init__()
        self.config = configparser.ConfigParser()
        self.config.read("config.ini", "UTF8")
        self.connections = []
        self.host = host
        self.port = port
        self.data = {}
        self.data["title"] = "undefined"
        self.data["state"] = "wait"
        self.data["users"] = {}
        self.data["messages"] = {}
        self.data["scores"] = {}
        self.data["total_scores"] = {}
        self.votes = {}

    def reset(self):
        time.sleep(10)
        print("New round")
        self.votes = {}
        self.data["scores"] = {}
        self.data["messages"] = {}
        self.data["title"] = random.choice(TITLES)
        self.data["state"] = "wait"
        if self.player_count() >= 3:
            self.data["state"] = "game"
        else:
            self.data["state"] = "wait"
        dump = json.dumps(self.data, ensure_ascii=False)
        self.broadcast_all(dump)

    def run(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((self.host, self.port))

        sock.listen(1)
        print('Listening at', sock.getsockname())

        idx = 0
        try:
            while True:
                sc, sockname = sock.accept()
                print('{} has joined'.format(idx))
                server_socket = ServerSocket(sc, sockname, self, idx)
                idx += 1
                server_socket.start()
                self.connections.append(server_socket)
        except KeyboardInterrupt:
            self.quit()

    def quit(self):
        with open("config.ini", 'w') as config_file:
            self.config.write(config_file)
        os._exit(0)

    def broadcast(self, message, source):
        for connection in self.connections:
            # Send to all connected clients except the source client
            if connection.sockname != source:
                connection.send(message)

    def broadcast_all(self, message):
        for connection in self.connections:
            connection.send(message)

    def remove_connection(self, connection):
        self.connections.remove(connection)

    def player_count(self):
        return len(self.connections)


class ServerSocket(threading.Thread):
    def __init__(self, sc, sockname, server, id):
        super().__init__()
        self.sc = sc
        self.id = id
        self.sockname = sockname
        self.server = server
        self.username = ""

    def call_quit(self):
        print('{} has left'.format(self.id))
        self.server.data["users"].pop(self.id, None)
        self.server.data["messages"].pop(self.id, None)
        self.server.data["scores"].pop(self.id, None)
        self.server.data["total_scores"].pop(self.id, None)
        self.server.votes.pop(self.id, None)
        self.sc.close()
        server.remove_connection(self)
        if self.server.player_count() == 0:
            self.server.data["state"] = "wait"

    def run(self):
        """
        Receives data from the connected client and broadcasts the message to all other clients.
        If the client has left the connection, closes the connected socket and removes itself
        from the list of ServerSocket threads in the parent Server thread.
        """
        try:
            while True:
                message = self.sc.recv(1024).decode('utf8')
                if not message:
                    self.call_quit()
                    return
                elif message:
                    if self.username == "":
                        self.username = message
                        self.server.data["users"][self.id] = self.username
                        if len(self.server.data["users"]) >= 3 and self.server.data["state"] == "wait":
                            self.server.data["title"] = random.choice(TITLES)
                            self.server.data["state"] = "game"
                        dump = json.dumps(self.server.data, ensure_ascii=False)
                        self.server.broadcast(dump, self.sockname)
                        data_copy = self.server.data.copy()
                        data_copy["playerid"] = self.id
                        dump = json.dumps(data_copy, ensure_ascii=False)
                        self.send(dump)
                    elif self.server.data["state"] == "game":
                        self.server.data["messages"][self.id] = message
                        if len(self.server.data["messages"]) == self.server.player_count():
                            self.server.data["state"] = "vote"
                            dump = json.dumps(self.server.data, ensure_ascii=False)
                            self.server.broadcast_all(dump)
                    elif self.server.data["state"] == "vote":
                        self.server.votes[self.id] = int(message)
                        if len(self.server.votes) == self.server.player_count():
                            for key in self.server.votes:
                                player = self.server.votes[key]
                                if player not in self.server.data["scores"]:
                                    self.server.data["scores"][player] = 0
                                self.server.data["scores"][player] += 1
                            for player in self.server.data["scores"]:
                                name = self.server.data["users"][player]
                                if player not in self.server.data["total_scores"]:
                                    if name in self.server.config["DEFAULT"]:
                                        self.server.data["total_scores"][player] = int(
                                            self.server.config["DEFAULT"][name])
                                    else:
                                        self.server.data["total_scores"][player] = 0
                                        self.server.config["DEFAULT"][name] = "0"
                                self.server.data["total_scores"][player] += self.server.data["scores"][player]
                                self.server.config["DEFAULT"][name] = str(int(
                                    int(self.server.config["DEFAULT"][name]) + int(self.server.data["scores"][player])))
                            self.server.data["state"] = "display"
                            dump = json.dumps(self.server.data, ensure_ascii=False)
                            self.server.broadcast_all(dump)
                            with open("config.ini", 'w') as config_file:
                                self.server.config.write(config_file)
                            self.server.reset()
                    # print(self.server.data)

        except KeyboardInterrupt or EOFError:
            print("Caught keyboard interrupt, exiting")
            self.call_quit()
            os._exit(0)
        except ConnectionResetError:
            self.call_quit()

    def send(self, message):
        self.sc.sendall(message.encode('utf8'))


def quit(server):
    for connection in server.connections:
        connection.sc.close()
    os._exit(0)


def exit(server):
    try:
        while True:
            input('')
    except KeyboardInterrupt:
        quit(server)
    except EOFError:
        quit(server)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Aphorism Server')
    parser.add_argument('host', help='Interface the server listens at')
    args = parser.parse_args()

    server = Server(args.host, 7312)
    server.start()

    exit = threading.Thread(target=exit, args=(server,))
    exit.start()