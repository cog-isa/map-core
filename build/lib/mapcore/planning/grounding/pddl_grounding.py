import logging
from collections import defaultdict
import itertools

from mapcore.swm.src.components.semnet import Sign
from mapcore.planning.grounding.planning_task import PlanningTask as Task


def ground(problem, agent, exp_signs=None):
    domain = problem.domain
    actions = domain.actions.values()
    predicates = domain.predicates.values()

    # Objects
    objects = problem.objects
    objects.update(domain.constants)
    logging.debug('Objects:\n%s' % objects)

    # Remove old type_map
    if exp_signs:
        objects = _update_exp_signs(exp_signs, objects)

    # Create a map from types to objects
    type_map = _create_type_map(objects)
    logging.debug("Type to object map:\n%s" % type_map)

    # Create type subtype map
    subtype_map = _create_subtype(domain.types)

    obj_signifs = {}
    obj_means = {}

    # Check logic in exp
    if exp_signs:
        signs = exp_signs
        I_sign = signs['I']
        obj_means[I_sign] = I_sign.meanings[1]
        obj_signifs[I_sign] = I_sign.significances[1]
    else:
        signs = {}
        I_sign = Sign("I")
        obj_means[I_sign] = I_sign.add_meaning()
        obj_signifs[I_sign] = I_sign.add_significance()
        signs[I_sign.name] = I_sign
        signs['situation'] = Sign('situation')

    for obj in objects:
        obj_sign = Sign(obj)
        obj_signifs[obj] = obj_sign.add_significance()
        signs[obj] = obj_sign
        if obj_sign.name == agent:
            connector = obj_signifs[obj].add_feature(obj_signifs[I_sign], zero_out=True)
            I_sign.add_out_significance(connector)

    for tp, objects in type_map.items():
        if exp_signs:
            tp_sign = signs[tp.name]
        else:
            tp_sign = Sign(tp.name)
        for obj in objects:
            obj_signif = obj_signifs[obj]
            tp_signif = tp_sign.add_significance()
            connector = tp_signif.add_feature(obj_signif, zero_out=True)
            signs[obj].add_out_significance(connector)
        if not exp_signs:
            signs[tp.name] = tp_sign

    if not exp_signs:
        updated_predicates = _update_predicates(predicates, actions)
        signify_predicates(predicates, updated_predicates, signs, subtype_map, domain.constants)
        agent_roles = {}
        pred_names = {pred.name for pred in predicates}
        if agent:
            agent_role_cms = signs[agent].spread_up_activity_obj('significance', 3)
            roles = {cm.sign for cm in agent_role_cms if cm.sign.name not in pred_names}
            agent_roles[signs[agent]] = roles
        signify_actions(actions, signs, obj_means, agent_roles)

    start_situation, pms = _define_situation('*start*', problem.initial_state, signs, 'image')
    goal_situation, pms = _define_situation('*finish*', problem.goal, signs, 'image')

    return Task(problem.name, signs, start_situation, goal_situation)


