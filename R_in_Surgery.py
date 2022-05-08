
from datetime import date, datetime, timedelta, time
from Surgery_Variable import SurgeryVariable
from Surgery_Request import Surgery_Request
from copy import deepcopy, copy
import sys
# Neighbours : SurgeryVariable_Surgeon with same index, SurgeryRequest Varialbe in the same day,
# in principle all diff - all surgeryRequest Variables

# in the furture we would like arguments like approved by ward/patient notified


class SurgeryVariable_SurgeryRequest(SurgeryVariable):
    def __init__(self, room, day, order, sr_domain, constraints, start_time=time(hour=0, minute=0),
                 end_time=time(hour=0, minute=0), surgery_request=None):
        super(SurgeryVariable_SurgeryRequest, self).__init__(room, day, order, start_time, end_time, constraints, sr_domain, surgery_request)

    def assign(self):
        pass

    def calculate_cost(self):
        pass

    def initialize_domain(self, sr_domain):
        """initializes the domain of the specific variable according to unary hard constraints
        :param sr_domain:set of all the RTG of the ward
        :return: set of RTG of the ward according to constraints
        """
        newDomain = sr_domain.copy()
        if len(newDomain) > 0:
            for sr in sr_domain:
                # Room must hold the surgery type needed by the patient
                if sr.surgery_type.st_id not in self.room.surgery_types:
                    newDomain.discard(sr)
                    continue
                # surgery date can't be before entrance date
                if sr.entrance_date > self.day:
                    newDomain.discard(sr)
        return newDomain


    def __str__(self):
        return "SRV: room-" + str(self.room) + " day- " + str(self.day) + " order- " + str(self.order)













