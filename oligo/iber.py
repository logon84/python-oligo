from requests import Session
from datetime import datetime
from io import StringIO
from dateutil.relativedelta import relativedelta
import calendar
from decimal import Decimal


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
        response = self.__session.request("GET", self.__consumption_between_dates_csv_url.format(str(start_date.strftime('%d-%m-%Y')),str(end_date.strftime('%d-%m-%Y'))), headers=self.__headers_i_de)
        if response.status_code != 200:
            raise ResponseException
        if not response.text:
            raise NoResponseException
        p1 = []
        p2 = []
        csvdata = StringIO(response.text)
        next(csvdata)
        for line in csvdata:
            curr_hour = int(line.split(";")[1][11:13])
            curr_consumption = int(line.split(";")[3])/1000
            summer_flag = int(line.split(";")[2])
            if (12 + summer_flag) < curr_hour <= (22 + summer_flag):
                 p1.append(curr_consumption) #peak hours consumption
                 p2.append(0)
            else:
                 p2.append(curr_consumption) #low hours consumption
                 p1.append(0)
        return start_date, end_date, p1, p2

    def get_hourly_consumption_by_invoice(self,invoice_number,start_date,end_date):
        """Returns hour consumption by invoice.This DOES return R and E consumptions, so it's better for costs comparison"""
        self.__check_session()
        response = self.__session.request("GET", self.__consumption_by_invoice_csv_url.format(invoice_number,str(start_date.strftime('%d-%m-%Y')),end_date.strftime('%d-%m-%Y')), headers=self.__headers_i_de)
        if response.status_code != 200:
            raise ResponseException
        if not response.text:
            raise NoResponseException
        p1 = []
        p2 = []
        csvdata = StringIO(response.text)
        next(csvdata)
        for line in csvdata:
            curr_hour = int(line.split(";")[2])
            curr_consumption = float(line.split(";")[3].replace(',','.'))
            curr_day = datetime.strptime(line.split(";")[1], '%d/%m/%Y')
            summer_flag = int(curr_day.timetuple().tm_yday in range(80,266))
            if (12 + summer_flag) < curr_hour <= (22 + summer_flag):
                 p1.append(curr_consumption) #peak hours consumption
                 p2.append(0)
            else:
                 p2.append(curr_consumption) #low hours consumption
                 p1.append(0)
        return start_date, end_date, p1, p2

    def get_consumption(self,index):
        """Returns consumptions. Index 0 means current consumption not yet invoiced. Bigger indexes returns consumption by every already created invoice"""
        self.__check_session()
        if index == 0: #get current cost
            last_invoice = self.get_invoice(0) #get last invoice
            start_date = last_invoice['fechaHasta'] #get last day used in the last invoice to use next day as starting day for current cost
            start_date = datetime.strptime(start_date, '%d/%m/%Y')
            start_date = start_date + relativedelta(days=1)
            end_date = self.today
            start_date, end_date, p1, p2 = self.get_hourly_consumption(start_date,end_date)
        else:
            invoice = self.get_invoice(index-1)
            start_date = invoice['fechaDesde']
            start_date = datetime.strptime(start_date, '%d/%m/%Y')
            end_date = invoice['fechaHasta']
            end_date = datetime.strptime(end_date, '%d/%m/%Y')
            start_date, end_date, p1, p2 = self.get_hourly_consumption_by_invoice(invoice['numero'],start_date,end_date)
        return start_date, end_date, p1, p2

    def get_ree_data(self,token,start_date,end_date):
        """Returns energy & toll prices from REE"""
        IDprices20_total = '1013'
        IDtoll20 = '1018'
        IDprices20DHA_total = '1014'
        IDtoll20DHA = '1025'
        self.__headers_ree['Authorization'] = "Token token=" + token

        response = self.__session.request("GET", self.__ree_api_url.format(IDtoll20,str(start_date.strftime('%Y-%m-%d')),str(end_date.strftime('%Y-%m-%d'))), headers=self.__headers_ree)
        if response.status_code != 200:
            raise ResponseException
        if not response.text:
            raise NoResponseException
        json_response = response.json()
        toll20 = []
        for i in range(len(json_response['indicator']['values'])):
            toll20.append(self.roundup(float(json_response['indicator']['values'][i]['value'])/1000, 6))

        response = self.__session.request("GET", self.__ree_api_url.format(IDprices20_total,str(start_date.strftime('%Y-%m-%d')),str(end_date.strftime('%Y-%m-%d'))), headers=self.__headers_ree)
        if response.status_code != 200:
            raise ResponseException
        if not response.text:
            raise NoResponseException
        json_response = response.json()
        energy20 = []
        for i in range(len(json_response['indicator']['values'])):
            energy20.append(self.roundup(float(json_response['indicator']['values'][i]['value'])/1000, 6) - toll20[i])


        response = self.__session.request("GET", self.__ree_api_url.format(IDtoll20DHA,str(start_date.strftime('%Y-%m-%d')),str(end_date.strftime('%Y-%m-%d'))), headers=self.__headers_ree)
        if response.status_code != 200:
            raise ResponseException
        if not response.text:
            raise NoResponseException
        json_response = response.json()
        toll20DHA = []
        for i in range(len(json_response['indicator']['values'])):
            toll20DHA.append(self.roundup(float(json_response['indicator']['values'][i]['value'])/1000, 6))

        response = self.__session.request("GET", self.__ree_api_url.format(IDprices20DHA_total,str(start_date.strftime('%Y-%m-%d')),str(end_date.strftime('%Y-%m-%d'))), headers=self.__headers_ree)
        if response.status_code != 200:
            raise ResponseException
        if not response.text:
            raise NoResponseException
        json_response = response.json()
        energy20DHA = []
        for i in range(len(json_response['indicator']['values'])):
            energy20DHA.append(self.roundup(float(json_response['indicator']['values'][i]['value'])/1000, 6) - toll20DHA[i])

        return energy20, toll20, energy20DHA, toll20DHA

    def roundup(self, num, ndecimals):
        return float(round(Decimal(str(num)),ndecimals))

    def calculate_invoice_PVPC(self, token, index):
        """Returns cost of same consumptions on pvpc . Index 0 means current consumption not yet invoiced. Bigger indexes returns costs of every already created invoice"""
        start_date, end_date, p1, p2 = self.get_consumption(index)
        energy20, toll20, energy20DHA, toll20DHA = self.get_ree_data(token,start_date,end_date)
        ndays = (end_date - start_date).days+1
        pot = (self.contract()['potMaxima'])/1000
        print("\nDESDE: "+start_date.strftime('%d-%m-%Y')+"\nHASTA: "+end_date.strftime('%d-%m-%Y')+"\nDIAS: "+str(ndays)+"\nPOTENCIA: "+str(pot)+"KW\nCONSUMO PUNTA P1: " + '{0:.2f}'.format(sum(p1))+ "kwh"+"\nCONSUMO VALLE P2: "+ '{0:.2f}'.format(sum(p2))+ "kwh\n")
        average_price_energy20 = 0
        average_price_toll20 = 0
        average_price_energy20DHA_peak = 0
        average_price_toll20DHA_peak = 0
        average_price_energy20DHA_low = 0
        average_price_toll20DHA_low = 0
        for i in range(len(p1)):
            average_price_energy20 = average_price_energy20 + (p1[i]*energy20[i] + p2[i]*energy20[i])/(sum(p1)+sum(p2))
            average_price_toll20 = average_price_toll20 + (p1[i]*toll20[i] + p2[i]*toll20[i])/(sum(p1)+sum(p2))

            average_price_energy20DHA_peak = average_price_energy20DHA_peak + (p1[i]*energy20DHA[i])/sum(p1)
            average_price_toll20DHA_peak = average_price_toll20DHA_peak + (p1[i]*toll20DHA[i])/sum(p1)

            average_price_energy20DHA_low = average_price_energy20DHA_low + (p2[i]*energy20DHA[i])/sum(p2)
            average_price_toll20DHA_low = average_price_toll20DHA_low + (p2[i]*toll20DHA[i])/sum(p2)

        power_cost = pot * (38.043426+3.113)/(365+int(calendar.isleap(start_date.year))) * ndays
        energy_cost_20 = self.roundup(average_price_energy20*(self.roundup(sum(p1)+sum(p2),1)),2) + self.roundup(average_price_toll20*(self.roundup(sum(p1)+sum(p2),1)),2)
        energy_cost_20DHA = self.roundup(average_price_energy20DHA_peak*(self.roundup(sum(p1),1)),2) + self.roundup(average_price_toll20DHA_peak*(self.roundup(sum(p1),1)),2) + self.roundup(average_price_energy20DHA_low*(self.roundup(sum(p2),1)),2) + self.roundup(average_price_toll20DHA_low*(self.roundup(sum(p2),1)),2)
        energy_and_power_cost_20 = energy_cost_20 + power_cost
        energy_and_power_cost_20DHA = energy_cost_20DHA + power_cost
        energy_tax_20 = energy_and_power_cost_20*0.0511269632
        energy_tax_20DHA = energy_and_power_cost_20DHA*0.0511269632
        equipment_cost = ndays * (0.81*12/(365+int(calendar.isleap(start_date.year))))
        total_20 =  energy_and_power_cost_20 + energy_tax_20 + equipment_cost
        total_20DHA =  energy_and_power_cost_20DHA + energy_tax_20DHA + equipment_cost
        VAT_20 = self.roundup(total_20*0.21,2)
        VAT_20DHA = self.roundup(total_20DHA*0.21,2)
        total_plus_vat_20 = total_20 + VAT_20
        total_plus_vat_20DHA = total_20DHA + VAT_20DHA
