"""
.. include:: ./README.md
"""

import random
from dataclasses import dataclass
from enum import Enum
from typing import List

import pygame

__all__ = [
    "MoveResult",
    "Direction",
    "Coordinate",
    "SnakeGame",
    "SnakeCanvas",
    "Canvas",
    "FPSFrames",
    "run_game",
]


class MoveResult(Enum):
    """
    This is the result of SnakeGame.move method.
    This indicate what happened during the move.
    """

    OK = "ok"
    OVERFLOW = "overflow"
    COLISION = "colision"

    @property
    def is_lost(self):
        """
        Indicate if this result indicates that the player lost
        """
        return self in (MoveResult.COLISION, MoveResult.COLISION)


class Direction(Enum):
    LEFT = "left"
    RIGHT = "right"
    UP = "up"
    DOWN = "down"

    def get_opposite(self):
        """
        Returns the opposite direction
        """
        return OPPOSITE_DIRECTIONS_MAP[self]

    def is_opposed(self, direction: "Direction"):
        """
        Returns True if the directions are opposite to each others
        """
        return self.get_opposite() == direction


# NOTE: Keep this global variables close to Direction enum
OPPOSITE_DIRECTIONS = (
    (Direction.LEFT, Direction.RIGHT),
    (Direction.UP, Direction.DOWN),
)

OPPOSITE_DIRECTIONS_MAP = {
    Direction.LEFT: Direction.RIGHT,
    Direction.RIGHT: Direction.LEFT,
    Direction.UP: Direction.DOWN,
    Direction.DOWN: Direction.UP,
}


@dataclass
class Coordinate:
    """
    Represents a 2-d discret coordinate
    """

    x: int
    y: int

    def totuple(self):
        """
        Convert the coordinate to a tuple (x, y)
        """
        return (self.x, self.y)

    def __iter__(self):
        yield self.x
        yield self.y

    def __eq__(self, value: object) -> bool:
        if value is None:
            return False
        if not isinstance(value, Coordinate):
            raise NotImplementedError()
        return self.totuple() == value.totuple()

    def __hash__(self) -> int:
        return hash(self.totuple())

    # NOTE: The x-axis goes right
    def left(self):
        """
        Returns the coordinate on the left
        """
        return Coordinate(self.x - 1, self.y)

    def right(self):
        """
        Returns the coordinate on the right
        """
        return Coordinate(self.x + 1, self.y)

    # NOTE: The y-axis goes down
    def up(self):
        """
        Returns the coordinate above
        """
        return Coordinate(self.x, self.y - 1)

    def down(self):
        """
        Returns the coordinate below
        """
        return Coordinate(self.x, self.y + 1)

    def overflows(self, width, height):
        """
        Compute the new coordinate as if going out of
        the boundaries would teleports you to the other side.
        """
        return Coordinate(self.x % width, self.y % height)

    def is_outside(self, width, height):
        """
        Check if a coordinate is out of defined boundaries.
        """
        if self.x < 0 or self.x >= width:
            return True
        if self.y < 0 or self.y >= height:
            return True
        return False


