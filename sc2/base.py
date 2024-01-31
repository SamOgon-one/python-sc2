# TODO

# conver self.workers_mining_tag into sets

# if something block minerals, example building  cover mineral pocket, chech when last time worker has mineral and switch to default mining
# check if gather point is not blocked, when  turret inside minerals, or back from defence


# check if something in mineral can block speed mining, if yes change to default  mining
# avoid bump repair squad, defend squad also, all other ground units
# mule

# info: worker.return_resource() breaks speed-mining, worker slows down returning

import os
import sys
from pathlib import Path
import random
import math
import numpy as np
from collections import defaultdict, Counter
from time import perf_counter
from typing import TYPE_CHECKING, Dict, List, Set, Union

from sc2 import maps
from sc2.bot_ai import BotAI
from sc2.data import Difficulty, Race, AIBuild, Result, race_gas, race_worker, Alert
from sc2.ids.unit_typeid import UnitTypeId
from sc2.main import run_game
from sc2.player import Bot, Computer
from sc2.unit import Unit
from sc2.units import Units

from sc2.ids.ability_id import AbilityId
from sc2.ids.buff_id import BuffId
from sc2.ids.upgrade_id import UpgradeId
import sc2.ids.effect_id
from sc2.position import Point2, Point3

from sc2.action import combine_actions
from sc2.unit_command import UnitCommand
from sc2.score import ScoreDetails


