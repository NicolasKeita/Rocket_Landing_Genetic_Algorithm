from matplotlib import pyplot as plt, cm
from src.Point2D import Point2D


def create_graph(points: list[Point2D], title: str):
    plt.xlim(0, 7000)
    plt.ylim(0, 3000)
    plt.xlabel('X Coordinate')
    plt.ylabel('Y Coordinate')
    plt.title(title)
    plt.plot(*zip(*[(point.x, point.y) for point in points]), marker='o', label='Mars Surface')
    plt.legend()
    plt.grid(True)
    plt.draw()


def display_graph(trajectories: list[tuple[float, float]], id_lines_color: int):
    cmap = cm.get_cmap('Set1')
    color = cmap(id_lines_color % 8)

    ax = plt.gca()

    # Clear previous trajectories
    for line in ax.lines:
        if line.get_label() != 'Mars Surface':
            line.remove()

    for trajectory in trajectories:
        plt.plot(trajectory[0], trajectory[1], marker='o', markersize=2, color=color, label=f'Rocket {id_lines_color}')
        plt.pause(0.001)