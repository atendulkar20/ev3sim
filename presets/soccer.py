import pygame
import numpy as np
from simulation.interactor import IInteractor
from simulation.loader import ScriptLoader
from simulation.world import World
from objects.base import objectFactory
from objects.colliders import colliderFactory
from visual.manager import ScreenObjectManager
from visual.utils import screenspace_to_worldspace

class SoccerInteractor(IInteractor):

    BOTS_PER_TEAM = 1

    # Constants for grabbing the ball
    ball_grabbed = False
    ball_rel_pos = None
    ball_m_pos = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.names = kwargs.get('names', ['Team 1', 'Team 2'])
        self.spawns = kwargs.get('spawns')
        self.goals = kwargs.get('goals')
        self.show_goal_colliders = kwargs.get('show_goal_colliders', False)
    
    def startUp(self):
        assert len(self.names) == len(self.spawns) and len(self.spawns) == len(self.goals), "All player related arrays should be of equal size."
        # Initialise the goal colliders.
        self.goal_colliders = []
        self.team_scores = []
        self.robots = []
        for x in range(len(self.names)):
            # Set up goal collider.
            pos = self.goals[x]['position']
            del self.goals[x]['position']
            obj = {
                'collider': 'inherit',
                'visual': self.goals[x],
                'position': pos,
                'physics': True
            }
            self.goal_colliders.append(objectFactory(**obj))
            if self.show_goal_colliders:
                ScreenObjectManager.instance.registerVisual(self.goal_colliders[-1].visual, f'Soccer_DEBUG_collider-{len(self.goal_colliders)}')
            # Set up team scores
            self.team_scores.append(0)
            # Set up team name
            ScriptLoader.instance.object_map[f'name{x+1}Text'].text = self.names[x]
            for y in range(self.BOTS_PER_TEAM):
                # Find the BOTS_PER_TEAM*x+yth robot.
                possible_keys = []
                for key in ScriptLoader.instance.object_map.keys():
                    if key.startswith(f'Robot-{self.BOTS_PER_TEAM*x+y}'):
                        possible_keys.append(key)
                if len(possible_keys) == 0:
                    raise ValueError(f"No Robot-{self.BOTS_PER_TEAM*x+y} for simulation, quitting.")
                possible_keys.sort(key=len)
                self.robots.append(ScriptLoader.instance.object_map[possible_keys[0]])
        self.updateScoreText()
        self.resetPositions()

    def updateScoreText(self):
        for x in range(len(self.names)):
            ScriptLoader.instance.object_map[f'score{x+1}Text'].text = str(self.team_scores[x])

    def resetPositions(self):
        # It is assumed that 2 robots to each team, with indexes increasing as we go across teams.
        for team in range(len(self.names)):
            for index in range(self.BOTS_PER_TEAM):
                self.robots[team*self.BOTS_PER_TEAM + index].position = self.spawns[team][index][0]
                self.robots[team*self.BOTS_PER_TEAM + index].rotation = self.spawns[team][index][1] * np.pi / 180
                self.robots[team*self.BOTS_PER_TEAM + index].velocity = np.array([0.0, 0.0])
        ScriptLoader.instance.object_map['IR_BALL'].position = [0, -18]
        ScriptLoader.instance.object_map['IR_BALL'].velocity = np.array([0., 0.])

    def tick(self, tick):
        super().tick(tick)
        collider = objectFactory(**{
            'physics': True,
            'position': ScriptLoader.instance.object_map['IR_BALL'].position,
            'collider': {
                'name': 'Point'
            }
        }).collider
        for i, goal in enumerate(self.goal_colliders):
            if collider.getCollisionInfo(goal.collider)["collision"]:
                # GOAL!
                self.goalScoredIn(i)
                break
        if self.ball_grabbed:
            ScriptLoader.instance.object_map['IR_BALL'].position = self.ball_rel_pos + self.ball_m_pos

    def goalScoredIn(self, teamIndex):
        self.team_scores[1-teamIndex] += 1
        self.updateScoreText()
        self.resetPositions()

    def handleEvent(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            m_pos = screenspace_to_worldspace(event.pos)
            collider = objectFactory(**{
                'physics': True,
                'position': m_pos,
                'collider': {
                    'name': 'Point'
                }
            }).collider
            ball = ScriptLoader.instance.object_map['IR_BALL']
            if ball.collider.getCollisionInfo(collider)["collision"]:
                # Grab the ball!
                ball.velocity = np.array([0.0, 0.0])
                World.instance.unregisterObject(ball)
                self.ball_grabbed = True
                self.ball_rel_pos = ball.position - m_pos
                self.ball_m_pos = m_pos
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1 and self.ball_grabbed:
            self.ball_grabbed = False
            World.instance.registerObject(ScriptLoader.instance.object_map['IR_BALL'])
        if event.type == pygame.MOUSEMOTION and self.ball_grabbed:
            self.ball_m_pos = screenspace_to_worldspace(event.pos)