#####################_____OTHER_COMPARISON (fill values)_____###############################
        power_cost_other = pot * (38.043426/(365+int(calendar.isleap(start_date.year)))) * ndays
        energy_cost_other = sum(p1) * 0.161 + sum(p2) * 0.082
        energy_and_power_cost_other = energy_cost_other + power_cost_other
        social_bonus = 0.02 * ndays
        energy_tax_other = (energy_and_power_cost_other + social_bonus)*0.0511269632
        equipment_cost_other = ndays *(0.81*12)/(365+int(calendar.isleap(start_date.year)))
        total_other = energy_and_power_cost_other + energy_tax_other + equipment_cost_other + social_bonus
        VAT_other = self.roundup(total_other*0.21,2)
        total_plus_vat_other = total_other + VAT_other
############################################################################################

        print('{:<30} {:<30} {:<30}'.format("PVPC 2.0A price", "PVPC 2.0DHA price", "SOM ENERGIA 2.0DHA price"))
        print("-----------------------------------------------------------------------------------------")
        print('{:<30} {:<30} {:<30}'.format("Power cost: "+'{0:.2f}'.format(power_cost)+"€", "Power cost: "+'{0:.2f}'.format(power_cost)+"€", "Power cost: "+'{0:.2f}'.format(power_cost_other)+"€"))
        print('{:<30} {:<30} {:<30}'.format("Energy cost: "+'{0:.2f}'.format(energy_cost_20)+"€", "Energy cost: "+'{0:.2f}'.format(energy_cost_20DHA)+"€", "Energy cost: "+'{0:.2f}'.format(energy_cost_other)+"€"))
        print('{:<30} {:<30} {:<30}'.format("Electric tax: "+'{0:.2f}'.format(energy_tax_20)+"€", "Electric tax: "+'{0:.2f}'.format(energy_tax_20DHA)+"€", "Electric tax: "+'{0:.2f}'.format(energy_tax_other)+"€"))
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