class SnakeGame:
    """
    Represents all the computations for the snake's game.
    This does not handle the display.
    """

    def __init__(self, width, height, start_len=3, overflows_allowed=True):
        """ """
        self._width = width
        self._height = height
        self._start_len = start_len
        self._overflows_allowed = overflows_allowed
        self._direction = Direction.RIGHT
        self._snake = [  # NOTE: an ordered-set would have been better
            Coordinate(i, 0) for i in range(start_len)
        ]
        self._all_coordinates = {
            Coordinate(x, y) for x in range(self._width) for y in range(self._height)
        }
        self._apple = None
        self._new_apple()

    # Map operations

    def _get_free_coordinates(self):
        """
        Returns all the coordinates that don't contain
        a part of the snake's body
        """
        return self._all_coordinates - set(self._snake)

    def _get_n_random_free_coordinates(self, n):
        """
        Find `n` random cells that does not contains
        a part of the snake
        """
        free_coords = list(self._get_free_coordinates())
        if n > free_coords:
            return None
        return random.sample(free_coords, n)

    def _get_random_free_coordinate(self):
        """
        Find a random cell that does not contains
        a part of the snake
        """
        free_coords = list(self._get_free_coordinates())
        if not free_coords:
            return None
        # NOTE: `random` library is cryptographically bad
        # So we get errors from static analyze tools
        # But this is fine for us here, so we can ignore them
        return random.choice(free_coords)  # nosec # noqa: S311

    def _new_apple(self):
        """
        Find a new coordinate for the apple
        """
        self._apple = self._get_random_free_coordinate()

    # Movements
    @property
    def head(self):
        """
        The coordinate of the snake's head
        """
        return self._snake[-1]

    @property
    def tail(self):
        """
        The coordinate of the snake's tail
        """
        return self._snake[0]

    @property
    def width(self):
        """
        Total number of cell horizontally
        """
        return self._width

    @property
    def height(self):
        """
        Total number of cell vertically
        """
        return self._height

    def get_snake(self):
        """
        Returns the coordinates of the snake body
        """
        return self._snake[:]

    def get_apple(self):
        """
        Returns the coordinate of the apple
        """
        return self._apple

    @property
    def score(self):
        """
        Returns the current score of the player
        """
        # Compute instead of keeping the count manually
        return len(self._snake) - self._start_len

    def _next_coord(self):
        """
        Get the next coordinate of the snake's head
        based on its current location and the snake's direction.
        """
        d = self._direction
        if d == Direction.LEFT:
            return self.head.left()
        if d == Direction.RIGHT:
            return self.head.right()
        if d == Direction.UP:
            return self.head.up()
        if d == Direction.DOWN:
            return self.head.down()
        raise Exception(f"Invalid direction {d}")

    def set_direction(self, direction: Direction):
        """
        Set the active direction of the snake.
        Each time the snake moves, it moves according to its active direction.
        """
        if self._direction.is_opposed(direction):
            return
        self._direction = direction

    # This function does all the logic
    def move(self) -> MoveResult:
        """
        Move the snake in the current direction.
        Handle all the logic like colision or getting a bonus.

        This returns the result of what happened
        """
        coordinate = self._next_coord()
        # If the game does not allow overflowing, then loose
        if coordinate.is_outside(self._width, self._height):
            if not self._overflows_allowed:
                return MoveResult.OVERFLOW
            coordinate = coordinate.overflows(self._width, self._height)

        # Check colisions
        if coordinate != self.tail and coordinate in self._snake:
            return MoveResult.COLISION

        # Check if it ate the apple
        self._snake.append(coordinate)
        if coordinate == self._apple:
            # The snake grows => do not remove the tail
            self._new_apple()
        else:
            # Remove the tail to keep the same size
            self._snake.pop(0)
        return MoveResult.OK


