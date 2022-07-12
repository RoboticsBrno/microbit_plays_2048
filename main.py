# Import the pygame module
import pygame
import random
import time
import enum
import sys
import serial
import re
from py2048_classes import Board

# Import pygame.locals for easier access to key coordinates
# Updated to conform to flake8 and black standards
from pygame.locals import (
    K_UP,
    K_DOWN,
    K_LEFT,
    K_RIGHT,
    K_ESCAPE,
    KEYDOWN,
    QUIT,
)

# Colours
TEXT_DARK = pygame.Color(119, 110, 100)
TEXT_LIGHT = pygame.Color(255, 255, 255)
BACKGROUND = pygame.Color(188, 173, 159)
EMPTY = pygame.Color(206, 192, 179)
TILE_MAX = pygame.Color(18, 91, 146)

CELL_STYLES = {
    0: {"font": TEXT_DARK, "fill": EMPTY},
    1: {"font": TEXT_DARK, "fill": pygame.Color(239, 229, 218)},
    2: {"font": TEXT_DARK, "fill": pygame.Color(238, 225, 199)},
    3: {"font": TEXT_LIGHT, "fill": pygame.Color(242, 177, 121)},
    4: {"font": TEXT_LIGHT, "fill": pygame.Color(245, 149, 99)},
    5: {"font": TEXT_LIGHT, "fill": pygame.Color(247, 127, 96)},
    6: {"font": TEXT_LIGHT, "fill": pygame.Color(246, 94, 59)},
    7: {"font": TEXT_LIGHT, "fill": pygame.Color(241, 219, 147)},
    8: {"font": TEXT_LIGHT, "fill": pygame.Color(237, 204, 97)},
    9: {"font": TEXT_LIGHT, "fill": pygame.Color(235, 193, 57)},
    10: {"font": TEXT_LIGHT, "fill": pygame.Color(231, 181, 23)},
    11: {"font": TEXT_DARK, "fill": pygame.Color(192, 154, 16)},
    12: {"font": TEXT_LIGHT, "fill": pygame.Color(94, 218, 146)},
    13: {"font": TEXT_LIGHT, "fill": pygame.Color(37, 187, 100)},
    14: {"font": TEXT_LIGHT, "fill": pygame.Color(35, 140, 81)},
    15: {"font": TEXT_LIGHT, "fill": pygame.Color(113, 180, 213)},
    16: {"font": TEXT_LIGHT, "fill": pygame.Color(25, 130, 205)},
}

# Define constants for the screen width and height
DPI_MUL = 1.25
BORDER_WIDTH = 10
TILE_SIZE = 100*DPI_MUL
NUMBER_OF_ROWS = NUMBER_OF_COLUMNS = 4
SCREEN_WIDTH = SCREEN_HEIGHT = ((NUMBER_OF_ROWS + 1) * BORDER_WIDTH) + (NUMBER_OF_ROWS * TILE_SIZE)

FONT_SIZE = int(24*DPI_MUL)

MOVE_TIMER = 10



class Tile(pygame.sprite.Sprite):

    def __init__(self, row, column):
        super(Tile, self).__init__()
        self.font = pygame.font.Font(pygame.font.get_default_font(), FONT_SIZE)
        self.x_pos = BORDER_WIDTH + (row * (BORDER_WIDTH + TILE_SIZE))
        self.y_pos = BORDER_WIDTH + (column * (BORDER_WIDTH + TILE_SIZE))
        self.surface = pygame.Surface((TILE_SIZE, TILE_SIZE))
        self.value = None
        self.update(None)

        self.tile_id = 0

    def update(self, tile):
        value = tile.get_value() if tile else None
        self.change_fill(value)
        self.change_text(value)
        self.tile_id = tile.id if tile else 0
        self.value = value

    def changed(self):
        return self.x_pos != self.prev_x or self.y_pos != self.prev_y

    def change_text(self, value):
        if value:
            if value in CELL_STYLES:
                text_colour = CELL_STYLES[value]["font"]
            else:
                text_colour = TEXT_LIGHT
            text_surface = self.font.render(str(2 ** value), True, text_colour, None)
            text_rectangle = text_surface.get_rect(center=(TILE_SIZE/2, TILE_SIZE/2))
            self.surface.blit(text_surface, text_rectangle)

    def change_fill(self, value):
        if value:
            if value in CELL_STYLES:
                fill_colour = CELL_STYLES[value]["fill"]
            else:
                fill_colour = TILE_MAX
        else:
            fill_colour = EMPTY
        self.surface.fill(fill_colour)

