import socket
import threading
import json
import tkinter as tk
from tkinter import ttk, messagebox

class CheckersClient:
    def __init__(self):
        self.sock = None
        self.connected = False
        self.name = ""
        self.color = None
        self.board = []
        self.my_turn = False
        self.selected = None
        self.waiting = False

        self.create_gui()

    def create_gui(self):
        self.root = tk.Tk()
        self.root.title("Шашки Онлайн")
        self.root.geometry("600x720")

        top = ttk.Frame(self.root)
        top.pack(pady=5)

        ttk.Label(top, text="Имя:").pack(side=tk.LEFT)
        self.name_entry = ttk.Entry(top, width=10)
        self.name_entry.pack(side=tk.LEFT, padx=5)
        self.name_entry.insert(0, "Игрок")

        self.connect_btn = ttk.Button(top, text="Подключиться", command=self.connect)
        self.connect_btn.pack(side=tk.LEFT, padx=5)

        self.find_btn = ttk.Button(top, text="Найти игру", command=self.find_game, state=tk.DISABLED)
        self.find_btn.pack(side=tk.LEFT, padx=5)

        self.info = tk.StringVar(value="Не подключен")
        ttk.Label(self.root, textvariable=self.info).pack()

        board_frame = ttk.Frame(self.root)
        board_frame.pack(pady=10)

        self.cells = []
        for r in range(8):
            row = []
            for c in range(8):
                dark = (r + c) % 2 == 1
                color = "#8B4513" if dark else "#F5DEB3"
                btn = tk.Button(
                    board_frame, width=4, height=2,
                    bg=color, font=("Arial", 14),
                    state=tk.DISABLED,
                    command=lambda r=r, c=c: self.click(r, c)
                )
                btn.grid(row=r, column=c)
                row.append(btn)
            self.cells.append(row)

        self.log = tk.Text(self.root, height=6, state=tk.DISABLED)
        self.log.pack(fill=tk.X)

    def connect(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect(("127.0.0.1", 12345))
            self.connected = True
            self.name = self.name_entry.get().strip() or "Игрок"

            threading.Thread(target=self.receive, daemon=True).start()
            self.send("JOIN", {"name": self.name})

            self.info.set("Подключено")
            self.connect_btn.config(state=tk.DISABLED)
            self.find_btn.config(state=tk.NORMAL)
            self.log_msg("Система", "Подключено к серверу")
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    def find_game(self):
        self.send("FIND", {})
        self.info.set("Поиск игры...")

    def send(self, cmd, data):
        self.sock.send(f"{cmd}|{json.dumps(data)}\n".encode())

    def receive(self):
        buffer = ""
        while self.connected:
            data = self.sock.recv(1024).decode()
            if not data:
                break
            buffer += data
            while "\n" in buffer:
                msg, buffer = buffer.split("\n", 1)
                self.process(msg)

    def process(self, msg):
        if "|" not in msg:
            return
        cmd, data = msg.split("|", 1)
        data = json.loads(data)

        if cmd == "START":
            self.color = data["color"]
            self.board = data["board"]
            self.my_turn = self.color == "white"
            self.info.set(f"Вы играете за {self.color}")
            self.draw()
            self.update_board_state()

        elif cmd == "BOARD":
            self.board = data["board"]
            self.my_turn = data["turn"] == self.color
            self.waiting = False
            self.draw()
            self.update_board_state()

        elif cmd == "ERROR":
            self.waiting = False
            self.my_turn = True   
            self.update_board_state()
            self.log_msg("Ошибка", data["text"])

    def real_coords(self, r, c):
        """Преобразование координат для чёрных"""
        if self.color == "black":
            return 7 - r, 7 - c
        return r, c

    def draw(self):
        symbols = {"w": "⚪", "W": "♔", "b": "⚫", "B": "♚", ".": ""}
        for r in range(8):
            for c in range(8):
                rr, cc = self.real_coords(r, c)
                piece = self.board[rr][cc]
                self.cells[r][c].config(text=symbols[piece])

    def update_board_state(self):
        for r in range(8):
            for c in range(8):
                dark = (r + c) % 2 == 1
                state = tk.NORMAL if self.my_turn and dark else tk.DISABLED
                self.cells[r][c].config(state=state)

    def click(self, r, c):
        if not self.my_turn or self.waiting:
            return

        rr, cc = self.real_coords(r, c)

        if self.selected is None:
            self.selected = (rr, cc)
        else:
            fr, fc = self.selected
            move = f"{chr(fc+97)}{8-fr}-{chr(cc+97)}{8-rr}"
            self.send("MOVE", {"move": move})
            self.selected = None
            self.waiting = True
            self.my_turn = False
            self.update_board_state()

    def log_msg(self, sender, text):
        self.log.config(state=tk.NORMAL)
        self.log.insert(tk.END, f"[{sender}] {text}\n")
        self.log.see(tk.END)
        self.log.config(state=tk.DISABLED)

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    CheckersClient().run()