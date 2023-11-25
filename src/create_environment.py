import math
import random

import numpy as np
from scipy.spatial import distance
from itertools import product

import torch
from matplotlib import pyplot as plt

from src.hyperparameters import limit_actions, GRAVITY, actions_min_max


# TODO changer GRID to function
# False = underneath the surface
def create_env(surface_points: list, x_max: int, y_max: int) -> list[list[bool]]:
    def surface_function(x, sorted_points):
        for i in range(len(sorted_points) - 1):
            x1, y1 = sorted_points[i][0], sorted_points[i][1]
            x2, y2 = sorted_points[i + 1][0], sorted_points[i + 1][1]
            if x1 <= x <= x2:
                return round(y1 + (x - x1) * (y2 - y1) / (x2 - x1))
        return 0

    world = [[False] * x_max for _ in range(y_max)]
    sorted_points = sorted(surface_points, key=lambda p: p[0])

    for x in range(x_max):
        for y in range(surface_function(x, sorted_points), y_max):
            world[y][x] = True
    return world


def distance_to_line_segment(point, landing_spot_points: list):
    def squared_distance(p1, p2):
        return np.sum((p1 - p2) ** 2)

    landing_spot_left = landing_spot_points[0]
    landing_spot_right = landing_spot_points[-1]
    if landing_spot_left[0] < point[0] < landing_spot_right[0] and point[1] < landing_spot_left[1]:
        return 0
    if point[0] < landing_spot_left[0]:
        return squared_distance(point, landing_spot_left)
    elif point[0] > landing_spot_right[0]:
        return squared_distance(point, landing_spot_right)
    distance = np.inf
    for landing_spot_point in landing_spot_points:
        squared_dist = squared_distance(point, landing_spot_point)
        if squared_dist < distance:
            distance = squared_dist
    return distance



def point_to_line_distance(point, line_segments):
    line_segments = np.array(line_segments)
    distances = []

    for i in range(len(line_segments) - 1):
        p1, p2 = line_segments[i], line_segments[i + 1]
        d = distance.euclidean(point, closest_point_on_segment(point, p1, p2))
        distances.append(d)

    return min(distances)


def closest_point_on_segment(point, p1, p2):
    p1 = np.array(p1)
    p2 = np.array(p2)
    v = p2 - p1
    w = point - p1

    c1 = np.dot(w, v)
    c2 = np.dot(v, v)

    if c1 <= 0:
        return p1
    elif c2 <= c1:
        return p2
    else:
        b = c1 / c2
        pb = p1 + b * v
        return pb


# def distance_to_surface(additional_point, surface_points):
#     def surface_function(x, sorted_points):
#         for i in range(len(sorted_points) - 1):
#             x1, y1 = sorted_points[i][0], sorted_points[i][1]
#             x2, y2 = sorted_points[i + 1][0], sorted_points[i + 1][1]
#             if x1 <= x <= x2:
#                 return y1 + (x - x1) * (y2 - y1) / (x2 - x1)
#         return 0
#
#     def distance_to_linear(x, y, x1, y1, x2, y2):
#         # Calculate the distance from a point (x, y) to the line defined by (x1, y1) and (x2, y2)
#         numerator = np.abs((y2 - y1) * x - (x2 - x1) * y + x2 * y1 - y2 * x1)
#         denominator = np.sqrt((y2 - y1)**2 + (x2 - x1)**2)
#         return numerator / denominator
#
#     sorted_points = sorted(surface_points, key=lambda p: p[0])
#     closest_distance = distance_to_linear(additional_point[0], additional_point[1],
#                                           sorted_points[0][0], surface_function(sorted_points[0][0], sorted_points),
#                                           sorted_points[1][0], surface_function(sorted_points[1][0], sorted_points))
#
#     for i in range(1, len(sorted_points) - 1):
#         distance = distance_to_linear(additional_point[0], additional_point[1],
#                                       sorted_points[i][0], surface_function(sorted_points[i][0], sorted_points),
#                                       sorted_points[i + 1][0], surface_function(sorted_points[i + 1][0], sorted_points))
#         closest_distance = min(closest_distance, distance)
#     return closest_distance

def display_grid(grid):
    # Convert the boolean values to integers (0 for False, 1 for True)
    array_data = np.array(grid, dtype=int)

    # Plot the binary image
    plt.imshow(array_data, cmap='binary', interpolation='none', origin='lower')
    plt.show()


