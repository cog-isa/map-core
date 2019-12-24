import itertools
from copy import copy


class CausalMatrix:
    """
    Causal matrix - main structure in causal network defining causal and hierarchical relations
    cause - is the list of causal events at each moment
    effect - is the list of effect events at each moment (can be empty)
    """

    def __init__(self, sign=None, index=None, cause=None, effect=None):
        self.sign = sign
        self.index = index
        if not cause:
            self.cause = []
        else:
            self.cause = cause
        if not effect:
            self.effect = []
        else:
            self.effect = effect

    def __str__(self):
        return '{0}:{1}'.format(str(self.sign), str(self.index))

    def __repr__(self):
        return '{0}:{1}'.format(str(self.sign), str(self.index))

    def __eq__(self, other):
        return self.sign == other.sign and self.index == other.index

    def __hash__(self):
        if self.sign:
            return 3 * hash(self.index) + 5 * hash(self.sign)
        else:
            return hash(self.index)

    def __contains__(self, sign):
        for event in itertools.chain(self.cause, self.effect):
            if sign in event:
                return True

        return False

    def __sub__(self, cm):
        subtraction = []
        for e1 in self.cause:
            for e2 in cm.cause:
                if e1.exp_resonate(e2):
                    break
            else:
                subtraction.append(e1)
        for e1 in self.effect:
            for e2 in cm.effect:
                if e1.exp_resonate(e2):
                    break
            else:
                subtraction.append(e1)
        return subtraction

    def longstr(self):
        return '{0}:{1}->{2}'.format(str(self.sign), '|'.join([str(e) for e in self.cause]),
                                     '|'.join([str(e) for e in self.effect]))

    def add_event(self, event, effect=False):
        mult, part = (-1, self.effect) if effect else (1, self.cause)
        order = (len(part) + 1) * mult
        part.append(event)
        return order

    def get_event(self, order):
        d, part = (order - 1, self.cause) if order > 0 else (-1 * order - 1, self.effect)
        return part[d]

    def add_feature(self, cm, order=None, effect=False, zero_out=False, actuator = False, view = False):
        """
        Add causal matrix cm in the new or existed in order event
        @param zero_out: special case of undefined out
        @param cm: causal matrix to add
        @param order: order of existed event
        @param effect: if to add as effect
        @return:
        """
        if actuator:
            connector = Actuator(self.sign, cm, order)
        elif view:
            if not isinstance(cm, (list, tuple)):
                raise Exception('Views can be only tuple or list!')
            connector = View(self.sign, cm, order)
        else:
            connector = Connector(self.sign, cm.sign, self.index, cm.index, order)
        mult, part = (-1, self.effect) if effect else (1, self.cause)

        if order is None:
            connector.in_order = (len(part) + 1) * mult
            part.append(Event(connector.in_order, {connector}))
        else:
            part[abs(order) - 1].coincidences.add(connector)
        if zero_out and not actuator and not view:
            connector.out_index = 0
        return connector

    def is_empty(self):
        return len(self.cause) == 0 and len(self.effect) == 0

    def is_causal(self):
        return len(self.effect) > 0

    def includes(self, base, smaller):
        sub1 = [event for event in itertools.chain(self.cause, self.effect) if "I" not in event.get_signs_names()]
        sub2 = [event for event in itertools.chain(smaller.cause, smaller.effect) if "I" not in event.get_signs_names()]
        for event2 in sub2:
            for event1 in sub1:
                if event2.resonate(base, event1):
                    break
            else:
                return False

        return True

    def copy(self, base, new_base, copied=None):
        if copied is None:
            copied = {}
        pm = getattr(self.sign, 'add_' + new_base)()
        for event in self.cause:
            pm.cause.append(event.copy(pm, base, new_base, copied))
        for event in self.effect:
            pm.effect.append(event.copy(pm, base, new_base, copied))
        return pm

    def expand(self, base, copied=None):
        """
        get inner signs of cms
        :param base:
        :param copied:
        :return:
        """
        if copied is None:
            copied = {}
        cm = getattr(self.sign, 'add_' + base)()
        for event in self.cause:
            cm.cause.extend(event.expand(cm, base, copied))
        for event in self.effect:
            cm.effect.extend(event.expand(cm, base, copied))
        return cm

    def replace(self, base, old_sign, new_cm, deleted=None):
        if deleted is None:
            deleted = []
        for event in self.cause:
            event.replace(base, old_sign, new_cm, deleted)
        for event in self.effect:
            event.replace(base, old_sign, new_cm, deleted)

    def resonate(self, base, pm, check_order=True, check_sign=True):
        if check_sign and not self.sign == pm.sign:
            return False
        sub1 = [event for event in itertools.chain(self.cause, self.effect) if "I" not in event.get_signs_names()]
        sub2 = [event for event in itertools.chain(pm.cause, pm.effect) if "I" not in event.get_signs_names()]
        if not len(sub1) == len(sub2):
            return False
        if check_order:
            for e1, e2 in zip(itertools.chain(self.cause, self.effect), itertools.chain(pm.cause, pm.effect)):
                if not e1.resonate(base, e2):
                    return False
        else:
            for e1 in sub1:
                for e2 in sub2:
                    if e1.resonate(base, e2, check_order):
                        break
                else:
                    return False

        return True

    def get_signs(self):
        signs = set()
        for event in itertools.chain(self.cause, self.effect):
            for connector in event.coincidences:
                signs.add(connector.out_sign)
        return signs

    def spread_down_activity(self, base, depth):
        """
        Spread activity down in hierarchy
        @param base: name of semantic net that activity spreads on
        @param depth: recursive depth of spreading
        @return: active chains of PredictionMatrices
        """
        active_chains = []

        def check_pm(pm):
            if not pm.is_empty():
                chains = pm.spread_down_activity(base, depth - 1)
                for chain in chains:
                    active_chains.append([self] + chain)
            else:
                active_chains.append([self, pm])

        if depth > 0:
            for event in itertools.chain(self.cause, self.effect):
                for connector in event.coincidences:
                    if connector.out_index > 0:
                        # connector.out_sign with index
                        pm = connector.get_out_cm(base)
                        check_pm(pm)
                    else:
                        pms = getattr(connector.out_sign, base + 's')
                        for index, pm in pms.items():
                            check_pm(pm)
        return active_chains

    def spread_down_htn_activity_act(self, base, depth):
        """
        Spread activity down in hierarchy from the HTN
        @param base: name of semantic net that activity spreads on
        @param depth: recursive depth of spreading
        @return: List of Causal Matrices on the lowest level
        """

        active_matrices = []

        def check_pm(pm):
            if not pm.is_empty() and not pm.is_causal():
                matrices = pm.spread_down_htn_activity_act(base, depth - 1)
                active_matrices.extend(matrices)
            else:
                active_matrices.append(pm)
        if depth > 0:
            if self.effect:
                print("Can't get inner matrices from the matrix: {0} -> {1}".format(self.sign.name, self.index))
            for event in self.cause:
                for connector in event.coincidences:
                    if connector.out_index > 0:
                        # connector.out_sign with index
                        pm = connector.get_out_cm(base)
                        check_pm(pm)
                    else:
                        pms = getattr(connector.out_sign, base + 's')
                        for index, pm in pms.items():
                            check_pm(pm)
        return active_matrices

    def spread_down_activity_view(self, depth):
        """
        :param depth: depth of view search
        :return: dict sign:view
        """
        fviews = {}
        if depth > 0:
            for event in itertools.chain(self.cause, self.effect):
                for connector in event.coincidences:
                    if connector.out_index > 0:
                        pm = connector.get_out_cm('image')
                        for event in itertools.chain(pm.cause, pm.effect):
                            for object in event.coincidences:
                                if isinstance(object, View):
                                    if len(pm.cause) != 1:
                                        raise Exception('Found CausalMatrix with several views! {0} -> {1}'.format(pm.sign.name, connector.out_index))
                                    fviews[pm.sign.name] = object.view
                                else:
                                    fviews.update(pm.spread_down_activity_view(depth-1))
        return fviews

    def get_iner(self, sign, base):
        iner = []
        for event in itertools.chain(self.cause, self.effect):
            if sign in event:
                for connector in event.coincidences:
                    if connector.out_sign == sign:
                        cm = getattr(connector.out_sign, base+'s')[connector.out_index]
                        iner.append(cm)
        return iner

