from requests import Session
from datetime import datetime
from io import StringIO
from dateutil.relativedelta import relativedelta


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
    __consumption_by_invoice_url = __domain + "/consumidores/rest/consumoNew/obtenerDatosFacturasConsumo/fechaInicio/{0}/fechaFinal/{1}".format(twoyearsago.strftime("%d-%m-%Y%H:%M:%S"),today.strftime("%d-%m-%Y%H:%M:%S"))
    __consumption_max_date_url = __domain + "/consumidores/rest/consumoNew/obtenerLimiteFechasConsumo"
    __consumption_between_dates_csv_url = __domain + "/consumidores/rest/consumoNew/exportarACSVPeriodoConsumo/fechaInicio/{0}/fechaFinal/{1}/tipo/horaria/"
    __headers_i_de = {
        'User-Agent': "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/77.0.3865.90 Chrome/77.0.3865.90 Safari/537.36",
        'accept': "application/json; charset=utf-8",
        'content-type': "application/json; charset=utf-8",
        'cache-control': "no-cache"
    }

    __ree_api_url = "https://api.esios.ree.es/indicators/1014?start_date=\"{0}\"T01:00:00&end_date=\"{1}\"T24:00:00"
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
        response = self.__session.request("GET", self.__consumption_by_invoice_url, headers=self.__headers_i_de)
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
        """Returns hour consumption between dates."""
        self.__check_session()
        max_date = self.get_last_day_with_recorded_data()
        if end_date > max_date:
            end_date = max_date
        response = self.__session.request("GET", self.__consumption_between_dates_csv_url.format(str(start_date.strftime('%d-%m-%Y'))+'00:00:00',str(end_date.strftime('%d-%m-%Y'))+'00:00:00'), headers=self.__headers_i_de)
        if response.status_code != 200:
            raise ResponseException
        if not response.text:
            raise NoResponseException
        consumptions = []
        csvdata = StringIO(response.text)
        next(csvdata)
        for line in csvdata:
            consumptions.append(float(line.split(";")[3])/1000)
        return consumptions, start_date, end_date

    def get_invoice_consumption(self,index):
        """Returns consumption by invoice. Index 0 means current consumption not yet invoiced. Bigger indexes returns consumption by every already created invoice"""
        self.__check_session()
        if index == 0: #get current cost
            last_invoice = self.get_invoice(0) #get last invoice
            start_date = last_invoice['fechaHasta'] #get last day used in the last invoice to use next day as starting day for current cost
            start_date = datetime.strptime(start_date, '%d/%m/%Y')
            start_date = start_date + relativedelta(days=1)
            end_date = self.today
        else:
            invoice = self.get_invoice(index-1)
            start_date = invoice['fechaDesde']
            start_date = datetime.strptime(start_date, '%d/%m/%Y')
            end_date = invoice['fechaHasta']
            end_date = datetime.strptime(end_date, '%d/%m/%Y')
        consumptions, start_date, end_date = self.get_hourly_consumption(start_date,end_date)
        return consumptions, start_date, end_date

    def get_ree_20dha_data(self,token,start_date,end_date):
        """Returns 2.0DHA prices from REE"""
        self.__headers_ree['Authorization'] = "Token token=" + token
        response = self.__session.request("GET", self.__ree_api_url.format(str(start_date.strftime('%Y-%m-%d')),str(end_date.strftime('%Y-%m-%d'))), headers=self.__headers_ree)
        if response.status_code != 200:
            raise ResponseException
        if not response.text:
            raise NoResponseException
        json_response = response.json()
        prices = []
        for i in range(len(json_response['indicator']['values'])):
            prices.append(float(json_response['indicator']['values'][i]['value'])/1000)
        return prices

    def calculate_invoice_20dha_PVPC(self, token, index):
        """Returns cost of same consumptions on pvpc . Index 0 means current consumption not yet invoiced. Bigger indexes returns costs of every already created invoice"""
        consumptions, start_date, end_date = self.get_invoice_consumption(index)
        costs_per_kwh = self.get_ree_20dha_data(token,start_date,end_date)
        ndays = (end_date - start_date).days+1
        pot = (self.contract()['potMaxima'])/1000
        print("\n\nCOSTE PVPC 2.0DHA\nDESDE: "+start_date.strftime('%d-%m-%Y')+"\nHASTA: "+end_date.strftime('%d-%m-%Y')+"\nDIAS: "+str(ndays)+"\n\n")
        energy_cost = 0
        for i in range(len(consumptions)):
            energy_cost = energy_cost + (consumptions[i]*costs_per_kwh[i])
        power_cost = pot * ((38.043426+3.113)/366) * ndays
        energy_and_power_cost = energy_cost + power_cost
        energy_tax = energy_and_power_cost*0.0511269632
        equipment_cost = ndays * (0.81*12/366)
        total =  energy_and_power_cost + energy_tax + equipment_cost
        total_plus_vat = total * 1.21
        print("Power cost: "+'{0:.2f}'.format(power_cost)+ "€")
        print("Energy cost: "+'{0:.2f}'.format(energy_cost)+ "€")
        print("Electric tax: "+'{0:.2f}'.format(energy_tax)+ "€")
        print("Measure equipments: " +'{0:.2f}'.format(equipment_cost)+ "€")
        print("VAT: " +'{0:.2f}'.format(total*0.21)+ "€")
        return "TOTAL: " + '{0:.2f}'.format(total_plus_vat) + "€"

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
