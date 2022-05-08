import Room, datetime,Surgery_Request, Constraint
from abc import ABC, abstractmethod


class SurgeryVariable(object):
    def __init__(self, room, day, order, start_time, end_time, constraints, domain, value):
        self.room = room  # room object
        self.day = day
        self.order = order
        self.start_time = start_time
        self.end_time = end_time
        self.domain = self.initialize_domain(domain)
        self.constraints = self.init_constraints_in_variables(constraints)
        self.value = value
        self.prior_value = None
        self.best_value = None

    @abstractmethod
    def initialize_domain(self, domain):
        pass

    def get_constraint_dro_key(self):
        dro_key = str(self.day) + '_' + str(self.room.num) + '_' + str(self.order)  # date_room_order
        return dro_key

    def get_constraint_dr_key(self):
        return str(self.day) + '_' + str(self.room.num)  # date_room

    def get_constraint_d_key(self, s_id):
        return str(self.day) + '_' + str(s_id)

    def get_init_d_key(self):
        d_key = []
        for surgeon in self.domain:
            d_key.append(str(self.day) + '_' + str(surgeon.s_id))
        return d_key

    def init_constraints_in_variables(self, c_dict):
        """
        adds the required keys to each dictionary constraint and initializes the price value to 0. via the keys the price of
        the concerning variable will be updated the keys refer to the index of the variable.
        :param dro: key referring to date room order
        :param dr: key referring to date room
        :param d: key referring to date
        :param c_dict: dictionary of constraints of a variable type
        """
        if 'dro' in c_dict:
            dro_cons = c_dict['dro']
            for cons in dro_cons:
                dro_cons[cons].prices[self.get_constraint_dro_key()] = 0

        if 'dr' in c_dict:
            dr_cons = c_dict['dr']
            for cons in dr_cons:
                dr_cons[cons].prices[self.get_constraint_dr_key()] = 0

        if 'd' in c_dict:
            d_cons = c_dict['d']
            for cons in d_cons:
                d_key_list = self.get_init_d_key()
                for d_key in d_key_list:
                    d_cons[cons].prices[d_key] = 0

        return c_dict







