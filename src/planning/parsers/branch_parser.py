"""
This file contain functions to parse branches and  leaves

"""

import re

import logging


class HtnStmt():
    def __init__(self, parameters, subtasks, ordering_list):
        self.parameters = parameters
        self.subtasks = subtasks
        self.ordering = ordering_list


class PredicatesStmt():
    def __init__(self, name, signature):
        self.name = name[0]
        self.signature = signature
        self.arity = len(signature)

    def __repr__(self):
        predicate = self.name + ' '
        for element in self.signature:
            if isinstance(element, tuple):
                element = element[0] +' - ' + element[1]
            predicate+=element + ' '
        return predicate[:-1]


class TaskStmt():
    def __init__(self, name, parameters, precondition, effect):
        self.name = name[0]
        self.parameters = parameters
        self.precondition = precondition
        self.effect = effect

    def __repr__(self):
        return 'Task ' + self.name

class MethodStmt():
    def __init__(self, name, parameters, task, subtasks, ordering_list):
        self.name = name[0]
        self.parameters = parameters
        self.task = task[0][0]
        self.task_parameters = task[1]
        self.subtasks = subtasks
        self.ordering = ordering_list

    def __repr__(self):
        return 'Method ' + self.name + '. task: '+ self.task

class ActionStmt():
    def __init__(self,name, parameters, precond, effect):
        self.name = name[0]
        self.parameters = parameters
        self.preconditions = precond
        self.effect = [ef for ef in effect if len(ef) == 2]
        self.del_predicates = [(ef[1], ef[2]) for ef in effect if len(ef) == 3]

    def __repr__(self):
        return 'Action ' + self.name

def parse_types (types):
    """
    Parse are list of types
    :return: returns the list of tuples subtypes and types
    """
    return re.findall('([A-Za-z]*) - ([A-Za-z]*)', types)

def parse_predicates (preds_descr):
    """
    Parse a list of predicates
    :return: returns the list of PredicatesStmt objects
    """
    predicates = []
    for st, end, _ in tree_sample(preds_descr):
        predicate_descr = preds_descr[st:end].strip()
        name = re.findall('^\w+', predicate_descr)
        signatures = re.findall('(\?\w+) - (\w+)', predicate_descr)
        predicate = PredicatesStmt(name, signatures)
        predicates.append(predicate)
    return predicates

def tokenizer(tokens):
    for val in tokens:
        yield val

def parse_task (task):
    """
    Parse task. Tasks contain parameters, preconditions
    and effect groups of statements. Tasks can be realized by one or several
    methods. Tasks are abstract actions.
    :return: returns the TaskStmt object

    """
    ukeys = [':parameters', ':precondition', ':effect']
    name = re.findall('^\w+', task.strip())
    my_token = tokenizer(ukeys)
    flag = False
    start_token = next(my_token)
    definition =[]
    while not flag:
        try:
            next_token = next(my_token)
            part = [''.join(el) for el in task.split(start_token)[1].split(next_token)][0]
            signatures = re.findall('(\?\w+) - (\w+)', part)
            definition.append(signatures)
            start_token = next_token
        except StopIteration:
            part = [''.join(el) for el in task.split(start_token)][1]
            definition.append(re.findall('(\?\w+) - (\w+)', part))
            flag = True

    return TaskStmt(name, definition[0], definition[1], definition[2])

def method_task_parse(task):
    task_name = []
    task_params = []
    key = ''
    try:
        brackets =  list(*tree_sample(task))
        if brackets:
            task_descr = task[brackets[0]:brackets[1]].strip()
            key = task[:brackets[0]-1].strip()
        else:
            task_descr = task
        task_name = re.findall('^\w+', task_descr)
        task_params = re.findall('\?\w+', task_descr)
        if not task_params:
            task_params = [param for param in re.findall('\w+', task_descr) if param != task_name[0]]
    except Exception:
        logging.warning('Wrong pattern!! The pattern is "task_number (task_name params)"')
    return key, task_name, task_params

def parse_method (method):
    """
    Parse method. Methods contain parameters, task, subtasks
    and ordering if subtasks more than one. Methods are lists of actions or subtasks.
    Sometimes methods contain constraints of the current realization.
    :return: returns the MethodStmt object.

    """
    name = re.findall('^\w+', method.strip())
    params = [''.join(el) for el in method.split(':parameters')[1].split(':task')][0]
    parameters = re.findall('(\?\w+) - (\w+)', params)
    task = [''.join(el) for el in method.split(':task')[1].split(':subtasks')][0]
    _, task_name, task_params = method_task_parse('task' + task)
    task = task_name, task_params
    if ':ordering' in method:
        subtasks_descr = [''.join(el) for el in method.split(':subtasks')[1].split(':ordering')][0]
    else:
        subtasks_descr = [''.join(el) for el in method.split(':subtasks')][1]
    # Here is only 1 block parsing. If you want more - do the same. The key of block is 'and'.
    stasks = parse_block(subtasks_descr, maxd = 1)
    subtasks = {s[0]: (s[1], s[2]) for s in stasks}
    ordering_list = []
    if len(subtasks) > 1:
        ordering = [''.join(el) for el in method.split(':ordering')][1]
        # Here is only 1 block parsing. If you want more - do the same. The key of block is 'and'.
        brackets = list(tree_sample(ordering))
        max_depth = max([x for _, _, x in brackets])
        brackets = [br for br in brackets if br[2] == max_depth]
        for st, end, _ in brackets:
            or_decr = ordering[st:end].strip()
            lb = re.findall('(\w+) < (\w+)', or_decr)[0]
            if not ordering_list:
                ordering_list.extend(lb)
            else:
                ordering_list.append(lb[1])
    return MethodStmt(name, parameters, task, subtasks, ordering_list)

