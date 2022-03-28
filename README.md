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

connection.continous_calc(ree_token)
```

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
