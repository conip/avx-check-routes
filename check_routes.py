import logging
import requests
import os
import sys
import urllib3
import json
import re
import time
 
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

#---------------------------------------------------------------------------------------------------------------
class APICALL:
    def __init__(self,URL=None, DATA=None, VERIFY = None):
        self.url = URL
        self.data = DATA
        self.verify = VERIFY if VERIFY != None else False
        self.response = ''

    def post_request(self):
        try:
            self.response = requests.post(self.url, self.data, self.verify)
            return json.loads(self.response.text)
        except requests.exceptions.RequestException as e:
            return e


#---------------------------------------------------------------------------------------------------------------
def main():
    controller_ip=str(sys.argv[1])
    controller_user=str(sys.argv[2])
    controller_password=str(sys.argv[3])
    check_route = str(sys.argv[4])

    url = f"https://{controller_ip}/v1/api"
    
    #-------------- Login to CTRL to get authorization CID
    get_cid = {'action': 'login', 'password' : controller_password, 'username' : controller_user }
    call1 = APICALL(url,get_cid)
    json_formatted_response = call1.post_request()
    var_cid = call1.post_request()['CID']
    
    #-------------- Listing all spokes where we are going to look for specific routes
    list_all_spoke_gw = {"action": "list_spoke_gws", "CID": var_cid}
    call2 = APICALL(url,list_all_spoke_gw)
    response2 = call2.post_request()

    # adding "read_status" = "not read" - to all GWs in the list as we will walk through it for all entries
    gw_list_with_status = []

    for i in response2["results"]:
        gw_list_with_status.append({ 'read_status' : 'not_read', 'gw_name' : i})

    all_gw_read = False
    number_of_gw_left = len(gw_list_with_status)
    found = False

    #-------------- formatting the columns for displaying
    columns = "{:<7}{:<45}{:<70}{:<25}{:<30}"
    columns_ = "{:_<7}{:_<45}{:_<70}{:_<25}{:_<30}"
    print(columns.format("Cloud","Spoke GW name","RT name","[ Route/Mask  ]","Next Hop"))
    print(columns_.format("","","","",""))
    #--------------
    # as there might be cases when script cant get the response from ctrl (response is "Requests limit exceeded").
    # we want to do it untill getting the respone for all spoke GWs so counting to 0 for number of GWs

    while number_of_gw_left != 0:
        for count, specific_gw in enumerate(gw_list_with_status):
            if specific_gw['read_status'] == "not_read":
                request_data = {
                    "action": "get_transit_or_spoke_gateway_details", 
                    "CID": var_cid, 
                    "gateway_name": specific_gw["gw_name"],
                    "option" : "vpc_route" 
                }
                call2.data = request_data
                get_spoke_gw_details = call2.post_request()

                #regex_route_table_pattern = re.compile(r'^user-route-table-.*')
                regex_route_table_pattern = re.compile(r'.*')
                # try block with except for KeyError as if there is not vpc_route_table list that means CTRL responsed with something else (i.e. RequestLimitExceeded)
                try: 
                    cloud_type = get_spoke_gw_details["results"]["cloud_type"]
                    number_of_gw_left = number_of_gw_left - 1
                    gw_list_with_status[count]['read_status'] = 'ok'
                
                    for item_gw in get_spoke_gw_details["results"]["vpc_route_table"]:
                        if regex_route_table_pattern.match(item_gw["name"]):
                            for item_route in item_gw["route_info"]:
                                if item_route["route"] == check_route:
                                    found = True
                                    target = item_route["target"]

                            if found == True:
                                print(columns.format(cloud_type,specific_gw["gw_name"], item_gw["name"] ,"[ " + check_route + " ]",target))
                            elif found == False:
                                print(columns.format(cloud_type,specific_gw["gw_name"], item_gw["name"] ,"[ NOT FOUND ]","" ))
                            
                            # reseting found variable to FALSE
                            found = False
                            target = ""
                except KeyError:
                    gw_list_with_status[count]['read_status'] = 'not_read'

                # end of while
            
#---------------------------------------------------------------------------------------------------------------
if __name__ == '__main__':
    main()