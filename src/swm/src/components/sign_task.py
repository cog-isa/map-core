import datetime
import logging
import os
import pickle

DEFAULT_FILE_PREFIX = 'wmodel_'
DEFAULT_FILE_SUFFIX = '.swm'

SIT_COUNTER = 0
SIT_PREFIX = 'situation_'
PLAN_PREFIX = 'action_'

def load_signs(agent, file_name=None, load_type=None):
    if not file_name:
        file_name = []
        for f in os.listdir(os.getcwd()):
            if f.startswith(DEFAULT_FILE_PREFIX):
                if f.split(".")[0].endswith(agent) or f.split(".")[0].endswith('agent'):
                    file_name.append(f)
    else:
        file_name = [file_name]
    if file_name:
        if load_type:
            file_name = [name for name in file_name if load_type in name]
        newest = 0
        file_load = ''
        for file in file_name:
            file_signature = int(''.join([i if i.isdigit() else '' for i in file]))
            if file_signature > newest:
                newest = file_signature
                file_load = file
        if file_load:
            signs = pickle.load(open(file_load, 'rb'))
        else:
            signs = None
    else:
        logging.debug('No experience file was found for agent %s' % agent)
        return None
    return signs

class Task:
    def __init__(self, name, signs):
        self.name = name
        self.signs = signs


    def __str__(self):
        s = 'Task {0}\n  Signs:  {1}\n'
        return s.format(self.name, '\n'.join(map(repr, self.signs)))

    __repr__ = __str__

    def save_signs(self):
        """
        Cleaning swm and saving signs
        """
        def __is_role(pm):
            chains = pm.spread_down_activity('meaning', 6)
            for chain in chains:
                maxim = max([len(cm.cause) for cm in chain[-1].sign.significances.values()])
                if maxim != 0:
                    break
            else:
                return False
            return True

        logging.info('\tCleaning swm...')

        for name, s in self.signs.copy().items():
            signif=list(s.significances.items())
            if name.startswith(SIT_PREFIX):
                for _, pm in s.meanings.copy().items():
                    s.remove_meaning(pm)
                for _, im in s.images.copy().items():
                    s.remove_image(im)
            elif len(signif):
                if len(signif[0][1].cause) and len(signif[0][1].effect): #delete action's meanings that are not in plan
                    for index, pm in s.meanings.copy().items():
                        if __is_role(pm):  # delete only fully signed actions
                            continue
                        else:
                            s.remove_meaning(pm)
        else:
            for name, sign in self.signs.copy().items():
                if name.startswith(SIT_PREFIX):
                    self.signs.pop(name)
                else:
                    sign.meanings = {}
                    sign.out_meanings = []
                    sign.images = {}
                    sign.out_images = []

        file_name = DEFAULT_FILE_PREFIX + datetime.datetime.now().strftime('%m_%d_%H_%M') + '_classic_'+ DEFAULT_FILE_SUFFIX
        logging.debug('Start saving to {0}'.format(file_name))
        logging.debug('\tDumping swm...')
        pickle.dump(self.signs, open(file_name, 'wb'))
        logging.debug('\tDumping swm finished')
        return file_name