class Event:
    """
    Event - the set of coincident connectors
    """

    def __init__(self, order, coincidences=None):
        self.order = order
        if not coincidences:
            self.coincidences = set()
        else:
            self.coincidences = coincidences

    def __str__(self):
        return '{{{0}}}'.format(','.join(str(x) for x in self.coincidences))

    def __repr__(self):
        return '{{{0}}}'.format(','.join(str(x) for x in self.coincidences))

    def __eq__(self, other):
        return self.coincidences == other.coincidences

    def __contains__(self, sign):
        for connector in self.coincidences:
            if connector.out_sign == sign:
                return True
        return False

    def add_coincident(self, base, connector):
        self.coincidences.add(connector)
        getattr(connector.out_sign, 'add_out_' + base)(connector)

    def resonate(self, base, event, check_order=True):
        if not len(self.coincidences) == len(event.coincidences):
            if not len(self.coincidences) == 1 and not [con.out_sign.name for con in self.coincidences][0] in [con.out_sign.name for con in event.coincidences]:
                return False
        for connector in self.coincidences:
            for conn in event.coincidences:
                if connector.out_sign == conn.out_sign:
                    cm = connector.get_out_cm(base)
                    pm = conn.get_out_cm(base)
                    if cm.get_signs() == pm.get_signs():
                        break
            else:
                return False
            pm1 = connector.get_out_cm(base)
            pm2 = conn.get_out_cm(base)
            if not pm1.resonate(base, pm2, check_order):
                return False
        return True

    def exp_resonate(self, event):
        if not len(self.coincidences) == len(event.coincidences):
            return False
        for connector in self.coincidences:
            for conn in event.coincidences:
                if connector.out_sign == conn.out_sign:
                    break
            else:
                return False
        return True

    def copy(self, new_parent, base, new_base, copied):
        if copied is None:
            copied = {}
        event = Event(self.order)
        for connector in self.coincidences:
            if connector.out_index == 0:
                cm = getattr(connector.out_sign, 'add_' + new_base)()
            else:
                pm = connector.get_out_cm(base)
                if pm not in copied:
                    cm = pm.copy(base, new_base, copied)
                    copied[pm] = cm
                else:
                    cm = copied[pm]
            conn = Connector(new_parent.sign, connector.out_sign, new_parent.index, cm.index, event.order)
            event.add_coincident(new_base, conn)
        return event

    def expand(self, new_parent, base, copied, effect=False):
        events = []
        for conn in self.coincidences:
            if conn.out_index == 0:
                raise Exception('Cannot expand throw zero agent')
            else:
                cm = conn.get_out_cm(base)
                part = cm.effect if effect else cm.cause
                for event in part:
                    events.append(event.copy(new_parent, base, base, copied))
        return events

    def replace(self, base, old_sign, new_cm, deleted):
        for connector in self.coincidences:
            if connector.out_sign == old_sign:
                if connector.out_index not in deleted:
                    getattr(connector.out_sign, 'remove_' + base)(connector.get_out_cm(base))
                    deleted.append(connector.out_index)
                connector.out_sign = new_cm.sign
                connector.out_index = new_cm.index
            else:
                connector.get_out_cm(base).replace(base, old_sign, new_cm, deleted)
    def get_signs(self):
        scm = set()
        for connector in self.coincidences:
            scm.add(connector.out_sign)
        return scm
    def get_signs_names(self):
        scm = set()
        for connector in self.coincidences:
            scm.add(str(connector.out_sign.name))
        #names = {s.name for s in scm}
        return scm

