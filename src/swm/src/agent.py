import logging
import importlib
import multiprocessing

class Agent:
    def __init__(self):
        pass

    # Initialization
    def initialize(self, name):
        """
        This function allows agent to be initialized. We do not use basic __init__ to let
        user choose a valid variant of agent. You can take agent with other abilities.
        """
        self.name = name

    def load_swm(self, path=None, type = None):
        from mapcore.swm.src.components.sign_task import load_signs
        """
        This functions is needed to load swm.
        :return: signs
        """
        logging.info('Означивание начато: {0}'.format(self.name))
        signs = load_signs(self.name, file_name=path, load_type=type)
        logging.info('Означивание окончено: {0}'.format(self.name))
        if signs:
            logging.info('{0} знаков создано'.format(len(signs)))
        return signs

    def update_swm(self, signs):
        pass

class Manager:
    def __init__(self, agpath = 'swm.agent.agent_search', agtype = 'Agent'):
        self.agtype = agtype
        self.agpath = agpath

    def agent_start(self, agent):
        """
        Function that send task to agent
        :param agent: I
        :return: flag that task accomplished
        """
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger("process-%r" % (agent.name))
        #logger.info('Агент {0} начал означивание'.format(agent.name))
        saved = agent.update_swm()
        if saved:
            logger.info('Агент {0} окончил означивание.'.format(agent.name))
        return agent.name +' finished'

    def manage_agent(self):
        """
        Create a separate process for the agent
        """
        class_ = getattr(importlib.import_module(self.agpath), self.agtype)
        workman = class_()
        workman.initialize('I')
        multiprocessing.set_start_method('spawn')
        ag = multiprocessing.Process(target=self.agent_start, args = (workman, ))
        ag.start()
        ag.join()
        return None
