#!/usr/bin/env python3

import configparser
import tkinter as tk
import tkinter.messagebox
from tkinter.constants import NSEW
import threading
import socket
import selectors
import json
from functools import partial

sel = selectors.DefaultSelector()

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
        self.config.read("client_config.ini", "UTF8")
        tk.Frame.__init__(self, master)
        self.master.protocol("WM_DELETE_WINDOW", self.quit)
        domyslne=self.config["DEFAULT"]
        self.geometria_baza=domyslne.get('bazowa_geometria',"1000x800+50+50")
        self.master.geometry(self.geometria_baza)
        self.master.minsize(1024, 480)
        self.add_file_menu()
        self.add_help_menu()
        self.master.columnconfigure(0, weight=999)
        self.master.columnconfigure(1, weight=1)
        self.master.rowconfigure(0, weight=1)
        self.master.rowconfigure(1, weight=9999)
        self.master.rowconfigure(2, weight=1)
        self.client = None
        self.bg_color = '#36393f'
        self.font_color = '#cccccc'

        self.server_data = {}
        self.frames = {}

        self.frames["welcome"] = self.draw_welcome_screen()
        self.switch_to("welcome")

        self.messages = []
        self.player_id = -1

        if "username" in domyslne:
            self.username_entry.insert(0, domyslne["username"])

        if "hostname" in domyslne:
            self.address_entry.insert(0, domyslne["hostname"])
        else:
            self.address_entry.insert(0, "localhost")

        self.master.title("AFORYZMY")
    
    def add_file_menu(self):
        self.menubar = tk.Menu(self.master)
        self.master["menu"] = self.menubar
        fileMenu = tk.Menu(self.menubar)
        for label, command, shortcut_text, shortcut in (
                ("Rozłącz", self.disconnect, None, None),
                ("Wyjdź", self.quit, "Ctrl+Q", "<Control-q>")):
            if label is None:
                fileMenu.add_separator()
            else:
                fileMenu.add_command(label=label, underline=0,
                        command=command, accelerator=shortcut_text)
                self.master.bind(shortcut, command)
        self.menubar.add_cascade(label="Plik", menu=fileMenu, underline=0)
        pass

    def popup(self, a=""):
        window = tk.Toplevel()
        window.minsize(240, 80)
        window.configure(bg=self.bg_color)

        label = tk.Label(window, text="Języki skryptowe 2021", bg=self.bg_color, fg=self.font_color)
        label.pack(fill='x', padx=50, pady=5)

        button_close = tk.Button(window, text="Zamknij", command=window.destroy, width=6)#, bg=self.bg_color, fg=self.font_color)
        button_close.pack()
    
    def add_help_menu(self):
        fileMenu = tk.Menu(self.menubar)
        fileMenu.add_command(label="O Aforyzmach...", underline=0,
                command=self.popup, accelerator="Ctrl+B")
        self.master.bind("<Control-b>", self.popup)
        self.menubar.add_cascade(label="Help", menu=fileMenu, underline=0) 
        pass    

    def close(self):
        geometria = self.master.winfo_geometry()
        self.config["DEFAULT"]["bazowa_geometria"] = geometria
        self.config["DEFAULT"]["username"] = self.username_entry.get()
        self.config["DEFAULT"]["hostname"] = self.address_entry.get()
        with open("client_config.ini", 'w') as config_file:
            self.config.write(config_file)
        self.master.destroy()

    def disconnect(self, event= None):
        if self.client is not None:
            self.client.close()
            self.client = None
            self.switch_to("welcome")

    def quit(self, event= None):
        reply = True
        reply = tkinter.messagebox.askyesno(
                        "Wyjście",
                        "Naprawdę wyjść?", master=self.master)
        event=event
        if reply:
            if (self.client is not None):
                self.client.close()
            self.close()

    def connect(self):
        if len(self.username_entry.get()) > 0:
            self.client = Client(self.address_entry.get(), 7312, self.username_entry.get(), self)

    def upload(self):
        if len(self.aphorism_entry.get()) > 0:
            self.switch_to("wait")
            self.client.send(self.aphorism_entry.get())

    def vote(self, player):
        self.switch_to("wait")
        self.client.vote(player)

    def switch_to(self, state):
        for frame in self.frames:
            self.frames[frame].grid_forget()
        if state != "welcome":
            self.frames[state] = self.draw_screen(state)
        self.frames[state].grid(row=1, column=0, columnspan=1, rowspan=1, sticky=NSEW)

    def draw_screen(self, type):
        if type == "wait":
            frame = tk.Frame(self.master, background=self.bg_color)
            label = tk.Label(frame, text="Oczekiwanie na innych graczy", pady=100, bg=self.bg_color, fg=self.font_color)
            label.pack()
            return frame
        if type == "vote":
            frame = tk.Frame(self.master, background=self.bg_color)
            title_label = tk.Label(frame, text="AFORYZMY", bg=self.bg_color, fg=self.font_color, font="Helvetica 22")
            title_label.pack()

            tk.Label(frame, text="Wybierz najlepszą definicję {}".format(self.server_data["title"].upper()), fg=self.font_color, bg=self.bg_color, font="Helvetica 12", height="2", anchor="n").pack()

            for message in self.messages:
                player, text = message
                if str(player) != str(self.player_id):
                    tk.Button(frame, text=text, fg=self.font_color, bg=self.bg_color, font="Helvetica 12", width="80", height="3", pady="2", relief="flat", command=partial(self.vote, player)).pack()

            return frame
        if type == "display":
            frame = tk.Frame(self.master, background=self.bg_color)
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
                tk.Label(frame, text="{} ({}): {} ({})".format(self.server_data["users"][player], total_score, text, score), fg=self.font_color, bg=self.bg_color, font="Helvetica 12", width="100", anchor="nw",
                          height="3", pady="2", padx="2").pack(fill="x")

            tk.Label(frame, text="Kolejna runda rozpocznie się za chwilę", fg=self.font_color, bg=self.bg_color,
                     font="Helvetica 12", height="3", anchor="n").pack(side="bottom")

            return frame
        if type == "game":
            frame = tk.Frame(self.master, background=self.bg_color)
            title_label = tk.Label(frame, text="AFORYZMY", bg=self.bg_color, fg=self.font_color, font="Helvetica 22")
            title_label.pack()

            tk.Label(frame, text="Napisz złotą myśl na temat wyrazu {}".format(self.server_data["title"].upper()),
                     fg=self.font_color, bg=self.bg_color, font="Helvetica 12").pack()
            sv = tk.StringVar()
            self.aphorism_entry = tk.Entry(frame, width=80, textvariable=sv)
            sv.trace_add("write", lambda x, y, z: self.key_fix(sv, 100))
            self.aphorism_entry.pack()

            send_button = tk.Button(frame, text="Wyślij", command=self.upload)
            send_button.pack()
            return frame
    
    def draw_welcome_screen(self):
        frame = tk.Frame(self.master, background=self.bg_color)
        title_label = tk.Label(frame, text="AFORYZMY", bg=self.bg_color, fg=self.font_color, font="Helvetica 22")
        title_label.pack()

        tk.Label(frame, text="Login", fg=self.font_color, bg=self.bg_color, font="Helvetica 12").pack()
        sv = tk.StringVar()
        self.username_entry = tk.Entry(frame, textvariable=sv)
        sv.trace_add("write", lambda x,y,z: self.key_fix(sv, 20))
        self.username_entry.pack()

        tk.Label(frame, text="Host", fg=self.font_color, bg=self.bg_color, font="Helvetica 12").pack()
        self.address_entry = tk.Entry(frame)
        self.address_entry.pack()

        title_button = tk.Button(frame, text="Połącz", command=self.connect, anchor="s")
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
            ('ź', 'Ÿ'), ('', "=")#('Ź', '')
        ]
        for (pl, k) in list:
            str = str.replace(k, pl)
        sv.set(str[:limit])
    
if __name__ == '__main__':
    root = tk.Tk()
    app = GUI(master=root)
    app.mainloop()
    pass