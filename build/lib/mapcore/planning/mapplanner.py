import logging
import os
from mapcore.planning.agent.planning_agent import Manager

SOLUTION_FILE_SUFFIX = '.soln'

import platform

if platform.system() != 'Windows':
    delim = '/'
else:
    delim = '\\'

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("process-main")

class MapPlanner():
    def __init__(self, **kwargs):
        if 'Settings' in kwargs.keys():
            self.kwgs = kwargs['Settings']
        else:
            self.kwgs = kwargs
        self.agpath = self.kwgs['agpath']
        self.TaskType = self.kwgs['tasktype']
        self.domain, self.problem = self.find_domain(self.kwgs['domain'],self.kwgs['path'], self.kwgs['task'])
        self.refinement = eval(self.kwgs['refinement_lv'])
        self.backward = eval(self.kwgs['backward'])
        logger.info('Планировщик МАР активирован...')

    def search_upper(self, path, file):
        """
        Recursive domain search
        :param path: path to the current task
        :param file: domain name
        :return: full path to the domain
        """
        if not file in os.listdir(path):
            path_to_list = path.split(delim)[:-2]
            if platform.system() != 'Windows':
                new_path = delim
            else:
                new_path = path_to_list[0]+delim
            path_to_list = path_to_list[1:]
            for element in path_to_list:
                new_path+=element + delim
            return self.search_upper(new_path, file)
        else:
            if not path.endswith(delim):
                path = path + delim
            return path + file


    def find_domain(self, domain, path, number):
        """
        Domain search function
        :param path: path to current task
        :param number: task number
        :return:
        """
        ext = '.pddl'
        if self.TaskType == 'hddl':
            ext = '.hddl'
        task = 'task' + number + ext
        domain += ext
        if not domain in os.listdir(path):
            domain2 = self.search_upper(path, domain)
            if not domain2:
                raise Exception('domain not found!')
            else:
                domain = domain2
        else:
            domain = path + domain
        if not task in os.listdir(path):
            raise Exception('task not found!')
        else:
            problem = path + task

        return domain, problem

    def _parse_pddl(self):
        """
        pddl Parser
        :param domain_file:
        :param problem_file:
        :return:
        """
        from mapcore.planning.parsers.pddl_parser import Parser

        parser = Parser(self.domain, self.problem)
        logging.info('Parsing Domain {0}'.format(self.domain))
        domain = parser.parse_domain()
        logging.info('Parsing Problem {0}'.format(self.problem))
        problem = parser.parse_problem(domain)
        logging.debug(domain)
        logging.debug('{0} Predicates parsed'.format(len(domain.predicates)))
        logging.debug('{0} Actions parsed'.format(len(domain.actions)))
        logging.debug('{0} Objects parsed'.format(len(problem.objects)))
        logging.debug('{0} Constants parsed'.format(len(domain.constants)))
        return problem

    def _parse_hddl(self):
        """
        pddl Parser
        :param domain_file:
        :param problem_file:
        :return:
        """
        from mapcore.planning.parsers.hddl_parser import HTNParser
        parser = HTNParser(self.domain, self.problem)
        logging.info('Распознавание домена {0} ...'.format(self.domain))
        domain = parser.ParseDomain(parser.domain)
        logging.info('Распознавание проблемы {0} ...'.format(self.problem))
        problem = parser.ParseProblem(parser.problem, domain)
        logging.debug('{0} Predicates parsed'.format(len(domain['predicates'])))
        logging.debug('{0} Actions parsed'.format(len(domain['actions'])))
        return problem


    def search(self):
        """
        classic PDLL- or HTN- based plan search
        :return: the final solution
        """
        if self.TaskType == 'hddl':
            problem = self._parse_hddl()
        else:
            problem = self._parse_pddl()
        logger.info('Классическая задача получена и распознана.')
        manager = Manager(problem, self.agpath, TaskType=self.TaskType, backward=self.backward)
        solution = manager.manage_agent()
        return solution