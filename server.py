import socket
import threading
import json
from datetime import datetime

class CheckersServer:
    def __init__(self, host='0.0.0.0', port=12345):
        self.host = host
        self.port = port
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        self.clients = []
        self.players = {}
        self.waiting = None
        self.games = {}
        self.game_id = 1
        
        print("="*50)
        print("🎯 СЕРВЕР ШАШЕК")
        print(f"📡 Адрес: {host}:{port}")
        print("="*50)
    
    def start(self):
        self.server.bind((self.host, self.port))
        self.server.listen(5)
        print("✅ Сервер готов. Ожидание игроков...")
        
        while True:
            client, addr = self.server.accept()
            print(f"🔗 Подключен: {addr}")
            self.clients.append(client)
            
            thread = threading.Thread(target=self.handle_client, args=(client,))
            thread.daemon = True
            thread.start()
    
    def handle_client(self, client):
        try:
            self.send(client, "HELLO", {"text": "Добро пожаловать в шашки!"})
            
            while True:
                data = client.recv(1024)
                if not data:
                    break
                
                msg = data.decode().strip()
                if msg:
                    self.process(client, msg)
                    
        except:
            pass
        finally:
            self.disconnect(client)
    
    def process(self, client, message):
        try:
            if '|' not in message:
                return
                
            cmd, data = message.split('|', 1)
            data = json.loads(data)
            
            print(f"📨 [{cmd}] от {self.get_player_name(client)}")
            
            if cmd == "JOIN":
                self.handle_join(client, data)
                
            elif cmd == "FIND":
                self.handle_find(client)
                
            elif cmd == "MOVE":
                self.handle_move(client, data)
                
            elif cmd == "QUIT":
                self.handle_quit(client)
                
        except json.JSONDecodeError:
            print(f"❌ Ошибка JSON: {message[:50]}")
        except Exception as e:
            print(f"❌ Ошибка: {e}")
    
    def handle_join(self, client, data):
        name = data.get('name', 'Игрок').strip()
        if not name:
            name = f"Игрок_{len(self.players)+1}"
        
        self.players[client] = {
            "name": name,
            "game": None,
            "color": None
        }
        
        print(f"👤 {name} присоединился")
        self.send(client, "JOINED", {"name": name})
    
    def handle_find(self, client):
        if self.waiting is None:
            self.waiting = client
            self.send(client, "WAIT", {"text": "Ждем второго игрока..."})
            print(f"⏳ {self.players[client]['name']} ожидает соперника")
        else:
            p1 = self.waiting
            p2 = client
            
            game = {
                "id": self.game_id,
                "white": p1,
                "black": p2,
                "board": self.create_board(),
                "turn": "white",
                "moves": [],
                "white_name": self.players[p1]["name"],
                "black_name": self.players[p2]["name"],
                "started": datetime.now().isoformat()
            }
            
            self.games[self.game_id] = game
            self.players[p1]["game"] = self.game_id
            self.players[p2]["game"] = self.game_id
            self.players[p1]["color"] = "white"
            self.players[p2]["color"] = "black"
            
            self.waiting = None
            
            # Белым
            self.send(p1, "START", {
                "color": "white",
                "opponent": self.players[p2]["name"],
                "board": game["board"],
                "text": "Игра началась! Ваш ход."
            })
            
            # Черным
            self.send(p2, "START", {
                "color": "black",
                "opponent": self.players[p1]["name"],
                "board": game["board"],
                "text": "Игра началась! Ход противника."
            })
            
            print(f"🎮 Игра #{self.game_id}: {self.players[p1]['name']} vs {self.players[p2]['name']}")
            self.game_id += 1
    
    def handle_move(self, client, data):
        player = self.players.get(client)
        if not player or not player.get("game"):
            self.send(client, "ERROR", {"text": "Вы не в игре"})
            return
        
        game_id = player["game"]
        game = self.games.get(game_id)
        if not game:
            self.send(client, "ERROR", {"text": "Игра не найдена"})
            return
        
        if game["turn"] != player["color"]:
            self.send(client, "ERROR", {"text": "Не ваш ход!"})
            return
        
        move = data.get("move", "")
        if not move or '-' not in move:
            self.send(client, "ERROR", {"text": "Неверный формат хода"})
            return
        
        # Парсим ход
        try:
            from_pos, to_pos = move.split('-')
            from_col = ord(from_pos[0]) - ord('a')
            from_row = 8 - int(from_pos[1])
            to_col = ord(to_pos[0]) - ord('a')
            to_row = 8 - int(to_pos[1])
            
            print(f"🎯 Ход: {from_pos}({from_row},{from_col}) -> {to_pos}({to_row},{to_col})")
            
        except:
            self.send(client, "ERROR", {"text": "Неверные координаты"})
            return
        
        # Проверяем ход
        valid, error_msg = self.check_move(game["board"], from_row, from_col, to_row, to_col, player["color"])
        
        if not valid:
            self.send(client, "ERROR", {"text": error_msg})
            return
        
        # Выполняем ход
        new_board = self.apply_move(game["board"], from_row, from_col, to_row, to_col, player["color"])
        game["board"] = new_board
        game["turn"] = "black" if game["turn"] == "white" else "white"
        game["moves"].append(move)
        
        # Находим противника
        opponent = game["black"] if client == game["white"] else game["white"]
        
        # Отправляем обновление
        update_data = {
            "board": new_board,
            "last_move": move,
            "turn": game["turn"],
            "player": player["name"]
        }
        
        self.send(client, "BOARD", update_data)
        self.send(opponent, "BOARD", update_data)
        
        print(f"✅ Ход принят: {player['name']} -> {move}")
        
        # Проверка на победу
        winner = self.check_winner(new_board)
        if winner:
            self.end_game(game_id, winner)
    
    def check_move(self, board, from_row, from_col, to_row, to_col, color):
        """Проверка допустимости хода"""
        try:
            # Проверяем границы
            if not (0 <= from_row < 8 and 0 <= from_col < 8 and
                    0 <= to_row < 8 and 0 <= to_col < 8):
                return False, "Координаты вне доски"
            
            # Проверяем черную клетку
            if (from_row + from_col) % 2 == 0:
                return False, "Шашки ходят только по черным клеткам"
            if (to_row + to_col) % 2 == 0:
                return False, "Шашки ходят только по черным клеткам"
            
            piece = board[from_row][from_col]
            target = board[to_row][to_col]
            
            # Проверяем что клетка не пустая
            if piece == '.':
                return False, "На выбранной клетке нет шашки"
            
            # Проверяем свою шашку
            if color == "white" and piece not in ['w', 'W']:
                return False, "Это не ваша шашка"
            if color == "black" and piece not in ['b', 'B']:
                return False, "Это не ваша шашка"
            
            # Проверяем что целевая клетка пуста
            if target != '.':
                return False, "Целевая клетка занята"
            
            # Проверяем направление (для обычных шашек)
            if piece in ['w', 'b']:
                if piece == 'w' and to_row >= from_row:  # белые должны ходить вверх
                    return False, "Белые шашки ходят только вперед (вверх)"
                if piece == 'b' and to_row <= from_row:  # черные должны ходить вниз
                    return False, "Черные шашки ходят только вперед (вниз)"
            
            # Проверяем диагональ
            row_diff = abs(to_row - from_row)
            col_diff = abs(to_col - from_col)
            
            if row_diff != col_diff:
                return False, "Ход должен быть по диагонали"
            
            # Обычный ход (на 1 клетку)
            if row_diff == 1:
                return True, ""
            
            # Взятие (на 2 клетки)
            if row_diff == 2:
                mid_row = (from_row + to_row) // 2
                mid_col = (from_col + to_col) // 2
                mid_piece = board[mid_row][mid_col]
                
                if mid_piece == '.':
                    return False, "Нет шашки для взятия"
                
                # Проверяем что бьем шашку противника
                if color == "white" and mid_piece not in ['b', 'B']:
                    return False, "Можно бить только шашки противника"
                if color == "black" and mid_piece not in ['w', 'W']:
                    return False, "Можно бить только шашки противника"
                
                return True, ""
            
            return False, "Недопустимая длина хода"
            
        except Exception as e:
            return False, f"Ошибка проверки: {e}"
    
    def apply_move(self, board, from_row, from_col, to_row, to_col, color):
        """Применение хода к доске"""
        new_board = [list(row) for row in board]
        
        # Перемещаем шашку
        piece = new_board[from_row][from_col]
        new_board[from_row][from_col] = '.'
        new_board[to_row][to_col] = piece
        
        # Если был прыжок - удаляем побитую шашку
        if abs(to_row - from_row) == 2:
            mid_row = (from_row + to_row) // 2
            mid_col = (from_col + to_col) // 2
            new_board[mid_row][mid_col] = '.'
        
        # Превращение в дамку
        if piece == 'w' and to_row == 0:
            new_board[to_row][to_col] = 'W'
        elif piece == 'b' and to_row == 7:
            new_board[to_row][to_col] = 'B'
        
        return [''.join(row) for row in new_board]
    
    def check_winner(self, board):
        """Проверка победителя"""
        white_count = sum(row.count('w') + row.count('W') for row in board)
        black_count = sum(row.count('b') + row.count('B') for row in board)
        
        if white_count == 0:
            return "black"
        if black_count == 0:
            return "white"
        return None
    
    def end_game(self, game_id, winner):
        """Завершение игры"""
        game = self.games.get(game_id)
        if not game:
            return
        
        winner_name = game["white_name"] if winner == "white" else game["black_name"]
        
        for player_socket in [game["white"], game["black"]]:
            if player_socket in self.players:
                self.send(player_socket, "END", {
                    "winner": winner,
                    "winner_name": winner_name,
                    "text": f"Игра окончена! Победили {winner} ({winner_name})"
                })
                self.players[player_socket]["game"] = None
        
        del self.games[game_id]
        print(f"🏆 Игра #{game_id} завершена. Победитель: {winner_name}")
    
    def handle_quit(self, client):
        """Сдача"""
        player = self.players.get(client)
        if not player:
            return
        
        game_id = player.get("game")
        if game_id and game_id in self.games:
            game = self.games[game_id]
            winner = "black" if player["color"] == "white" else "white"
            self.end_game(game_id, winner)
    
    def disconnect(self, client):
        """Отключение клиента"""
        if client in self.clients:
            self.clients.remove(client)
        
        player = self.players.pop(client, None)
        if player:
            print(f"🔌 Отключился: {player['name']}")
            
            if self.waiting == client:
                self.waiting = None
            
            game_id = player.get("game")
            if game_id and game_id in self.games:
                game = self.games[game_id]
                winner = "black" if player["color"] == "white" else "white"
                self.end_game(game_id, winner)
        
        try:
            client.close()
        except:
            pass
    
    def send(self, client, cmd, data):
        """Отправка сообщения"""
        try:
            message = f"{cmd}|{json.dumps(data, ensure_ascii=False)}\n"
            client.send(message.encode())
        except:
            pass
    
    def get_player_name(self, client):
        """Имя игрока"""
        if client in self.players:
            return self.players[client]["name"]
        return "Unknown"
    
    def create_board(self):
        """Создание начальной доски"""
        return [
            ".b.b.b.b",  # 1
            "b.b.b.b.",  # 2
            ".b.b.b.b",  # 3
            "........",  # 4
            "........",  # 5
            "w.w.w.w.",  # 6
            ".w.w.w.w",  # 7
            "w.w.w.w."   # 8
        ]

if __name__ == "__main__":
    print("🎯 СЕРВЕР ШАШЕК - ИСПРАВЛЕННЫЙ")
    print("="*50)
    
    server = CheckersServer()
    server.start()