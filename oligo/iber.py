from requests import Session
from datetime import datetime
from io import StringIO
from dateutil.relativedelta import relativedelta
import calendar
from decimal import Decimal
import aiohttp
import asyncio


class ResponseException(Exception):
    pass


class LoginException(Exception):
    pass


class SessionException(Exception):
    pass


class NoResponseException(Exception):
    pass


class SelectContractException(Exception):
    pass


class Iber:

    __domain = "https://www.i-de.es"
    __login_url = __domain + "/consumidores/rest/loginNew/login"
    __watthourmeter_url = __domain + "/consumidores/rest/escenarioNew/obtenerMedicionOnline/24"
    __icp_status_url = __domain + "/consumidores/rest/rearmeICP/consultarEstado"
    __contracts_url = __domain + "/consumidores/rest/cto/listaCtos/"
    __contract_detail_url = __domain + "/consumidores/rest/detalleCto/detalle/"
    __contract_selection_url = __domain + "/consumidores/rest/cto/seleccion/"
    today = datetime.now()
    twoyearsago =  today - relativedelta(years=2)
    __invoice_list_url = __domain + "/consumidores/rest/consumoNew/obtenerDatosFacturasConsumo/fechaInicio/{0}/fechaFinal/{1}".format(twoyearsago.strftime("%d-%m-%Y%H:%M:%S"),today.strftime("%d-%m-%Y%H:%M:%S"))
    __consumption_max_date_url = __domain + "/consumidores/rest/consumoNew/obtenerLimiteFechasConsumo"
    __consumption_between_dates_csv_url = __domain + "/consumidores/rest/consumoNew/exportarACSVPeriodoConsumo/fechaInicio/{0}00:00:00/fechaFinal/{1}00:00:00/tipo/horaria/"
    __consumption_by_invoice_csv_url = __domain + "/consumidores/rest/consumoNew/exportarACSV/factura/{0}/fechaInicio/{1}00:00:00/fechaFinal/{2}23:59:59/modo/R"
    __headers_i_de = {
        'User-Agent': "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/77.0.3865.90 Chrome/77.0.3865.90 Safari/537.36",
        'accept': "application/json; charset=utf-8",
        'content-type': "application/json; charset=utf-8",
        'cache-control': "no-cache"
    }

    __ree_api_url = "https://api.esios.ree.es/indicators/{0}?start_date=\"{1}\"T00:00:00&end_date=\"{2}\"T23:00:00"
    __headers_ree = {
        'User-Agent': "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/77.0.3865.90 Chrome/77.0.3865.90 Safari/537.36",
        'accept': "application/json; application/vnd.esios-api-v1+json",
        'content-type': "application/json",
        'Host': "api.esios.ree.es",
        'Authorization': "Token token=",
        'Cookie': ""
    }
    

    def __init__(self):
        """Iber class __init__ method."""
        self.__session = None

    def login(self, user, password):
        """Creates session with your credentials"""
        self.__session = Session()
        login_data = "[\"{}\",\"{}\",null,\"Linux -\",\"PC\",\"Chrome 77.0.3865.90\",\"0\",\"\",\"s\"]".format(user, password)
        response = self.__session.request("POST", self.__login_url, data=login_data, headers=self.__headers_i_de)
        if response.status_code != 200:
            self.__session = None
            raise ResponseException("Response error, code: {}".format(response.status_code))
        json_response = response.json()
        if json_response["success"] != "true":
            self.__session = None
            raise LoginException("Login error, bad login")

    def __check_session(self):
        if not self.__session:
            raise SessionException("Session required, use login() method to obtain a session")

    def watthourmeter(self):
        """Returns your current power consumption."""
        self.__check_session()
        response = self.__session.request("GET", self.__watthourmeter_url, headers=self.__headers_i_de)
        if response.status_code != 200:
            raise ResponseException
        if not response.text:
            raise NoResponseException
        json_response = response.json()
        return json_response['valMagnitud']+"kw"

    def get_invoice(self,index):
        """Returns invoice data."""
        self.__check_session()
        response = self.__session.request("GET", self.__invoice_list_url, headers=self.__headers_i_de)
        if response.status_code != 200:
            raise ResponseException
        if not response.text:
            raise NoResponseException
        json_response = response.json()
        return json_response['facturas'][index]

    def get_last_day_with_recorded_data(self):
        """Returns hour consumption between dates."""
        self.__check_session()
        response = self.__session.request("GET", self.__consumption_max_date_url, headers=self.__headers_i_de)
        if response.status_code != 200:
            raise ResponseException
        if not response.text:
            raise NoResponseException
        json_response = response.json()
        max_date = datetime.strptime(json_response['fechaMaxima'], '%d-%m-%Y%H:%M:%S')
        return max_date

    def get_hourly_consumption(self,start_date,end_date):
        """Returns hour consumption between dates.This DOES NOT return E consumptions"""
        self.__check_session()
        max_date = self.get_last_day_with_recorded_data()
        if end_date > max_date:
            end_date = max_date
        response = self.__session.request("GET", self.__consumption_between_dates_csv_url.format(start_date.strftime('%d-%m-%Y'),end_date.strftime('%d-%m-%Y')), headers=self.__headers_i_de)
        if response.status_code != 200:
            raise ResponseException
        if not response.text:
            raise NoResponseException
        consumption_kwh = []
        csvdata = StringIO(response.text)
        next(csvdata)
        last_date = start_date
        for line in csvdata:
            #spaguetti.run
            current_date = datetime.strptime(line.split(";")[1], '%Y/%m/%d %H:%M')
            if not(current_date == last_date + relativedelta(hours=1)) and not(current_date == last_date) and not(current_date.month == 3 and current_date.day in range (25,32) and current_date.isoweekday() == 7 and current_date.hour == 3):
                 #NOT(current hour is consecutive to previous) and NOT(october hour change 0-1-2-2-3-4) and NOT(march hour change 0-1-3-4)
                 #value missing detected, fill with 0's
                 while current_date > (last_date + relativedelta(hours=1)):
                       consumption_kwh.append(0)
                       last_date = last_date + relativedelta(hours=1)
                 print("--------------------ATTENTION: SOME VALUES ARE MISSING FOR THIS SIMULATION---------------------")
            consumption_kwh.append(int(line.split(";")[3])/1000)
            last_date = current_date
        return start_date, end_date, consumption_kwh

    def get_hourly_consumption_by_invoice(self,invoice_number,start_date,end_date):
        """Returns hour consumption by invoice.This DOES return R and E consumptions, so it's better for costs comparison"""
        self.__check_session()
        response = self.__session.request("GET", self.__consumption_by_invoice_csv_url.format(invoice_number,start_date.strftime('%d-%m-%Y'),end_date.strftime('%d-%m-%Y')), headers=self.__headers_i_de)
        if response.status_code != 200:
            raise ResponseException
        if not response.text:
            raise NoResponseException
        consumption_kwh = []
        csvdata = StringIO(response.text)
        next(csvdata)
        for line in csvdata:
            consumption_kwh.append(float(line.split(";")[3].replace(',','.')))
        return start_date, end_date, consumption_kwh

    def get_consumption(self,index):
        """Returns consumptions. Index 0 means current consumption not yet invoiced. Bigger indexes returns consumption by every already created invoice"""
        self.__check_session()
        if index == 0: #get current cost
            last_invoice = self.get_invoice(0) #get last invoice
            start_date = last_invoice['fechaHasta'] #get last day used in the last invoice to use next day as starting day for current cost
            start_date = datetime.strptime(start_date, '%d/%m/%Y')
            start_date = start_date + relativedelta(days=1)
            end_date = self.today
            start_date, end_date, consumption_kwh = self.get_hourly_consumption(start_date,end_date)
        else:
            invoice = self.get_invoice(index-1)
            start_date = invoice['fechaDesde']
            start_date = datetime.strptime(start_date, '%d/%m/%Y')
            end_date = invoice['fechaHasta']
            end_date = datetime.strptime(end_date, '%d/%m/%Y')
            start_date, end_date, consumption_kwh = self.get_hourly_consumption_by_invoice(invoice['numero'],start_date,end_date)
        return start_date, end_date, consumption_kwh

    async def get(self,url,headers):
        """async request.GET to speedup REE data fetch"""
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status != 200:
                     raise ResponseException
                if not response.text:
                     raise NoResponseException
                return await response.json()

    def get_ree_data(self,token,start_date,end_date):
        """Returns energy prices from REE"""
        IDenergy20 = '10254'
        IDenergy20DHA = '10255'

        energy20 = []
        energy20DHA = []
        peak_mask = []

        url_0 = self.__ree_api_url.format(IDenergy20,start_date.strftime('%Y-%m-%d'),end_date.strftime('%Y-%m-%d'))
        url_1 = self.__ree_api_url.format(IDenergy20DHA,start_date.strftime('%Y-%m-%d'),end_date.strftime('%Y-%m-%d'))
        self.__headers_ree['Authorization'] = "Token token=" + token

        loop = asyncio.get_event_loop()
        parallel_http_get = [self.get(url_0, self.__headers_ree),self.get(url_1, self.__headers_ree)]
        results = loop.run_until_complete(asyncio.gather(*parallel_http_get))

        for i in range(len(results[0]['indicator']['values'])):
            energy20.append(self.roundup(float(results[0]['indicator']['values'][i]['value'])/1000, 6))
            energy20DHA.append(self.roundup(float(results[1]['indicator']['values'][i]['value'])/1000, 6))
            summer_flag = int("+02:00" in results[0]['indicator']['values'][i]['datetime'])
            is_it_peak_hour = int(results[0]['indicator']['values'][i]['datetime'][11:13]) in range(12+summer_flag,22+summer_flag)
            peak_mask.append(is_it_peak_hour)
        return energy20, energy20DHA, peak_mask

    def roundup(self, num, ndecimals):
        return float(round(Decimal(str(num)),ndecimals))

    def calculate_invoice_PVPC(self, token, index):
        """Returns cost of same consumptions on pvpc . Index 0 means current consumption not yet invoiced. Bigger indexes returns costs of every already created invoice"""
        start_date, end_date, consumption_kwh = self.get_consumption(index)
        energy20, energy20DHA, peak_mask = self.get_ree_data(token,start_date,end_date)
        p1 = []
        p2 = []
        for i in range(len(consumption_kwh)):
            p1.append(int(peak_mask[i]) * consumption_kwh[i])
            p2.append(int(not(peak_mask[i])) * consumption_kwh[i])

        ndays = (end_date - start_date).days+1
        pot = (self.contract()['potMaxima'])/1000

        average_price_energy20 = 0
        average_price_energy20DHA_peak = 0
        average_price_energy20DHA_low = 0

        for i in range(len(consumption_kwh)):
            average_price_energy20 = average_price_energy20 + self.roundup((consumption_kwh[i]*energy20[i])/sum(consumption_kwh),6)
            average_price_energy20DHA_peak = average_price_energy20DHA_peak + self.roundup((p1[i]*energy20DHA[i])/sum(p1),6)
            average_price_energy20DHA_low = average_price_energy20DHA_low + self.roundup((p2[i]*energy20DHA[i])/sum(p2),6)

        power_cost = self.roundup(pot * ndays * 38.043426/(365+int(calendar.isleap(start_date.year))),2) + self.roundup(pot * ndays * 3.113/(365+int(calendar.isleap(start_date.year))),2)
        energy_cost_20 = self.roundup(average_price_energy20*(self.roundup(sum(consumption_kwh),1)),2) + self.roundup(0.044027*(self.roundup(sum(consumption_kwh),1)),2)
        energy_cost_20DHA = self.roundup(average_price_energy20DHA_peak*(self.roundup(sum(p1),1)),2) + self.roundup(0.062012*(self.roundup(sum(p1),1)),2) + self.roundup(average_price_energy20DHA_low*(self.roundup(sum(p2),1)),2) + self.roundup(0.002215*(self.roundup(sum(p2),1)),2)
        energy_and_power_cost_20 = energy_cost_20 + power_cost
        energy_and_power_cost_20DHA = energy_cost_20DHA + power_cost
        energy_tax_20 = self.roundup(energy_and_power_cost_20*0.0511269632,2)
        energy_tax_20DHA = self.roundup(energy_and_power_cost_20DHA*0.0511269632,2)
        equipment_cost = self.roundup(ndays * (0.81*12/(365+int(calendar.isleap(start_date.year)))),2)
        total_20 =  energy_and_power_cost_20 + energy_tax_20 + equipment_cost
        total_20DHA =  energy_and_power_cost_20DHA + energy_tax_20DHA + equipment_cost
        VAT_20 = self.roundup(total_20*0.21,2)
        VAT_20DHA = self.roundup(total_20DHA*0.21,2)
        total_plus_vat_20 = total_20 + VAT_20
        total_plus_vat_20DHA = total_20DHA + VAT_20DHA
