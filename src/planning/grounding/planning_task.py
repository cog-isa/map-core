import datetime
import logging
import pickle

from mapcore.swm.src.components.semnet import Sign
from mapcore.swm.src.components.sign_task import Task

DEFAULT_FILE_PREFIX = 'wmodel_'
DEFAULT_FILE_SUFFIX = '.swm'

SIT_COUNTER = 0
SIT_PREFIX = 'situation_'
PLAN_PREFIX = 'action_'


class PlanningTask(Task):
    def __init__(self, name, signs, start_situation, goal_situation, subtasks=None):
        super().__init__(name, signs)
        self.name = name
        self.signs = signs
        self.start_situation = start_situation
        self.goal_situation = goal_situation
        self.subtasks = subtasks
        self.I_obj = [con.in_sign for con in self.signs["I"].out_significances if con.out_sign.name == "I"]
        self.agents = [self.signs["I"]]
        self.agents.extend(self.I_obj)

    def __str__(self):
        s = 'Task {0}\n  Signs:  {1}\n  Start:  {2}\n  Goal: {3}\n'
        return s.format(self.name, '\n'.join(map(repr, self.signs)),
                        self.start_situation, self.goal_situation)

    def __repr__(self):
        return '<Task {0}, signs: {1}>'.format(self.name, len(self.signs))

    def save_classic(self, plan):
        logging.info('\tСохраняю классический прецедент...')
        plan_sign, _, _ = self.save_plan(self.signs[self.start_situation.name].images[1], self.signs[self.goal_situation.name].images[1], plan, '')
        # Add connection to goal situation
        goal_signif = self.goal_situation.add_significance()
        connector = goal_signif.add_feature(plan_sign.significances[1])
        plan_sign.add_out_significance(connector)

    def save_signs(self, plan):
        """
        Cleaning swm and saving experience
        :param plan:
        :return:
        """
        def __is_role(pm, agents):
            chains = pm.spread_down_activity('meaning', 6)
            for chain in chains:
                if chain[-1].sign not in agents:
                    maxim = max([len(cm.cause) for cm in chain[-1].sign.significances.values()])
                    if maxim != 0:
                        break
            else:
                return False
            return True

        logging.info('Начинаю подготовку к сохранению плана...')
        if plan:
            logging.debug('\tCleaning swm...')

            self.start_situation.name += self.name
            self.goal_situation.name += self.name

            plan_sit = [pm[0].sign for pm in plan]
            pl_cm_ind = [pm[0].index for pm in plan]

            if self.start_situation not in plan_sit:
                plan_sit.append(self.start_situation)
            if self.goal_situation not in plan_sit:
                plan_sit.append(self.goal_situation)
            pms_act = [pm[2] for pm in plan]

            for name, s in self.signs.copy().items():
                signif=list(s.significances.items())
                if name.startswith(SIT_PREFIX):
                    if s in plan_sit: # save only 1 image per plan sit
                        for index, im in s.images.copy().items():
                            if index not in pl_cm_ind:
                                s.remove_image(im)
                        for index, pm in s.meanings.copy().items():
                            if index != 1:
                                s.remove_meaning(pm)  # save only 1 mean per plan sit
                    else:
                        for _, pm in s.meanings.copy().items():
                            s.remove_meaning(pm)  # delete all meanings of not-plan situations
                        self.signs.pop(name)

                elif len(signif):
                    if len(signif[0][1].cause) and len(signif[0][1].effect): #delete action's meanings that are not in plan
                        for index, pm in s.meanings.copy().items():
                            if __is_role(pm, self.agents):  # delete only fully signed actions
                                if len(pm.cause)-1 == len(signif[0][1].cause) and len(pm.effect)-1 == len(signif[0][1].effect):
                                    continue
                                else:
                                    s.remove_meaning(pm)
                            else:
                                if pm not in pms_act:
                                    s.remove_meaning(pm)
            global_sit = self.signs['situation']
            for ind, im in global_sit.images.copy().items():
                pm_signs = im.get_signs()
                for sit in pm_signs:
                    if sit in plan_sit:
                        global_sit.images.pop(ind)
                    else:
                        global_sit.remove_image(im)

            for sit in plan_sit:
                sit.out_images = []
                global_cm = global_sit.add_image()
                sit_im = sit.images[1]
                connector = global_cm.add_feature(sit_im)
                sit.add_out_image(connector)

            self.signs[self.start_situation.name] = self.start_situation
            self.signs[self.goal_situation.name] = self.goal_situation

            self.save_classic(pms_act)

        else:
            for name, sign in self.signs.copy().items():
                if name.startswith(SIT_PREFIX):
                    self.signs.pop(name)
                else:
                    sign.meanings = {}
                    sign.out_meanings = []
                    sign.images = {}
                    sign.out_images = []
        if self.I_obj:
            I_obj = "_"+self.I_obj[0].name
        else:
            I_obj = 'I'
        file_name = DEFAULT_FILE_PREFIX + datetime.datetime.now().strftime('%m_%d_%H_%M') + '_classic_' + I_obj + DEFAULT_FILE_SUFFIX
        logging.info('Файл классического опыта: {0}'.format(file_name))
        logging.debug('\tDumping swm...')
        pickle.dump(self.signs, open(file_name, 'wb'))
        logging.info('\tСохранение выполнено.')
        return file_name

    def save_plan(self, start, finish, actions, plan_name):
        # Creating plan action for further use
        if not plan_name:
            plan_name = 'plan_'+ self.name
        if not start.sign.meanings:
            scm = start.copy('image', 'meaning')
            start.sign.add_meaning(scm)
            for con in start.sign.out_meanings.copy():
                if con.in_sign.name == plan_name:
                    start.sign.out_meanings.remove(con)
        if not finish.sign.meanings:
            fcm = finish.copy('image', 'meaning')
            finish.sign.add_meaning(fcm)
            for con in finish.sign.out_meanings.copy():
                if con.in_sign.name == plan_name:
                    finish.sign.out_meanings.remove(con)
        plan_sign = Sign(plan_name + self.name)
        plan_mean = plan_sign.add_meaning()
        connector = plan_mean.add_feature(start.sign.meanings[1])
        start.sign.add_out_meaning(connector)
        conn = plan_mean.add_feature(finish.sign.meanings[1], effect=True)
        finish.sign.add_out_meaning(conn)
        self.signs[plan_sign.name] = plan_sign

        # Adding Sequence of actions to plan image
        plan_image = plan_sign.add_image()
        for act in actions:
            im = act.sign.add_image()
            connector = plan_image.add_feature(im)
            act.sign.add_out_image(connector)

        # Adding scenario vs partly concrete actions to the plan sign
        scenario = self.scenario_builder(start, finish, actions)
        plan_signif = plan_sign.add_significance()
        for act in scenario:
            connector = plan_signif.add_feature(act)
            act.sign.add_out_significance(connector)

        return [plan_sign, start.sign, finish.sign]

    def scenario_builder(self, start, goal, PlActs):
        scenario = []
        for act in PlActs:
            scenario.append(act.sign.significances[1])

        return scenario

