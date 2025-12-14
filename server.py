import socket
import threading
import json

class CheckersServer:
    def __init__(self):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind(("0.0.0.0", 12345))
        self.server.listen(5)

        self.players = {}
        self.waiting = None
        self.games = {}
        self.game_id = 1

        print("Сервер запущен")

    # ================= NETWORK =================
    def start(self):
        while True:
            client, _ = self.server.accept()
            threading.Thread(target=self.handle, args=(client,), daemon=True).start()

    def handle(self, client):
        buffer = ""
        try:
            while True:
                data = client.recv(1024).decode()
                if not data:
                    break
                buffer += data
                while "\n" in buffer:
                    msg, buffer = buffer.split("\n", 1)
                    self.process(client, msg)
        finally:
            self.disconnect(client)

    def process(self, client, msg):
        if "|" not in msg:
            return
        cmd, data = msg.split("|", 1)
        data = json.loads(data)

        if cmd == "JOIN":
            self.players[client] = {"name": data["name"], "game": None, "color": None}

        elif cmd == "FIND":
            if self.waiting is None:
                self.waiting = client
            else:
                self.start_game(self.waiting, client)
                self.waiting = None

        elif cmd == "MOVE":
            self.handle_move(client, data["move"])

    # ================= GAME =================
    def start_game(self, p1, p2):
        board = self.create_board()
        gid = self.game_id
        self.game_id += 1

        self.games[gid] = {
            "white": p1,
            "black": p2,
            "board": board,
            "turn": "white"
        }

        self.players[p1]["game"] = gid
        self.players[p1]["color"] = "white"
        self.players[p2]["game"] = gid
        self.players[p2]["color"] = "black"

        self.send(p1, "START", {"color": "white", "board": board})
        self.send(p2, "START", {"color": "black", "board": board})

    # ================= MOVE =================
    def handle_move(self, client, move):
        player = self.players[client]
        game = self.games[player["game"]]

        if game["turn"] != player["color"]:
            self.send(client, "ERROR", {"text": "Не ваш ход"})
            return

        fr, to = move.split("-")
        fc, fr = ord(fr[0]) - 97, 8 - int(fr[1])
        tc, tr = ord(to[0]) - 97, 8 - int(to[1])

        board = game["board"]

        result = self.validate_and_apply(board, fr, fc, tr, tc, player["color"])
        if not result:
            self.send(client, "ERROR", {"text": "Недопустимый ход"})
            return

        # ход успешен → меняем очередь
        game["turn"] = "black" if game["turn"] == "white" else "white"

        data = {"board": board, "turn": game["turn"]}
        self.send(game["white"], "BOARD", data)
        self.send(game["black"], "BOARD", data)

    # ================= VALIDATION =================
    def validate_and_apply(self, board, fr, fc, tr, tc, color):
        if not all(0 <= x < 8 for x in (fr, fc, tr, tc)):
            return False
        if (tr + tc) % 2 == 0:
            return False

        piece = board[fr][fc]
        if piece == "." or board[tr][tc] != ".":
            return False

        if color == "white" and piece not in ("w", "W"):
            return False
        if color == "black" and piece not in ("b", "B"):
            return False

        dr = tr - fr
        dc = tc - fc

        must_capture = self.has_any_capture(board, color)

        # ---------- ВЗЯТИЕ ----------
        if abs(dr) == 2 and abs(dc) == 2:
            mr, mc = fr + dr // 2, fc + dc // 2
            mid = board[mr][mc]

            if color == "white" and mid.lower() != "b":
                return False
            if color == "black" and mid.lower() != "w":
                return False

            # направление пешки
            if piece == "w" and dr != -2:
                return False
            if piece == "b" and dr != 2:
                return False

            board[fr][fc] = "."
            board[mr][mc] = "."
            board[tr][tc] = piece
            return True

        # ---------- ОБЫЧНЫЙ ХОД ----------
        if must_capture:
            return False  # обязательное взятие

        if abs(dr) != 1 or abs(dc) != 1:
            return False

        if piece == "w" and dr != -1:
            return False
        if piece == "b" and dr != 1:
            return False

        board[fr][fc] = "."
        board[tr][tc] = piece
        return True

    # ================= CAPTURE CHECK =================
    def has_any_capture(self, board, color):
        enemy = "b" if color == "white" else "w"

        for r in range(8):
            for c in range(8):
                piece = board[r][c]
                if color == "white" and piece != "w":
                    continue
                if color == "black" and piece != "b":
                    continue

                direction = -1 if color == "white" else 1
                for dc in (-1, 1):
                    r1, c1 = r + direction, c + dc
                    r2, c2 = r + 2 * direction, c + 2 * dc
                    if (
                        0 <= r2 < 8 and 0 <= c2 < 8
                        and board[r1][c1].lower() == enemy
                        and board[r2][c2] == "."
                    ):
                        return True
        return False

    # ================= UTILS =================
    def create_board(self):
        board = []
        for r in range(8):
            row = []
            for c in range(8):
                if (r + c) % 2 == 1:
                    if r < 3:
                        row.append("b")
                    elif r > 4:
                        row.append("w")
                    else:
                        row.append(".")
                else:
                    row.append(".")
            board.append(row)
        return board

    def send(self, client, cmd, data):
        try:
            client.send(f"{cmd}|{json.dumps(data)}\n".encode())
        except:
            pass

    def disconnect(self, client):
        self.players.pop(client, None)
        try:
            client.close()
        except:
            pass


if __name__ == "__main__":
    CheckersServer().start()
