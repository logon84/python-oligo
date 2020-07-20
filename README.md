# python-oligo

## [ES] Cliente Python (NO OFICIAL) para i-DE (Iberdrola distribución).
### Instalación:

~~pip install oligo~~

### Ejemplos:
#### Calcular factura en PVPC con los consumos del contador:

```python
from oligo import Iber

connection = Iber()
connection.login("user", "password")

x = connection.calculate_invoice_PVPC(ree_token,i)
print(x)
```
Donde 'ree_token' es el token solicitado a Red Electrica española para la consulta de precios de electricidad e 'i' es:  
0 para el calculo de la factura del consumo actual aun no facturado en una hipotética comercializadora PVPC.  
1 para el calculo de la factura en una hipotética comercializadora PVPC con los consumos que sirvieron de base en la última factura de electricidad.  
2 para el calculo de la factura en una hipotética comercializadora PVPC con los consumos que sirvieron de base en la penúltima factura de electricidad.  
etc...

#### Consultar consumo actual:

```python
from oligo import Iber

connection = Iber()
connection.login("user", "password")

watt = connection.watthourmeter()
print(watt)
```
#### Consultar estado ICP interno:

```python
from oligo import Iber
connection = Iber()
connection.login("user", "password")
status = connection.icpstatus()
print(status)
```
## [EN] Python client (UNOFFICIAL) for i-DE (Iberdrola distribución).
### Install:

```
pip install oligo
```
### Example:
#### Obtain current consumption:

```python
from oligo import Iber

connection = Iber()
connection.login("user", "password")

watt = connection.watthourmeter()
print(watt)
```
#### Get ICP status:

```python
from oligo import Iber
connection = Iber()
connection.login("user", "password")
status = connection.icpstatus()
print(status)
```