class Connector:
    """
    Connector - link between to sign components with marker (in_index, in_order, out_index)
    """

    def __init__(self, in_sign, out_sign, in_index, out_index=None, in_order=None):
        self.in_sign = in_sign
        self.out_sign = out_sign

        self.in_index = in_index
        self.in_order = in_order

        self.out_index = out_index

    def __str__(self):
        return '{0}:{1}->{2}'.format(self.out_sign, self.out_index, self.in_order)

    def __repr__(self):
        return '{0}:{1}-{2}->{3}:{4}'.format(self.out_sign, self.out_index, self.in_order, self.in_sign, self.in_index)

    def out_eq(self, other):
        return self.out_sign == other.out_sign and self.out_index == other.out_index

    def in_eq(self, other):
        return self.in_sign == other.in_sign and self.in_index == other.in_index and self.in_order == other.in_order

    def get_out_cm(self, base):
        if self.out_index > 0:
            if not self.out_index in getattr(self.out_sign, base + 's'):
                raise Exception('In connector {0} you cannot get out causal matrix'.format(self))
            return getattr(self.out_sign, base + 's')[self.out_index]
        else:
            raise Exception('In connector {0} you cannot get out causal matrix'.format(self))

    def get_in_cm(self, base):
        return getattr(self.in_sign, base + 's')[self.in_index]

