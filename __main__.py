#!/usr/bin/env python
import random
import sys
import matplotlib.pyplot as plt
from typing import List

import numpy as np

from src.Action import Action
from src.Point2D import Point2D
import time
import math
from src.Rocket import Rocket
from src.create_Q_table import create_q_table

gravity = 3.711


def parse_mars_surface() -> List[Point2D]:
    return [Point2D(int(x), int(y)) for x, y in (input().split(' ') for _ in range(int(input())))]


def create_graph(points: List[Point2D], title: str):
    plt.xlim(0, 7000)
    plt.ylim(0, 3000)
    plt.xlabel('X Coordinate')
    plt.ylabel('Y Coordinate')
    plt.title(title)
    plt.plot(*zip(*[(point.x, point.y) for point in points]), marker='o', label='Mars Surface')
    plt.legend()
    plt.grid(True)
    plt.draw()


def compute_next_turn_rocket(rocket: Rocket):
    radians = rocket.rotation * (math.pi / 180)
    x_acceleration = math.sin(radians) * rocket.power
    y_acceleration = math.cos(radians) * rocket.power - gravity
    new_horizontal_speed = rocket.hs - x_acceleration
    new_vertical_speed = rocket.vs + y_acceleration
    new_x = rocket.x + new_horizontal_speed - x_acceleration * 0.5
    new_y = rocket.y + new_vertical_speed + y_acceleration * 0.5 + gravity
    return new_x, new_y, new_horizontal_speed, new_vertical_speed

#
# RL is
#  - Optimization
#  - Delayed consequences
#  - Exploration
#  - Generalization (my agent has been trained with a specific environment
#       but I'd like it to be effective on future unknown environment as well
#
if __name__ == '__main__':
    turn = 0
    init_rocket = Rocket(2500, 2700, 0, 0, 550, 0, 0)
    rocket = init_rocket
    print('INFO: this program is meant to be launched with an test-case as input.')
    mars_surface = parse_mars_surface()

    q_table = create_q_table(mars_surface)
    exit(0)
    scatter = plt.scatter(rocket.x, rocket.y, color='red', label='Rocket')
    create_graph(mars_surface, 'Landing on Mars')
    while True:
        turn += 1
        x, y, hs, vs = compute_next_turn_rocket(rocket)
        #legal_actions = create_legal_actions(rocket.rotation, rocket.power)  # TODO unused
        rocket = Rocket(x, y, hs, vs, rocket.state.fuel, rocket.state.rotation, rocket.state.power)
        time.sleep(0.1)
        if rocket.y <= 0:
            break
        rotation_chosen = rocket.rotation
        power_chosen = rocket.power
        print(
            f"Turn: {turn} nextX: {rocket.x} nextY: {rocket.y} My actions. Rocket Rotation: {rocket.rotation} Rocket Power: {rocket.power}")
        scatter.set_offsets([rocket.x, rocket.y])
        plt.pause(0.01)

    print(mars_surface, file=sys.stderr)
