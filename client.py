import socket
import threading
import json
import tkinter as tk
from tkinter import ttk, messagebox
import time

class CheckersClient:
    def __init__(self):
        self.socket = None
        self.connected = False
        self.connection_attempted = False
        self.name = ""
        self.color = ""
        self.game_id = None
        self.my_turn = False
        self.selected = None
        self.valid_moves = []
        self.board = []
        self.waiting_for_server = False
        
        self.create_gui()
    
    def create_gui(self):
        """Создание интерфейса"""
        self.root = tk.Tk()
        self.root.title("Шашки Онлайн")
        self.root.geometry("650x750")
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        style = ttk.Style()
        style.theme_use('clam')
        
        main_frame = ttk.Frame(self.root, padding="5")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Верхняя панель
        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill=tk.X, pady=(0, 5))
        
        # Панель подключения
        conn_frame = ttk.LabelFrame(top_frame, text="Подключение", padding="5")
        conn_frame.pack(side=tk.LEFT, fill=tk.Y)
        
        ttk.Label(conn_frame, text="Имя:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.name_entry = ttk.Entry(conn_frame, width=12)
        self.name_entry.grid(row=0, column=1, pady=2, padx=(5, 0))
        self.name_entry.insert(0, "Игрок")
        
        ttk.Label(conn_frame, text="Сервер:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.host_entry = ttk.Entry(conn_frame, width=12)
        self.host_entry.grid(row=1, column=1, pady=2, padx=(5, 0))
        self.host_entry.insert(0, "127.0.0.1")
        
        ttk.Label(conn_frame, text="Порт:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.port_entry = ttk.Entry(conn_frame, width=12)
        self.port_entry.grid(row=2, column=1, pady=2, padx=(5, 0))
        self.port_entry.insert(0, "12345")
        
        self.connect_btn = ttk.Button(conn_frame, text="Подключиться", 
                                     command=self.connect, width=12)
        self.connect_btn.grid(row=3, column=0, columnspan=2, pady=5)
        
        self.find_btn = ttk.Button(conn_frame, text="Найти игру",
                                  command=self.find_game, state=tk.DISABLED, width=12)
        self.find_btn.grid(row=4, column=0, columnspan=2, pady=2)
        
        # Панель информации
        info_frame = ttk.LabelFrame(top_frame, text="Информация", padding="5")
        info_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 0))
        
        self.status_var = tk.StringVar(value="❌ Отключено")
        ttk.Label(info_frame, textvariable=self.status_var, 
                 font=('Arial', 10)).pack(anchor=tk.W)
        
        self.game_info_var = tk.StringVar(value="Не в игре")
        ttk.Label(info_frame, textvariable=self.game_info_var,
                 font=('Arial', 9)).pack(anchor=tk.W)
        
        self.turn_info_var = tk.StringVar(value="")
        ttk.Label(info_frame, textvariable=self.turn_info_var,
                 font=('Arial', 9, 'bold')).pack(anchor=tk.W)
        
        self.help_var = tk.StringVar(value="Сначала подключитесь к серверу")
        ttk.Label(info_frame, textvariable=self.help_var,
                 font=('Arial', 8)).pack(anchor=tk.W, pady=(5, 0))
        
        self.resign_btn = ttk.Button(info_frame, text="Сдаться",
                                    command=self.resign, state=tk.DISABLED, width=10)
        self.resign_btn.pack(anchor=tk.W, pady=(5, 0))
        
        # Доска
        board_frame = ttk.LabelFrame(main_frame, text="Доска шашек", padding="10")
        board_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        
        self.create_board(board_frame)
        
        # Панель сообщений
        msg_frame = ttk.LabelFrame(main_frame, text="Лог", padding="5")
        msg_frame.pack(fill=tk.X)
        
        self.msg_text = tk.Text(msg_frame, height=4, width=60, state=tk.DISABLED,
                               font=('Arial', 9))
        self.msg_text.pack(fill=tk.X)
        
        # Статусная строка
        self.protocol_var = tk.StringVar(value="Статус: Сервер не запущен")
        status_bar = ttk.Label(main_frame, textvariable=self.protocol_var, 
                              relief=tk.SUNKEN, font=('Arial', 8))
        status_bar.pack(fill=tk.X, pady=(5, 0))
    
    def create_board(self, parent):
        """Создание доски 8x8"""
        board_frame = ttk.Frame(parent)
        board_frame.pack(expand=True)
        
        self.cells = []
        for row in range(8):
            cell_row = []
            for col in range(8):
                # ИСПРАВЛЕНИЕ: МЕНЯЕМ ЦВЕТА НА ПРОТИВОПОЛОЖНЫЕ
                # Теперь: тёмные клетки = (row + col) % 2 == 0
                #         светлые клетки = (row + col) % 2 == 1
                is_dark = (row + col) % 2 == 1  # ИЗМЕНИЛИ!
                color = '#8B4513' if is_dark else '#F5DEB3'  # тёмный/светлый
                
                cell = tk.Button(
                    board_frame,
                    width=4,
                    height=2,
                    bg=color,
                    font=('Arial', 14),
                    relief=tk.RAISED,
                    borderwidth=1,
                    state=tk.DISABLED,
                    command=lambda r=row, c=col: self.click(r, c)
                )
                cell.grid(row=row, column=col, padx=1, pady=1)
                cell_row.append(cell)
            self.cells.append(cell_row)
        
        # Буквы (a-h)
        letters_frame = ttk.Frame(board_frame)
        letters_frame.grid(row=8, column=0, columnspan=8, pady=(2, 0))
        
        letters = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']
        for i, letter in enumerate(letters):
            label = ttk.Label(letters_frame, text=letter, font=('Arial', 10))
            label.grid(row=0, column=i, padx=15)
        
        # Цифры (1-8)
        for i in range(8):
            label = ttk.Label(board_frame, text=str(8-i), font=('Arial', 10))
            label.grid(row=i, column=8, padx=(5, 0))
    
    def connect(self):
        """Подключение к серверу"""
        if self.connection_attempted:
            messagebox.showwarning("Внимание", "Переподключение...")
            self.disconnect()
        
        try:
            host = self.host_entry.get()
            port = int(self.port_entry.get())
            name = self.name_entry.get().strip()
            
            if not name:
                messagebox.showerror("Ошибка", "Введите имя")
                return
            
            self.add_message("Система", f"Попытка подключения к {host}:{port}...")
            self.status_var.set("🔄 Подключение...")
            self.root.update()
            
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5)
            
            try:
                self.socket.connect((host, port))
            except socket.timeout:
                messagebox.showerror("Ошибка", "Таймаут подключения")
                self.socket = None
                self.status_var.set("❌ Таймаут")
                return
            except ConnectionRefusedError:
                messagebox.showerror("Ошибка", f"Сервер не найден на {host}:{port}")
                self.socket = None
                self.status_var.set("❌ Сервер не найден")
                return
            except Exception as e:
                messagebox.showerror("Ошибка", f"Ошибка: {e}")
                self.socket = None
                self.status_var.set("❌ Ошибка")
                return
            
            self.socket.settimeout(None)
            self.connected = True
            self.connection_attempted = True
            self.name = name
            
            self.receive_thread = threading.Thread(target=self.receive, daemon=True)
            self.receive_thread.start()
            
            self.send("JOIN", {"name": name})
            
            self.connect_btn.config(state=tk.DISABLED)
            self.find_btn.config(state=tk.NORMAL)
            self.status_var.set(f"✅ Подключен")
            self.protocol_var.set("Ожидание сервера...")
            self.help_var.set("Теперь можно найти игру")
            
            self.add_message("Система", "Подключение установлено!")
            
        except ValueError:
            messagebox.showerror("Ошибка", "Некорректный порт")
            self.status_var.set("❌ Ошибка порта")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка: {e}")
            self.status_var.set("❌ Ошибка")
    
    def find_game(self):
        """Поиск игры"""
        if not self.connected:
            messagebox.showerror("Ошибка", "Нет подключения")
            self.status_var.set("❌ Нет подключения")
            return
        
        self.send("FIND", {})
        self.status_var.set("🔄 Поиск игры...")
        self.add_message("Система", "Ищем соперника...")
    
    def send(self, cmd, data):
        """Отправка команды"""
        if not self.connected:
            self.add_message("Ошибка", "Нет подключения")
            return False
        
        try:
            message = f"{cmd}|{json.dumps(data, ensure_ascii=False)}\n"
            self.socket.send(message.encode())
            self.add_message("Отправка", f"{cmd}")
            return True
        except ConnectionError:
            self.add_message("Ошибка", "Соединение разорвано")
            self.disconnect()
            return False
        except Exception as e:
            self.add_message("Ошибка", f"Ошибка: {e}")
            return False
    
    def receive(self):
        """Прием сообщений"""
        buffer = ""
        
        while self.connected:
            try:
                data = self.socket.recv(1024)
                if not data:
                    self.add_message("Система", "Сервер отключился")
                    break
                
                buffer += data.decode('utf-8', errors='ignore')
                
                while '\n' in buffer:
                    msg, buffer = buffer.split('\n', 1)
                    if msg:
                        self.root.after(0, self.process_message, msg)
                        
            except ConnectionError:
                self.add_message("Система", "Потеряно соединение")
                break
            except Exception as e:
                self.add_message("Ошибка", f"Ошибка приема: {e}")
                break
        
        self.root.after(0, self.disconnect)
    
    def process_message(self, message):
        """Обработка сообщения"""
        try:
            if '|' not in message:
                return
            
            cmd, data = message.split('|', 1)
            data = json.loads(data)
            
            self.protocol_var.set(f"Получено: {cmd}")
            
            if cmd == "HELLO":
                self.add_message("Сервер", data.get("text", ""))
                
            elif cmd == "JOINED":
                self.add_message("Сервер", f"Привет, {data.get('name')}!")
                
            elif cmd == "WAIT":
                self.status_var.set(f"{data.get('text', '')}")
                self.add_message("Система", data.get("text", ""))
                
            elif cmd == "START":
                self.on_game_start(data)
                
            elif cmd == "BOARD":
                self.on_board_update(data)
                
            elif cmd == "END":
                self.on_game_end(data)
                
            elif cmd == "ERROR":
                error_msg = data.get('text', '')
                self.add_message("Ошибка сервера", error_msg)
                self.waiting_for_server = False
                self.enable_board()
                
            elif cmd == "MSG":
                self.add_message(data.get('from', ''), data.get('text', ''))
                
        except json.JSONDecodeError:
            self.add_message("Ошибка", f"Некорректный JSON")
        except Exception as e:
            self.add_message("Ошибка", f"Ошибка обработки: {e}")
    
    def on_game_start(self, data):
        """Начало игры"""
        self.color = data.get("color", "")
        opponent = data.get("opponent", "")
        board = data.get("board", [])
        
        self.board = board
        self.game_id = 1
        self.my_turn = (self.color == "white")
        self.waiting_for_server = False
        
        self.game_info_var.set(f"Вы: {self.color} | Противник: {opponent}")
        
        if self.my_turn:
            self.turn_info_var.set("✅ ВАШ ХОД!")
            self.help_var.set("Вы ходите первыми. Нажмите на свою шашку")
            self.enable_board()
        else:
            self.turn_info_var.set("⏳ ХОД ПРОТИВНИКА")
            self.help_var.set("Противник ходит первым. Ожидайте...")
            self.disable_board()
        
        self.display_board(board)
        self.resign_btn.config(state=tk.NORMAL)
        
        self.add_message("Система", data.get("text", ""))
        self.status_var.set(f"🎮 Игра с {opponent}")
    
    def on_board_update(self, data):
        """Обновление доски"""
        board = data.get("board", [])
        last_move = data.get("last_move", "")
        turn = data.get("turn", "")
        player = data.get("player", "")
        
        self.board = board
        self.display_board(board)
        
        if last_move:
            self.add_message("Ход", f"{player}: {last_move}")
        
        self.my_turn = (turn == self.color)
        self.waiting_for_server = False
        
        if self.my_turn:
            self.turn_info_var.set("✅ ВАШ ХОД!")
            self.help_var.set("Ваш ход! Нажмите на свою шашку")
            self.enable_board()
        else:
            self.turn_info_var.set("⏳ ХОД ПРОТИВНИКА")
            self.help_var.set("Ожидайте хода противника")
            self.disable_board()
        
        self.selected = None
        self.valid_moves = []
    
    def display_board(self, board):
        """Отображение доски"""
        symbols = {
            'w': '○',
            'W': '♔',
            'b': '●',
            'B': '♚',
            '.': ''
        }
        
        if self.color == "black":
            for row in range(8):
                display_row = 7 - row
                for col in range(8):
                    piece = board[row][col]
                    symbol = symbols.get(piece, '')
                    
                    # ТЁМНЫЕ клетки: (row + col) % 2 == 0 (ИЗМЕНИЛИ!)
                    is_dark = (row + col) % 2 == 1
                    bg_color = '#8B4513' if is_dark else '#F5DEB3'
                    
                    if self.selected and self.selected[0] == row and self.selected[1] == col:
                        bg_color = '#FFFF00'
                    
                    if (row, col) in self.valid_moves:
                        bg_color = '#90EE90'
                    
                    cell = self.cells[display_row][col]
                    
                    if piece in ['w', 'W']:
                        fg_color = 'white'
                    elif piece in ['b', 'B']:
                        fg_color = 'black'
                    else:
                        fg_color = 'black'
                    
                    cell.config(
                        text=symbol,
                        fg=fg_color,
                        bg=bg_color
                    )
        else:
            # Для черных доска как есть
            for row in range(8):
                for col in range(8):
                    piece = board[row][col]
                    symbol = symbols.get(piece, '')
                    
                    # ТЁМНЫЕ клетки: (row + col) % 2 == 0 (ИЗМЕНИЛИ!)
                    is_dark = (row + col) % 2 == 1
                    bg_color = '#8B4513' if is_dark else '#F5DEB3'
                    
                    if self.selected and self.selected[0] == row and self.selected[1] == col:
                        bg_color = '#FFFF00'
                    
                    if (row, col) in self.valid_moves:
                        bg_color = '#90EE90'
                    
                    cell = self.cells[row][col]
                    
                    if piece in ['w', 'W']:
                        fg_color = 'white'
                    elif piece in ['b', 'B']:
                        fg_color = 'black'
                    else:
                        fg_color = 'black'
                    
                    cell.config(
                        text=symbol,
                        fg=fg_color,
                        bg=bg_color
                    )
    
    def enable_board(self):
        """Включить доску для хода"""
        if not self.my_turn or self.waiting_for_server:
            return
    
        for row in range(8):
            for col in range(8):
                # Получаем реальные координаты
                real_row, real_col = self.display_to_real(row, col)
            
                # Проверяем, что это РЕАЛЬНАЯ тёмная клетка
                # Тёмные клетки в реальных координатах: (real_row + real_col) % 2 == 0
                # (потому что в create_board мы инвертировали цвета)
            
                # В create_board: тёмные = (row+col)%2==1
                # Но это для GUI. В реальной логике доски тёмные клетки: (row+col)%2==0
                is_real_dark = (real_row + real_col) % 2 == 1
            
                if is_real_dark:
                    self.cells[row][col].config(state=tk.NORMAL)
                else:
                    self.cells[row][col].config(state=tk.DISABLED)
        
            for row in range(8):
                for col in range(8):
                    # Включаем только ТЁМНЫЕ клетки (row + col) % 2 == 0
                    is_dark = (row + col) % 2 == 1
                    if is_dark:
                        self.cells[row][col].config(state=tk.NORMAL)
    
    def disable_board(self):
        """Отключить доску"""
        for row in range(8):
            for col in range(8):
                self.cells[row][col].config(state=tk.DISABLED)
    
    def get_piece_at(self, row, col):
        """Получить фигуру на позиции"""
        if 0 <= row < 8 and 0 <= col < 8 and self.board:
            return self.board[row][col]
        return '.'
    
    def get_valid_moves_for_piece(self, row, col):
        """Получить возможные ходы для шашки"""
        moves = []
        piece = self.get_piece_at(row, col)
        
        if piece == '.':
            return moves
        
        # Обычные ходы на 1 клетку вперед
        if piece in ['w', 'b']:
            if piece == 'w':  # белые ходят вверх
                moves.append((row-1, col-1)) if row > 0 and col > 0 else None
                moves.append((row-1, col+1)) if row > 0 and col < 7 else None
            elif piece == 'b':  # черные ходят вниз
                moves.append((row+1, col-1)) if row < 7 and col > 0 else None
                moves.append((row+1, col+1)) if row < 7 and col < 7 else None
        
        valid_moves = []
        for r, c in moves:
            if self.get_piece_at(r, c) == '.':
                valid_moves.append((r, c))
        
        return valid_moves
    
    def click(self, row, col):
        """Клик по клетке"""
        if not self.my_turn or self.waiting_for_server or not self.game_id:
            return
        
        # Только ТЁМНЫЕ клетки (row + col) % 2 == 0
        is_dark = (row + col) % 2 == 1
        if not is_dark:
            return
        
        # Конвертируем отображаемую позицию в реальную
        real_row, real_col = self.display_to_real(row, col)
        
        if self.selected is None:
            # Выбор шашки
            piece = self.get_piece_at(real_row, real_col)
            
            if (self.color == "white" and piece not in ['w', 'W']) or \
               (self.color == "black" and piece not in ['b', 'B']):
                self.add_message("Ошибка", "Это не ваша шашка!")
                return
            
            self.selected = (real_row, real_col)
            self.valid_moves = self.get_valid_moves_for_piece(real_row, real_col)
            
            if not self.valid_moves:
                self.add_message("Инфо", "У этой шашки нет ходов")
                self.selected = None
                self.valid_moves = []
                return
            
            pos = self.pos_to_notation(real_row, real_col)
            self.help_var.set(f"Выбрана шашка на {pos}")
            self.display_board(self.board)
            
        else:
            # Ход
            from_row, from_col = self.selected
            to_row, to_col = real_row, real_col
            
            if (to_row, to_col) not in self.valid_moves:
                self.add_message("Ошибка", "Недопустимый ход")
                self.selected = None
                self.valid_moves = []
                self.display_board(self.board)
                return
            
            from_pos = self.pos_to_notation(from_row, from_col)
            to_pos = self.pos_to_notation(to_row, to_col)
            move = f"{from_pos}-{to_pos}"
            
            # Блокируем доску до ответа сервера
            self.waiting_for_server = True
            self.disable_board()
            self.turn_info_var.set("🔄 Ожидание ответа сервера...")
            self.help_var.set(f"Отправлен ход: {move}")
            
            self.send("MOVE", {"move": move})
            
            self.selected = None
            self.valid_moves = []
    
    def display_to_real(self, display_row, display_col):
        """Конвертировать отображаемую позицию в реальную"""
        if self.color == "black":
            real_row = 7 - display_row
        else:
            real_row = display_row
        return real_row, display_col
    
    def pos_to_notation(self, row, col):
        """Конвертировать позицию в нотацию"""
        letter = chr(ord('a') + col)
        number = 8 - row
        return f"{letter}{number}"
    
    def on_game_end(self, data):
        """Конец игры"""
        winner = data.get("winner", "")
        text = data.get("text", "")
        
        self.add_message("Система", text)
        messagebox.showinfo("Конец игры", text)
        
        self.game_id = None
        self.color = ""
        self.my_turn = False
        self.selected = None
        self.valid_moves = []
        self.waiting_for_server = False
        self.board = []
        
        self.game_info_var.set("Не в игре")
        self.turn_info_var.set("")
        self.help_var.set("Игра окончена")
        self.resign_btn.config(state=tk.DISABLED)
        
        self.disable_board()
        for row in range(8):
            for col in range(8):
                is_dark = (row + col) % 2 == 0
                color = '#8B4513' if is_dark else '#F5DEB3'
                self.cells[row][col].config(text="", bg=color)
    
    def resign(self):
        """Сдача"""
        if messagebox.askyesno("Сдача", "Вы уверены?"):
            self.send("QUIT", {})
    
    def disconnect(self):
        """Отключение"""
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
        
        self.connected = False
        self.connection_attempted = False
        
        self.connect_btn.config(state=tk.NORMAL)
        self.find_btn.config(state=tk.DISABLED)
        self.resign_btn.config(state=tk.DISABLED)
        
        self.status_var.set("❌ Отключено")
        self.protocol_var.set("Отключено от сервера")
        self.help_var.set("Подключитесь к серверу")
        
        self.disable_board()
        for row in range(8):
            for col in range(8):
                is_dark = (row + col) % 2 == 0
                color = '#8B4513' if is_dark else '#F5DEB3'
                self.cells[row][col].config(text="", bg=color)
        
        self.add_message("Система", "Отключено от сервера")
    
    def add_message(self, sender, message):
        """Добавление сообщения"""
        self.msg_text.config(state=tk.NORMAL)
        timestamp = time.strftime("%H:%M:%S")
        
        if sender:
            self.msg_text.insert(tk.END, f"[{timestamp}] {sender}: {message}\n")
        else:
            self.msg_text.insert(tk.END, f"[{timestamp}] {message}\n")
        
        lines = self.msg_text.get('1.0', tk.END).split('\n')
        if len(lines) > 15:
            self.msg_text.delete('1.0', f'{len(lines)-15}.0')
        
        self.msg_text.see(tk.END)
        self.msg_text.config(state=tk.DISABLED)
    
    def on_closing(self):
        """Закрытие окна"""
        if self.connected:
            if messagebox.askokcancel("Выход", "Отключиться и выйти?"):
                self.disconnect()
                self.root.destroy()
        else:
            self.root.destroy()
    
    def run(self):
        """Запуск клиента"""
        self.root.mainloop()

if __name__ == "__main__":
    print("="*60)
    print("🎯 КЛИЕНТ ШАШЕК - ИСПРАВЛЕННЫЕ ЦВЕТА КЛЕТОК")
    print("ТЁМНЫЕ клетки: (row + col) % 2 == 0")
    print("СВЕТЛЫЕ клетки: (row + col) % 2 == 1")
    print("Шашки теперь на тёмных клетках ✓")
    print("="*60)
    
    client = CheckersClient()
    client.run()