def signify_predicates(predicates, updated_predicates, signs, subtype_map, constants = None):
    for predicate in predicates:
        pred_sign = Sign(predicate.name)
        signs[predicate.name] = pred_sign
        def update_single(facts):
            for fact in facts:
                role_name = fact[1][0].name + fact[0]
                fact_name = fact[1][0].name
                if role_name not in signs:
                    role_sign = Sign(role_name)
                    signs[role_name] = role_sign
                else:
                    role_sign = signs[role_name]
                if fact_name not in signs:
                    fact_sign = Sign(fact_name)
                    signs[fact_name] = fact_sign
                else:
                    fact_sign = signs[fact_name]
                role_signif = role_sign.add_significance()
                fact_signif = fact_sign.add_significance()
                connector = role_signif.add_feature(fact_signif, zero_out=True)
                fact_sign.add_out_significance(connector)


        def update_significance(fact, predicate, subtype_map, updated_predicates, index, effect=False, constants=None):
            def add_sign(updated_fact, ufn, ufr):
                if isinstance(updated_fact[0], tuple):
                    used_facts.add(updated_fact[0][1:])
                else:
                    used_facts.add(ufn)
                if ufr not in signs:
                    signs[ufr] = Sign(ufr)
                if not ufr in roles:
                    roles.append(ufr)

            role_name = fact[1][0].name + fact[0]
            fact_name = fact[1][0].name
            roles = []
            roles.append(role_name)
            role_signifs = []
            subroles = []
            if role_name not in signs:
                signs[role_name] = Sign(role_name)
            if fact_name in subtype_map.keys():
                subroles = subtype_map[fact_name]
                for role, signif in subtype_map.items():
                    if fact_name in signif:
                        for srole in subroles:
                            srole_name = role + "?" + srole
                            signs[srole_name] = Sign(srole_name)
                            if not srole_name in roles:
                                roles.append(srole_name)
                            sfact_name = fact_name + "?" + srole
                            signs[sfact_name] = Sign(sfact_name)
                            if not sfact_name in roles:
                                roles.append(sfact_name)
            used_facts = set()
            for updated_fact in updated_predicates[pred_sign.name]:
                ufn = updated_fact[1][0].name
                if not updated_fact[0].startswith('?'):
                    new_fact = '?' + updated_fact[0]
                else:
                    new_fact = updated_fact[0]
                ufr = updated_fact[1][0].name + new_fact
                if updated_fact[0] in constants:
                    ufr_sign = Sign(ufr)
                    signs[ufr] = ufr_sign
                    role_signif = ufr_sign.add_significance()
                    obj_sign = signs[updated_fact[0]]
                    conn = role_signif.add_feature(obj_sign.significances[1], zero_out=True)
                    obj_sign.add_out_significance(conn)
                    role_signifs.append(role_signif)
                else:
                    predicate_names = [signa[1][0].name for signa in predicate.signature]
                    if fact_name == ufn:
                        add_sign(updated_fact, ufn, ufr)
                    elif fact[0] == updated_fact[0]:
                        add_sign(updated_fact, ufn, ufr)
                    elif ufn in subtype_map[fact_name] and not ufn in predicate_names:
                        add_sign(updated_fact, ufn, ufr)
            for role_name in roles:
                role_sign = signs[role_name]
                obj_sign = signs[fact_name]
                spec_sign = None
                if obj_sign.name in role_sign.name:
                    spec_sign = role_sign.name[len(obj_sign.name) + 1:]
                smaller_roles = []
                if spec_sign and subroles:
                    for srole in subroles:
                        if spec_sign in srole:
                            smaller_roles.append(srole)
                if not smaller_roles and spec_sign:
                    smaller_roles = [obj for obj in used_facts if spec_sign in obj and obj in signs]
                if smaller_roles:
                    for obj in smaller_roles:
                        updated_obj_sign = signs[obj]
                        if not obj_sign == updated_obj_sign:
                            role_signif = role_sign.add_significance()
                            connector = role_signif.add_feature(updated_obj_sign.significances[1], zero_out=True)
                            updated_obj_sign.add_out_significance(connector)
                            role_signifs.append(role_signif)
                        else:
                            role_signif = role_sign.add_significance()
                            conn = role_signif.add_feature(obj_sign.significances[1], zero_out=True)
                            obj_sign.add_out_significance(conn)
                            role_signifs.append(role_signif)
                else:
                    role_signif = role_sign.add_significance()
                    conn = role_signif.add_feature(obj_sign.significances[1], zero_out=True)
                    obj_sign.add_out_significance(conn)
                    role_signifs.append(role_signif)
            # signa - variations
            if index < len(predicate.signature)-1:
                signifs[index] = role_signifs
            else:
                signifs[index] = role_signifs
                if not constants:
                    for elems in itertools.product(*signifs.values()):
                        pred_signif = pred_sign.add_significance()
                        for elem in elems:
                            conn = pred_signif.add_feature(elem, zero_out=True)
                            elem.sign.add_out_significance(conn)
                else:
                    pred_signif = pred_sign.add_significance()
                    for signa in predicate.signature:
                        for element in signifs:
                            if signa[1][0].name in element.sign.name:
                                conn = pred_signif.add_feature(element, zero_out=True)
                                element.sign.add_out_significance(conn)
                                break
        # predicate with solo signa or without signa simular to role
        if len(predicate.signature) >=2:
            signifs = {}
            for index in range(len(predicate.signature)):
                update_significance(predicate.signature[index], predicate, subtype_map, updated_predicates, index, constants = constants)
        else:
            update_single(updated_predicates[predicate.name])
            pred_sign.add_significance()