class Actuator():
    """
    Actuator - link between sign and motor function with order marker
    """

    def __init__(self, in_sign, motor, in_order=None):
        self.in_sign = in_sign
        self.motor = motor
        self.in_order = in_order

    def __str__(self):
        return '{0}:{1}->{2}'.format(self.in_sign, self.motor, self.in_order)
    def __repr__(self):
        return '{0}->{1}:{2}'.format(self.in_sign, self.motor, self.in_order)

class View:
    """
    View - link between sign and view of this sign.
    Views can be implemented in lists, tuples, ndarrays, etc...
    """
    def __init__(self, in_sign, view, in_order = None):
        self.in_sign = in_sign
        self.view = view
        self.in_order = in_order

    def __str__(self):
        return '{0}:{1}->{2}'.format(self.in_sign, self.view, self.in_order)

    def __repr__(self):
        return '{0}->{1}:{2}'.format(self.in_sign, self.view, self.in_order)

class Sign:
    def __init__(self, name):
        self.name = name
        self.images = {}
        self.significances = {}
        self.meanings = {}
        self.out_significances = []
        self.out_images = []
        self.out_meanings = []

        self._next_image = 1
        self._next_significance = 1
        self._next_meaning = 1

    def __str__(self):
        return '"{0}"'.format(self.name)

    def __repr__(self):
        return '"{0}"'.format(self.name)

    def __eq__(self, other):
        return self.name == other.name

    def __hash__(self):
        if hasattr(self, 'name'):  # pickle call hash during loading before instantiating
            return hash(self.name)
        else:
            return object.__hash__(self)

    def is_abstract(self):
        return len(self.images) == 0

    def add_image(self, pm=None):
        if not pm:
            pm = CausalMatrix(self, self._next_image)
        else:
            pm.index = self._next_image
        self.images[pm.index] = pm
        self._next_image += 1
        return pm

    def add_significance(self, pm=None):
        if not pm:
            pm = CausalMatrix(self, self._next_significance)
        else:
            pm.index = self._next_significance
        self.significances[pm.index] = pm
        self._next_significance += 1
        return pm

    def add_meaning(self, pm=None):
        if not pm:
            pm = CausalMatrix(self, self._next_meaning)
        else:
            pm.index = self._next_meaning
        self.meanings[pm.index] = pm
        self._next_meaning += 1
        return pm


    def add_out_significance(self, connector):
        self.out_significances.append(connector)

    def add_out_image(self, connector):
        self.out_images.append(connector)

    def add_out_meaning(self, connector):
        self.out_meanings.append(connector)

    def remove_meaning(self, cm, deleted=None):
        if deleted is None:
            deleted = []
        for event in cm.cause:
            for connector in event.coincidences:
                if (connector.out_sign, connector.out_index) not in deleted:
                    connector.out_sign.remove_meaning(connector.get_out_cm('meaning'), deleted)
                    deleted.append((connector.out_sign, connector.out_index))
        for event in cm.effect:
            for connector in event.coincidences:
                if (connector.out_sign, connector.out_index) not in deleted:
                    connector.out_sign.remove_meaning(connector.get_out_cm('meaning'), deleted)
                    deleted.append((connector.out_sign, connector.out_index))

        for connector in copy(self.out_meanings):
            if connector.out_index == cm.index:
                self.out_meanings.remove(connector)


        if self.meanings[cm.index]:
            del self.meanings[cm.index]
        else:
            raise Exception('Already removed!')

    def remove_significance(self, cm, deleted=None):
        if deleted is None:
            deleted = []
        for event in cm.cause:
            for connector in event.coincidences:
                if (connector.out_sign, connector.out_index) not in deleted and connector.out_index !=0:
                    connector.out_sign.remove_significance(connector.get_out_cm('significance'), deleted)
                    deleted.append((connector.out_sign, connector.out_index))
        for event in cm.effect:
            for connector in event.coincidences:
                if (connector.out_sign, connector.out_index) not in deleted and connector.out_index !=0:
                    connector.out_sign.remove_significance(connector.get_out_cm('significance'), deleted)
                    deleted.append((connector.out_sign, connector.out_index))

        for connector in copy(self.out_significances):
            if connector.out_index == cm.index:
                self.out_significances.remove(connector)


        if self.significances[cm.index]:
            del self.significances[cm.index]
        else:
            raise Exception('Already removed!')

    def remove_image(self, cm, deleted=None):
        if deleted is None:
            deleted = []
        for event in cm.cause:
            for connector in event.coincidences:
                if (connector.out_sign, connector.out_index) not in deleted:
                    connector.out_sign.remove_image(connector.get_out_cm('image'), deleted)
                    deleted.append((connector.out_sign, connector.out_index))
        for event in cm.effect:
            for connector in event.coincidences:
                if (connector.out_sign, connector.out_index) not in deleted:
                    connector.out_sign.remove_image(connector.get_out_cm('image'), deleted)
                    deleted.append((connector.out_sign, connector.out_index))

        for connector in copy(self.out_images):
            if connector.out_index == cm.index:
                self.out_images.remove(connector)

        if self.images[cm.index]:
            del self.images[cm.index]
        else:
            raise Exception('Already removed!')

    def remove_view(self, cm):
        for event in itertools.chain(cm.cause, cm.effect):
            for connector in event.coincidences:
                if connector.out_index > 0:
                    pm = connector.get_out_cm('image')
                    del pm.sign.images[pm.index]
                    for connector in copy(pm.sign.out_images):
                        if connector.out_index == pm.index:
                            pm.sign.out_images.remove(connector)
        del self.images[cm.index]


    def rename(self, new_name):
        new_sign = Sign(new_name)
        networks = ['significance', 'meaning', 'image']
        renamed = {}
        removed = []
        for base in networks:
            matrices = getattr(self, base + 's')
            for _, pm in copy(list(matrices.items())):
                cm = getattr(new_sign, 'add_' + base)()
                for event in pm.cause:
                    ordered = []
                    for connector in event.coincidences:
                        if not ordered:
                            conn = cm.add_feature(getattr(connector.out_sign, base +'s')[connector.out_index])
                        else:
                            conn = cm.add_feature(getattr(connector.out_sign, base + 's')[connector.out_index], ordered[0].in_order)
                        getattr(connector.out_sign, 'add_out_'+base)(conn)
                        ordered.append(conn)
                        if connector not in removed:
                            attr = getattr(connector.out_sign, 'out_'+base+'s')
                            if connector in attr:
                                attr.remove(connector)
                                removed.append(connector)
                for event in pm.effect:
                    ordered = []
                    for connector in event.coincidences:
                        if not ordered:
                            conn = cm.add_feature(getattr(connector.out_sign, base +'s')[connector.out_index], effect=True)
                        else:
                            conn = cm.add_feature(getattr(connector.out_sign, base + 's')[connector.out_index], ordered[0].in_order, effect=True)
                        getattr(connector.out_sign, 'add_out_'+base)(conn)
                        ordered.append(conn)
                        if connector not in removed:
                            attr = getattr(connector.out_sign, 'out_'+base+'s')
                            if connector in attr:
                                attr.remove(connector)
                                removed.append(connector)
                renamed.setdefault(base, []).append(pm)
        return new_sign

    def spread_up_activity_act(self, base, depth):
        """
        Spread activity up in hierarchy
        @param base: type of semantic net that activity spreads on
        @param depth: recursive depth of spreading
        @return: active PredictionMatrices
        """
        active_pms = set()
        if depth > 0:
            for connector in getattr(self, 'out_' + base + 's'):
                if connector.get_in_cm(base).is_causal():
                    active_pms.add(connector.get_in_cm(base))
                else:
                    pms = connector.in_sign.spread_up_activity_act(base, depth - 1)
                    active_pms |= pms
        return active_pms

    def spread_up_activity_obj(self, base, depth):
        """
        Spread activity up in hierarchy
        @param base: type of semantic net that activity spreads on
        @param depth: recursive depth of spreading
        @return: active PredictionMatrices
        """
        active_pms = set()
        if depth > 0:
            for connector in getattr(self, 'out_' + base + 's'):
                if not connector.get_in_cm(base).is_causal():
                    active_pms.add(connector.get_in_cm(base))
                    pms = connector.in_sign.spread_up_activity_obj(base, depth - 1)
                    active_pms |= pms
        return active_pms

    def spread_down_activity_obj(self, base, depth):
        """
        Spread activity down in hierarchy
        @param base: type of semantic net that activity spreads on
        @param depth: recursive depth of spreading
        @return: active matrices
        """
        active_pms = set()
        if depth > 0:
            for _, cm in getattr(self, base + 's').items():
                if not cm.is_causal():
                    for event in cm.cause:
                        for connector in event.coincidences:
                            active_pms.add(connector.get_out_cm(base))
                            pms = connector.out_sign.spread_down_activity_obj(base, depth - 1)
                            active_pms |= pms
        return active_pms

    def spread_up_act_one(self, base):
        pms = set()
        for connector in getattr(self, 'out_' + base + 's'):
            if not connector.get_in_cm(base).is_causal():
                pms.add(connector.get_in_cm(base))
        return pms

    def spread_up_activity_slice(self, base, depth_start, depth_finish):
        """
        Spread activity up in hierarchy
        @param base: type of semantic net that activity spreads on
        @param depth_start: recursive depth of spreading - start lv
        @param depth_finish: recursive depth of spreading - finish lv
        @return: active PredictionMatrices between 2 lv of hierarchy
        """

        pmss = set()
        depth = 1
        start_pms = self.spread_up_act_one(base)
        while depth < depth_start:
            for pm in start_pms:
                pmss |= pm.sign.spread_up_act_one(base)
            start_pms = pmss.copy()
            pmss.clear()
            depth+=1
        finish_pms = start_pms.copy()
        while depth < depth_finish:
            for pm in finish_pms:
                pmss |= pm.sign.spread_up_act_one(base)
                finish_pms = pmss.copy()
            pmss.clear()
            depth+=1

        active_pms = finish_pms - start_pms

        return active_pms

    def spread_up_activity_motor(self, base, depth):
        """
        @param base: type a variations of function realization threw semantic net
        @param depth: recursive depth of spreading
        @return: dict of PM and functions that they are implemented in
        """
        actions = set()
        if depth > 0:
            for actuator in getattr(self, 'out_' + base + 's'):
                if hasattr(actuator, 'motor'):
                    actions.add((actuator.in_sign, actuator.motor))
                else:
                    pms = actuator.in_sign.spread_up_activity_motor(base, depth-1)
                    actions |= pms
        return actions

    def get_role(self, base = "significance"):
        sub_role = set()
        for con in getattr(self, 'out_' + base + 's'):
            sub_role.add(con.in_sign)
        return sub_role

    def get_predicates(self, base="significance"):
        predicates = set()
        for con in getattr(self, 'out_' + base + 's'):
            cm = con.get_in_cm(base)
            if len(cm.cause) > 1 and len(cm.effect) == 0:
                predicates.add(con.in_sign)
            else:
                predicates |= cm.sign.get_predicates()
        return predicates