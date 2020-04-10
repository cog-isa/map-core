import importlib
import logging
import multiprocessing
import os
import random
import time
from copy import copy

from mapcore.planning.grounding import pddl_grounding
from mapcore.planning.search.mapsearch import MapSearch
from mapcore.planning.grounding import hddl_grounding
from mapcore.swm.src.agent import Agent


class PlanningAgent(Agent):
    def __init__(self):
        pass

    # Initialization
    def initialize(self, problem, TaskType, backward):
        """
        This function allows agent to be initialized. We do not use basic __init__ to let
        user choose a valid variant of agent. You can take agent with othe abilities.
        :param problem: problem
        :param ref: the dynamic value of plan clarification
        """
        try:
            if TaskType != 'hddl':
                self.name = [el for el, type in problem.objects.items() if type.name == 'agent'][0]
                self.backward = backward
            else:
                self.name = [el for el, type in problem.objects if type == 'agent'][0]
                self.backward = False
        except Exception:
            self.name = 'I'
            self.backward = backward
        self.problem = problem
        self.solution = []
        self.final_solution = ''

        self.TaskType = TaskType
        super().initialize(self.name)

    # Grounding tasks
    def get_task(self):
        """
        This functions is needed to load swm.
        :return: task - sign representation of the problem.
        """
        logging.info('Начато означивание: {0}'.format(self.problem.name))
        signs = self.load_swm(type='classic')
        if self.TaskType == 'hddl':
            task = hddl_grounding.ground(self.problem, self.name, signs)
        else:
            task = pddl_grounding.ground(self.problem, self.name, signs)
        logging.info('Означивание окончено: {0}'.format(self.problem.name))
        logging.info('{0} знаков добавлено'.format(len(task.signs)))
        return task

    def is_actual(self, task, action, agent_predicates):
        chains = task.start_situation.images[1].spread_down_activity('image', 5)
        used = set()
        for chain in chains:
            if chain[-1].sign.name == 'I':
                ag_pred = chain[1].sign.name
                if ag_pred in action[1]:
                    cm_signs_names = {s.name for s in chain[1].get_signs() if s.name != 'I'}
                    for name, value in action[1].items():
                        if name == ag_pred and len(value) == 1:
                            if cm_signs_names == value:
                                used.add(ag_pred)
                                if used == agent_predicates:
                                    return False
        return True

    def search_solution(self):
        """
        This function is needed to synthesize all plans, choose the best one and
        save the experience.
        """
        task = self.get_task()
        logging.info('Классический поиск плана в задаче {0} начат. Время: {1}'.format(task.name, time.clock()))
        solutions = []
        goal = None
        if self.TaskType == 'hddl':
            task = self.expand_task_blocks(task)
            htn = task.subtasks[0]
            start = task.start_situation
            for subtask in task.scenario:
                subt_solutions= []
                for action in subtask[1]:
                    agent_predicates = {cm.sign.name for cm in task.signs['I'].spread_up_activity_obj('significance', 4)
                                        if cm.sign.name in action[1]}
                    if self.is_actual(task, action, agent_predicates):
                        task.actions = [action[0]]
                        task.subtasks = {name:value for name, value in action[1].items() if name in agent_predicates}
                        search = MapSearch(task, self.TaskType, self.backward)
                        solution, goal = search.search_plan()
                        task.start_situation = goal
                        subt_solutions.extend(solution[0])
                sol_repr = ', '.join([act[1] for act in subt_solutions])
                logging.info('При решении подзадачи {0} был синтезирован план: {1}'.format(subtask[0].sign.name, sol_repr))
                solutions.extend(subt_solutions)
            logging.info('При решении задачи {0} был синтезирован план: {1}'.format(htn.name, ', '.join([act[1] for act in solutions])))
            solutions = [solutions]
            task.start_situation = start
        else:
            search = MapSearch(task, self.TaskType, self.backward)
            solutions, goal = search.search_plan()
        if goal:
            if not self.backward:
                task.goal_situation = goal
            else:
                task.start_situation = goal
        file_name = None
        if solutions:
            self.solution = self.sort_plans(solutions)
            if self.backward:
                self.solution = list(reversed(self.solution))
            file_name = task.save_signs(self.solution)
            if file_name:
                logging.info('Агент ' + self.name + ' закончил закочил деятельность.')
        else:
            logging.info('Агент' + self.name + ' не смог найти решения проблемы %s' % self.problem.name)
        if not file_name:
            for f in os.listdir(os.getcwd()):
                if f.startswith('wmodel_'):
                    if f.split(".")[0].endswith(self.name) or f.split(".")[0].endswith('agent'):
                        file_name = f
                        break
        if file_name:
            file_name = os.getcwd() +'/'+ file_name
        else:
            raise Exception("Can't find solution! Change your task.")
        return (self.solution, goal), file_name

    def sort_plans(self, plans):
        logging.info("Агент %s выбрал наиболее приемлимый для него план." %self.name)

        minlength = min([len(pl) for pl in plans])
        plans = [plan for plan in plans if len(plan) == minlength]
        busiest = []
        for index, plan in enumerate(plans):
            previous_agent = ""
            agents = {}
            counter = 0
            plan_agents = []
            for action in plan:
                if action[3] not in agents:
                    agents[action[3]] = 1
                    previous_agent = action[3]
                    counter = 1
                    if not action[3] is None:
                        plan_agents.append(action[3].name)
                    else:
                        plan_agents.append(str(action[3]))
                elif not previous_agent == action[3]:
                    previous_agent = action[3]
                    counter = 1
                elif previous_agent == action[3]:
                    counter += 1
                    if agents[action[3]] < counter:
                        agents[action[3]] = counter
            # max queue of acts
            longest = 0
            agent = ""
            for element in range(len(agents)):
                item = agents.popitem()
                if item[1] > longest:
                    longest = item[1]
                    agent = item[0]
            busiest.append((index, agent, longest, plan_agents))
        cheap = []
        alternative = []
        cheapest = []
        longest = 0
        min_agents = 100

        for plan in busiest:
            if plan[2] > longest:
                longest = plan[2]

        for plan in busiest:
            if plan[2] == longest:
                if len(plan[3]) < min_agents:
                    min_agents = len(plan[3])

        for plan in busiest:
            if plan[3][0]:
                if plan[2] == longest and len(plan[3]) == min_agents and "I" in plan[3]:
                    plans_copy = copy(plans)
                    cheap.append(plans_copy.pop(plan[0]))
                elif plan[2] == longest and len(plan[3]) == min_agents and not "I" in plan[3]:
                    plans_copy = copy(plans)
                    alternative.append(plans_copy.pop(plan[0]))
            else:
                plans_copy = copy(plans)
                cheap.append(plans_copy.pop(plan[0]))
        if len(cheap) >= 1:
            cheapest.extend(random.choice(cheap))
        elif len(cheap) == 0 and len(alternative):
            logging.info("There are no plans in which I figure")
            cheapest.extend(random.choice(alternative))

        return cheapest

    def expand_task_blocks(self, task):
        """
        Expand standart HTN mastrix to list of subtasks
        :param task:
        :return:
        """
        def spread_down_activity_act(cm, base, depth):
            active_pms = []
            if depth > 0:
                for event in cm.cause:
                    for connector in event.coincidences:
                        out_cm = connector.get_out_cm(base)
                        if out_cm.is_causal():
                            active_pms.append(connector.get_out_cm(base))
                        else:
                            pms = spread_down_activity_act(out_cm, base, depth - 1)
                            active_pms.extend(pms)
            return active_pms
        htn = task.subtasks[0]
        subtasks = []
        subt_scenario = []
        for event in htn.meanings[1].cause:
            for connector in event.coincidences:
                cm = connector.out_sign.meanings[connector.out_index]
                subtasks.append(cm)
                logging.info('Для HTN задачи была найдена подцель %s' % cm.sign.name)
        for subtask in subtasks:
            actions = spread_down_activity_act(subtask, 'meaning', 3)
            task_scenario = []
            for act in actions:
                replaced = {}
                #take only effects of action, because we need only last situation to check.
                chains = []
                for event in act.effect:
                    for connector in event.coincidences:
                        out_cm = connector.get_out_cm('meaning')
                        chains.extend(out_cm.spread_down_activity('meaning', 4))
                for chain in chains:
                    role_or_obj = chain[-1].sign
                    is_role = [cm for _, cm in role_or_obj.significances.items() if not cm.is_empty()]
                    if not is_role:
                        replaced.setdefault(chain[0].sign.name, set()).add(role_or_obj.name)
                        if (act.sign, replaced) not in task_scenario:
                            task_scenario.append((act.sign, replaced))
            subt_scenario.append((subtask, task_scenario))
        task.scenario = subt_scenario
        return task