def signify_actions(actions, signs, obj_means, agent_roles):
    for action in actions:
        act_sign = Sign(action.name)
        act_signif = act_sign.add_significance()

        def update_significance(predicate, signature, effect=False):
            pred_sign = signs[predicate.name]
            if len(pred_sign.significances) > 1:
                pred_cm = pred_resonate('significance', pred_sign, predicate, signs, signature)
                if not pred_cm:
                    raise Exception('Cant find *{0}* matrice in *{1}* action'.format(predicate.name, action.name))
            elif len(pred_sign.significances) == 0:
                pred_cm = pred_sign.add_significance()
            else:
                pred_cm = pred_sign.significances[1]
            connector = act_signif.add_feature(pred_cm, effect=effect)
            pred_sign.add_out_significance(connector)
            if len(predicate.signature) == 1:
                signa = predicate.signature[0]
                if not signa[0].startswith('?'):
                    new_fact = '?' + signa[0]
                else:
                    new_fact = signa[0]
                role_sign = signs[signa[1][0].name + new_fact]
                conn = act_signif.add_feature(role_sign.significances[1], connector.in_order, effect=effect,
                                              zero_out=True)
                role_sign.add_out_significance(conn)
            elif not len(predicate.signature) == 0:
                if not predicate.signature[0][1][0].name == predicate.signature[1][1][0].name:
                    for role_sign in pred_cm.get_signs():
                        connector_new = act_signif.add_feature(role_sign.significances[1], connector.in_order,
                                                               effect=effect,
                                                               zero_out=True)
                        role_sign.add_out_significance(connector_new)

        for predicate in action.precondition:
            update_significance(predicate,  action.signature, False)
        for predicate in action.effect.addlist:
            update_significance(predicate, action.signature, True)
        signs[action.name] = act_sign
        act_meaning = act_signif.copy('significance', 'meaning')
        I_sign = signs['I']
        connector = act_meaning.add_feature(obj_means[I_sign])
        efconnector = act_meaning.add_feature(obj_means[I_sign], effect=True)
        I_sign.add_out_meaning(connector)

        for agent, roles in agent_roles.items():
            I_obj_mean = agent.add_meaning()
            mean_signs = set()
            act_mean = act_meaning.spread_down_activity('meaning', 3)
            for pm_list in act_mean:
                mean_signs |= set([c.sign for c in pm_list])
            role_signs = roles & mean_signs
            for rs in role_signs:
                act_meaning.replace('meaning', rs, I_obj_mean)



def pred_resonate(base, sign, predicate, signs, signature):
    cms = getattr(sign, base + 's')
    roles = []
    for fact in predicate.signature:
        if fact[1][0].name+fact[0] in signs:
            roles.append(fact)
        else:
            sfact = [signa for signa in signature if fact[0] == signa[0]]
            if sfact:
                if sfact[0][1][0].name+sfact[0][0] in signs:
                    roles.extend(sfact)
    uroles = []
    for signa in roles:
        if not signa[0].startswith('?'):
            new_fact = '?' + signa[0]
        else:
            new_fact = signa[0]
        uroles.append(signs[signa[1][0].name+new_fact])
    for index, cm in cms.items():
        if not len(cm.cause) + len(cm.effect) == len(predicate.signature):
            continue
        cm_signs = cm.get_signs()
        for role in uroles:
            if not role in cm_signs:
                break
        else:
            return cm
    return None

def _update_predicates(predicates, actions):
    new_predicates = {}
    for pred in predicates:
        if pred.signature:
            for signa in pred.signature:
                new_predicates.setdefault(pred.name, set()).add((signa[0], tuple(signa[1])))
        else:
            new_predicates[pred.name] = set()
    for action in actions:
        actions_predicates = action.precondition.copy()
        actions_predicates.extend([pred for pred in action.effect.addlist.copy()])
        for predicate in actions_predicates:
            new_predicates[predicate.name] |= set([(signa[0], tuple(signa[1])) for signa in predicate.signature])
            for fact in predicate.signature:
                for action_fact in action.signature:
                    if fact[0] == action_fact[0] and (fact[0], tuple(fact[1])) in new_predicates[predicate.name]:
                        new_predicates[predicate.name].add((action_fact[0], tuple(action_fact[1])))

    return new_predicates


def task_signs(problem):
    signs = []
    above = []
    bottom = []
    for pred in problem.goal:
        if pred.name == "on":
            above.append(pred.signature[0][0])
            bottom.append(pred.signature[1][0])
    signs.append(list(set(above) - set(bottom))[0])
    signs.append(list(set(bottom) - set(above))[0])
    return signs


def _update_exp_signs(signs, objects):
    for obj, type in list(objects.items()).copy():
        if signs.get(obj):
            try:
                objects.pop(obj)
            except KeyError:
                break

    return objects


def _create_subtype(types):
    """
    Create a map of types/subtypes to make true role signs
    """
    subtype_map = defaultdict(set)

    for object_name, object_type in types.items():
        parent_type = object_type.parent
        if parent_type:
            subtype_map[parent_type.name].add(object_type.name)
    return subtype_map


