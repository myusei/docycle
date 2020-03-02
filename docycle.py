import requests
from bs4 import BeautifulSoup
import re
import random

class DocomoCycle:
    URL = 'https://tcc.docomo-cycle.jp/cycle/'

    TYO_AREA_ID_LIST = {
        'chiyoda' : '1',
        'chuo' : '2',
        'minato' : '3',
        'koto' : '4',
        'shinjuku' : '5',
        'bunkyo' : '6',
        'ota' : '7',
        'shibuya' : '8',
        'nerima' : '9',
        'shinagawa' : '10',
        'kawasaki' : '11',
        'meguro' : '12',
    }
    EVENT_LIST = {
        'login' : '21401',
        'get_parking_list' : '21614',
        'get_cycle_list' : '25701',
        'get_cycle' : '27501',
        'reserve' : '25901',
        'top' : '25904',
        'cancel' : '27901',
    }
    USER_STATUS = {
        'unknown' : -1,
        'neutral' : 0,
        'reserved' : 1,
        'use' : 2,
    }

    MAX_INFO_NUM = '255'

    class DocomoCycleError(Exception):
        pass
    class DocomoCycleLoginError(DocomoCycleError):
        pass
    class DocomoCycleRequestsError(DocomoCycleError):
        pass
    class DocomoCycleConnectionError(DocomoCycleError):
        pass


    ##### constructor #####
    def __init__(self, user, password, user_id, area_id):
        self.user = user
        self.password = password
        self.area_id = area_id
        self.user_id = user_id
        self.session = requests.session()
        self.session_id = None
        self.last_response = None
        self.user_status = None
        self.login()

    ##### request  methods #####
    # when request to the url, call these methods in another method
    def _post(self, data):
        url = self.URL + self.user_id + '/cs_web_main.php'
        response = self.session.post(url , data=data)
        if response.status_code != 200:
            raise self.DocomoCycleRequestsError()
        else:
            self._check_response_content(response)
            self.last_response = response
            return response

    def _new_post_data_base(self, event_name):
        return {
            'EventNo' : self.EVENT_LIST[event_name],
            'SessionID' : self.session_id,
            'UserID' : self.user_id,
            'MemberID' : self.user,
        }

    def _request_top(self):
        post_data = self._new_post_data_base('top')

        return self._post(post_data)


    def _request_cancel(self):
        post_data = self._new_post_data_base('cancel')

        return self._post(post_data)

    def _request_parking_list(self, area_id):
        post_data = self._new_post_data_base('get_parking_list')
        post_data['GetInfoNum'] = self.MAX_INFO_NUM
        post_data['GetInfoTopNum'] = '1'
        post_data['MapType'] = '0'
        post_data['MapCenterLat'] = ''
        post_data['MapCenterLon'] = ''
        post_data['MapZoom'] = '0'
        post_data['EntServiceID'] = self.user_id + '0001'
        post_data['AreaID'] = area_id
        post_data['Location'] = ''

        return self._post(post_data)

    def _request_cycle_list(self, parking_id):
        post_data = self._new_post_data_base('get_cycle_list')
        post_data['GetInfoNum'] = self.MAX_INFO_NUM
        post_data['GetInfoTopNum'] = '1'
        post_data['ParkingEntID'] = self.user_id
        post_data['ParkingID'] = parking_id
        post_data['ParkingLat'] = '0'
        post_data['ParkingLon'] = '0'

        return self._post(post_data)

    def _request_reserve(self, cycle_id, attach_id):
        post_data = self._new_post_data_base('reserve')
        post_data['CenterLat'] = '0'
        post_data['CenterLon'] = '0'
        post_data['CycLat'] = '0'
        post_data['CycLon'] = '0'
        post_data['CycleID'] = cycle_id
        post_data['AttachID'] = attach_id
        post_data['CycleTypeNo'] = '6'
        post_data['CycleEntID'] = self.user_id

        return self._post(post_data)

    def _request_cancel(self):
        post_data = self._new_post_data_base('cancel')

        return self._post(post_data)

    def _check_response_content(self, response):
        soup = BeautifulSoup(response.content, 'html.parser')
        message = soup.find('div', {'class' : 'main_inner_message'})
        if message != None:
            if 'Please login again' in self._parse_inner_text(message):
                raise self.DocomoCycleConnectionError

    ##### get methods #####
    def _parse_inner_text(self, html):
        return html.decode_contents(formatter='html')

    # find 'sp_view'(SmartPhone_view) class in html.
    # sp_view contains any parking or cycle forms.
    def _parse_form_list(self, html):
        soup = BeautifulSoup(html.content, 'html.parser')
        view_block = soup.find('div', {'class' : 'sp_view'})
        if view_block != None:
            return view_block.find_all('form')

    def _parse_usr_stat(self, html):
        soup = BeautifulSoup(html.content, 'html.parser')
        return soup.find('p', {'class' : 'usr_stat'})

    # parse parking name and unreserved cycles
    def parse_parking_info(self, parking):
        return parking.find('a').decode_contents(formatter='html').split('<br/>')

    def _check_user_status(self):
        response = self._request_top()
        user_status_block = self._parse_usr_stat(response)
        # when not reserved, 'usr_stat' isn't in response.
        if user_status_block == None:
            self.user_status = self.USER_STATUS['neutral']
        else:
            inner_text = self._parse_inner_text(user_status_block)
            pattern_reserved = r'.+/Reserved:.+'
            pattern_use = r'.+/In use:.+'
            if re.match(pattern_reserved, inner_text.strip()):
                self.user_status = self.USER_STATUS['reserved']
            elif re.match(pattern_use, inner_text.strip()):
                self.user_status = self.USER_STATUS['use']
            else:
                self.user_status = self.USER_STATUS['unknown']
        return response

    # get parking form list
    def get_parking_list(self, area_id):
        response = self._request_parking_list(area_id)
        return self._parse_form_list(response)

    def get_parking(self, parking_list, parking_id):
        for parking in parking_list:
            if parking.find('input', {'name' : 'ParkingID'})['value'] == parking_id:
                return parking

    # get cycle form list
    def get_cycle_list(self, parking_id):
        self._request_cycle_list(parking_id)
        return self._parse_form_list(self.last_response)

    def get_cycle(self, cycle_list, cycle_id):
        for cycle in cycle_list:
            if cycle.find('input', {'name' : 'CycleID'})['value'] == cycle_id:
                return cycle

    ############################
    ############################
    def login(self):
        post_data = {
            'EventNo' : self.EVENT_LIST['login'],
            'MemberID': self.user,
            'Password' : self.password,
            'MemAreaID' : self.area_id
        }
        response = self._post(post_data)
        soup = BeautifulSoup(response.content, 'html.parser')
        self.session_id = soup.find('input', {'name' : 'SessionID'})['value']
        self._check_user_status()
        if self.user_status == None:
            raise self.DocomoCycleLoginError()

    def reserve_cycle(self, parking_id, count=10):
        self._check_user_status()
        # user can reserve, only status is neutral
        if self.user_status == self.USER_STATUS['neutral']:
            cycle_list = self.get_cycle_list(parking_id)
            if cycle_list == None:
                return False
            cycle = cycle_list[random.randrange(len(cycle_list))]
            cycle_id = cycle.find('input', {'name' : 'CycleID'})['value']
            attach_id = cycle.find('input', {'name' : 'AttachID'})['value']
            self._request_reserve(cycle_id, attach_id)
            if count > 0:
                return self.reserve_cycle(parking_id, count - 1)
        else:
            return True

    def reserve_info(self):
        response = self._check_user_status()
        if self.user_status in [self.USER_STATUS['reserved'], self.USER_STATUS['use']]:
            inner_text = self._parse_inner_text(self._parse_usr_stat(response))
            return re.sub(r'<.+?>', '', inner_text)

    def cancel(self):
        if self.user_status == self.EVENT_LIST['reserved']:
            self._request_cancel()