#####################_____OTHER_COMPARISON (fill values)_____###############################
        name_other = "SOM ENERGIA 2.0DHA"
        power_cost_other = self.roundup(pot * (38.043426/(365+int(calendar.isleap(start_date.year)))) * ndays,2)
        energy_cost_other = self.roundup(sum(p1) * 0.147 + sum(p2) * 0.075,2)
        energy_and_power_cost_other = energy_cost_other + power_cost_other
        social_bonus_other = 0.02 * ndays
        energy_tax_other = self.roundup((energy_and_power_cost_other + social_bonus_other)*0.0511269632,2)
        equipment_cost_other = self.roundup(ndays *(0.81*12)/(365+int(calendar.isleap(start_date.year))),2)
        total_other = energy_and_power_cost_other + energy_tax_other + equipment_cost_other + social_bonus_other
        VAT_other = self.roundup(total_other*0.21,2)
        total_plus_vat_other = total_other + VAT_other
############################################################################################

        print("\nDESDE: "+start_date.strftime('%d-%m-%Y')+"\nHASTA: "+end_date.strftime('%d-%m-%Y')+"\nDIAS: "+str(ndays)+"\nPOTENCIA: "+str(pot)+"KW\nCONSUMO PUNTA P1: " + '{0:.2f}'.format(sum(p1))+ "kwh"+"\nCONSUMO VALLE P2: "+ '{0:.2f}'.format(sum(p2))+ "kwh\n")
        print('{:<30} {:<30} {:<30}'.format("PVPC 2.0A price", "PVPC 2.0DHA price", name_other + " price"))
        print("-----------------------------------------------------------------------------------------")
        print('{:<30} {:<30} {:<30}'.format("Power cost: "+'{0:.2f}'.format(power_cost)+"€", "Power cost: "+'{0:.2f}'.format(power_cost)+"€", "Power cost: "+'{0:.2f}'.format(power_cost_other)+"€"))
        print('{:<30} {:<30} {:<30}'.format("Energy cost: "+'{0:.2f}'.format(energy_cost_20)+"€", "Energy cost: "+'{0:.2f}'.format(energy_cost_20DHA)+"€", "Energy cost: "+'{0:.2f}'.format(energy_cost_other)+"€"))
        print('{:<30} {:<30} {:<30}'.format("Electric tax: "+'{0:.2f}'.format(energy_tax_20)+"€", "Electric tax: "+'{0:.2f}'.format(energy_tax_20DHA)+"€", "Electric tax: "+'{0:.2f}'.format(energy_tax_other)+"€"))
        print('{:<30} {:<30} {:<30}'.format("Social bonus: "+'{0:.2f}'.format(0)+"€", "Social bonus: "+'{0:.2f}'.format(0)+"€", "Social bonus: "+'{0:.2f}'.format(social_bonus_other)+"€"))
        print('{:<30} {:<30} {:<30}'.format("Measure equipments: "+'{0:.2f}'.format(equipment_cost)+"€", "Measure equipments: "+'{0:.2f}'.format(equipment_cost)+"€", "Measure equipments: "+'{0:.2f}'.format(equipment_cost_other)+"€"))
        print('{:<30} {:<30} {:<30}'.format("VAT: "+'{0:.2f}'.format(VAT_20)+"€", "VAT: "+'{0:.2f}'.format(VAT_20DHA)+"€", "VAT: "+'{0:.2f}'.format(VAT_other)+"€"))
        print('{:<30} {:<30} {:<30}'.format("TOTAL: "+'{0:.2f}'.format(total_plus_vat_20)+"€", "TOTAL: "+'{0:.2f}'.format(total_plus_vat_20DHA)+"€", "TOTAL: "+'{0:.2f}'.format(total_plus_vat_other)+"€\n\n"))
        return "Done"

    def icpstatus(self):
        """Returns the status of your ICP."""
        self.__check_session()
        response = self.__session.request("POST", self.__icp_status_url, headers=self.__headers_i_de)
        if response.status_code != 200:
            raise ResponseException
        if not response.text:
            raise NoResponseException
        json_response = response.json()
        if json_response["icp"] == "trueConectado":
            return True
        else:
            return False

    def contracts(self):
        self.__check_session()
        response = self.__session.request("GET", self.__contracts_url, headers=self.__headers_i_de)
        if response.status_code != 200:
            raise ResponseException
        if not response.text:
            raise NoResponseException
        json_response = response.json()
        if json_response["success"]:
            return json_response["contratos"]

    def contract(self):
        self.__check_session()
        response = self.__session.request("GET", self.__contract_detail_url, headers=self.__headers_i_de)
        if response.status_code != 200:
            raise ResponseException
        if not response.text:
            raise NoResponseException
        return response.json()

    def contractselect(self, id):
        self.__check_session()
        response = self.__session.request("GET", self.__contract_selection_url + id, headers=self.__headers_i_de)
        if response.status_code != 200:
            raise ResponseException
        if not response.text:
            raise NoResponseException
        json_response = response.json()
        if not json_response["success"]:
            raise SelectContractException
