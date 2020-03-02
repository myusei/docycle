import requests
from bs4 import BeautifulSoup
import re

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
        'top' : '25904',
    }
    USER_STATUS = {
        'unknown' : -1,
        'neutral' : 0,
        'reserved' : 1,
    }

    MAX_INFO_NUM = '255'

    class DocomoCycleError(Exception):
        pass
    class DocomoCycleLoginError(DocomoCycleError):
        pass
    class DocomoCycleRequestsError(DocomoCycleError):
        pass


    ##### constructor #####
    def __init__(self, user, password, user_id, area_id):
        self.user = user
        self.password = password
        self.area_id = area_id
        self.user_id = user_id
        self.session = requests.session()
        self.session_id = None
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

    ##### get methods #####
    def _parse_inner_text(self, html):
        return html.decode_contents(formatter='html')

    # find 'sp_view'(SmartPhone_view) class in html.
    # sp_view contains any parking or cycle forms.
    # Added pc_view. sp_view's H1-Area parking ides are buggy, but pc_view too.
    def _parse_form_list(self, html):
        soup = BeautifulSoup(html.content, 'html.parser')
        view_block = soup.find('div', {'class' : 'sp_view'})
        #view_block = soup.find('div', {'class' : 'pc_view'})
        if view_block != None:
            return view_block.find_all('form')

    def _parse_usr_stat(self, html):
        soup = BeautifulSoup(html.content, 'html.parser')
        return soup.find('p', {'class' : 'usr_stat'})

    def _check_user_status(self):
        response = self._request_top()
        user_status_block = self._parse_usr_stat(response)
        # when not reserved, 'usr_stat' isn't in response.
        if user_status_block == None:
            self.user_status = self.USER_STATUS['neutral']
        else:
            pattern_reserved = r'.+/Reserved:.+'
            inner_text = self._parse_inner_text(user_status_block)
            if re.match(pattern_reserved, inner_text.strip()):
                self.user_status = self.USER_STATUS['reserved']
            else:
                # probably, when using cycle is this
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

    # get parking name and unreserved cycles
    def get_parking_info(self, parking):
        return parking.find('a').decode_contents(formatter='html').split('<br/>')

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

    def create_parking_list_header(self, file_name):
        with open(file_name, mode='w') as f:
            f.write('TYO_PARKING_LIST = {\n')

    def create_parking_list(self, file_name, area_id):
        with open(file_name, mode='a') as f:
            parking_list = self.get_parking_list(area_id)
            if parking_list != None:
                for p in parking_list:
                    p_info = self.get_parking_info(p)
                    # H1-Are is buggy.
                    # The ParkingID is always 'TYO' and the ParkingLat is ParkingID.
                    if(p.find('input', {'name' : 'ParkingID'})['value'] == 'TYO'):
                        pair = '\tr\'' + p.find('input', {'name' : 'ParkingLat'})['value'] + '\' : \''
                        pair += p_info[0] + '\',\n'
                    else:
                        pair = '\tr\'' + p_info[1].replace('\'','') + '\' : \''
                        pair += p.find('input', {'name' : 'ParkingID'})['value'] + '\',\n'
                    f.write(pair)
    def create_parking_list_footer(self, file_name):
        with open(file_name, mode='a') as f:
            f.write('}\n')

if __name__ == '__main__':
    import os
    user = os.environ['CYCLE_USER']
    password = os.environ['CYCLE_PASS']
    file_name = 'parking.py'

    dc = DocomoCycle(user,password,'TYO','1')
    dc.create_parking_list_header(file_name)
    for i in range(1,12):
        dc.create_parking_list(file_name, str(i))
    dc.create_parking_list_footer(file_name)
