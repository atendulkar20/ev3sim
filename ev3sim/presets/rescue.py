import datetime
import numpy as np
import math
import pymunk
from ev3sim.simulation.interactor import IInteractor
from ev3sim.simulation.loader import ScriptLoader
from ev3sim.simulation.world import World, stop_on_pause
from ev3sim.objects.base import objectFactory
from ev3sim.objects.utils import local_space_to_world_space
from ev3sim.file_helper import find_abs
from ev3sim.visual.manager import ScreenObjectManager

class RescueInteractor(IInteractor):

    FOLLOW_POINT_CATEGORY = 0b1000
    SHOW_FOLLOW_POINTS = True
    SHOW_ROBOT_COLLIDER = True
    FOLLOW_POINT_COLLISION_TYPE = 5
    ROBOT_CENTRE_COLLISION_TYPE = 6
    ROBOT_CENTRE_RADIUS = 3
    FOLLOW_POINT_RADIUS = 1

    START_TIME = datetime.timedelta(minutes=5)

    TILE_LENGTH = 30

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.spawns = kwargs.get('spawns')
        self.time_tick = 0
        self.tiles = []
        for i, tile in enumerate(kwargs['tiles']):
            self.tiles.append({})
            import yaml
            path = find_abs(tile['path'], allowed_areas=['local/presets/', 'local', 'package/presets/', 'package'])
            with open(path, 'r') as f:
                t = yaml.safe_load(f)
            self.maxZpos = 0
            base_pos = np.array(tile.get('position', [0, 0]))
            # Transfer to rescue space.
            base_pos = [base_pos[0] * self.TILE_LENGTH, base_pos[1] * self.TILE_LENGTH]
            for obj in t['elements']:
                rel_pos = np.array(obj.get('position', [0, 0]))
                obj['rotation'] = (obj.get('rotation', 0) + tile.get('rotation', 0)) * np.pi / 180
                obj['position'] = local_space_to_world_space(rel_pos, tile.get('rotation', 0) * np.pi / 180, base_pos)
                obj['sensorVisible'] = True
                k = obj['key']
                obj['key'] = f'Tile-{i}-{k}'
                self.maxZpos = max(self.maxZpos, obj.get('zPos', 0))
            t['elements'].append({
                'position': local_space_to_world_space(np.array([0, 0]), tile.get('rotation', 0) * np.pi / 180, base_pos),
                'rotation': tile.get('rotation', 0) * np.pi / 180,
                'type': 'visual',
                'name': 'Rectangle',
                'width': self.TILE_LENGTH,
                'height': self.TILE_LENGTH,
                'fill': None,
                'stroke_width': 0.1,
                'stroke': 'rescue_outline_color',
                'zPos': self.maxZpos + 0.1,
                'key': f'Tile-{i}-outline',
                'sensorVisible': False,
            })
            self.tiles[-1]['follows'] = []
            for j, (x, y) in enumerate(t['follow_points']):
                self.tiles[-1]['follows'].append(local_space_to_world_space(np.array([x, y]), tile.get('rotation', 0) * np.pi / 180, base_pos))
            ScriptLoader.instance.loadElements(t['elements'])

    def collidedFollowPoint(self, follow_indexes):
        # TODO: Implement
        self.tiles[follow_indexes[0]]['follow_colliders'][follow_indexes[1]].visual.fill = '#00ff00'

    def spawnFollowPointPhysics(self):
        for i, tile in enumerate(self.tiles):
            tile['follow_colliders'] = []
            for j, pos in enumerate(tile['follows']):
                obj = objectFactory(**{
                    'collider': 'inherit',
                    'visual': {
                        'name': 'Circle',
                        'radius': self.FOLLOW_POINT_RADIUS,
                        'position': pos,
                        'fill': '#ff0000' if self.SHOW_FOLLOW_POINTS else None,
                        'stroke_width': 0,
                        'sensorVisible': False,
                        'zPos': self.maxZpos + 0.2,
                    },
                    'position': pos,
                    'physics': True,
                    'static': True,
                    'key': f'Tile-{i}-follow-{j}',
                })
                obj.shape.filter = pymunk.ShapeFilter(categories=self.FOLLOW_POINT_CATEGORY)
                obj.shape.sensor = True
                obj.shape._follow_indexes = (i, j)
                obj.shape.collision_type = self.FOLLOW_POINT_COLLISION_TYPE
                World.instance.registerObject(obj)
                if self.SHOW_FOLLOW_POINTS:
                    ScreenObjectManager.instance.registerObject(obj, obj.key)
                tile['follow_colliders'].append(obj)

    def locateBots(self):
        self.robots = []
        self.bot_follows = []
        bot_index = 0
        while True:
            # Find the next robot.
            possible_keys = []
            for key in ScriptLoader.instance.object_map.keys():
                if key.startswith(f'Robot-{bot_index}'):
                    possible_keys.append(key)
            if len(possible_keys) == 0:
                break
            possible_keys.sort(key=len)
            self.robots.append(ScriptLoader.instance.object_map[possible_keys[0]])
            # Spawn the robot follow point collider.
            obj = objectFactory(**{
                'collider': 'inherit',
                'visual': {
                    'name': 'Circle',
                    'radius': self.ROBOT_CENTRE_RADIUS,
                    'fill': '#00ff00' if self.SHOW_ROBOT_COLLIDER else None,
                    'stroke_width': 0,
                    'sensorVisible': False,
                    'zPos': 100,
                },
                'physics': True,
                'key': f'Robot-{bot_index}-follow',
            })
            obj.shape.sensor = True
            obj.shape.collision_type = self.ROBOT_CENTRE_COLLISION_TYPE
            World.instance.registerObject(obj)
            if self.SHOW_ROBOT_COLLIDER:
                ScreenObjectManager.instance.registerObject(obj, obj.key)
            self.bot_follows.append(obj)
            bot_index += 1

        if len(self.robots) == 0:
            raise ValueError("No robots loaded.")

    def startUp(self):
        self.spawnFollowPointPhysics()
        self.locateBots()
        assert len(self.robots) <= len(self.spawns), "Not enough spawning locations specified."
        self.scores = [0]*len(self.robots)

        self.resetPositions()
        for i in range(len(self.robots)):
            self.bot_follows[i].body.position = self.robots[i].body.position
        self.addCollisionHandler()

        for robot in self.robots:
            robot.robot_class.onSpawn()

    def addCollisionHandler(self):
        handler = World.instance.space.add_collision_handler(self.FOLLOW_POINT_COLLISION_TYPE, self.ROBOT_CENTRE_COLLISION_TYPE)
        def handle_collide(arbiter, space, data):
            a, b = arbiter.shapes
            if hasattr(a, '_follow_indexes'):
                self.collidedFollowPoint(a._follow_indexes)
            elif hasattr(b, '_follow_indexes'):
                self.collidedFollowPoint(b._follow_indexes)
            else:
                raise ValueError("Two objects with collision types used by rescue don't have a tile follow point.")
            return False
        handler.begin = handle_collide

    def resetPositions(self):
        for i, robot in enumerate(self.robots):
            robot.body.position = [self.spawns[i][0][0] * self.TILE_LENGTH, self.spawns[i][0][1] * self.TILE_LENGTH]
            robot.body.angle = self.spawns[i][1] * np.pi / 180
            robot.body.velocity = np.array([0.0, 0.0])
            robot.body.angular_velocity = 0

    def tick(self, tick):
        super().tick(tick)
        self.cur_tick = tick
        for i in range(len(self.robots)):
            self.bot_follows[i].body.position = self.robots[i].body.position
            # Ensure visual is not 1 frame behind.
            self.bot_follows[i].position = self.robots[i].body.position
        self.update_time()

    @stop_on_pause
    def update_time(self):
        self.time_tick += 1
        elapsed = datetime.timedelta(seconds=self.time_tick / ScriptLoader.instance.GAME_TICK_RATE)
        show = self.START_TIME - elapsed
        seconds = show.seconds
        minutes = seconds // 60
        seconds = seconds - minutes * 60
        ScriptLoader.instance.object_map['TimerText'].text = '{:02d}:{:02d}'.format(minutes, seconds)