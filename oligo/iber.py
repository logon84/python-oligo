from requests import Session
from datetime import datetime
from io import StringIO
from dateutil.relativedelta import relativedelta
from . import omiedata
import calendar
from decimal import Decimal
import aiohttp
import asyncio
import sys
import unidecode
import glob

try:
	# Win32
	from msvcrt import getch
except ImportError:
	# UNIX
	def getch():
		import sys, tty, termios
		fd = sys.stdin.fileno()
		old = termios.tcgetattr(fd)
		try:
			tty.setraw(fd)
			return sys.stdin.read(1)
		finally:
			termios.tcsetattr(fd, termios.TCSADRAIN, old)

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
	__wattmeter_url = __domain + "/consumidores/rest/escenarioNew/obtenerMedicionOnline/24"
	__icp_status_url = __domain + "/consumidores/rest/rearmeICP/consultarEstado"
	__contracts_url = __domain + "/consumidores/rest/cto/listaCtos/"
	__contract_detail_url = __domain + "/consumidores/rest/detalleCto/detalle/"
	__contract_selection_url = __domain + "/consumidores/rest/cto/seleccion/"
	__ps_info_url = __domain + "/consumidores/rest/infoPS/datos/"
	__ps_info_url_2 = __domain + "/consumidores/rest/detalleCto/opcionFE/"
	__power_peak_dates_url = __domain + "/consumidores/rest/consumoNew/obtenerLimitesFechasPotencia/"
	__power_peak_url = __domain + "/consumidores/rest/consumoNew/obtenerPotenciasMaximas/{0}"
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

	__ree_api_url = "https://api.esios.ree.es/indicators/{0}?start_date={1}T00:00:00&end_date={2}T23:00:00"
	__headers_ree = {
		'User-Agent': "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/77.0.3865.90 Chrome/77.0.3865.90 Safari/537.36",
		'accept': "application/json; application/vnd.esios-api-v1+json",
		'content-type': "application/json",
		'Host': "api.esios.ree.es",
		'Cookie': ""
	}
	delay = 0
	day_reference_20td = datetime.strptime('01/06/2021', '%d/%m/%Y')
	days_reference_pot_reduct = [datetime.strptime('15/09/2021', '%d/%m/%Y'),datetime.strptime('01/01/2022', '%d/%m/%Y'),datetime.strptime('31/03/2022', '%d/%m/%Y'),datetime.strptime('31/05/2024', '%d/%m/%Y')]
	

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

	def wattmeter(self):
		"""Returns your current power consumption."""
		self.__check_session()
		response = self.__session.request("GET", self.__wattmeter_url, headers=self.__headers_i_de)
		if response.status_code != 200:
			raise ResponseException
		if not response.text:
			raise NoResponseException
		json_response = response.json()
		return str(json_response['valMagnitud']/1000)+"kw"

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
			#spaguetti.run!!
			if int(line.split(";")[2]) == 25:
				#OCTOBER HOUR FIX
				current_date = datetime.strptime(line.split(";")[1] + " " + "23" + ":00", '%d/%m/%Y %H:%M')
			else:
				current_date = datetime.strptime(line.split(";")[1] + " " + str(int(line.split(";")[2]) - 1) + ":00", '%d/%m/%Y %H:%M')
				if not(current_date == last_date + relativedelta(hours=1)) and not(current_date == last_date):
					#NOT(current hour is consecutive to previous)
					#value missing detected, fill with 0's
					counter = 0
					while current_date > (last_date + relativedelta(hours=1)):
						consumption_kwh.append(0)
						last_date = last_date + relativedelta(hours=1)
						counter = counter + 1
					print("----------------ATENCION: FALTAN ALGUNOS VALORES DE CONSUMO EN ESTA SIMULACION-----------------(" + str(counter) + ")")
			consumption_kwh.append(float(line.split(";")[3].replace(',','.')))
			last_date = current_date
			if current_date.month == 3 and current_date.day in range (25,32) and current_date.isoweekday() == 7 and current_date.hour == 22:
				#MARCH HOUR FIX
				last_date = last_date + relativedelta(hours=1)
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
		real_reads = []
		csvdata = StringIO(response.text)
		next(csvdata)
		for line in csvdata:
			consumption_kwh.append(float(line.split(";")[3].replace(',','.')))
			real_reads.append(int("R" in line.split(";")[4]))
		return start_date, end_date, consumption_kwh, real_reads

	def get_consumption(self,index,local=0):
		"""Returns consumptions. Index 0 means current consumption not yet invoiced. Bigger indexes returns consumption by every already created invoice"""
		self.__check_session()
		real_reads = []
		if local == 0:
			if index == 0: #get current cost
				last_invoice = self.get_invoice(0) #get last invoice
				start_date = datetime.strptime(last_invoice['fechaHasta'], '%d/%m/%Y') + relativedelta(days=1) #get last day used in the last invoice to use next day as starting day for current cost
				end_date = self.get_last_day_with_recorded_data()
				if end_date <= datetime.strptime(last_invoice['fechaHasta'], '%d/%m/%Y'):
				#no hourly consumption since last invoice, activate delay 1 to jump to the first billing data
					self.delay = 1
				else:
					start_date, end_date, consumption_kwh = self.get_hourly_consumption(start_date,end_date)
					real_reads= [1 for i in range(len(consumption_kwh))]
					type_consumptions = str(index)
			if (index + self.delay) > 0:
				index = index + self.delay
				invoice = self.get_invoice(index-1)
				start_date = datetime.strptime(invoice['fechaDesde'], '%d/%m/%Y')
				end_date = datetime.strptime(invoice['fechaHasta'], '%d/%m/%Y')
				start_date, end_date, consumption_kwh, real_reads = self.get_hourly_consumption_by_invoice(invoice['numero'],start_date,end_date)
				type_consumptions = str(index)
		else:
			f = open('C:\\Users\\TESEO-DEMO\\Downloads\\peik\\' + str(index+1) + '.csv', "r")
			consumption_kwh = []
			real_reads = []
			csvdata = StringIO(f.read())
			next(csvdata)
			for line in csvdata:
				consumption_kwh.append(float(line.split(";")[3].replace(',','.')))
				real_reads.append(int("R" in line.split(";")[4]))
			f.close()
			start_date = datetime.strptime("01/"+ str(index + 1).zfill(2) +"/2022", '%d/%m/%Y')
			end_date = datetime.strptime("01/"+ str(index + 2).zfill(2) +"/2022", '%d/%m/%Y') - relativedelta(days=1)
			type_consumptions = str(index+1)
			
		return start_date, end_date, consumption_kwh, real_reads, type_consumptions

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
		IDenergy20TD = '1001'
		IDhourtype = '1002'
		ID20TDzone = 'Península'
		
		energy20TD = []
		period_mask = []
		
		self.__headers_ree['x-api-key'] = token

		if start_date >= self.day_reference_20td:
		#2.0TD calc
			url_0 = self.__ree_api_url.format(IDenergy20TD,start_date.strftime('%Y-%m-%d'),end_date.strftime('%Y-%m-%d'))
			url_1 = self.__ree_api_url.format(IDhourtype,start_date.strftime('%Y-%m-%d'),end_date.strftime('%Y-%m-%d'))
			parallel_http_get = [self.get(url_0, self.__headers_ree),self.get(url_1, self.__headers_ree)]
			loop = asyncio.get_event_loop()
			results = loop.run_until_complete(asyncio.gather(*parallel_http_get))
			max_data_length = max(len(results[0]['indicator']['values']),len(results[1]['indicator']['values']))
			if len(results[0]['indicator']['values']) == max_data_length:
				data_ref = 0
			elif len(results[1]['indicator']['values']) == max_data_length:
				data_ref = 1
			else:
				data_ref = 2
			tmp_dates = []
			k = 0
			move_0 = 0
			move_1 = 0
			for i in range(len(results[data_ref]['indicator']['values'])):
				if unidecode.unidecode(results[data_ref]['indicator']['values'][i]['geo_name']) == unidecode.unidecode(ID20TDzone):
					tmp_dates.append(results[data_ref]['indicator']['values'][i]['datetime'])
			for i in range(len(results[data_ref]['indicator']['values'])):
				try:
					if unidecode.unidecode(results[0]['indicator']['values'][i - move_0]['geo_name']) == unidecode.unidecode(ID20TDzone):
						if results[0]['indicator']['values'][i - move_0]['datetime'] != tmp_dates[k]:
							energy20TD.append(0)
							move_0 = move_0 + 1
						else:
							energy20TD.append(self.roundup(float(results[0]['indicator']['values'][i - move_0]['value'])/1000, 6))
				except:
					pass
				try:
					if unidecode.unidecode(results[1]['indicator']['values'][i - move_1]['geo_name']) == unidecode.unidecode(ID20TDzone):
						if results[1]['indicator']['values'][i - move_1]['datetime'] != tmp_dates[k]:
							period_mask.append(0)
							move_1 = move_1 + 1
						else:
							period_mask.append(int(results[1]['indicator']['values'][i - move_1]['value']))
				except:
					pass
				if len(energy20TD) > k and len(period_mask) > k:
					k = k + 1
		return [0] * len(energy20TD), energy20TD, period_mask
		
	def roundup(self, num, ndecimals):
		return float(round(Decimal(str(num)),ndecimals))

	def day_leap_splitter(self, start_date, end_date):
		days_365 = 0
		days_366 = 0
		if calendar.isleap(start_date.year) and calendar.isleap(end_date.year):
			days_366 = (end_date - start_date).days+1
		elif not calendar.isleap(start_date.year) and not calendar.isleap(end_date.year):
			days_365 = (end_date - start_date).days+1
		elif not calendar.isleap(start_date.year) and calendar.isleap(end_date.year):
			days_365 = 366 - start_date.timetuple().tm_yday
			days_366 = (end_date - start_date).days+1 - days_365
		elif calendar.isleap(start_date.year) and not calendar.isleap(end_date.year):
			days_366 = 367 - start_date.timetuple().tm_yday
			days_365 = (end_date - start_date).days+1 - days_366
		return days_365, days_366
	
	def tax_toll_calc(self, start_date, end_date, pot):
		#pot_toll = [low, peak]
		#pot_tax = [low, peak]
		
		pot_toll = []
		pot_tax = []
		energy_toll = []
		energy_tax = []

		#2021:
		pot_toll.append([0.961130, 23.469833])
		pot_tax.append([0.463229, 7.202827])
		#2021_2:
		pot_toll.append([0.961130, 23.469833])
		pot_tax.append([0.018107, 0.281544])
		#2022:
		pot_toll.append([0.938890, 22.988256])
		pot_tax.append([0.319666, 4.970533])
		#2022_2:
		pot_toll.append([0.938890, 22.988256])
		pot_tax.append([0.204242, 3.175787])
		#2024_2:
		pot_toll.append([0.776564, 22.401746])
		pot_tax.append([0.192288, 2.989915])
		
		index_start = len(self.days_reference_pot_reduct)
		index_end = len(self.days_reference_pot_reduct)
		for date in self.days_reference_pot_reduct:
			if date > start_date:
				index_start = self.days_reference_pot_reduct.index(date)
				break
		for date in self.days_reference_pot_reduct:
			if date > end_date:
				index_end = self.days_reference_pot_reduct.index(date)
				break
		if index_start == index_end:
			days_1 = (end_date - start_date).days + 1
			days_2 = 0
		else:
			days_1 = (self.days_reference_pot_reduct[index_start] - start_date).days
			days_2 = (end_date - self.days_reference_pot_reduct[index_start]).days + 1
		
		power_toll_tax_cost_peak = self.roundup(pot * days_1 * pot_toll[index_start][1]/(365 + int(calendar.isleap(start_date.year))), 2) + self.roundup(pot * days_1 * pot_tax[index_start][1]/(365 + int(calendar.isleap(start_date.year))), 2) + self.roundup(pot * days_2 * pot_toll[index_end][1]/(365 + int(calendar.isleap(end_date.year))), 2) + self.roundup(pot * days_2 * pot_tax[index_end][1]/(365 + int(calendar.isleap(end_date.year))), 2)
		power_toll_tax_cost_low = self.roundup(pot * days_1 * pot_toll[index_start][0]/(365 + int(calendar.isleap(start_date.year))), 2) + self.roundup(pot * days_1 * pot_tax[index_start][0]/(365 + int(calendar.isleap(start_date.year))), 2) + self.roundup(pot * days_2 * pot_toll[index_end][0]/(365 + int(calendar.isleap(end_date.year))), 2) + self.roundup(pot * days_2 * pot_tax[index_end][0]/(365 + int(calendar.isleap(end_date.year))), 2)
		
		return power_toll_tax_cost_peak, power_toll_tax_cost_low

					
	def calculate_invoice_PVPC(self, token, index, simulate_pot):
		"""Returns cost of same consumptions on pvpc . Index 0 means current consumption not yet invoiced. Bigger indexes returns costs of every already created invoice"""
		start_date, end_date, consumption_kwh, real_reads, type_consumptions = self.get_consumption(index)
		energy_fixed_price, energy_var_price, period_mask = self.get_ree_data(token,start_date,end_date)
		days_365, days_366 = self.day_leap_splitter(start_date,end_date)

		p1 = []
		p2 = []
		p3 = []
		energy_real_read = 0
		for i in range(len(consumption_kwh)):
			p1.append(int(period_mask[i] == 1) * consumption_kwh[i])
			p2.append(int(period_mask[i] == 2) * consumption_kwh[i])
			p3.append(int(period_mask[i] == 3) * consumption_kwh[i])
			energy_real_read = energy_real_read + real_reads[i]*consumption_kwh[i]

		PERC_REAL_KWH = self.roundup(energy_real_read*100/sum(consumption_kwh),2)
		PERC_ESTIM_KWH = self.roundup((sum(consumption_kwh)-energy_real_read)*100/sum(consumption_kwh),2)
		PERC_REAL_H = self.roundup(sum(real_reads)*100/len(real_reads),2)
		PERC_ESTIM_H = self.roundup((len(real_reads)-sum(real_reads))*100/len(real_reads),2)
		try:
			AVERAGE_KWH_H_REAL = self.roundup(energy_real_read/sum(real_reads),2)
		except:
			AVERAGE_KWH_H_REAL = 0
		try:
			AVERAGE_KWH_H_ESTIM = self.roundup((sum(consumption_kwh)-energy_real_read)/(len(real_reads)-sum(real_reads)),2)
		except:
			 AVERAGE_KWH_H_ESTIM = 0

		if simulate_pot>0:
			pot = simulate_pot
		else:
			pot = (self.contract()['potMaxima'])/1000

		avg_price_energy_fixed_price = 0
		avg_price_energy_var_price_peak = 0
		avg_price_energy_var_price_low = 0
		avg_price_energy_var_price_superlow = 0

		for i in range(len(consumption_kwh)):
			avg_price_energy_fixed_price = avg_price_energy_fixed_price + self.roundup((consumption_kwh[i]*energy_fixed_price[i])/sum(consumption_kwh),6)
			avg_price_energy_var_price_peak = avg_price_energy_var_price_peak + self.roundup((p1[i]*energy_var_price[i])/sum(p1),6)
			avg_price_energy_var_price_low = avg_price_energy_var_price_low + self.roundup((p2[i]*energy_var_price[i])/sum(p2),6)
			try:
				avg_price_energy_var_price_superlow = avg_price_energy_var_price_superlow + self.roundup((p3[i]*energy_var_price[i])/sum(p3),6)
			except:
				avg_price_energy_var_price_superlow = 0
				
		if start_date >= self.day_reference_20td:
		#2.0TD CASE
			vat_value = omiedata.get_iva(end_date.year,end_date.month)
			et_value = 0.0511269632
			power_margin = self.roundup(pot * days_365 * 3.113/365, 2) + self.roundup(pot * days_366 * 3.113/366, 2)
			power_toll_tax_cost_peak, power_toll_tax_cost_low = self.tax_toll_calc(start_date, end_date, pot)
			power_cost20TD = power_margin + power_toll_tax_cost_peak + power_toll_tax_cost_low
			energy_cost_20TD_peak = self.roundup(avg_price_energy_var_price_peak*(self.roundup(sum(p1),2)),2)
			energy_cost_20TD_low = self.roundup(avg_price_energy_var_price_low*(self.roundup(sum(p2),2)),2)
			energy_cost_20TD_superlow = self.roundup(avg_price_energy_var_price_superlow*(self.roundup(sum(p3),2)),2)
			energy_cost_20TD = energy_cost_20TD_peak + energy_cost_20TD_low + energy_cost_20TD_superlow
			energy_and_power_cost_20TD = energy_cost_20TD + power_cost20TD
			social_bonus_20TD = 5.394483 * 2.299047 * days_365/365 + 5.394483 * 2.299047 * days_366/366
			energy_tax_20TD = self.roundup((energy_and_power_cost_20TD + social_bonus_20TD)*et_value,2)
			equipment_cost = self.roundup(days_365 * (0.81*12/365) + days_366 * (0.81*12/366),2)
			total_20TD =  energy_and_power_cost_20TD + energy_tax_20TD + equipment_cost + social_bonus_20TD
			VAT_20TD = self.roundup(total_20TD*vat_value,2)
			total_plus_vat_20TD = self.roundup(total_20TD + VAT_20TD,2)
			
			
			#####################_____OTHER_COMPARISON (fill values)_____###############################
			name_other = "ENERGIA NUFRI"
			power_cost_other = self.roundup(pot * days_365 * 0.079977, 2) + self.roundup(pot * days_365 * 0.033339, 2)
			power_cost_other = power_cost_other + self.roundup(pot * days_366 * 0.079977, 2) + self.roundup(pot * days_366 * 0.033339, 2)
			energy_cost_other = self.roundup(self.roundup(sum(p1),0) * 0.162850 + self.roundup(sum(p2),0) * 0.106026 + self.roundup(sum(p3),0) * 0.076359,2)
			social_bonus_other = 0.006364 * (days_365 + days_366)
			
			energy_and_power_cost_other = energy_cost_other + power_cost_other
			energy_tax_other = self.roundup((energy_and_power_cost_other + social_bonus_other)*et_value,2)
			equipment_cost_other = self.roundup(days_365 * (0.81*12/365) + days_366 * (0.81*12/366),2)
			total_other = energy_and_power_cost_other + energy_tax_other + equipment_cost_other + social_bonus_other
			VAT_other = self.roundup(total_other*vat_value,2)
			total_plus_vat_other = self.roundup(total_other + VAT_other,2)
			
			

			name_other2 = "NATURGY TARIFA COMPROMISO"
			power_cost_other2 = self.roundup(pot * days_365 * 0.047561, 2) + self.roundup(pot * days_365 * 0.054542, 2)
			power_cost_other2 = power_cost_other2 + self.roundup(pot * days_366 * 0.047561, 2) + self.roundup(pot * days_366 * 0.054542, 2)
			energy_cost_other2 = self.roundup(self.roundup(sum(p1),0) * 0.135334 + self.roundup(sum(p2),0) * 0.135334 + self.roundup(sum(p3),0) * 0.135334,2)
			energy_and_power_cost_other2 = energy_cost_other2 + power_cost_other2

			social_bonus_other2 = 0.038455 * (days_365 + days_366)
			energy_tax_other2 = self.roundup((energy_and_power_cost_other2 + social_bonus_other2)*et_value,2)

			equipment_cost_other2 = self.roundup(days_365 * round((0.81*12/365),3) + days_366 * round((0.81*12/366),3),2)
			total_other2 = energy_and_power_cost_other2 + energy_tax_other2 + equipment_cost_other2 + social_bonus_other2
			VAT_other2 = self.roundup(total_other2*vat_value,2)
			total_plus_vat_other2 = self.roundup(total_other2 + VAT_other2,2)
			############################################################################################
			
			
			header = [type_consumptions, start_date.strftime('%d-%m-%Y'), end_date.strftime('%d-%m-%Y'), str(days_365 + days_366), str(pot), sum(p1), sum(p2), sum(p3), PERC_REAL_H, PERC_REAL_KWH, AVERAGE_KWH_H_REAL, PERC_ESTIM_H, PERC_ESTIM_KWH, AVERAGE_KWH_H_ESTIM]
			c1 = ["PVPC 2.0TD", power_cost20TD, energy_cost_20TD, energy_tax_20TD, social_bonus_20TD, equipment_cost, vat_value, VAT_20TD, total_plus_vat_20TD]
			c2 = [name_other, power_cost_other, energy_cost_other, energy_tax_other, social_bonus_other, equipment_cost_other, vat_value, VAT_other, total_plus_vat_other]
			c3 = [name_other2, power_cost_other2, energy_cost_other2, energy_tax_other2, social_bonus_other2, equipment_cost_other2, vat_value, VAT_other2, total_plus_vat_other2]

		return [header, c1, c2, c3]

	def print_comparison(self, header, company1, company2, company3):
		#header = [type_consumptions, start_date, end_date, ndays, pot, p1, p2, p3, PERC_REAL_H, PERC_REAL_KWH, AVERAGE_KWH_H_REAL, PERC_ESTIM_H, PERC_ESTIM_KWH, AVERAGE_KWH_H_ESTIM]
		#companyX = [name, pot_cost, energy_cost, elec_tax, social_bonus, equip_cost, vat, total]
		if header[0] == "0":
			print("[CONSUMO ACTUAL]")
		else:
			print("[FACTURA " + header[0] + "]")
		print("\nPERIODO: {0} - {1}\nDIAS: {2}\nPOTENCIA: {3}KW\nCONSUMOS: TOTAL = {4:.2f}kwh || PUNTA_P1 = {5:.2f}kwh VALLE_P2 = {6:.2f}kwh SUPERVALLE_P3 = {7:.2f}kwh\nLECTURA REAL: {8:.2f}%/h  {9:.2f}%/kwh  {10:.2f}kwh/h\nLECTURA ESTIMADA: {11:.2f}%/h  {12:.2f}%/kwh  {13:.2f}kwh/h \n".format(header[1],header[2],header[3],header[4],header[5]+header[6]+header[7],header[5],header[6],header[7],header[8],header[9],header[10],header[11],header[12], header[13]))
		print('{:<30} {:<30} {:<30}'.format(company1[0] + " precio",company2[0] + " precio", company3[0] + " precio"))
		print("-----------------------------------------------------------------------------------------")
		print('{:<30} {:<30} {:<30}'.format("Coste potencia: {0:.2f}€".format(company1[1]), "Coste potencia: {0:.2f}€".format(company2[1]), "Coste potencia: {0:.2f}€".format(company3[1])))
		print('{:<30} {:<30} {:<30}'.format("Coste energía: {0:.2f}€".format(company1[2]), "Coste energía: {0:.2f}€".format(company2[2]), "Coste energía: {0:.2f}€".format(company3[2])))
		print('{:<30} {:<30} {:<30}'.format("Impuesto eléctrico: {0:.2f}€".format(company1[3]), "Impuesto eléctrico: {0:.2f}€".format(company2[3]), "Impuesto eléctrico: {0:.2f}€".format(company3[3])))
		print('{:<30} {:<30} {:<30}'.format("Bono social: {0:.2f}€".format(company1[4]), "Bono social: {0:.2f}€".format(company2[4]), "Bono social: {0:.2f}€".format(company3[4])))
		print('{:<30} {:<30} {:<30}'.format("Equipos de medida: {0:.2f}€".format(company1[5]), "Equipos de medida: {0:.2f}€".format(company2[5]), "Equipos de medida: {0:.2f}€".format(company3[5])))
		print('{:<30} {:<30} {:<30}'.format("IVA ({0}%): {1:.2f}€".format(100*company1[6],company1[7]), "IVA ({0}%): {1:.2f}€".format(100*company2[6],company2[7]), "IVA ({0}%): {1:.2f}€".format(100*company3[6],company3[7])))
		print('{:<30} {:<30} {:<30}'.format("TOTAL: {0:.2f}€".format(company1[8]), "TOTAL: {0:.2f}€".format(company2[8]), "TOTAL: {0:.2f}€\n\n".format(company3[8])))
		return "Done"

	def get_PS_info(self):
		self.__check_session()
		response = self.__session.request("GET", self.__ps_info_url, headers=self.__headers_i_de)
		if response.status_code != 200:
			raise ResponseException
		if not response.text:
			raise NoResponseException
		json_response = response.json()
		
		self.__check_session()
		response2 = self.__session.request("GET", self.__ps_info_url_2, headers=self.__headers_i_de)
		if response2.status_code != 200:
			raise ResponseException
		if not response2.text:
			raise NoResponseException
		json_response2 = response2.json()

		print("\n[INFORMACIÓN DEL CONTRATO]" + "\n\n\t\tComercializadora: " + json_response["des_EPS_COM_VIG"] + "\n\t\tDirección suministro: " + str(json_response["ps_DIREC"]) + "\n\t\tTarifa: " + json_response2["detalle"]["desTarifIbdla"] + "\n\t\tPotencia: " + json_response["val_POT_P1"] + "W" + "\n\t\tTensión: " + json_response["val_TENSION_PTO_SUMIN"] + "V\n")
		return

	def get_power_peaks_max_date(self):
		self.__check_session()
		response = self.__session.request("GET", self.__power_peak_dates_url, headers=self.__headers_i_de)
		if response.status_code != 200:
			raise ResponseException
		if not response.text:
			raise NoResponseException
		json_response = response.json()
		max_date = datetime.strptime(json_response['fecMax'], '%d-%m-%Y%H:%M:%S')
		return max_date

	def get_power_peaks(self,year):
		self.__check_session()
		max_date = self.get_power_peaks_max_date()
		end_date = datetime.strptime("31-12-"+year+"23:59:59", '%d-%m-%Y%H:%M:%S')
		if end_date > max_date:
			end_date = max_date
		response = self.__session.request("GET", self.__power_peak_url.format(end_date.strftime('%d-%m-%Y%H:%M:%S')), headers=self.__headers_i_de)
		if response.status_code != 200:
			raise ResponseException
		if not response.text:
			raise NoResponseException
		json_response = response.json()
		monthly_max_power = ["NO_DATA", "NO_DATA", "NO_DATA", "NO_DATA", "NO_DATA", "NO_DATA", "NO_DATA", "NO_DATA", "NO_DATA", "NO_DATA", "NO_DATA", "NO_DATA"]
		print("[POTENCIAS MAXIMAS DEL AÑO " + end_date.strftime('%Y') + "]\n")
		try:
			for i in range(len(json_response["potMaxMens"])):
				  monthly_max_power[int(json_response["potMaxMens"][i]["name"][3:5])-1] = str(json_response["potMaxMens"][i]["y"]) + "w"
			for i in range(len(monthly_max_power)):
				  print("\t\t{:02d}".format(i+1) + "/"+end_date.strftime('%Y') + ": " + monthly_max_power[i])
			print("\n")
		except:
			print("No power data available\n\n")			   
		return

	def continuous_calc(self,ree_token):
		simulate_pot = input("Introduza la potencia con la que desea simular el cálculo, o pulse ENTER si desea simular con la potencia actualmente contratada:")
		if len(simulate_pot) == 0:
			simulate_pot = 0
		else:
			simulate_pot = float(simulate_pot)
		totals = [0,0,0]
		for i in range(0,27,1):
			try:
				header, c1, c2, c3 = self.calculate_invoice_PVPC(ree_token,i,simulate_pot)
				self.print_comparison(header, c1, c2, c3)
				totals[0] = totals[0] + c1[8]
				totals[1] = totals[1] + c2[8]
				totals[2] = totals[2] + c3[8]
				min_cost = min(totals)
				if totals.index(min_cost) == 0:
					print("ACUMULADO: La tarifa (1) habría supuesto un ahorro de {0:.2f}€ frente a la tarifa (2) y de {1:.2f}€ frente a la tarifa (3). [{2:.2f}€, {3:.2f}€, {4:.2f}€]".format(totals[1]-totals[0],totals[2]-totals[0], totals[0], totals[1], totals[2]))
				elif totals.index(min_cost) == 1:
					print("ACUMULADO: La tarifa (2) habría supuesto un ahorro de {0:.2f}€ frente a la tarifa (1) y de {1:.2f}€ frente a la tarifa (3). [{2:.2f}€, {3:.2f}€, {4:.2f}€]".format(totals[0]-totals[1],totals[2]-totals[1], totals[0], totals[1], totals[2]))
				elif totals.index(min_cost) == 2:
					print("ACUMULADO: La tarifa (3) habría supuesto un ahorro de {0:.2f}€ frente a la tarifa (1) y de {1:.2f}€ frente a la tarifa (2). [{2:.2f}€, {3:.2f}€, {4:.2f}€]".format(totals[0]-totals[2],totals[1]-totals[2], totals[0], totals[1], totals[2]))
				print("\n##########  PULSE CUALQUIER TECLA PARA CONTINUAR O ESPACIO PARA ABANDONAR  ###########", end="")
				input_char = getch()
				print("\n")
				if input_char == " ".encode() or input_char == " ":
					break
			except:
				continue
		return