class RocketLandingEnv:
    def __init__(self, initial_state: tuple,
                 landing_spot,
                 grid,
                 surface: np.ndarray,
                 landing_spot_points):
        self.feature_amount = len(initial_state)
        self.initial_state = initial_state
        self.state = np.array(initial_state)
        self.landing_spot = landing_spot
        self.landing_spot_points = landing_spot_points
        self.grid = grid
        self.surface_points = surface

        self.raw_intervals = [
            [0, 7000],  # x
            [0, 3000],  # y
            [-500, 500],  # vs
            [-500, 500],  # hs
            [-10, 20000],  # fuel remaining
            [-90, 90],  # rot
            [0, 4],  # thrust
            [-100, 10000],  # dist landing_spot
            [-100, 10000]  # distance surface
        ]
        self.action_constraints = [15, 1]

    @staticmethod
    def normalize_state(raw_state, raw_intervals):
        normalized_state = [(val - interval[0]) / (interval[1] - interval[0]) for val, interval in
                            zip(raw_state, raw_intervals)]
        return np.array(normalized_state)

    @staticmethod
    def denormalize_state(normalized_state, raw_intervals):
        # cpu_state = normalized_state.cpu().numpy()
        cpu_state = normalized_state
        denormalized_state = [val * (interval[1] - interval[0]) + interval[0]
                              for val, interval in
                              zip(cpu_state, raw_intervals)]
        return np.array(denormalized_state)

    @staticmethod
    def denormalize_action(raw_output):
        def sig(x):
            return 1 / (1 + np.exp(-np.clip(x, -700, 700)))

        output_dim1 = np.round(np.tanh(raw_output[0]) * 90.0)
        output_dim2 = np.round(sig(raw_output[1]) * 4.0)
        output = np.array([output_dim1, output_dim2], dtype=int)
        return output

    @staticmethod
    def normalize_action(action):
        def inv_sig(x):
            epsilon = 1e-10
            x = np.clip(x, epsilon, 1 - epsilon)
            return np.log(x / (1 - x))

        norm_dim1 = np.tanh(action[0] / 90)
        norm_dim2 = inv_sig(action[1] / 4.0)
        normalized_output = np.array([norm_dim1, norm_dim2])
        return normalized_output

    def get_action_constraints(self, previous_action):
        if previous_action is None:
            return [self.normalize_action([-15, 0]), self.normalize_action([15, 1])]
        action = self.denormalize_action(previous_action)
        legal_min_max = actions_min_max(action)
        minimun = self.normalize_action((legal_min_max[0][0], legal_min_max[1][0]))
        maximun = self.normalize_action((legal_min_max[0][1], legal_min_max[1][1]))
        return [minimun, maximun]

    def reset(self):
        self.state = np.array(self.initial_state)
        return self.normalize_state(self.state, self.raw_intervals)

    def step(self, action: tuple[int, int]):
        # action = self.action_space[action_index]
        next_state = self.compute_next_state(self.state, action)
        self.state = next_state
        reward, done = reward_function(next_state, self.grid, self.landing_spot)
        next_state = self.normalize_state(next_state, self.raw_intervals)
        return next_state, reward, done, None

    def generate_random_action(self, old_rota: int, old_power_thrust: int) -> tuple[int, tuple[int, int]]:
        action_min_max = actions_min_max((old_power_thrust, old_rota))
        random_action = (
            random.randint(action_min_max[1][0], action_min_max[1][1]),
            random.randint(action_min_max[0][0], action_min_max[0][1])
        )
        return self.action_space.index(random_action), random_action

    def action_indexes_to_real_action(self, action_indexes):
        real_actions = []
        for i in action_indexes:
            real_actions.append(self.action_space[i])
        return real_actions

    def real_actions_to_indexes(self, policy):
        indexes = []
        for action in policy:
            act_1 = np.clip(round(action[0]), -90, 90)
            act_2 = np.clip(round(action[1]), 0, 4)
            indexes.append(self.action_space.index((act_1, act_2)))
        return indexes

    def compute_next_state(self, state, action: tuple[int, int]):
        curr_pos = [state[0], state[1]]
        rot, thrust = limit_actions(state[5], state[6], action)
        radians = rot * (math.pi / 180)
        x_acceleration = math.sin(radians) * thrust
        y_acceleration = (math.cos(radians) * thrust) - GRAVITY
        new_horizontal_speed = state[2] - x_acceleration
        new_vertical_speed = state[3] + y_acceleration
        new_x = curr_pos[0] + state[2] - 0.5 * x_acceleration
        new_y = curr_pos[1] + state[3] + 0.5 * y_acceleration
        new_pos: LineString | list = [new_x, new_y]

        line1 = LineString(self.surface_points)
        line2 = LineString([curr_pos, new_pos])
        intersection: LineString = line1.intersection(line2)
        if intersection:
            new_x = intersection.coords.xy[0][0]
            new_y = intersection.coords.xy[1][0]
            new_pos = np.array([new_x, new_y])

        remaining_fuel = state[4] - thrust

        new_state = (new_pos[0], new_pos[1], new_horizontal_speed,
                     new_vertical_speed, remaining_fuel, rot,
                     thrust,
                     distance_to_line_segment(np.array(new_pos), self.landing_spot_points),
                     point_to_line_distance(new_pos, self.surface_points)
        )
        return new_state


