#!/usr/bin/env python3

import configparser
import sys
import tkinter as tk
import tkinter.messagebox
from tkinter.constants import NSEW
import threading
import os
import socket
import selectors
import json
from functools import partial

config_fname = "config.txt"

sel = selectors.DefaultSelector()
messages = [b"Message 1 from client.", b"Message 2 from client."]

class Client(threading.Thread):
    def __init__(self, host, port, username, gui):
        super().__init__()
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.name = username
        self.gui = gui
        self.start()

    def start(self):
        self.sock.connect((self.host, self.port))
        print('Connected to {}:{}'.format(self.host, self.port))

        # Send the username as a welcome message
        self.sock.sendall(self.name.encode('utf8'))
        super().start()

    def close(self):
        try:
            self.sock.close()
        except:
            pass

    def send(self, message):
        self.sock.sendall(message.encode('utf8'))

    def vote(self, player):
        self.sock.sendall(str(player).encode('utf8'))

    def run(self):
        try:
            while True:
                message = self.sock.recv(4096).decode('utf8')
                if message:
                    data = json.loads(message)
                    if "playerid" in data:
                        self.gui.player_id = int(data["playerid"])
                    self.gui.server_data = data
                    if data["state"] == "vote":
                        self.gui.messages = []
                        for key in data["messages"]:
                            self.gui.messages.append((key, data["messages"][key]))
                    self.gui.switch_to(data["state"])

                else:
                    self.close()
        except:
            self.close()