def agent_activation(agpath, agtype, problem, backward, TaskType, childpipe):
    """
    Function that activate an agent
    :param agent: I
    :return: flag that task accomplished
    """
    logging.basicConfig(level=logging.INFO)
    class_ = getattr(importlib.import_module(agpath), agtype)
    workman = class_()
    workman.initialize(problem, TaskType, backward)
    logging.info('Агент начал классическое планирование')
    solution, file_name = workman.search_solution()
    if solution:
        #logging.info('Агент закончил классическое планирование')
        childpipe.send({workman.name:(solution, file_name)})


class Manager:
    def __init__(self, problem, agpath = 'planning.agent.planning_agent', agtype = 'PlanningAgent', TaskType = 'pddl', backward = False):
        self.problem = problem
        self.solution = []
        self.finished = None
        self.agtype = agtype
        self.agpath = agpath
        self.TaskType = TaskType
        self.backward = backward

    def manage_agent(self):
        """
        Create a separate process for the agent
        :return: the best solution
        """
        try:
            multiprocessing.set_start_method('spawn')
        except RuntimeError:
            pass
        parent_conn, child_conn = multiprocessing.Pipe()
        p = multiprocessing.Process(target=agent_activation, args = (self.agpath, self.agtype, self.problem, self.backward, self.TaskType, child_conn,))
        p.start()
        solution = parent_conn.recv()
        p.join()
        return solution