def norm_reward(feature, interval_low, interval_high) -> float:
    return max(0.0, 1.0 - abs(feature) / interval_high)

def compute_reward(state, landing_spot) -> float:
    # dist_landing_spot = state[7]
    x, y, hs, vs, remaining_fuel, rotation, thrust, dist_landing_spot_squared, dist_surface = state
    # print(dist_landing_spot_squared)
    dist_normalized = norm_reward(dist_landing_spot_squared, 0, 49000000)
    # print(dist_normalized)
    # exit(9)
    hs_normalized = norm_reward(hs, 0, 550)
    vs_normalized = norm_reward(vs, 0, 550)
    rotation_normalized = norm_reward(rotation, 0, 90)
    # print(dist_normalized, hs_normalized, vs_normalized, rotation_normalized)
    return dist_normalized + hs_normalized + vs_normalized + rotation_normalized
    x1 = landing_spot[0].x
    y1 = landing_spot[0].y
    x2 = landing_spot[1].x
    y2 = landing_spot[1].y
    x0 = state[0]
    y0 = state[1]
    numerator = abs((y2 - y1) * x0 - (x2 - x1) * y0 + x2 * y1 - y2 * x1)
    denominator = math.sqrt((y2 - y1) ** 2 + (x2 - x1) ** 2)

    distance = numerator / denominator
    return -distance

from shapely.geometry import LineString
def find_intersection(segment1, segment2):


    left1 = segment1[0]
    right1 = segment1[1]
    left2 = segment2[0]
    right2 = segment2[1]
    x1, y1 = left1
    x2, y2 = right1
    # x1, y1, x2, y2 = segment1
    # x3, y3, x4, y4 = segment2
    x3, y3 = left2
    x4, y4 = right2

    def orientation(x1, y1, x2, y2, x3, y3):
        return (y2 - y1) * (x3 - x2) - (x2 - x1) * (y3 - y2)

    def on_segment(xi, yi, xj, yj, xk, yk):
        return (
            (xi <= xk <= xj or xj <= xk <= xi) and
            (yi <= yk <= yj or yj <= yk <= yi)
        )

    det = orientation(x1, y1, x2, y2, x3, y3) * orientation(x1, y1, x2, y2, x4, y4)
    if det == 0:
        return None  # Segments are parallel or collinear

    intersection_x = (
        (x1 * y2 - y1 * x2) * (x3 - x4) - (x1 - x2) * (x3 * y4 - y3 * x4)
    ) / det
    intersection_y = (
        (x1 * y2 - y1 * x2) * (y3 - y4) - (y1 - y2) * (x3 * y4 - y3 * x4)
    ) / det

    if on_segment(x1, y1, x2, y2, intersection_x, intersection_y) and \
       on_segment(x3, y3, x4, y4, intersection_x, intersection_y):
        return intersection_x, intersection_y
    else:
        return None


def reward_function(state, grid, landing_spot) -> (float, bool):
    x, y, hs, vs, remaining_fuel, rotation, thrust, dist_landing_spot, dist_surface = state

    is_successful_landing = (landing_spot[0][0] <= x <= landing_spot[1][0] and
                             landing_spot[0][1] >= y and rotation == 0 and
                             abs(vs) <= 40 and abs(hs) <= 20)

    # is_crashed = (y < 0 or y >= 3000 - 1 or x < 0 or x >= 7000 - 1 or
    #               grid[round(y)][round(x)] is False or remaining_fuel < -4)

    print(dist_surface, state)

    is_crashed = (y < 0 or y >= 3000 - 1 or x < 0 or x >= 7000 - 1 or
                  dist_surface == 0 or remaining_fuel < -4)

    if is_successful_landing:
        print("GOOD", x, remaining_fuel)
        exit(42)
        # return remaining_fuel * 10, True
    reward = compute_reward(state, landing_spot)
    done = False
    if is_crashed:
        done = True
        reward -= 100
    return reward, done
    # elif is_crashed:
    #     return normalize_unsuccessful_rewards(state, landing_spot), True
    # else:
    #     return 0, False
        # return compute_reward(state, landing_spot), False