class SnakeCanvas:
    def __init__(self, game, unit=30, position=(0, 0)):
        self._unit = unit  # in pixels
        self._game = game
        self._position = position
        self._border = 1
        self._margin = 10

    @property
    def x(self):
        """
        Top-left corner x-coordinate of the game canvas
        """
        return self._position[0]

    @property
    def y(self):
        """
        Top-left corner y-coordinate of the game canvas
        """
        return self._position[1]

    @property
    def _iwidth(self):
        """
        The width within the game's borders
        """
        return self._game.width * self._unit

    @property
    def _iheight(self):
        """
        The height within the game's borders
        """
        return self._game.height * self._unit

    @property
    def width(self):
        """
        The full width of the game (considering borders and margin)
        """
        return self._iwidth + self._border * 2 + self._margin * 2

    @property
    def height(self):
        """
        The full height of the game (considering borders and margin)
        """
        return self._iheight + self._border * 2 + self._margin * 2

    def _draw_coord(self, screen, coord: Coordinate, color):
        """
        Utility function to draw an rectangle on the map.
        NOTE: everything is just a rectangle for now,
        we differentiate the elements based on their color.
        """
        u = self._unit
        xoffset = self.x + self._border + self._margin
        yoffset = self.y + self._border + self._margin
        pygame.draw.rect(
            screen,
            color,
            pygame.Rect(
                (
                    coord.x * u + xoffset,
                    coord.y * u + yoffset,
                ),
                (u, u),
            ),
        )

    def _draw_border(self, screen):
        """
        Utility function to borders of the game.
        """
        thickness = 1
        x = self.x + self._margin
        y = self.y + self._margin
        pygame.draw.rect(
            screen,
            "black",
            pygame.Rect(
                (x, y),
                (self._iwidth, self._iheight),
            ),
            width=thickness,
        )

    def _draw_apple(self, screen, apple: Coordinate):
        self._draw_coord(screen, apple, "red")

    def _draw_snake(self, screen, snake: List[Coordinate]):
        for coord in snake:
            self._draw_coord(screen, coord, "green")

    def set_position(self, position):
        self._position = position

    def draw(self, screen, border=True):
        self._draw_apple(screen, self._game.get_apple())
        self._draw_snake(screen, self._game.get_snake())
        if border:
            self._draw_border(screen)


class Canvas:
    def __init__(self, game: SnakeGame):
        snake = SnakeCanvas(game)
        self._snake_canvas = snake
        self._screen = pygame.display.set_mode((snake.width, snake.height))

    def clear(self):
        """
        Remove everything from the current display.
        """
        self._screen.fill("white")

    def draw_game(self):
        """
        Render all the elements of the game
        """
        self._snake_canvas.draw(self._screen)

    def display(self):
        """
        Show the new frame.
        NOTE: This works using the double-buffering strategy
        See "Software double buffering" in https://en.wikipedia.org/wiki/Multiple_buffering
        """
        pygame.display.flip()


class FPSFrames:
    """
    Utility class to manage the game loop.
    - It yields every frames
    - We can stop it smoothly
    """

    def __init__(self, fps=60, start_index=1):
        self._start_index = start_index
        self._fps = fps
        self._running = True

    def stop(self):
        """
        Stop the game loop
        """
        self._running = False

    def __iter__(self):
        """
        Yield the current frame on each loop
        """
        clock = pygame.time.Clock()
        i = self._start_index
        fps = self._fps
        while self._running:
            yield i
            i += 1
            clock.tick(fps)  # limits FPS to 60


WIDTH, HEIGHT = 15, 15


# Base exemple taken from the documentation:
# https://www.pygame.org/docs/


def run_game(width=WIDTH, height=HEIGHT):
    """
    Run the snake game.
    Upon losing, the game closes itself
    and the score is displayed in the terminal
    """
    # pygame setup
    pygame.init()

    game = SnakeGame(width, height)
    canvas = Canvas(game)
    frames = FPSFrames()
    for f in frames:
        # poll for events
        # pygame.QUIT event means the user clicked X to close your window
        # https://www.pygame.org/docs/ref/event.html
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                frames.stop()
            if event.type == pygame.KEYDOWN:
                key = event.key
                if key == pygame.K_LEFT:
                    game.set_direction(Direction.LEFT)
                elif key == pygame.K_RIGHT:
                    game.set_direction(Direction.RIGHT)
                elif key == pygame.K_UP:
                    game.set_direction(Direction.UP)
                elif key == pygame.K_DOWN:
                    game.set_direction(Direction.DOWN)

        # Don't move each frame, this would be too fast
        # NOTE: This is a drity trick, we should instead use the elapsed time
        if f % 4 == 0:
            res = game.move()
            if res.is_lost:
                print(f"Final Score: {game.score}")
                frames.stop()

        # fill the screen with a color to wipe away anything from last frame
        canvas.clear()
        canvas.draw_game()
        canvas.display()

        # For snake, we could use the FPS to handle the speed to simplify
        # clock.tick(10)  # limits FPS to 60

    pygame.quit()


if __name__ == "__main__":
    run_game()