class Base():


    def __init__(self, bot: BotAI,  th: Unit):

        self.bot = bot
        self.th = th
        self.th_tag = th.tag
        self.th_pos = th.position

        # self.mineral_mining_type = 'default'
        # self.mineral_mining_type = 'speed_mining'
        self.mineral_mining_type = 'speed_mining_simple'


        self.workers_mining_tag = []  
        self.worker_tag_mineral_tag = {}
        self.mineral_tag_occupation = defaultdict(lambda: 0)  
        self.mineral_field = self.bot.mineral_field.closer_than(10, self.th)
        self.minerals_tags = self.mineral_field.tags             
        self.minerals_positions = set([mineral.position for mineral in self.mineral_field]) # to handle shnalpshot with different tags

        self.mineral_tag_gather_point = {}
        # self.mineral_tag_simple_gather_point = {}
        # self.mineral_tag_short = set()
        self.mineral_distance_for_simple = defaultdict(lambda: 1)       
        self.mineral_tag_corrected_gather_point = {}
        self.mineral_tag_return_point = {}
        self.worker_tag_last_position = {}

        # self.gas_mining_type = 'default'
        self.gas_mining_type = 'speed_gas_mining'
        self.workers_gas_mining_tags = set()
        self.gas_worker_tag_gas_structure_tag = {}
        self.gas_structure_tag_workers_gas_tag = defaultdict(lambda: set())

        self.gas_structures: Units = Units([], self)

        geysers = self.bot.vespene_geyser.closer_than(10, self.th).sorted_by_distance_to(self.th)
        self.geysers_positions = [geyser.position for geyser in geysers]
        # self.geysers_tag = []
        self.gas_structures_tag = []
       
        self.base_destroyed = False

        # print(th.position)

        self.calculate_points_to_gather(self.th)



    def every_iteration(self):

        # is th alive # todo check is_flying
        if not self.th_tag in self.bot.structures.tags:
            self.base_destroyed = True
            return

        self.th = self.bot.structures.find_by_tag(self.th_tag)

        # if self.bot.alert(Alert.MineralsExhausted):
        #     # print('Alert.MineralsExhausted')
        #     self.mineralsexhausted()

        # if self.bot.alert(Alert.VespeneExhausted):
        #     # print('Alert.VespeneExhausted base')
            # self.gas_structures = self.bot.structures.filter(lambda structure: structure.has_vespene and structure.position in self.geysers_positions).ready

        #     self.vespeneexhausted()

        # add minerals, and handle snapshots tag change
        # todo (?) do we need Alert.MineralsExhausted method then?
        self.mineral_field = self.bot.mineral_field.positions_in(self.minerals_positions)
        if self.minerals_tags != self.mineral_field.tags:

            self.mineralsexhausted()
            if any(tag not in self.minerals_tags for tag in self.mineral_field.tags):
                self.calculate_points_to_gather(self.th)
            self.minerals_tags = self.mineral_field.tags
            self.minerals_positions = set([mineral.position for mineral in self.mineral_field])     


        # add gas, when not snapshots
        # self.gas_structures = self.structures(race_gas[self.race]).filter(lambda structure: structure.position in self.geysers_positions).ready
        self.gas_structures = self.bot.structures.filter(lambda structure: structure.has_vespene and structure.position in self.geysers_positions).ready
        self.workers = self.bot.workers.tags_in(self.workers_mining_tag)
        for tag in self.workers_mining_tag:
            if tag not in self.workers.tags:
                self.remove_worker_from_mining(tag)
                # print("every iteration worker not in self.workers.tags")


        # # testing
        # print(self.bot.iteration, "base")  
        # print("self.workers_mining_tag", len(self.workers_mining_tag), sorted(self.workers_mining_tag))
        # print("self.bot.workers.tags", self.bot.workers.amount, len(self.bot.workers.tags), sorted(list(self.bot.workers.tags)))        
        # print("self.workers.tags", len(self.workers.tags), sorted(list(self.workers.tags)))
        # print()


        # dead workers while mining
        # todo modyfy this for bunker mining, tag of worker wont be in self.workers but in bunker.passangers
        # if self.workers.tags != (self.workers_mining_tag):
        #     if len(self.workers.tags) > len(self.workers_mining_tag):      

        for tag in self.workers_mining_tag:
            if tag not in self.workers.tags:
                
                print()
                print("worker died while mining", self.bot.time_formatted)
                print("self.workers_mining_tag", self.workers_mining_tag)
                print("self.workers.tags", self.workers.tags)
                print()

                self.remove_worker_from_mining(tag)
                
                # if tag in self.worker_tag_mineral_tag:
                #     mineral_tag =  self.worker_tag_mineral_tag[worker.tag]
                #     self.mineral_tag_occupation[mineral_tag] -= 1

        # if self.workers.tags != set(self.workers_mining_tag):
        self.workers_mining_tag = list(self.workers.tags)







        # if self.mineral_field.amount != 8:
        #     print("mineral_field.amount", self.mineral_field.amount)
            
        for mineral in self.mineral_field:
            o = self.mineral_tag_occupation[mineral.tag]
            if o not in [0, 1, 2]:
                print("mineral_tag_occupation", mineral.tag, mineral.position, o)
                self.mineral_tag_occupation[mineral.tag] = min(2, max(0, self.mineral_tag_occupation[mineral.tag]))






        self.balance_gas_and_mineral_mining()

        if self.mineral_mining_type == 'default':
            self.default_mining()
        elif self.mineral_mining_type == 'speed_mining':
            self.speed_mining()
        elif self.mineral_mining_type == 'speed_mining_simple':
            self.speed_mining_simple()




        if self.gas_mining_type == 'default':
            self.default_gas_mining()

        elif self.gas_mining_type == 'speed_gas_mining':
            self.almost_default_gas_mining()

        if self.bot.iteration % 13 == 0:
            self.pick_better_mineral()



    def default_mining(self):

        # print('default mining method')
        for worker in self.workers:
            # print(worker.tag, worker.orders)

            mineral = self.mineral_field.find_by_tag(self.worker_tag_mineral_tag[worker.tag])
            if not worker.is_collecting:
                # print('not collecting', worker.tag)
                if worker.is_carrying_resource:
                    worker.return_resource()
                else:                    
                    worker.gather(mineral)
                continue

            # correct gathering other mineral tag
            if worker.is_gathering and worker.orders[0].target != self.worker_tag_mineral_tag[worker.tag]:
                worker.gather(mineral)



    def speed_mining(self):

        # sometimes workers bump to each other and return resorcue with that (!) bym orders stays move+smart and worker start to moves follow th, doing nothing with move command, thats why len(worker.orders) == 2 and worker.orders[0].ability.id in {AbilityId.MOVE}

        # bump prevention  # gain half percent at old speed-mining it it's 
        worker_tag_to_exclude = []
        workers_move = Units([], self)
        workers_move = self.workers.filter(lambda worker: len(worker.orders) == 2 and worker.orders[0].ability.id in {AbilityId.MOVE})
        for i in range(len(workers_move)-1):
            worker = workers_move[i]
            for j in range(i+1, len(workers_move)):
                if worker.distance_to(workers_move[j]) < 0.75: # probably can make it even smaller, about 6.4, same below
                    if worker.orders[1].ability.id in {AbilityId.HARVEST_RETURN}:
                        worker.return_resource()
                    else:
                        mineral = self.mineral_field.find_by_tag(self.worker_tag_mineral_tag[worker.tag])
                        worker.gather(mineral)
                    # print('trigger time', self.bot.time, 'len(workers_move)', len(workers_move))
                    worker_tag_to_exclude.append(worker.tag)
                    break


        # mining
        for worker in self.workers.tags_not_in(worker_tag_to_exclude):
            mineral = self.mineral_field.find_by_tag(self.worker_tag_mineral_tag[worker.tag])              

            # and type(worker.orders[0].target) != int
            if (len(worker.orders) == 1 and worker.orders[0].ability.id not in {AbilityId.HARVEST_RETURN, AbilityId.HARVEST_GATHER}) or len(worker.orders) == 0 or (worker.orders[0].ability.id in {AbilityId.HARVEST_RETURN} and not worker.is_carrying_resource) or (len(worker.orders) == 2 and worker.orders[1].ability.id in {AbilityId.HARVEST_RETURN} and not worker.is_carrying_resource) or (worker.orders[0].ability.id not in {AbilityId.HARVEST_GATHER} and self.worker_tag_last_position[worker.tag] == worker.position) or (worker.orders[0].ability.id in {AbilityId.HARVEST_GATHER} and worker.orders[0].target != mineral.tag): #  or (self.worker_tag_last_position[worker.tag] == worker.position and worker.orders[0].target == self.th_pos) 
            # if len(worker.orders) == 0 or (worker.orders[0].ability.id not in {AbilityId.HARVEST_GATHER} and self.worker_tag_last_position[worker.tag] == worker.position) or (worker.orders[0].ability.id in {AbilityId.HARVEST_GATHER} and worker.orders[0].target != mineral.tag):
                if worker.is_carrying_resource:
                    worker.return_resource()
                else:
                    worker.gather(mineral)

            elif worker.orders[0].ability.id in {AbilityId.HARVEST_RETURN} and len(worker.orders) < 2 and 0.4 < self.mineral_tag_return_point[mineral.tag].distance_to(worker.position) < 0.7 * self.mineral_tag_return_point[mineral.tag].distance_to(self.mineral_tag_gather_point[mineral.tag]) and all(worker.distance_to(worker2) > 0.75 for worker2 in workers_move):
                worker.move(self.mineral_tag_return_point[mineral.tag])
                # worker.return_resource(queue=True)
                worker.smart(self.th, queue=True)

            elif worker.orders[0].ability.id in {AbilityId.HARVEST_GATHER} and len(worker.orders) < 2 and 0.4  < self.mineral_tag_gather_point[mineral.tag].distance_to(worker.position) < 0.7 * self.mineral_tag_return_point[mineral.tag].distance_to(self.mineral_tag_gather_point[mineral.tag]) and all(worker.distance_to(worker2) > 0.75 for worker2 in workers_move):
                worker.move(self.mineral_tag_gather_point[mineral.tag])
                worker.gather(mineral, queue=True)
            
            self.worker_tag_last_position[worker.tag] = worker.position


    def speed_mining_simple(self):

        # sometimes workers bump to each other and return resorcue with that (!) bym orders stays move+smart and worker start to moves follow th, doing nothing with move command, thats why len(worker.orders) == 2 and worker.orders[0].ability.id in {AbilityId.MOVE}

        # bump prevention  # gain half percent at old speed-mining it it's 
        worker_tag_to_exclude = []
        workers_move = Units([], self)
        workers_move = self.workers.filter(lambda worker: len(worker.orders) == 2 and worker.orders[0].ability.id in {AbilityId.MOVE})
        for i in range(len(workers_move)-1):
            worker = workers_move[i]
            for j in range(i+1, len(workers_move)):
                if worker.distance_to(workers_move[j]) < 0.75: # probably can make it even smaller, about 6.4, same below
                    if worker.orders[1].ability.id in {AbilityId.HARVEST_RETURN}:
                        worker.return_resource()
                    else:
                        mineral = self.mineral_field.find_by_tag(self.worker_tag_mineral_tag[worker.tag])
                        worker.gather(mineral)
                    # print('trigger time', self.bot.time, 'len(workers_move)', len(workers_move))
                    worker_tag_to_exclude.append(worker.tag)
                    break

        # diagnostic
        # if worker_tag_to_exclude:
        #     print("worker_tag_to_exclude", len(worker_tag_to_exclude))


        # mining
        for worker in self.workers.tags_not_in(worker_tag_to_exclude):
            mineral = self.mineral_field.find_by_tag(self.worker_tag_mineral_tag[worker.tag])              

            if (
                len(worker.orders) == 0
                or (len(worker.orders) == 1 and worker.orders[0].ability.id not in {AbilityId.HARVEST_RETURN, AbilityId.HARVEST_GATHER}) 
                or (worker.orders[0].ability.id in {AbilityId.MOVE} and self.worker_tag_last_position[worker.tag] == worker.position) 
                or (worker.is_carrying_resource and worker.orders[0].ability.id in {AbilityId.HARVEST_GATHER})
                or (not worker.is_carrying_resource and worker.orders[0].ability.id in {AbilityId.HARVEST_GATHER} and worker.orders[0].target != mineral.tag)
            ):
                if worker.is_carrying_resource:
                    worker.return_resource()
                else:
                    worker.gather(mineral)


            elif (
                worker.orders[0].ability.id in {AbilityId.HARVEST_RETURN} 
                and 3.5 < self.th.distance_to(worker) < 4.5 
                and all(worker.distance_to(worker2) > 0.75 for worker2 in workers_move)
            ):
                target = self.th.position.towards(worker.position, self.th.radius + worker.radius)
                worker.move(target)
                worker.smart(self.th, queue=True)

            elif (
                worker.orders[0].ability.id in {AbilityId.HARVEST_GATHER}  
                and 2 < mineral.distance_to(worker) < 3
                and all(worker.distance_to(worker2) > 0.75 for worker2 in workers_move)
            ):
                # target = self.mineral_tag_simple_gather_point[mineral.tag]

                if mineral.tag in self.mineral_tag_corrected_gather_point:
                    target = self.mineral_tag_corrected_gather_point[mineral.tag]               
                # elif mineral.tag in self.mineral_tag_short:
                #     target = mineral.position.towards(worker.position, 0.5 + worker.radius)
                # else:
                #     target = mineral.position.towards(worker.position, 1 + worker.radius) # mineral.radius = 1 2x1
                else:
                    target = mineral.position.towards(worker.position, self.mineral_distance_for_simple[mineral.tag] + worker.radius) # mineral.radius = 1 2x1





                worker.move(target)                                
                worker.gather(mineral, queue=True)
            
            self.worker_tag_last_position[worker.tag] = worker.position




    def default_gas_mining(self):

        # correct gathering other mineral gas
        for worker in self.bot.workers.tags_in(self.workers_gas_mining_tags):
            gas_structure = self.gas_structures.find_by_tag(self.gas_worker_tag_gas_structure_tag[worker.tag])

            # wrong order
            if worker.is_idle or (worker.is_gathering and worker.orders[0].target != self.gas_worker_tag_gas_structure_tag[worker.tag]):
                if worker.is_carrying_resource:
                    worker.return_resource()
                    worker.gather(gas_structure, queue=True)
                else:                 
                    worker.gather(gas_structure)      


    def almost_default_gas_mining(self):

        # correct gathering other mineral gas
        for worker in self.bot.workers.tags_in(self.workers_gas_mining_tags):
            gas_structure = self.gas_structures.find_by_tag(self.gas_worker_tag_gas_structure_tag[worker.tag])

            # wrong order
            if worker.is_idle or (worker.is_gathering and worker.orders[0].target != self.gas_worker_tag_gas_structure_tag[worker.tag]):
                if worker.is_carrying_resource:
                    worker.return_resource()
                    worker.gather(gas_structure, queue=True)
                else:                 
                    worker.gather(gas_structure)                
                continue
            
            # speed-mining
            # TODO may couse collisions when another worker go build/repair and cross minig path
            # 1 worker per gas_structure, start move command earlier
            if len(self.gas_structure_tag_workers_gas_tag[gas_structure.tag]) == 1:
                # return
                if worker.is_carrying_resource and len(worker.orders) < 2 and 3.5 < worker.position.distance_to(self.th) < 5: #  and worker.orders[0].ability.id in {AbilityId.HARVEST_RETURN}
                    # point = self.th.position.towards(worker.position, 3.025) #  2.5 + 0.375 + 0.1
                    point = self.th.position.towards(worker.position, 2.9) #  2.5 + 0.375 + 0.1                    
                    worker.move(point)
                    worker.smart(self.th, queue=True)
                    # worker.return_resource(queue=True) # don't do that, it's break speed mining
                # gather
                elif len(worker.orders) < 2 and worker.orders[0].ability.id in {AbilityId.HARVEST_GATHER} and 2.5 < worker.position.distance_to(gas_structure.position) < 4:  
                    point = gas_structure.position.towards(worker.position, 2)
                    worker.move(point)
                    worker.gather(gas_structure, queue=True)

            # 2 worker per gas_structure
            elif len(self.gas_structure_tag_workers_gas_tag[gas_structure.tag]) == 2:
                # return
                if worker.is_carrying_resource and len(worker.orders) < 2 and 3.5 < worker.position.distance_to(self.th) < 4.2: #  and worker.orders[0].ability.id in {AbilityId.HARVEST_RETURN}
                    # point = self.th.position.towards(worker.position, 3.025) #  2.5 + 0.375 + 0.1
                    point = self.th.position.towards(worker.position, 2.9) #  2.5 + 0.375 + 0.1                    
                    worker.move(point)
                    worker.smart(self.th, queue=True)                    
                # gather
                elif len(worker.orders) < 2 and worker.orders[0].ability.id in {AbilityId.HARVEST_GATHER} and 2.5 < worker.position.distance_to(gas_structure.position) < 3.2:  
                    point = gas_structure.position.towards(worker.position, 2)
                    worker.move(point)
                    worker.gather(gas_structure, queue=True)



    def balance_gas_and_mineral_mining(self):

        # check for gas building if dead worker assigned  or if too many gas workers
        for gas_structure in self.gas_structures:
            if len(self.gas_structure_tag_workers_gas_tag[gas_structure.tag]) - gas_structure.assigned_harvesters > 1: # >1 when speed mining with no gather order
                # for tag in list(self.workers_gas_mining_tags)[::-1]:
                for tag in list(self.gas_structure_tag_workers_gas_tag[gas_structure.tag])[::-1]:  

                    if tag not in self.bot.workers.tags:
                        if tag in self.workers_gas_mining_tags:
                            self.workers_gas_mining_tags.remove(tag)
                        else:
                            print("balance_gas_and_mineral_mining  tag not in self.workers_gas_mining_tags")
                        self.gas_structure_tag_workers_gas_tag[gas_structure.tag].remove(tag)
                        del self.gas_worker_tag_gas_structure_tag[tag]

            # too many gas workers
            elif gas_structure.assigned_harvesters > 3:
            # if len(self.workers_gas_mining_tags) > self.gas_structures.amount * 3:
                worker = self.get_worker_from_gas_mining()
                if worker is not None:
                    self.add_worker_to_mining(worker)


        # destroyed and deplated gas_structure
        for worker_tag in list(self.workers_gas_mining_tags):
            if self.gas_worker_tag_gas_structure_tag[worker_tag] not in self.gas_structures.tags:
                self.workers_gas_mining_tags.remove(worker_tag)
                del self.gas_worker_tag_gas_structure_tag[worker_tag]
                # print('gas structure destroyed, remove gas-worker', self.bot.time_formatted)


        # from gas to minerals balance
        if len(self.workers_mining_tag) < len(self.minerals_tags) * 2 - 2 and self.bot.workers.tags_in(self.workers_gas_mining_tags): # or (self.bot.vespene > 200 and len(self.workers_mining_tag) < len(self.minerals_tags) * 2):
            worker = self.get_worker_from_gas_mining()
            # if worker is None:
            #     print('None worker getting from gas, when balancing')
            if worker is not None:  
                self.add_worker_to_mining(worker)   
                return  

        # from minerals to gas balance
        if len(self.workers_gas_mining_tags) < self.gas_structures.amount * 3 and len(self.workers_mining_tag) > len(self.minerals_tags) * 2 - 2: # or (self.bot.minerals > 200 and len(self.workers_mining_tag) < len(self.minerals_tags) * 2):
            worker = self.get_worker_from_mining()
            if worker is not None:
                self.add_worker_to_gas_mining(worker)
                return


        # balance gas buildings when occupation 3 and 1
        if self.gas_structures.amount == 2 and len(self.workers_gas_mining_tags) == 4:
            g1, g2 = self.gas_structures
            l1 = len(self.gas_structure_tag_workers_gas_tag[g1.tag]) 
            l2 = len(self.gas_structure_tag_workers_gas_tag[g2.tag])
            if [l1, l2] == [1 ,3] or [l1, l2] == [3 ,1]:
                worker = self.get_worker_from_gas_mining()
                if worker is not None:
                    self.add_worker_to_gas_mining(worker)
                    # print('balance gas 1 3')
                    



    def add_worker_to_mining(self, worker):   

        if worker.tag in self.workers_mining_tag:
            print("add_worker_to_mining", "worker.tag in self.workers_mining_tag", worker.orders)
            return True

        if len(self.workers_mining_tag) < 2*len(self.minerals_tags): # and worker.tag not in self.workers_mining_tag:
            for mineral in self.mineral_field.sorted_by_distance_to(self.th_pos):
                if self.mineral_tag_occupation[mineral.tag] < 2:
                    self.mineral_tag_occupation[mineral.tag] += 1
                    self.worker_tag_mineral_tag[worker.tag] = mineral.tag
                    self.worker_tag_last_position[worker.tag] = Point2((100, 100))
                    self.workers_mining_tag.append(worker.tag) 
                    # self.workers += self.bot.workers.tags_in([worker.tag])
                    self.workers += Units([worker], self)
                    if worker.is_carrying_resource:
                        worker.return_resource()
                        worker.gather(mineral, queue=True)
                    else:                 
                        worker.gather(mineral)
                    return True
        
        return False

    # initial distribute
    def add_many_worker_to_mining(self, workers_inp):   

        workers = workers_inp.copy() # when passing list of units from bot, this method remove part, thats why copy first
        for worker in workers[::-1]:
            if worker.tag in self.workers_mining_tag:
                workers.remove(worker)
                # print("add_many_worker_to_mining", "worker.tag in self.workers_mining_tag", worker.orders)

        # workers_with_resorcue = workers.filter(lambda worker: worker.is_carrying_resource)
        workers_without_resorcue = workers.filter(lambda worker: not worker.is_carrying_resource)

        # todo revert to take(6)
        # for mineral in self.mineral_field.sorted_by_distance_to(self.th_pos).take(6):
        for mineral in self.mineral_field.sorted_by_distance_to(self.th_pos).take(8):        

            if self.mineral_tag_occupation[mineral.tag] < 2 and workers_without_resorcue:
                worker = workers_without_resorcue.closest_to(mineral)
                workers_without_resorcue.remove(worker)

                self.mineral_tag_occupation[mineral.tag] += 1
                self.worker_tag_mineral_tag[worker.tag] = mineral.tag
                self.worker_tag_last_position[worker.tag] = Point2((100, 100))
                self.workers_mining_tag.append(worker.tag)   
        

        # for mineral in self.mineral_field.sorted_by_distance_to(self.th_pos):
        #     if self.mineral_tag_occupation[mineral.tag] < 2 and workers_with_resorcue:
        #         worker = workers_with_resorcue.closest_to(mineral)
        #         workers_with_resorcue.remove(worker)

        #         self.mineral_tag_occupation[mineral.tag] += 1
        #         self.worker_tag_mineral_tag[worker.tag] = mineral.tag
        #         self.worker_tag_last_position[worker.tag] = Point2((100, 100))
        #         self.workers_mining_tag.append(worker.tag)   




    def pick_better_mineral(self):   

        if self.mineral_field.amount > 4:
            close_minerals = self.mineral_field.sorted_by_distance_to(self.th_pos).take(4)
            for i, mineral in enumerate(close_minerals):
                if self.mineral_tag_occupation[mineral.tag] < 2 and len(self.workers_mining_tag) >= (i+1) * 2:
                    # print('serching_better_mineral')
                    # for mineral in self.mineral_field.sorted_by_distance_to(self.th_pos)[::-1]:
                    #     for i, mineral in enumerate(self.mineral_field.sorted_by_distance_to(self.th_pos)):
                    #         if i < 4:
                    #             continue

                    #         if self.mineral_tag_occupation[mineral.tag]:
                    #             # self.workers = self.bot.workers.tags_in(self.workers_mining_tag)
                    #             for worker in self.workers:
                    #                 if self.worker_tag_mineral_tag[worker.tag] == mineral.tag and not worker.is_carrying_resource and worker.distance_to(self.th) < 4:    
                    #                     self.remove_worker_from_mining(worker.tag)
                    #                     self.add_worker_to_mining(worker)   
                    #                     print('pick_better_mineral', self.bot.iteration)
                    #                     return True                       


                    workers_org = self.workers.filter(lambda worker: self.worker_tag_mineral_tag[worker.tag] not in close_minerals.tags)
                    workers = workers_org.filter(lambda worker: worker.is_carrying_resource)
                    if not workers:
                        workers = workers_org.filter(lambda worker: worker.distance_to(self.th) < 4)
                        # print('pick without resources')

                    if workers:
                        worker = workers.closest_to(mineral)
                        self.remove_worker_from_mining(worker.tag)
                        self.add_worker_to_mining(worker)   
                        # print('pick_better_mineral', self.bot.iteration)
                        return True     


    # TODO
    # maybe get worker closest also with minerals, return mineral and then queue new order

    def get_worker_from_mining(self, position=None): 
        if position is None:
            position = self.th.position

        # # not carrying resource
        # for worker in self.bot.workers.tags_in(self.workers_mining_tag).gathering.sorted_by_distance_to(position):             
        #     self.workers_mining_tag.remove(worker.tag)  
        #     self.mineral_tag_occupation[self.worker_tag_mineral_tag[worker.tag]] -= 1            
        #     return worker

        # every worker
        # for worker in self.bot.workers.tags_in(self.workers_mining_tag).sorted_by_distance_to(position):  
        for worker in self.workers.sorted_by_distance_to(position):    
            if worker.tag in self.workers_mining_tag:      
                self.workers_mining_tag.remove(worker.tag)  
            else:
                print("worker.tag not in workers_mining_tag  def get_worker_from_mining")
            self.mineral_tag_occupation[self.worker_tag_mineral_tag[worker.tag]] -= 1 
            self.workers.remove(worker)  
             # del self.worker_tag_mineral_tag[worker.tag]
            return worker

        return None


    def add_worker_to_gas_mining(self, worker):   

        if worker.tag in self.workers_gas_mining_tags:
            print("workers_gas_mining_tags", "worker.tag in self.workers_gas_mining_tags", worker.orders)
            return True

        if len(self.workers_gas_mining_tags) >= self.gas_structures.amount * 3:
            # print('too much worker added to gas   th.position', self.th.position, ' len(self.workers_gas_mining_tags)', len(self.workers_gas_mining_tags), 'self.gas_structures.amount', self.gas_structures.amount)
            return False

        # todo when 2 gas_structurec with 2 occupation both, put worker to furthest
        for gas_structure in self.gas_structures.sorted(lambda structure: len(self.gas_structure_tag_workers_gas_tag[structure.tag])):
            self.workers_gas_mining_tags.add(worker.tag)
            self.gas_structure_tag_workers_gas_tag[gas_structure.tag].add(worker.tag)
            self.gas_worker_tag_gas_structure_tag[worker.tag] = gas_structure.tag
            # if worker.is_carrying_resource:
            #     worker.return_resource()
            #     worker.gather(gas_structure, queue=True)
            # else:                 
            #     worker.gather(gas_structure)       

            # print('added to gas mining', self.bot.time_formatted)

            return True
        
        return False

    # TODO
    # maybe get worker closest also with minerals, return mineral and then queue new order

    def get_worker_from_gas_mining(self, position=None): 

        if position is None:
            position = self.th.position

        if len(self.workers_gas_mining_tags) == 0 :
            print('empty gas worker,  cant get worker from gas     th.position', self.th.position)
            # todo take only  without gas in hands
            return None

        # todo check if gas deplated
        # todo when 2 gas_structures with 3 occupation both, put worker to closer
        for gas_structure in self.gas_structures.sorted(lambda structure: structure.has_vespene and len(self.gas_structure_tag_workers_gas_tag[structure.tag]), reverse=True):
            # workers = self.bot.workers.tags_in(self.gas_structure_tag_workers_gas_tag[gas_structure.tag]).sorted(lambda worker: worker.is_carrying_resource)
            workers = self.bot.workers.tags_in(self.gas_structure_tag_workers_gas_tag[gas_structure.tag]).filter(lambda worker: not worker.is_carrying_resource)
            if workers:
                worker = workers.sorted_by_distance_to(position).first
                self.workers_gas_mining_tags.remove(worker.tag)
                self.gas_structure_tag_workers_gas_tag[gas_structure.tag].remove(worker.tag)
                del self.gas_worker_tag_gas_structure_tag[worker.tag]
                # print('get_worker_from_gas_mining', self.bot.time_formatted)

                return worker

        return None


    # for worker defence
    def get_worker_from_mining_health_sorted(self, position=None): 
        
        if position is None:
            position = self.th.position

        # # full health
        # workers = self.bot.workers.tags_in(self.workers_mining_tag).gathering
        # workers = workers.filter(lambda unit: unit.health > unit.health_max-5 and unit.shield > unit.shield_max-5)
        # workers = workers.sorted_by_distance_to(position)

        # for worker in workers:              
        #     self.workers_mining_tag.remove(worker.tag)  
        #     self.mineral_tag_occupation[self.worker_tag_mineral_tag[worker.tag]] -= 1
        #     return worker

        # full health also with minerals
        workers = self.workers
        workers = workers.filter(lambda unit: unit.health > unit.health_max-5 and unit.shield > unit.shield_max-5)
        workers = workers.sorted_by_distance_to(position)

        for worker in self.workers.sorted_by_distance_to(position):  
            if worker.tag in self.workers_mining_tag:      
                self.workers_mining_tag.remove(worker.tag)  
            else:
                print("worker.tag not in workers_mining_tag  def get_worker_from_mining_health_sorted")
            self.mineral_tag_occupation[self.worker_tag_mineral_tag[worker.tag]] -= 1   
            self.workers.remove(worker)         
            return worker

        # sorted by health
        workers = self.workers
        workers = workers.sorted(key=lambda unit: unit.health + unit.shield, reverse=True)
        if workers:
            worker = workers.first              
            self.workers_mining_tag.remove(worker.tag)  
            self.mineral_tag_occupation[self.worker_tag_mineral_tag[worker.tag]] -= 1    
            self.workers.remove(worker)         

            return worker

        return None


    # dead workers
    def remove_worker_from_mining(self, worker_tag: int = 0): 
        # TODO worker in bunker, pf
        
        worker = self.workers.find_by_tag(worker_tag)
        if worker is not None:
            self.workers.remove(worker)

        if worker_tag and worker_tag in self.workers_mining_tag:
            self.workers_mining_tag.remove(worker_tag)  
            self.mineral_tag_occupation[self.worker_tag_mineral_tag[worker_tag]] -= 1
            return True

        # else:
        #     # print('remove_worker_from_mining tag = 0')
        #     for worker_tag in self.workers_mining_tag[::-1]:
        #         if worker_tag not in self.bot.workers.tags:     # care when buner/prism mining

        #             print('remove_worker_from_mining tag = 0', 'worker_tag', worker_tag, 'self.bot.workers.tags', self.bot.workers.tags)

        #             self.workers_mining_tag.remove(worker_tag)  
        #             self.mineral_tag_occupation[self.worker_tag_mineral_tag[worker_tag]] -= 1
                    
        return False


    # dead workers
    def remove_worker_from_gas_mining(self, worker_tag): 
        # TODO worker in bunker, pf
        if worker_tag not in self.workers_gas_mining_tags:
            return False

        gas_structure_tag = self.gas_worker_tag_gas_structure_tag[worker_tag]
        self.gas_structure_tag_workers_gas_tag[gas_structure_tag].remove(worker_tag)
        self.workers_gas_mining_tags.remove(worker_tag)        
        del self.gas_worker_tag_gas_structure_tag[worker_tag]



        return True
        


    def mineralsexhausted(self):
        for mineral_tag in list(self.minerals_tags):
            if mineral_tag not in self.bot.mineral_field.tags:
                self.minerals_tags.remove(mineral_tag)
                del self.mineral_tag_occupation[mineral_tag]

                for worker_tag in self.workers_mining_tag[::-1]:
                    if self.worker_tag_mineral_tag[worker_tag] == mineral_tag:
                        del self.worker_tag_mineral_tag[worker_tag]
                        self.workers_mining_tag.remove(worker_tag)

    # def vespeneexhausted(self):        
    #     # destroyed or exhausted gas_structure
    #     for worker_tag in list(self.workers_gas_mining_tags):
    #         if self.gas_worker_tag_gas_structure_tag[worker_tag] not in self.gas_structures.tags:
    #             self.workers_gas_mining_tags.remove(worker_tag)
    #             del self.gas_worker_tag_gas_structure_tag[worker_tag]





    def calculate_points_to_gather(self, townhall: Unit):    

        for mineral in self.mineral_field.sorted_by_distance_to(self.th):
            if mineral.tag in self.mineral_tag_return_point:
                # print('already calculated')
                continue
            
            townhall_points_add_to_center = [Point2((-1, -2.5)), Point2((1, -2.5)), Point2((2.5, -1)), Point2((2.5, 1)), Point2((1, 2.5)), Point2((-1, 2.5)), Point2((-2.5, 1)), Point2((-2.5, -1))]      
            townhall_points = [townhall.position + point for point in townhall_points_add_to_center] # corner points

            mineral_points_add_to_center = [Point2((1, 0.5)), Point2((-1, 0.5)), Point2((-1, -0.5)), Point2((1, -0.5))]      
            mineral_points = [mineral.position + point for point in mineral_points_add_to_center] # corner points

            townhall_points = sorted(townhall_points, key = lambda p: sum([p.distance_to(p2) for p2 in  mineral_points]))[:2]
            mineral_points = sorted(mineral_points, key = lambda p: sum([p.distance_to(p2) for p2 in  townhall_points]))[:2]

            for i in range(1, 4):
                townhall_points.append(townhall_points[0].towards(townhall_points[1], i * 0.375)) 
                townhall_points.append(townhall_points[1].towards(townhall_points[0], i * 0.375))

            # # todo, more dense points
            # # check if any other taken points not closer than 0.75

            # for i in range(1, 4):
            #     point = townhall_points[0].towards(townhall_points[1], i * 0.375)
            #     if all(point.distance_to(point_taken) > 0.5 for point_taken in self.mineral_tag_return_point.values()): 
            #         townhall_points.append(point) 
            #     else:
            #         print("point too close")
            #     point = townhall_points[1].towards(townhall_points[0], i * 0.375)
            #     if all(point.distance_to(point_taken) > 1.5 for point_taken in self.mineral_tag_return_point.values()): 
            #         townhall_points.append(point)                     
            #     else:
            #         print("point too close")

            for i in range(1, 3):
                mineral_points.append(mineral_points[0].towards(mineral_points[1], i * 0.375))
                mineral_points.append(mineral_points[1].towards(mineral_points[0], i * 0.375))
            mineral_points = list(set(mineral_points))



            valid_paths = []
            for mineral_point in mineral_points:
                for townhall_point in townhall_points:
                    if self.bot.in_pathing_grid(mineral_point.towards(townhall_point, 0.375)): 
                        valid_paths.append((mineral_point.distance_to(townhall_point), mineral_point, townhall_point))

            # fix for speed_mining_simple pocket mineral hang
            if not valid_paths or not self.bot.in_pathing_grid(mineral.position.towards(self.th.position, 1.375)):
                # print(mineral.position, "not in_pathing_grid")
                mineral_points_add_to_center = [Point2((1.375, 0)), Point2((-1.375, 0)), Point2((0.5, 0.875)), Point2((0.5, -0.875)), Point2((-0.5, 0.875)), Point2((-0.5, -0.875))]                  
                mineral_points = [mineral.position + point for point in mineral_points_add_to_center] # corner points
                # mineral_points = [point for point in mineral_points_add_to_center if self.bot.in_pathing_grid(point)] 
                mineral_points = filter(self.bot.in_pathing_grid, mineral_points)
                point = min(mineral_points, key=lambda point: point.distance_to(self.th.position))
                self.mineral_tag_corrected_gather_point[mineral.tag] = point


            if not valid_paths:

                # print('something wrong with mineral patch', str(self.bot.game_info.map_name))
                # self.mineral_mining_type = 'default'
                # valid_paths = [(8, mineral.position, townhall.position)]

                print('correting mineral patch')
                # mineral_points_add_to_center = [Point2((1.375, 0)), Point2((-1.375, 0)), Point2((0.875, 0.5)), Point2((0.875, -0.5)), Point2((-0.875, 0.5)), Point2((-0.875, -0.5))]  
                mineral_points_add_to_center = [Point2((1, 0)), Point2((-1, 0)), Point2((0.5, 0.5)), Point2((0.5, -0.5)), Point2((-0.5, 0.5)), Point2((-0.5, -0.5))]                  
                mineral_points = [mineral.position + point for point in mineral_points_add_to_center] # corner points

                for mineral_point in mineral_points + [self.mineral_tag_corrected_gather_point[mineral.tag]]:
                    for townhall_point in townhall_points:
                        if self.bot.in_pathing_grid(mineral_point.towards(townhall_point, 0.375)): 
                            valid_paths.append((mineral_point.distance_to(townhall_point), mineral_point, townhall_point))

                if not valid_paths: # this should never happen
                    print('still something wrong with mineral patch', str(self.bot.game_info.map_name))
                    # self.mineral_mining_type = 'default'                    
                    # valid_paths = [(8, mineral.position.towards(townhall.position, 3), townhall.position)]



                
            valid_paths.sort()            
            dist, mineral_point, townhall_point = valid_paths[0]

            self.mineral_tag_gather_point[mineral.tag] = mineral_point.towards(townhall_point, 0.375) # + 0.04424 (?)
            self.mineral_tag_return_point[mineral.tag] = townhall_point.towards(mineral_point, 0.375)
            self.mineral_tag_occupation[mineral.tag] = 0


            # # speed_mining_simple gther point            
            # mineral_points_add_to_center = [Point2((1.375, 0)), Point2((-1.375, 0)), Point2((0.5, 0.875)), Point2((0.5, -0.875)), Point2((-0.5, 0.875)), Point2((-0.5, -0.875)),   Point2((0, 0.875)), Point2((0, -0.875)),     Point2((0.5, 0)).towards(Point2((1, 0.5)), 0.375 + 0.7), Point2((0.5, 0)).towards(Point2((1, -0.5)), 0.375 + 0.7),  Point2((-0.5, 0)).towards(Point2((-1, 0.5)), 0.375 + 0.7), Point2((-0.5, 0)).towards(Point2((-1, -0.5)), 0.375 + 0.7)]                  
            # mineral_points = [mineral.position + point for point in mineral_points_add_to_center] # corner points
            # # mineral_points = [point for point in mineral_points_add_to_center if self.bot.in_pathing_grid(point)] 
            # mineral_points = filter(self.bot.in_pathing_grid, mineral_points)
            # point = min(mineral_points, key=lambda point: point.distance_to(self.th.position))
            # self.mineral_tag_simple_gather_point[mineral.tag] = point


        # # # speed_mining_simple mineral distance        
        # for mineral in self.mineral_field.sorted_by_distance_to(self.th):
        #     dist_x = abs(self.th.position.x - mineral.position.x)
        #     dist_y = abs(self.th.position.y - mineral.position.y)
        #     if dist_x < 2.1:
        #         self.mineral_distance_for_simple[mineral.tag] = 0.55
        #     elif dist_x < 3.7:
        #         self.mineral_distance_for_simple[mineral.tag] = 0.65
        #     elif dist_y < 2.1:
        #         self.mineral_distance_for_simple[mineral.tag] = 1                
        #     elif dist_y < 3.7:
        #         self.mineral_distance_for_simple[mineral.tag] = 1
        #     else:
        #         self.mineral_distance_for_simple[mineral.tag] = 0.9




        #     mineral_points_add_to_center = [Point2((1.375, 0)), Point2((-1.375, 0)), Point2((0.5, 0.875)), Point2((0.5, -0.875)), Point2((-0.5, 0.875)), Point2((-0.5, -0.875)),   Point2((0, 0.875)), Point2((0, -0.875)),     Point2((0.5, 0)).towards(Point2((1, 0.5)), 0.375 + 0.7), Point2((0.5, 0)).towards(Point2((1, -0.5)), 0.375 + 0.7),  Point2((-0.5, 0)).towards(Point2((-1, 0.5)), 0.375 + 0.7), Point2((-0.5, 0)).towards(Point2((-1, -0.5)), 0.375 + 0.7)]                  
        #     mineral_points = [mineral.position + point for point in mineral_points_add_to_center]           
        #     point = min(mineral_points, key=lambda point: point.distance_to(self.th.position))
        #     if point.distance_to(mineral.position) == 0.875:
        #         self.mineral_tag_short.add(mineral.tag)

        # print("self.mineral_tag_short", len(self.mineral_tag_short), self.mineral_tag_short)