def normalize_unsuccessful_rewards(state, landing_spot):
    x, y, hs, vs, remaining_fuel, rotation, thrust, dist_landing_spot, dist_surface = state

    norm_dist = 1 if dist_landing_spot == 0 else max(0, 1 - dist_landing_spot / 7000)
    norm_rotation = 1 - abs(rotation) / 90
    # norm_rotation = 1000 if norm_rotation == 1 else norm_rotation -50
    norm_vs = 1.0 if abs(vs) <= 0 else 0.0 if abs(vs) > 120 else 1.0 if abs(vs) <= 37 else 1.0 - (abs(vs) - 37) / (
            120 - 37)
    # norm_vs = 1000 if norm_vs == 1 else norm_vs - 50
    norm_hs = 1.0 if abs(hs) <= 0 else 0.0 if abs(hs) > 120 else 1.0 if abs(hs) <= 17 else 1.0 - (abs(hs) - 17) / (
            120 - 17)
    # norm_hs = 1000 if norm_hs == 1 else norm_hs - 50
    # print([dist_landing_spot, norm_dist, norm_rotation, norm_rotation + norm_dist])

    print(norm_dist + norm_rotation + norm_vs + norm_hs)
    return norm_dist + norm_rotation + norm_vs + norm_hs
    # if norm_dist_landing_spot == 0:
    #     return 10
    #     norm_dist_landing_spot = -10
    # return 0
    # return -norm_dist_landing_spot
    # dist = get_landing_spot_distance(x, landing_spot[0][0], landing_spot[1][0])
    # norm_dist = 1.0 if dist == 0 else max(0, 1 - dist / 7000)
    norm_rotation = 1 - abs(rotation) / 90
    # return norm_dist + norm_rotation
    norm_vs = 1.0 if abs(vs) <= 0 else 0.0 if abs(vs) > 120 else 1.0 if abs(vs) <= 37 else 1.0 - (abs(vs) - 37) / (
            120 - 37)
    norm_hs = 1.0 if abs(hs) <= 0 else 0.0 if abs(hs) > 120 else 1.0 if abs(hs) <= 17 else 1.0 - (abs(hs) - 17) / (
            120 - 17)
    # print(
    #     "CRASH x=", x, 'dist=', dist, 'rot=', rotation, vs, hs,
    #     "norms:", "vs", norm_vs, "hs", norm_hs, "rotation", norm_rotation, "dist", norm_dist, "sum",
    #     (2 * norm_dist + 1 * norm_rotation + 1 * norm_vs + 1 * norm_hs) / 5
    # )
    print(norm_dist, norm_rotation, rotation)
    if norm_dist < 1:
        return norm_dist
    return norm_dist + norm_rotation

    return (2 * norm_dist + 1 * norm_rotation + 1 * norm_vs + 1 * norm_hs)

    # print("Crash ! , ", norm_dist, norm_vs, norm_hs, norm_dist + norm_vs + norm_hs)
    # return norm_dist
    return (1 * norm_dist + 1 * norm_vs + 1 * norm_hs)
    if dist != 0:
        return 1 * norm_dist
    # return norm_dist
    if norm_vs != 1 and norm_hs != 1:
        return (1 * norm_dist + 1 * norm_vs + 1 * norm_hs)
    # if rotation != 0:
    #     return (1 * norm_dist + 1 * norm_rotation)
    return (1 * norm_dist + 1 * norm_rotation + 1 * norm_vs + 1 * norm_hs)


# TODO no need to land in the middle
def get_landing_spot_distance(x, landing_spot_left_x, landing_spot_right_x):
    return 0 if landing_spot_left_x <= x <= landing_spot_right_x else min(abs(x - landing_spot_left_x),
                                                                          abs(x - landing_spot_right_x))
    # middle_of_landing_spot = (landing_spot_right_x + landing_spot_left_x) / 2
    # return abs(x - middle_of_landing_spot)
