Pyora
=====

# 1.功能
Python脚本监控Oracle

# 2.安装依赖包
```
cx-Oracle==5.1.2
python-argparse   #`easy_install argparse`  or  `yum install python-argarse` on RHEL/Centos
```

# 3.安装Oracle软件包
安装Oracle客户端软件包，执行如下命令：
```
rpm -ivh oracle-instantclient11.2-basic-11.2.0.3.0-1.x86_64.rpm
rpm -ivh oracle-instantclient11.2-devel-11.2.0.3.0-1.x86_64.rpm
rpm -ivh oracle-instantclient11.2-sqlplus-11.2.0.3.0-1.x86_64.rpm
rpm -ivh cx_Oracle-5.1.2-11g-py26-1.x86_64.rpm    #可以使用pip安装
rpm -ivh python-argparse-1.2.1-2.el6.noarch.rpm
```

Oracle客户端软件包的下载地址如下，读者需要根据不同的Oracle版本进行下载
http://www.oracle.com/technetwork/database/database-technologies/instant-client/downloads/index.html

# 4. 配置环境变量
安装成功后，配置环境变量如下：
```
shell# cat > /etc/profile.d/oracle.sh << EOF
#!/bin/bash
LD_LIBRARY_PATH="/usr/lib/oracle/11.2/client64/lib:${LD_LIBRARY_PATH}"
export LD_LIBRARY_PATH
ORACLE_HOME="/usr/lib/oracle/11.2/client64/lib"
export ORACLE_HOME
EOF
```
某些系统配置后，可能无法立即生效，可以退出ssh账号重新登录，重启zabbix_agentd服务

# 5. 代码配置文件
将代码和配置文件放到相应的目录下：
```
shell# /etc/zabbix/scripts/pyora.py
shell# vim /etc/zabbix/zabbix_agentd.conf.d/oracle.conf
UserParameter=pyora[*],/etc/zabbix/scripts/pyora.py --username $1 --password $2 --address $3 --port $4--database $5 $6 $7 $8 $9
```
配置后，需要重启zabbix_agentd服务
```
shell# systemctl restart zabbix_agentd
```

# 6.配置Oracle账号

配置Oracle的监控账户，账户名称是zabbix，密码为zabbix。
```
shell# su - oracle
shell# sqlplus / as sysdba
SQL> CREATE USER zabbix IDENTIFIED BY zabbix DEFAULT TABLESPACE SYSTEM TEMPORARY TABLESPACE TEMP PROFILE DEFAULT ACCOUNT UNLOCK;  #创建用户zabbix，密码为zabbix
SQL> GRANT CONNECT TO zabbix;
SQL> GRANT RESOURCE TO zabbix;
SQL> ALTER USER zabbix DEFAULT ROLE ALL;
SQL> GRANT SELECT ANY TABLE TO zabbix;
SQL> GRANT CREATE SESSION TO zabbix;
SQL> GRANT SELECT ANY DICTIONARY TO zabbix;
SQL> GRANT UNLIMITED TABLESPACE TO zabbix;
SQL> GRANT SELECT ANY DICTIONARY TO zabbix;
SQL> GRANT SELECT ON V_$SESSION TO zabbix;
SQL> GRANT SELECT ON V_$SYSTEM_EVENT TO zabbix;
SQL> GRANT SELECT ON V_$EVENT_NAME TO zabbix;
SQL> GRANT SELECT ON V_$RECOVERY_FILE_DEST TO zabbix;
```
# 7.测试监控指标数据
接下来，我们使用zabbix_get来测试获取数据。
```
在shell环境中设置变量，此操作在zabbix_server服务器上操作
USERNAME=zabbix
PASSWORD=zabbix
ADDRESS=127.0.0.1
PORT=1521
DATABASE=你的DB名称

shell# zabbix_get -s 127.0.0.1 -k pyora[$USERNAME,$PASSWORD,$ADDRESS,$PORT,$DATABASE,uptime] 
21623423
```


# 8.脚本用法

<pre><code>
» python pyora.py                                                                                                    
usage: pyora.py [-h] [--username USERNAME] [--password PASSWORD]
                [--address ADDRESS] [--database DATABASE]
                
                {activeusercount,bufbusywaits,check_active,check_archive,commits,db_close,db_connect,dbfilesize,dbprllwrite,dbscattread,dbseqread,dbsize,dbsnglwrite,deadlocks,directread,directwrite,dsksortratio,enqueue,freebufwaits,hparsratio,indexffs,lastapplarclog,lastarclog,latchfree,logfilesync,logonscurrent,logprllwrite,logswcompletion,netresv,netroundtrips,netsent,query_lock,query_redologs,query_rollbacks,query_sessions,query_temp,rcachehit,redowrites,rollbacks,show_tablespaces,tablespace,tblrowsscans,tblscans,uptime,version}
                ...
pyora.py: error: too few arguments


# Check Oracle version
0: python pyora.py --username pyora --password secret --address 127.0.0.1 --port 1521 --database DATABASE version
Oracle Database 10g Enterprise Edition Release 10.2.0.4.0 - 64bi

# Check Oracle active user count
0: python pyora.py --username pyora --password secret --address 127.0.0.1 --port 1521 --database DATABASE activeusercount
68

# Show the tablespaces names in a JSON format
0: python pyora.py show_tablespaces
{
	"data":[
	{ "{#TABLESPACE}":"ORASDPM"},
	{ "{#TABLESPACE}":"MDS"},
	{ "{#TABLESPACE}":"SOADEV_MDS"},
	{ "{#TABLESPACE}":"ORABAM"},
	{ "{#TABLESPACE}":"SOAINF"},
	{ "{#TABLESPACE}":"DATA"},
	{ "{#TABLESPACE}":"MGMT_AD4J_TS"},
	{ "{#TABLESPACE}":"MGMT_ECM_DEPOT_TS"},
	{ "{#TABLESPACE}":"MGMT_TABLESPACE"},
	{ "{#TABLESPACE}":"RECOVER"},
	{ "{#TABLESPACE}":"RMAN_CAT"},
	{ "{#TABLESPACE}":"SYSAUX"},
	{ "{#TABLESPACE}":"SYSTEM"},
	{ "{#TABLESPACE}":"TEMP"},
	{ "{#TABLESPACE}":"UNDOTBS"},
	{ "{#TABLESPACE}":"VIRTUALCENTER"},
	]
}

# Show a particular tablespace usage in %
0: python pyora.py --username pyora --password secret --address 127.0.0.1 --port 1521 --database DATABASE tablespace SYSTEM
92.45

</code></pre>

# 9. 环境变量无法生效问题解决 
如用root可以可以获取到数据，而用zabbix_get无法成功获取数据，多数情况下是zabbix用户下无法成功加载Oracle环境变量导致
在pyora.py脚本开始处增加设置环境变量的配置
```
########################################################################################
import os
# 设置环境变量
LD_LIBRARY_PATH=os.environ.get('LD_LIBRARY_PATH’)
os.environ['LD_LIBRARY_PATH']= "/usr/lib/oracle/11.2/client64/lib:"+LD_LIBRARY_PATH
os.environ['ORACLE_HOME']="/usr/lib/oracle/11.2/client64/lib”
########################################################################################
version = 0.2
```
