Get-Service | Where-Object { $_.Name -like "*mysql*" -or $_.Name -like "*mariadb*" } | Select-Object Name, Status, StartType

python -c "import mysql.connector; print('mysql-connector-python installed')" 2>$null
python -c "import pymysql; print('pymysql installed')" 2>$null