class Command(enum.IntEnum):
    LEFT = 0
    RIGHT = 1
    DOWN = 2
    UP = 3
    RESTART = 4

class Game:

    def __init__(self, board):
        self.board = board
        # Set up group to hold tile sprite objects
        self.all_tiles = pygame.sprite.Group()
        # The size is determined by the constant SCREEN_WIDTH and SCREEN_HEIGHT
        self.screen = pygame.display.set_mode((SCREEN_WIDTH*2, SCREEN_HEIGHT))
        self.screen.fill(BACKGROUND)
        # Initial the 16 tiles as sprites
        self.tiles = self.initialise_tiles()


        self.score_font = pygame.font.SysFont('Arial', int(80*DPI_MUL))
        self.info_font = pygame.font.SysFont("Arial", int(25*DPI_MUL))
        self.votes_font = pygame.font.SysFont("Arial", int(40*DPI_MUL))

        self.next_move = time.monotonic() + MOVE_TIMER
        self.votes = [ 0 for _ in Command ]

        self.draw_tiles()

    def initialise_tiles(self):
        tiles = []
        for row in range(0, NUMBER_OF_ROWS):
            row_of_tiles = []
            for column in range(0, NUMBER_OF_COLUMNS):
                tile = Tile(row, column)
                row_of_tiles.append(tile)
                self.all_tiles.add(tile)
            tiles.append(row_of_tiles)
        return tiles

    def update_tiles(self, tile_values):
        moves = {}
        for row in range(0, NUMBER_OF_ROWS):
            for column in range(0, NUMBER_OF_COLUMNS):
                t = tile_values[row][column]
                gt = self.tiles[row][column]

                if (t is None and gt.tile_id != 0) or (t is not None and t.id != gt.tile_id):
                    if t and t.id != 0:
                        d = moves.setdefault(t.id, {})
                        d["to"] = (row, column)
                        d["gametile"] = t
                    if gt.tile_id != 0:
                        d = moves.setdefault(gt.tile_id, {})
                        d["from"] = (row, column)
                        d["tile"] = gt

        anim_tiles = []
        STEPS = 20
        for _, m in moves.items():
            if "from" not in m or "to" not in m:
                continue
            src_tile = m["tile"]
            move_tile = Tile(m["from"][0], m["from"][1])
            move_tile.change_fill(src_tile.value)
            move_tile.change_text(src_tile.value)
            src_tile.update(None)
            dest_tile = self.tiles[m["to"][0]][m["to"][1]]


            anim_tiles.append({
                "tile": move_tile,
                "orig_x": src_tile.x_pos,
                "orig_y": src_tile.y_pos,
                "step_x": (dest_tile.x_pos - src_tile.x_pos) / STEPS,
                "step_y": (dest_tile.y_pos - src_tile.y_pos) / STEPS,
            })


        if anim_tiles:
            for _ in range(STEPS):
                for d in anim_tiles:
                    d["tile"].x_pos += d["step_x"]
                    d["tile"].y_pos += d["step_y"]

                self.draw_tiles()
                for d in anim_tiles:
                    self.screen.blit(d["tile"].surface, (d["tile"].x_pos, d["tile"].y_pos))
                pygame.display.flip()
                time.sleep(0.01)

            for d in anim_tiles:
                d["tile"].x_pos = d["orig_x"]
                d["tile"].y_pos = d["orig_y"]

        for row in range(0, NUMBER_OF_ROWS):
            for column in range(0, NUMBER_OF_COLUMNS):
                t = tile_values[row][column]
                self.tiles[row][column].update(t)

    def draw_tiles(self):
        self.screen.fill(BACKGROUND)
        for tile in self.all_tiles:
            self.screen.blit(tile.surface, (tile.x_pos, tile.y_pos))


        score = self.score_font.render(str(self.board.score), True, (0, 0, 0))
        self.screen.blit(score, (SCREEN_WIDTH + SCREEN_WIDTH/2 - score.get_width()/2, 70))

        info = self.info_font.render(f"Next move in {int(self.next_move - time.monotonic())}s", True, (0, 0, 0))
        self.screen.blit(info, (SCREEN_WIDTH + 10, 250))

        x = SCREEN_WIDTH + 10
        vote_w = (SCREEN_WIDTH - 20) / len(self.votes)

        max_votes = max(self.votes)
        if max_votes == 0:
            max_votes = -1

        for idx, votes in enumerate(self.votes):
            cmd = Command(idx)

            name = self.info_font.render(cmd.name, True, (0, 0, 0))
            self.screen.blit(name, (x + vote_w/2 - name.get_width()/2, SCREEN_HEIGHT-80))

            amount = self.votes_font.render(str(votes), True, (200, 0, 0) if votes == max_votes else (100, 100, 100))
            self.screen.blit(amount, (x + vote_w/2 - amount.get_width()/2, SCREEN_HEIGHT-200))
            x += vote_w

    @staticmethod
    def convert_grid(grid):

        tile_values = []

        for row in range(0, NUMBER_OF_ROWS):
            row_of_tiles = []
            for column in range(0, NUMBER_OF_COLUMNS):
                if grid[column][row]:
                    row_of_tiles.append(grid[column][row])
                else:
                    row_of_tiles.append(None)
            tile_values.append(row_of_tiles)
        return tile_values