class GUI(tk.Frame):
    def __init__(self, master=None):
        self.config= configparser.ConfigParser()
        self.config.read(config_fname, "UTF8")
        tk.Frame.__init__(self, master)
        self.parent=master
        self.parent.protocol("WM_DELETE_WINDOW", self.quit)
        domyslne=self.config["DEFAULT"]
        self.geometria_baza=domyslne.get('bazowa_geometria',"1000x800+50+50")
        self.parent.geometry(self.geometria_baza)
        self.parent.minsize(1024, 768)
        self.utworz_bazowe_menu()
        # self.utworz_pasek_narzedzi()
        self.utworz_status()

        self.dodaj_menu_custom()
        self.dodaj_menu_help()
        # self.utworz_dodatki()
        self.parent.columnconfigure(0, weight=999)
        self.parent.columnconfigure(1, weight=1)
        self.parent.rowconfigure(0, weight=1)
        self.parent.rowconfigure(1, weight=9999)
        self.parent.rowconfigure(2, weight=1)

        self.client = None

        self.bg_color = '#36393f'
        self.font_color = '#cccccc'

        self.frames = {}
        self.frames["wait"] = self.draw_wait_screen()
        self.frames["game"] = self.draw_game_screen()
        self.frames["welcome"] = self.draw_welcome_screen()
        self.switch_to("welcome")

        self.messages = []
        self.player_id = -1
        self.server_data = {}

        self.master.title("AFORYZMY")

    def utworz_pasek_narzedzi(self):
        self.toolbar_images = []   #muszą być pamiętane stale
        self.toolbar = tk.Frame(self.parent)
        for image, command in (
                ("res/filenew.gif", self.file_new),
                ("res/fileopen.gif", self.file_open),
                ("res/filesave.gif", self.file_save)):
            image = os.path.join(os.path.dirname(__file__), image)
            try:
                image = tkinter.PhotoImage(file=image)
                self.toolbar_images.append(image)
                button = tkinter.Button(self.toolbar, image=image,
                                        command=command)
                button.grid(row=0, column=len(self.toolbar_images) -1) #KOLEJNE ELEMENTY
            except tkinter.TclError as err:
                print(err)  # gdy kłopoty z odczytaniem pliku
        self.toolbar.grid(row=0, column=0, columnspan=2, sticky=tkinter.NSEW)
        
    
    def utworz_dodatki(self):
        pass
    
    def utworz_status(self):
        self.statusbar = tk.Label(self.parent, text="Status...",
                                       anchor=tkinter.W)
        self.statusbar.after(5000, self.clearStatusBar)
        self.statusbar.grid(row=2, column=0, columnspan=2,
                            sticky=tkinter.EW)
        pass
    
    def ustawStatusBar(self, txt):
        self.statusbar["text"] = txt
        
    def clearStatusBar(self):
        self.statusbar["text"] = ""
    
    def utworz_bazowe_menu(self):
        self.menubar = tk.Menu(self.parent)
        self.parent["menu"] = self.menubar
        fileMenu = tk.Menu(self.menubar)
        for label, command, shortcut_text, shortcut in (
                ("Rozłącz", self.disconnect, None, None),
                ("Quit", self.quit, "Ctrl+Q", "<Control-q>")):
            if label is None:
                fileMenu.add_separator()
            else:
                fileMenu.add_command(label=label, underline=0,
                        command=command, accelerator=shortcut_text)
                self.parent.bind(shortcut, command)
        self.menubar.add_cascade(label="File", menu=fileMenu, underline=0) 
        pass
    
    def dodaj_menu_help(self):
        fileMenu = tk.Menu(self.menubar)
        fileMenu.add_command(label="About...", underline=0,
                command=self.file_new, accelerator="Ctrl+B")
        self.parent.bind("<Control-b>", self.file_new)
        self.menubar.add_cascade(label="Help", menu=fileMenu, underline=0) 
        pass    

    def close(self):
        geometria = self.parent.winfo_geometry()
        self.config["DEFAULT"]["bazowa_geometria"] = geometria
        with open(config_fname, 'w') as config_plik:
            self.config.write(config_plik)
        self.parent.destroy()

    def disconnect(self, event= None):
        if self.client is not None:
            self.client.close()
            self.client = None
            self.switch_to("welcome")

    def quit(self, event= None):
        reply = tkinter.messagebox.askyesno(
                        "Wyjście",
                        "Naprawdę wyjść?", parent=self.parent)
        event=event
        if reply:
            if (self.client is not None):
                self.client.close()
            self.close()
    
    def dodaj_menu_custom(self):
        pass
    def file_new(self, event=None):
        event=event
    def file_open(self,event=None):
        event=event
        pass
    def file_save(self,event=None):
        event=event
        pass
    def connect(self):
        self.client = Client(self.address_entry.get(), 7312, self.username_entry.get(), self)

    def upload(self):
        self.switch_to("wait")
        self.client.send(self.aphorism_entry.get())

    def vote(self, player):
        self.switch_to("wait")
        self.client.vote(player)

    def switch_to(self, state):
        for frame in self.frames:
            self.frames[frame].grid_forget()
        if state == "vote" or state == "display":
            self.frames[state] = self.draw_screen(state)
        self.frames[state].grid(row=1, column=0, columnspan=1, rowspan=1, sticky=NSEW)


    def draw_wait_screen(self):
        frame = tk.Frame(self.parent, background=self.bg_color)
        label = tk.Label(frame, text="Waiting for other players", pady=100, bg=self.bg_color, fg=self.font_color)
        label.pack()
        return frame

    def draw_screen(self, type):
        if(type == "vote"):
            frame = tk.Frame(self.parent, background=self.bg_color)
            title_label = tk.Label(frame, text="AFORYZMY", bg=self.bg_color, fg=self.font_color, font="Helvetica 22")
            title_label.pack()

            tk.Label(frame, text="Wybierz najlepszą definicję ASS", fg=self.font_color, bg=self.bg_color, font="Helvetica 12", height="2", anchor="n").pack()

            for message in self.messages:
                player, text = message
                if str(player) != str(self.player_id):
                    tk.Button(frame, text=text, fg=self.font_color, bg=self.bg_color, font="Helvetica 12", width="80", height="3", pady="2", relief="flat", command=partial(self.vote, player)).pack()

            return frame
        if (type == "display"):
            frame = tk.Frame(self.parent, background=self.bg_color)
            title_label = tk.Label(frame, text="AFORYZMY", bg=self.bg_color, fg=self.font_color, font="Helvetica 22")
            title_label.pack()

            tk.Label(frame, text="Wyniki", fg=self.font_color, bg=self.bg_color,
                     font="Helvetica 12", height="2", anchor="n").pack()

            for message in self.messages:
                player, text = message
                total_score = 0
                score = 0
                if player in self.server_data["total_scores"]:
                    total_score = self.server_data["total_scores"][player]
                if player in self.server_data["scores"]:
                    score = self.server_data["scores"][player]
                tk.Label(frame, text="{} ({}):\n{} ({})".format(self.server_data["users"][player], total_score, text, score), fg=self.font_color, bg=self.bg_color, font="Helvetica 12", width="100", anchor="nw",
                          height="3", pady="2").pack()

            tk.Label(frame, text="Kolejna runda rozpocznie się za chwilę", fg=self.font_color, bg=self.bg_color,
                     font="Helvetica 12", height="3", anchor="s").pack()

            return frame

    def draw_game_screen(self):
        frame = tk.Frame(self.parent, background=self.bg_color)
        title_label = tk.Label(frame, text="AFORYZMY", bg=self.bg_color, fg=self.font_color, font="Helvetica 22")
        title_label.pack()

        tk.Label(frame, text="Describe the word: ASS", fg=self.font_color, bg=self.bg_color, font="Helvetica 12").pack()
        sv = tk.StringVar()
        self.aphorism_entry = tk.Entry(frame, width=80, textvariable=sv)
        sv.trace_add("write", lambda x, y, z: self.key_fix(sv, 100))
        self.aphorism_entry.pack()

        send_button = tk.Button(frame, text="Send", command=self.upload)
        send_button.pack()
        return frame
    
    def draw_welcome_screen(self):
        frame = tk.Frame(self.parent, background=self.bg_color)
        title_label = tk.Label(frame, text="AFORYZMY", bg=self.bg_color, fg=self.font_color, font="Helvetica 22")
        title_label.pack()

        tk.Label(frame, text="Login", fg=self.font_color, bg=self.bg_color, font="Helvetica 12").pack()
        sv = tk.StringVar()
        self.username_entry = tk.Entry(frame, textvariable=sv)
        sv.trace_add("write", lambda x,y,z: self.key_fix(sv, 20))
        self.username_entry.pack()

        tk.Label(frame, text="Address", fg=self.font_color, bg=self.bg_color, font="Helvetica 12").pack()
        self.address_entry = tk.Entry(frame)
        self.address_entry.insert(0,"localhost")
        self.address_entry.pack()

        title_button = tk.Button(frame, text="Connect", command=self.connect)
        title_button.pack()
        return frame


    def key_fix(self, sv, limit):
        str = sv.get()
        list = [
            ('ę', 'ê'), ('Ę', 'Ê'),
            ('ś', 'œ'), ('Ś', 'Œ'),
            ('ć', 'æ'), ('Ć', 'Æ'),
            ('ł', '³'), ('Ł', '£'),
            ('ń', 'ñ'), ('Ń', 'Ñ'),
            ('ą', '¹'), ('Ą', '¥'),
            ('ż', '¿'), ('Ż', '¯'),
            ('ź', 'Ÿ'), #('Ź', '')
        ]
        for (pl, k) in list:
            str = str.replace(k, pl)
        sv.set(str[:limit])
    
if __name__ == '__main__':
    root = tk.Tk()
    app = GUI(master=root)
    app.mainloop()
    pass