def parse_block(part, maxd=0):
    """
    Parse block of domen with attributes.
    :param part: block of hddl
    :param maxd: value of the max depth minus maxd
    :return: list with predicates names and parameters
    """
    part_to_list = []
    part_brackets = list(tree_sample(part))
    max_depth = max([x for _, _, x in part_brackets])
    part_brackets = [br for br in part_brackets if br[2] == max_depth-maxd]
    for st, end, _ in part_brackets:
        pred_decr = part[st:end].strip()
        key, pred_name, pred_params = method_task_parse(pred_decr)
        if key:
            part_to_list.append((key, pred_name[0], pred_params))
        else:
            part_to_list.append((pred_name[0], pred_params))
    return part_to_list

def parse_objects(objects):
    """
    Objects are list of objects with types.
    :param objects:
    :return: list of pairs object - type.
    """
    return re.findall('(\w+) - (\w+)', objects)

def parse_htn(htn):
    """
    htn - its a list of subgoals. Htn have parameters, subtasks and ordering
    :param htn:
    :return: htn Statement
    """
    params = [''.join(el) for el in htn.split(':parameters')[1].split(':subtasks')][0]
    parameters = re.findall('(\?\w+) - (\w+)', params)
    if ':ordering' in htn:
        subtasks_descr = [''.join(el) for el in htn.split(':subtasks')[1].split(':ordering')][0]
    else:
        subtasks_descr = [''.join(el) for el in htn.split(':subtasks')][1]
    # Here is only 1 block parsing. If you want more - do the same. The key of block is 'and'.
    part_brackets = [part for part in list(tree_sample(subtasks_descr)) if part[2] == 1]
    stasks = []
    for st, end, _ in part_brackets:
        stasks.append(method_task_parse(subtasks_descr[st:end]))
    subtasks = {s[0]: (s[1][0], s[2]) for s in stasks}
    ordering_list = []
    if len(subtasks) > 1:
        ordering = [''.join(el) for el in htn.split(':ordering')][1]
        # Here is only 1 block parsing. If you want more - do the same. The key of block is 'and'.
        brackets = list(tree_sample(ordering))
        max_depth = max([x for _, _, x in brackets])
        brackets = [br for br in brackets if br[2] == max_depth]
        for st, end, _ in brackets:
            or_decr = ordering[st:end].strip()
            lb = re.findall('(\w+) < (\w+)', or_decr)[0]
            if not ordering_list:
                ordering_list.extend(lb)
            else:
                ordering_list.append(lb[1])

    return HtnStmt(parameters, subtasks, ordering_list)

def parse_init(init_descr):
    """
    init - its an list of init predicates of the task.
    :param init:
    :return: list of statements
    """
    init = []
    for st, end, _ in tree_sample(init_descr):
        predicate_descr = init_descr[st:end].strip()
        name = re.findall('^\w+', predicate_descr)
        signatures = [sign for sign in re.findall('\w+', predicate_descr) if sign != name[0]]
        ipredicate = PredicatesStmt(name, signatures)
        init.append(ipredicate)
    return init


def parse_action (action):
    """
    Actions contain parameters, preconditions and effect groups of
    statements.
    :return: returns the ActionStmt object
    """
    name = re.findall('^\w+', action.strip())

    params = [''.join(el) for el in action.split(':parameters')[1].split(':precondition')][0]
    parameters = re.findall('(\?\w+) - (\w+)', params)
    precond_descr = [''.join(el) for el in action.split(':precondition')[1].split(':effect')][0]
    precond = parse_block(precond_descr)
    effect_descr = [''.join(el) for el in action.split(':effect')][1]
    effect = parse_block(effect_descr, maxd = 1)

    return ActionStmt(name, parameters, precond, effect)

def tree_sample(line, opendelim='(', closedelim=')'):
    stack = []
    for m in re.finditer(r'[{}{}]'.format(opendelim, closedelim), line):
        pos = m.start()
        if line[pos-1] == '\\':
            continue
        c = line[pos]
        if c == opendelim:
            stack.append(pos+1)

        elif c == closedelim:
            if len(stack) > 0:
                prevpos = stack.pop()
                yield prevpos, pos, len(stack)
            else:
                # error
                print("encountered extraneous closing quote at pos {}: '{}'".format(pos, line[pos:] ))
                pass

    if len(stack) > 0:
        for pos in stack:
            print("expecting closing quote to match open quote starting at: '{}'"
                  .format(line[pos-1:]))