def make_move(board, game, move):
    if move is not None and board.make_move(move):
        add_tile_result = board.add_random_tiles(1)
        game.update_tiles(Game.convert_grid(board.grid))
        game.draw_tiles()
        pygame.display.flip()

def parse(input):
    try:
        input = input.decode('ascii').rstrip().lstrip()
    except Exception:
        return None
    data = re.split(r" +", input)

    if len(data) < 2:
        return None

    return data


backoff_dict = {}
def handle_cmd(game, toks):
    user_id = toks[0]
    command_str = toks[1]
    print(f"{user_id} {command_str}")

    try:
        cmd = Command[command_str.upper()]
    except Exception:
        return

    if user_id in backoff_dict:
        return
    backoff_dict[user_id] = True
    game.votes[cmd.value] += 1


def main():

    # Initialize pygame
    pygame.init()
    pygame.font.init()

    board = Board()
    game = Game(board)
    board.add_random_tiles(2)
    game.update_tiles(Game.convert_grid(board.grid))
    game.draw_tiles()
    pygame.display.flip()


    # Variable to keep the main loop running
    running = True

    pygame.time.set_timer(pygame.USEREVENT, 300)
    pygame.time.set_timer(pygame.USEREVENT_DROPFILE, 100)

    with serial.Serial(sys.argv[1], 115200, timeout=0) as ser:

        # Main loop
        while running:
            # Look at every event in the queue
            event = pygame.event.wait()
            if True:
                # Did the user hit a key?
                if event.type == KEYDOWN:
                    # Was it the Escape key? If so, stop the loop.
                    if event.key == K_ESCAPE:
                        running = False
                    else:
                        if event.key == K_UP:
                            move = 'UP'
                        elif event.key == K_LEFT:
                            move = 'LEFT'
                        elif event.key == K_DOWN:
                            move = 'DOWN'
                        elif event.key == K_RIGHT:
                            move = 'RIGHT'
                        else:
                            move = None

                        make_move(board, game, move)

                # Did the user click the window close button? If so, stop the loop.
                elif event.type == QUIT:
                    running = False
                elif event.type == pygame.USEREVENT_DROPFILE:
                    while True:
                        line = ser.readline()
                        if len(line) == 0:
                            break
                        toks = parse(line)
                        if toks is None:
                            continue

                        handle_cmd(game, toks)
                elif event.type == pygame.USEREVENT:
                    game.draw_tiles()
                    pygame.display.flip()

                    if time.monotonic() > game.next_move:

                        max_votes = max(game.votes)
                        if max_votes > 0:
                            idx = game.votes.index(max_votes)
                            cmd = Command(idx)
                            if cmd == Command.RESTART:
                                board = Board()
                                game = Game(board)
                                board.add_random_tiles(2)
                                game.update_tiles(Game.convert_grid(board.grid))
                                game.draw_tiles()
                                pygame.display.flip()
                            else:
                                make_move(board, game, cmd.name)

                        global backoff_dict
                        backoff_dict = {}
                        game.next_move = time.monotonic() + MOVE_TIMER

                        for idx in range(len(game.votes)):
                            game.votes[idx] = 0


if __name__ == "__main__":
    main()
