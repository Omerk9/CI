from datetime import datetime


class Surgery_Request(object):

    def __init__(self, surgery_type, duration, entrance_date, patient, ward_name, id1):
        self.request_num = id1
        self.surgery_type = surgery_type
        self.duration = duration
        self.entrance_date = entrance_date
        self.entrance_date_cut = None
        self.patient = patient
        self.ward_name = ward_name
        self.assigned = []  # number of variables the algorithm assigned this surgery - list of dro key

    def __eq__(self, other):
        return self.__class__ == other.__class__ and self.patient == other.patient and (
               self.request_num == other.request_num)

    def __hash__(self):
        return int(self.request_num)

    def __str__(self):
        return self.request_num

    def calc_waiting_days(self, d):
        """
        calculates the waiting time of the surgery request to a certain date
        :param d: the date to which the waiting time is calculated
        :return: the difference in days
        """
        if d > self.entrance_date:
            return (d-self.entrance_date).days
        else:
            return 0

