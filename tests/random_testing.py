import numpy as np

from simulation.interactor import IInteractor
from objects.base import objectFactory
from visual import ScreenObjectManager

class RandomInteractor(IInteractor):

    ROBOT_DEFINITION = {
        'visual': {
            'name': 'Circle',
            'radius': 20,
            'fill': '#ff00ff',
            'stroke': '#aaaaaa',
            'stroke_width': 3,
        },
        'children': [
            {
                'visual': {
                    'name': 'Rectangle',
                    'width': 10,
                    'height': 20,
                    'fill': '#00ff00',
                    'stroke': '#0000ff',
                    'stroke_width': 2,
                },
                'position': (15, 0, 1)
            },
            {
                'visual': {
                    'name': 'Rectangle',
                    'width': 10,
                    'height': 20,
                    'stroke': '#ff0000',
                    'stroke_width': 2,
                },
                'position': (-15, 0, 1)
            },
        ]
    }

    def startUp(self):
        self.robot = objectFactory(**self.ROBOT_DEFINITION)
        ScreenObjectManager.instance.registerObject(self.robot, 'testingRobot')

    def tick(self, tick):
        x = tick / 2000
        self.robot.rotation = x
        self.robot.position = (
            np.cos(0.3*x) * 30,
            np.sin(0.3*x) * 30,
            1
        )
        return x >= 4 * np.pi / 0.3