def _create_type_map(objects):
    """
    Create a map from each type to its objects.

    For each object we know the type. This returns a dictionary
    from each type to a set of objects (of this type). We also
    have to care about type hierarchy. An object
    of a subtype is a specialization of a specific type. We have
    to put this object into the set of the supertype, too.
    """
    type_map = defaultdict(set)

    # for every type we append the corresponding object
    for object_name, object_type in objects.items():
        parent_type = object_type.parent
        while True:
            type_map[object_type].add(object_name)
            object_type, parent_type = parent_type, object_type.parent
            if parent_type is None:
                # if object_type is None:
                break

    return type_map


def _define_situation(name, predicates, signs, network = 'image'):
    situation = Sign(name)
    sit_cm = getattr(situation, 'add_'+network)()
    elements = {}

    def get_or_add(sign):
        if sign not in elements:
            cm = getattr(sign, 'add_'+network)()
            elements[sign] = cm
        return elements.get(sign)

    for predicate in predicates:
        pred_sign = signs[predicate.name]
        pred_cm = getattr(pred_sign, 'add_'+network)()
        connector = sit_cm.add_feature(pred_cm)
        getattr(pred_sign, 'add_out_'+network)(connector)
        if len(predicate.signature) == 1:
            obj_sign = signs[predicate.signature[0][0]]
            sig_cm = get_or_add(obj_sign)
            conn = sit_cm.add_feature(sig_cm, connector.in_order)
            getattr(obj_sign, 'add_out_' + network)(conn)
        elif len(predicate.signature) > 1:
            pre_signs = set()
            for fact in predicate.signature:
                role_signs = [con.in_sign for con in getattr(signs[fact[0]], 'out_significances') if con.in_sign.name != 'object']
                for el in role_signs:
                    if el.significances:
                        if len(el.significances[1].cause) == 1 and len(el.significances[1].effect) == 0:
                            pre_signs.add(el)
            if len(pre_signs) < len(predicate.signature):
                for fact in predicate.signature:
                    fact_sign = signs[fact[0]]
                    fact_cm = get_or_add(fact_sign)
                    conn = pred_cm.add_feature(fact_cm)
                    getattr(fact_sign, 'add_out_' + network)(conn)
            else:
                for fact in predicate.signature:
                    fact_sign = signs[fact[0]]
                    fact_image = get_or_add(fact_sign)
                    conn = sit_cm.add_feature(fact_image, connector.in_order)
                    getattr(fact_sign, 'add_out_' + network)(conn)
                    conn = pred_cm.add_feature(fact_image)
                    getattr(fact_sign, 'add_out_' + network)(conn)
    global_situation = signs['situation']
    global_cm = getattr(global_situation, 'add_'+network)()
    connector = global_cm.add_feature(sit_cm)
    getattr(situation, 'add_out_' + network)(connector)
    return situation, elements


def _expand_situation_blocks(goal_situation, signs, pms, list_signs):
    ont_image = signs['ontable'].add_image()
    a_image = pms[signs[list_signs[1]]]
    connector = goal_situation.images[1].add_feature(ont_image)
    conn = goal_situation.images[1].add_feature(a_image, connector.in_order)
    signs['ontable'].add_out_image(conn)
    signs[list_signs[1]].add_out_image(conn)
    cl_image = signs['clear'].add_image()
    d_image = pms[signs[list_signs[0]]]
    connector = goal_situation.images[1].add_feature(cl_image)
    conn = goal_situation.images[1].add_feature(d_image, connector.in_order)
    signs['clear'].add_out_image(conn)
    signs[list_signs[0]].add_out_image(conn)
    he_image = signs['handempty'].add_image()
    connector = goal_situation.images[1].add_feature(he_image)
    signs['handempty'].add_out_image(connector)

def _expand_situation_logistics(goal_situation, signs, pms):

    at_image = signs['at'].add_image()
    tru1_image = signs['tru1'].add_image()
    pos1_image = pms[signs['pos1']]
    connector = at_image.add_feature(tru1_image)
    connector = at_image.add_feature(pos1_image)
    connector = goal_situation.images[1].add_feature(at_image)
    conn = goal_situation.images[1].add_feature(tru1_image, connector.in_order)
    con = goal_situation.images[1].add_feature(pos1_image, connector.in_order)
    signs['at'].add_out_images(connector)
    signs['tru1'].add_out_image(conn)
    signs['pos1'].add_out_image(con)
