from Surgery_Request import Surgery_Request
import math
from Surgery_Type import SurgeryType
from Surgeon import Surgeon
import pandas as pd
import openpyxl

path = 'C:\\Users\\noamga\\Downloads\\Data-20200802T142933Z-001\\Data'


class Ward(object):

    def __init__(self, name, w_id, hospital, day_duration, max_slots, start_d_hour):

        self.max_slots = max_slots
        self.start_d_hour = start_d_hour
        self.w_id = w_id
        self.name = name
        self.d_duration = day_duration  # surgical minutes in a single day
        self.surgery_types = self._init_surgery_types()
        self.room_allocation = self._init_room_allocation(hospital)
        self.ward_surgeons = self._init_surgeons()
        self.RTG = self._init_RTG(hospital)

    @staticmethod
    def round_down(n, decimals=0):
        multiplier = 10 ** decimals
        return math.floor(n * multiplier) / multiplier

    @staticmethod
    def _by_duration(sr):
        return sr.duration

    @staticmethod
    def _by_birth_d(sr):
        return sr.patient.birth_date




    def _init_room_allocation(self, hospital):
        '''
        initiates the room_allocation variable
        :return: dictionary of wards room allocation {date: set of rooms}
        '''
        init_ra = self._getRoomAllocastionDB()
        # list of dictionaries containing information of the room allocations {'id':, 'ward_id': ,'date': , 'room_number':}
        room_allocation = {}
        for ra in init_ra:
            if ra['date'] in room_allocation:
                room_allocation[ra['date']].add(hospital.findRoom(ra['room_number']))
            else:
                room_allocation[ra['date']] = {hospital.findRoom(ra['room_number'])}
        return room_allocation

    def _init_surgery_types(self):
        '''
        initiates surgery type instants like those in  the DB
        :return: set of surgery types of the ward
        '''
        init_st = self._getSurgeryTypesDB()  # SQL command to recieve from DB returns a list
        surgery_types = set()
        for st in init_st:
            st_id = st['id']
            name = st['name']
            duration = st['duration']
            utility = st['utility']
            surgery_types.add(SurgeryType(st_id, name, duration, utility))
        return surgery_types

    def _init_surgeons(self):
        """
        initiates the surgeons objects of the ward and aggregates them to a set
        :return: set of the ward's surgeons
        """
        init_s = self._getSurgeonsDB()  # return list of surgeon id
        s_shifts = self._getShiftsDB()  # return dictionary {surgeon_id: set(shifts)}
        s_skills = self._getSkillsDB()  # return a Dictionary {surgeon_id : set(surgery_types)}
        surgeons = set()
        for s in init_s:  # s=surgeon id
            surgeons.add(Surgeon(int(s), s_skills[s], s_shifts[s]))
        return surgeons

    def _init_RTG(self, hospital):
        """
        initiates all the surgery requests that are rtg of the ward i.e. ready to go patients
        :return: set of surgery requests
        """
        init_RTG = self._getRTG_DB()  # return list of all surgery request
        RTG = set()
        for rtg in init_RTG:
            patient = hospital.findPatientByID(rtg['patient_id'])
            surgery_type = self.findSTbyId(rtg['surgeryT_id'])  # surgery type object
            duration = rtg['duration']
            request_num = rtg['id']
            entrance_date = rtg['entrance_date']
            RTG.add(
                Surgery_Request(surgery_type=surgery_type, duration=duration, entrance_date=entrance_date,
                                patient=patient, ward_name=self.name, id1=request_num))
        return RTG

    def findSTbyId(self, st_id):
        """
        :param st_id: surgery type id
        :return: object of surgery type
        """

        for st in self.surgery_types:
            if st.st_id == st_id:
                return st
        return None

    def _getRoomAllocastionDB(self):
        """
        get http request
        :return: list of dictionaries containing information of the room allocations {'id':, 'ward_id': ,'date': , 'room_number':}
        """
        df = pd.read_excel(io= 'RoomAllocation.xlsx')
        room_allocation = df.to_dict('records')
        return room_allocation

    def _getSurgeryTypesDB(self):
        """
        read excel file
        :return: list of dictionaries containing information of the surgery types {id,ward_id, name, urgency, complexity,duration}
        """
        df = pd.read_excel(io='SurgeryType.xlsx')
        surgery_types = df.to_dict('records')
        return surgery_types

    def _getSurgeonsDB(self):
        """
        initialize from DB
        :return: list of ward's surgeon's id
        """
        df = pd.read_excel(io='Surgeon.xlsx')
        surgeons_j = df.to_dict('records')
        surgeons = []
        for s in surgeons_j:
            surgeons.append(s['id'])
        return surgeons

    def _getSkillsDB(self):
        """
        :return: dictionary of {surgeon_id : set(surgery_types)} skills of specific surgeon
        """
        df = pd.read_excel(io= 'SurgeonSkill.xlsx')
        data = df.to_dict('records')

        skills = {}
        for d in data:
            st_id = d['surgeryT_id']
            st = self.findSTbyId(st_id)
            if d['surgeon_id'] in skills:
                skills[d['surgeon_id']].add(st)
            else:
                skills[d['surgeon_id']] = {st}
        return skills

    def _getShiftsDB(self):
        """
        get https request
        :return: dictionary : key - surgeon_id value set of dates of shifts
        """

        df = pd.read_excel(io='SurgeonShift.xlsx')
        data = df.to_dict('records')

        shifts = {}
        for d in data:
            if d['surgeon_id'] in shifts:
                shifts[d['surgeon_id']].add(d['date'])
            else:
                shifts[d['surgeon_id']] = set([d['date']])
        return shifts

    def _getRTG_DB(self):
        """
        :return:
        list of dictionaries [{'patient_id': - , 'surgeryT_id': - , 'duration': - , 'id': - , 'entrance_date' - }]
        """
        df = pd.read_excel(io='RTG.xlsx')
        data = df.to_dict('records')
        return data
