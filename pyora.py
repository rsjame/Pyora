#!/usr/bin/env python
# coding: utf-8
"""
    Author: Danilo F. Chilene
    Email:    bicofino@gmail.com
"""
########################################################################################
# 设置环境变量
'''
import os
LD_LIBRARY_PATH=os.environ.get('LD_LIBRARY_PATH’)
os.environ['LD_LIBRARY_PATH']= "/usr/lib/oracle/11.2/client64/lib:"+LD_LIBRARY_PATH
os.environ['ORACLE_HOME']="/usr/lib/oracle/11.2/client64/lib”
'''
########################################################################################

version = 0.2
import argparse,cx_Oracle
import inspect
import re
import ConfigParser
import platform
import json

def bytes2human(n):
  '''
  http://code.activestate.com/recipes/578019
  >>> bytes2human(10000)
  '9.8K'
  >>> bytes2human(100001221)
  '95.4M'
  '''
  symbols = ('K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y')
  prefix = {}
  for i, s in enumerate(symbols):
    prefix[s] = 1 << (i+1)*10
  for s in reversed(symbols):
    if n >= prefix[s]:
      value = float(n) / prefix[s]
      return '%.1f%s' % (value, s)
  return '%sB' % n

class Checks(object):

    def rman_check_status(self):
        sql="select ' DB NAME->'||DB_NAME||'- ROW TYPE->'||ROW_TYPE||'- START TIME->'||to_char(start_time, 'Dy DD-Mon-YYYY HH24:MI:SS') ||'- END TIME->'||to_char(end_time, 'Dy DD-Mon-YYYY HH24:MI:SS')||'- MBYTES PROCESSED->'||MBYTES_PROCESSED||'- OBJECT TYPE->'||OBJECT_TYPE||'- STATUS->'||STATUS||'- OUTPUT DEVICE->'||OUTPUT_DEVICE_TYPE||'- INPUT MB->'||INPUT_BYTES/1048576||'- OUT MB'||OUTPUT_BYTES/1048576 \
            FROM   rc_rman_status \
            WHERE  start_time > SYSDATE - 1 \
            AND ( STATUS like '%FAILED%' \
            OR  STATUS like '%ERROR%') \
            ORDER  BY END_TIME"
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            print i[0]

    def users_locked(self):
        sql="SELECT username||' '|| lock_date ||' '|| account_status FROM dba_users where ACCOUNT_STATUS like 'EXPIRED(GRACE)' or ACCOUNT_STATUS like 'LOCKED(TIMED)'"
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            print i[0]

    def audit(self):
        sql='''select username "username", \
            to_char(timestamp,'DD-MON-YYYY HH24:MI:SS') "time_stamp", \
            action_name "statement", \
            os_username "os_username", \
            userhost "userhost", \
            returncode||decode(returncode,'1004','-Wrong Connection','1005','-NULL Password','1017','-Wrong Password','1045','-Insufficient Priviledge','0','-Login Accepted','--') "returncode" \
            from sys.dba_audit_session \
            where (sysdate - timestamp)*24 < 1 and returncode <> 0 \
            order by timestamp'''
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            print i[0]

    def pga_aggregate_target(self):
        sql="select to_char(decode( unit,'bytes', value/1024/1024, value),'999999999.9') value from V$PGASTAT where name in 'aggregate PGA target parameter'"
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            print i[0]

    def pga(self):
        sql="select to_char(decode( unit,'bytes', value/1024/1024, value),'999999999.9') value from V$PGASTAT where name in 'total PGA inuse'"
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            print i[0]

    def phio_datafile_reads(self):
        sql="select to_char(sum(decode(name,'physical reads direct',value,0))) FROM V$SYSSTAT where name ='physical reads direct'"
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            print i[0]

    def phio_datafile_writes(self):
        sql="select to_char(sum(decode(name,'physical writes direct',value,0))) FROM V$SYSSTAT where name ='physical writes direct'"
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            print i[0]

    def phio_redo_writes(self):
        sql="select to_char(sum(decode(name,'redo writes',value,0))) FROM V$SYSSTAT where name ='redo writes'"
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            print i[0]

    def pinhitratio_body(self):
        sql="select pins/(pins+reloads)*100 \"pin_hit ratio\" FROM v$librarycache where namespace ='BODY'"
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            print i[0]

    def pinhitratio_sqlarea(self):
        sql="select pins/(pins+reloads)*100 \"pin_hit ratio\" FROM v$librarycache where namespace ='SQL AREA'"
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            print i[0]
   
    def pinhitratio_table_proc(self):
        sql="select pins/(pins+reloads)*100 \"pin_hit ratio\" FROM v$librarycache where namespace ='TABLE/PROCEDURE'"
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            print i[0]
 
    def pinhitratio_trigger(self):
        sql="select pins/(pins+reloads)*100 \"pin_hit ratio\" FROM v$librarycache where namespace ='TRIGGER'"
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            print i[0]

    def pool_dict_cache(self):
        sql="SELECT TO_CHAR(ROUND(SUM(decode(pool,'shared pool',decode(name,'dictionary cache',(bytes)/(1024*1024),0),0)),2)) pool_dict_cache FROM V$SGASTAT"
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            print i[0]

    def pool_free_mem(self):
        sql="SELECT TO_CHAR(ROUND(SUM(decode(pool,'shared pool',decode(name,'free memory',(bytes)/(1024*1024),0),0)),2)) pool_free_mem FROM V$SGASTAT"
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            print i[0]

    def pool_lib_cache(self):
        sql="SELECT TO_CHAR(ROUND(SUM(decode(pool,'shared pool',decode(name,'library cache',(bytes)/(1024*1024),0),0)),2)) pool_lib_cache FROM V$SGASTAT"
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            print i[0]

    def pool_misc(self):
        sql="SELECT TO_CHAR(ROUND(SUM(decode(pool,'shared pool',decode(name,'library cache',0,'dictionary cache',0,'free memory',0,'sql area', 0,(bytes)/(1024*1024)),0)),2)) pool_misc FROM V$SGASTAT"
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            print i[0]

    def pool_sql_area(self):
        sql="SELECT TO_CHAR(ROUND(SUM(decode(pool,'shared pool',decode(name,'sql area',(bytes)/(1024*1024),0),0)),2)) pool_sql_area FROM V$SGASTAT"
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            print i[0]

    def procnum(self):
        sql='''select count(*) "procnum" from v$process'''
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            print i[0]

    def pinhitratio_table_proc(self):
        sql="select pins/(pins+reloads)*100 \"pin_hit ratio\" FROM v$librarycache where namespace ='TABLE/PROCEDURE'"
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            print i[0]

    def maxprocs(self):
        sql="select value \"maxprocs\" from v$parameter where name ='processes'"
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            print i[0]

    def maxsession(self):
        sql="select value \"maxsess\" from v$parameter where name ='sessions'"
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            print i[0]

    def miss_latch(self):
        sql="SELECT SUM(misses) FROM V$LATCH"
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            print i[0]

    def session_active(self):
        sql="select count(*) from v$session where TYPE!='BACKGROUND' and status='ACTIVE'"
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            print i[0]

    def session_inactive(self):
        sql="select SUM(Decode(Type, 'BACKGROUND', 0, Decode(Status, 'ACTIVE', 0, 1))) FROM V$SESSION"
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            print i[0]

    def session(self):
        sql="select count(*) from v$session"
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            print i[0]

    def session_system(self):
        sql="select SUM(Decode(Type, 'BACKGROUND', 1, 0)) system_sessions FROM V$SESSION"
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            print i[0]

    def sga_buffer_cache(self):
        sql="SELECT to_char(ROUND(SUM(decode(pool,NULL,decode(name,'db_block_buffers',(bytes)/(1024*1024),'buffer_cache',(bytes)/(1024*1024),0),0)),2)) sga_bufcache FROM V$SGASTAT"
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            print i[0]

    def sga_fixed(self):
        sql="SELECT TO_CHAR(ROUND(SUM(decode(pool,NULL,decode(name,'fixed_sga',(bytes)/(1024*1024),0),0)),2)) sga_fixed FROM V$SGASTAT"
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            print i[0]

    def sga_java_pool(self):
        sql="SELECT to_char(ROUND(SUM(decode(pool,'java pool',(bytes)/(1024*1024),0)),2)) sga_jpool FROM V$SGASTAT"
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            print i[0]

    def sga_large_pool(self):
        sql="SELECT to_char(ROUND(SUM(decode(pool,'large pool',(bytes)/(1024*1024),0)),2)) sga_lpool FROM V$SGASTAT"
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            print i[0]

    def sga_log_buffer(self):
        sql="SELECT TO_CHAR(ROUND(SUM(decode(pool,NULL,decode(name,'log_buffer',(bytes)/(1024*1024),0),0)),2)) sga_lbuffer FROM V$SGASTAT"
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            print i[0]

    def sga_shared_pool(self):
        sql="SELECT TO_CHAR(ROUND(SUM(decode(pool,'shared pool',decode(name,'library cache',0,'dictionary cache',0,'free memory',0,'sql area',0,(bytes)/(1024*1024)),0)),2)) pool_misc FROM V$SGASTAT"
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            print i[0]

    def userconn(self):
        sql="select count(username) from v$session where username is not null \
             waits_controfileio.Query=SELECT to_char(sum(decode(event,'control file sequential read', \
             total_waits, 'control file single write', total_waits, 'control file parallel write',total_waits,0))) \
             ControlFileIO FROM V$system_event WHERE 1=1 AND event not in ( 'SQL*Net message from client', 'SQL*Net \
             more data from client','pmon timer', 'rdbms ipc message', 'rdbms ipc reply', 'smon timer')"
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            print i[0]

    def waits_controfileio(self):
        sql="SELECT to_char(sum(decode(event,'control file sequential read', total_waits, 'control file single write', total_waits, \
            'control file parallel write',total_waits,0))) ControlFileIO FROM V$system_event WHERE 1=1 AND event not in ( 'SQL*Net message\
             from client', 'SQL*Net more data from client','pmon timer', 'rdbms ipc message', 'rdbms ipc reply', 'smon timer')" 
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            print i[0]

    def waits_directpath_read(self):
        sql="SELECT to_char(sum(decode(event,'direct path read',total_waits,0))) DirectPathRead FROM V$system_event WHERE 1=1 AND event not in (   'SQL*Net message from ', 'SQL*Net more data from client','pmon timer', 'rdbms ipc message', 'rdbms ipc reply', 'smon timer') "
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            print i[0]

    def waits_file_io(self):
        sql="SELECT to_char(sum(decode(event,'file identify',total_waits, 'file open',total_waits,0))) FileIO FROM V$system_event WHERE 1=1 AND event not in (   'SQL*Net message from client',   'SQL*Net more data from client', 'pmon timer', 'rdbms ipc message', 'rdbms ipc reply', 'smon timer') "
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            print i[0]

    def waits_latch(self):
        sql="SELECT to_char(sum(decode(event,'control file sequential read', total_waits, \
            'control file single write', total_waits, 'control file parallel write',total_waits,0))) ControlFileIO \
            FROM V$system_event WHERE 1=1 AND event not in ( \
            'SQL*Net message from client', \
            'SQL*Net more data from client', \
            'pmon timer', 'rdbms ipc message', \
            'rdbms ipc reply', 'smon timer') "
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            print i[0]

    def waits_logwrite(self):
        sql="SELECT to_char(sum(decode(event,'log file single write',total_waits, 'log file parallel write',total_waits,0))) LogWrite \
            FROM V$system_event WHERE 1=1 AND event not in ( \
            'SQL*Net message from client', \
            'SQL*Net more data from client', \
            'pmon timer', 'rdbms ipc message', \
            'rdbms ipc reply', 'smon timer')"
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            print i[0]

    def waits_multiblock_read(self):
        sql="SELECT to_char(sum(decode(event,'db file scattered read',total_waits,0))) MultiBlockRead \
            FROM V$system_event WHERE 1=1 AND event not in ( \
            'SQL*Net message from client', \
            'SQL*Net more data from client', \
            'pmon timer', 'rdbms ipc message', \
            'rdbms ipc reply', 'smon timer') "
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            print i[0]

    def waits_other(self):
        sql="SELECT to_char(sum(decode(event,'control file sequential read',0,'control file single write',0,'control file parallel write',0,'db file sequential read',0,'db file scattered read',0,'direct path read',0,'file identify',0,'file open',0,'SQL*Net message to client',0,'SQL*Net message to dblink',0, 'SQL*Net more data to client',0,'SQL*Net more data to dblink',0, 'SQL*Net break/reset to client',0,'SQL*Net break/reset to dblink',0, 'log file single write',0,'log file parallel write',0,total_waits))) Other FROM V$system_event WHERE 1=1 AND event not in (  'SQL*Net message from client', 'SQL*Net more data from client', 'pmon timer', 'rdbms ipc message',  'rdbms ipc reply', 'smon timer')"
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            print i[0]

    def waits_singleblock_read(self):
        sql="SELECT to_char(sum(decode(event,'db file sequential read',total_waits,0))) SingleBlockRead \
            FROM V$system_event WHERE 1=1 AND event not in ( \
            'SQL*Net message from client', \
            'SQL*Net more data from client', \
            'pmon timer', 'rdbms ipc message', \
            'rdbms ipc reply', 'smon timer')"
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            print i[0]

    def waits_sqlnet(self):
        sql="SELECT to_char(sum(decode(event,'SQL*Net message to client',total_waits,'SQL*Net message to dblink',total_waits,'SQL*Net more data to client',total_waits,'SQL*Net more data to dblink',total_waits,'SQL*Net break/reset to client',total_waits,'SQL*Net break/reset to dblink',total_waits,0))) SQLNET FROM V$system_event WHERE 1=1 \
             AND event not in ( 'SQL*Net message from client','SQL*Net more data from client','pmon timer','rdbms ipc message','rdbms ipc reply', 'smon timer')"
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            print i[0]

    def dg_error(self):
        sql="SELECT ERROR_CODE, SEVERITY, MESSAGE, TO_CHAR(TIMESTAMP, 'DD-MON-RR HH24:MI:SS') TIMESTAMP FROM V$DATAGUARD_STATUS WHERE CALLOUT='YES' AND TIMESTAMP > SYSDATE-1"
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            print i[0]

    def dg_sequence_number(self):
        sql="SELECT MAX (sequence#) FROM v$log_history"
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            print i[0]

    def dg_sequence_number_stby(self):
        sql="select max(sequence#) from v$archived_log"
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            print i[0]

    def dbconsistentgets(self):
        sql="select to_char(sum(decode(name,'consistent gets', value,0))) \"consistent_gets\" FROM v$sysstat"
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            print i[0]

    def dbhitratio(self):
        sql='''select ( \
             sum(decode(name,'consistent gets', value,0)) + sum(decode(name,'db block gets', value,0)) - sum(decode(name,'physical reads', value,0))) / (sum(decode(name,'consistent gets', value,0)) + sum(decode(name,'db block gets', value,0)) ) * 100 "hit_ratio" \
             FROM v$sysstat'''
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            print i[0]

    def dbphysicalread(self):
        sql="select sum(decode(name,'physical reads', value,0)) \"phys_reads\" FROM v$sysstat"
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            print i[0]

    def dbversion(self):
        sql="SELECT version FROM v$instance;"
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            print i[0]

    def sga_java_pool(self):
        sql=""
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            print i[0]

    def sga_java_pool(self):
        sql=""
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            print i[0]

    def check_active(self):
        '''Check Intance is active and open'''
        sql = "select to_char(case when inst_cnt > 0 then 1 else 0 end,'FM99999999999999990') retvalue from (select count(*) inst_cnt from v$instance where status = 'OPEN' and logins = 'ALLOWED' and database_status = 'ACTIVE')"
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            print i[0]

    def rcachehit(self):
        '''Read Cache hit ratio'''
        sql = "SELECT to_char((1 - (phy.value - lob.value - dir.value) / ses.value) * 100, 'FM99999990.9999') retvalue \
                FROM   v$sysstat ses, v$sysstat lob, \
                       v$sysstat dir, v$sysstat phy \
                WHERE  ses.name = 'session logical reads' \
                AND    dir.name = 'physical reads direct' \
                AND    lob.name = 'physical reads direct (lob)' \
                AND    phy.name = 'physical reads'"
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            print i[0]

    def dsksortratio(self):
        '''Disk sorts ratio'''
        sql = "SELECT to_char(d.value/(d.value + m.value)*100, 'FM99999990.9999') retvalue \
                 FROM  v$sysstat m, v$sysstat d \
                 WHERE m.name = 'sorts (memory)' \
                 AND d.name = 'sorts (disk)'"
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            print i[0]

    def activeusercount(self):
        '''Count of active users'''
        sql = "select to_char(count(*)-1, 'FM99999999999999990') retvalue from v$session where username is not null \
                 and status='ACTIVE'"
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            print i[0]

    def dbsize(self):
        '''Size of user data (without temp)'''
        sql = "SELECT to_char(sum(  NVL(a.bytes - NVL(f.bytes, 0), 0)), 'FM99999999999999990') retvalue \
                 FROM sys.dba_tablespaces d, \
                 (select tablespace_name, sum(bytes) bytes from dba_data_files group by tablespace_name) a, \
                 (select tablespace_name, sum(bytes) bytes from dba_free_space group by tablespace_name) f \
                 WHERE d.tablespace_name = a.tablespace_name(+) AND d.tablespace_name = f.tablespace_name(+) \
                 AND NOT (d.extent_management like 'LOCAL' AND d.contents like 'TEMPORARY')"
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            #print bytes2human(int(i[0]))
            print i[0]

    def dbsize(self):
        """Size of user data (without temp)"""
        sql = "SELECT to_char(sum(  NVL(a.bytes - NVL(f.bytes, 0), 0)), \
              'FM99999999999999990') retvalue \
              FROM sys.dba_tablespaces d, \
              (select tablespace_name, sum(bytes) bytes from dba_data_files \
              group by tablespace_name) a, \
              (select tablespace_name, sum(bytes) bytes from \
              dba_free_space group by tablespace_name) f \
              WHERE d.tablespace_name = a.tablespace_name(+) AND \
              d.tablespace_name = f.tablespace_name(+) \
              AND NOT (d.extent_management like 'LOCAL' AND d.contents \
              like 'TEMPORARY')"
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            print i[0]
 
    def dbfilesize(self):
        '''Size of all datafiles'''
        sql = "select to_char(sum(bytes), 'FM99999999999999990') retvalue from dba_data_files"
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            #print bytes2human(int(i[0]))
            print i[0]

    def version(self):
        '''Oracle version (Banner)'''
        sql = "select banner from v$version where rownum=1"
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            print i[0]

    def uptime(self):
        '''Instance Uptime (seconds)'''
        sql = "select to_char((sysdate-startup_time)*86400, 'FM99999999999999990') retvalue from v$instance"
        self.cur.execute(sql)
        res = self.cur.fetchmany(numRows=3)
        for i in res:
            print i[0]

    def commits(self):
        '''User Commits'''
        sql = "select to_char(value, 'FM99999999999999990') retvalue from v$sysstat where name = 'user commits'"
        self.cur.execute(sql)
        res = self.cur.fetchmany(numRows=3)
        for i in res:
            print i[0]

    def rollbacks(self):
        '''User Rollbacks'''
        sql = "select to_char(value, 'FM99999999999999990') retvalue from v$sysstat where name = 'user rollbacks'"
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            print i[0]

    def deadlocks(self):
        '''Deadlocks'''
        sql = "select to_char(value, 'FM99999999999999990') retvalue from v$sysstat where name = 'enqueue deadlocks'"
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            print i[0]

    def redowrites(self):
        '''Redo Writes'''
        sql = "select to_char(value, 'FM99999999999999990') retvalue from v$sysstat where name = 'redo writes'"
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            print i[0]

    def tblscans(self):
        '''Table scans (long tables)'''
        sql = "select to_char(value, 'FM99999999999999990') retvalue from v$sysstat where name = 'table scans (long tables)'"
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            print i[0]

    def tblrowsscans(self):
        '''Table scan rows gotten'''
        sql = "select to_char(value, 'FM99999999999999990') retvalue from v$sysstat where name = 'table scan rows gotten'"
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            print i[0]

    def indexffs(self):
        '''Index fast full scans (full)'''
        sql = "select to_char(value, 'FM99999999999999990') retvalue from v$sysstat where name = 'index fast full scans (full)'"
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            print i[0]

    def sqlnotindexed(slef):
        sql="SELECT SUM(DECODE(NAME, 'table scans (long tables)', VALUE, 0))/ (SUM(DECODE(NAME, 'table scans (long tables)', VALUE, 0))+SUM(DECODE(NAME, 'table scans (short tables)', VALUE, 0)))*100 SQL_NOT_INDEXED FROM V$SYSSTAT WHERE 1=1 AND ( NAME IN ('table scans (long tables)','table scans (short tables)') )"
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            print i[0]

    def hparsratio(self):
        '''Hard parse ratio'''
        sql = "SELECT to_char(h.value/t.value*100,'FM99999990.9999') retvalue \
                 FROM  v$sysstat h, v$sysstat t \
                 WHERE h.name = 'parse count (hard)' \
                 AND t.name = 'parse count (total)'"
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            print i[0]

    def hitratio_body(slef):
        sql="select gethitratio*100 \"get_pct\" FROM v$librarycache where namespace ='BODY'"
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            print i[0]
    
    def hitratio_sqlarea(slef):
        sql="select gethitratio*100 \"get_pct\" FROM v$librarycache where namespace ='SQL AREA'"
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            print i[0]
 
    def hitratio_trigger(self):
        sql="select gethitratio*100 \"get_pct\" FROM v$librarycache where namespace ='TRIGGER'"
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            print i[0]
     
    def hitratio_table_proc(self):
        sql="select gethitratio*100 \"get_pct\" FROM v$librarycache where namespace = 'TABLE/PROCEDURE'"
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            print i[0]
     
    def lio_block_changes(self):
        sql="SELECT to_char(SUM(DECODE(NAME,'db block changes',VALUE,0))) FROM V$SYSSTAT WHERE NAME ='db block changes'"
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            print i[0]

     
    def lio_consistent_read(self):
        sql="SELECT to_char(sum(decode(name,'consistent gets',value,0))) FROM V$SYSSTAT WHERE NAME ='consistent gets'"
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            print i[0]

     
    def lio_current_read(self):
        sql="SELECT to_char(sum(decode(name,'db block gets',value,0))) FROM V$SYSSTAT WHERE NAME ='db block gets'"
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            print i[0]

     

    def netsent(self):
        '''Bytes sent via SQL*Net to client'''
        sql = "select to_char(value, 'FM99999999999999990') retvalue from v$sysstat where name = 'bytes sent via SQL*Net to client'"
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            print i[0]

    def netresv(self):
        '''Bytes received via SQL*Net from client'''
        sql = "select to_char(value, 'FM99999999999999990') retvalue from v$sysstat where name = 'bytes received via SQL*Net from client'"
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            print i[0]

    def netroundtrips(self):
        '''SQL*Net roundtrips to/from client'''
        sql = "select to_char(value, 'FM99999999999999990') retvalue from v$sysstat where name = 'SQL*Net roundtrips to/from client'"
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            print i[0]

    def logonscurrent(self):
        '''Logons current'''
        sql = "select to_char(value, 'FM99999999999999990') retvalue from v$sysstat where name = 'logons current'"
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            print i[0]
      
    def lastarclog(self):
        '''Last archived log sequence'''
        sql = "select to_char(max(SEQUENCE#), 'FM99999999999999990') retvalue from v$log where archived = 'YES'"
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            if i[0] == None:
                print 0
            else:
                print i[0]

    def lastapplarclog(self):
        '''Last applied archive log (at standby).Next items requires [timed_statistics = true]'''
        sql = "select to_char(max(lh.SEQUENCE#), 'FM99999999999999990') retvalue \
                 from v$loghist lh, v$archived_log al \
                 where lh.SEQUENCE# = al.SEQUENCE# and applied='YES'"
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            if i[0] == None:
                print 0
            else:
                print i[0]

    def freebufwaits(self):
        '''Free buffer waits'''
        sql = "select to_char(time_waited, 'FM99999999999999990') retvalue \
                 from v$system_event se, v$event_name en \
                 where se.event(+) = en.name and en.name = 'free buffer waits'"
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            if i[0] == None:
                print 0
            else:
                print i[0]

    def bufbusywaits(self):
        '''Buffer busy waits'''
        sql = "select to_char(time_waited, 'FM99999999999999990') retvalue \
                 from v$system_event se, v$event_name en \
                 where se.event(+) = en.name and en.name = 'buffer busy waits'"
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            print i[0]

    def logswcompletion(self):
        '''log file switch completion'''
        sql = "select to_char(time_waited, 'FM99999999999999990') retvalue \
                 from v$system_event se, v$event_name en \
                 where se.event(+) = en.name and en.name = 'log file switch completion'"
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            if i[0] == None:
                print 0
            else:
                print i[0]

    def logfilesync(self):
        '''Log file sync'''
        sql = "select to_char(time_waited, 'FM99999999999999990') retvalue \
                 from v$system_event se, v$event_name en \
                 where se.event(+) = en.name and en.name = 'log file sync'"
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            print i[0]

    def logprllwrite(self):
        '''Log file parallel write'''
        sql = "select to_char(time_waited, 'FM99999999999999990') retvalue \
                 from v$system_event se, v$event_name en \
                 where se.event(+) = en.name and en.name = 'log file parallel write'"
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            print i[0]

    def dbblockgets(self):
        sql = "select to_char(sum(decode(name,'db block gets', value,0))) \"block_gets\" FROM v$sysstat"
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            print i[0]

    def enqueue(self):
        '''Enqueue waits'''
        sql = "select to_char(time_waited, 'FM99999999999999990') retvalue \
                 from v$system_event se, v$event_name en \
                 where se.event(+) = en.name and en.name = 'enqueue'"
        self.cur.execute(sql)
        res = self.cur.fetchall()
        if len(res) == 0:
            print 0
            return 0
        for i in res:
            print i[0]

    def dbseqread(self):
        '''DB file sequential read waits'''
        sql = "select to_char(time_waited, 'FM99999999999999990') retvalue \
                 from v$system_event se, v$event_name en \
                 where se.event(+) = en.name and en.name = 'db file sequential read'"
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            print i[0]

    def dbscattread(self):
        '''DB file scattered read'''
        sql="select to_char(time_waited, 'FM99999999999999990') retvalue \
                 from v$system_event se, v$event_name en \
                 where se.event(+) = en.name and en.name = 'db file scattered read'"
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            print i[0]

    def dbsnglwrite(self):
        '''DB file single write'''
        sql="select to_char(time_waited, 'FM99999999999999990') retvalue \
                 from v$system_event se, v$event_name en \
                 where se.event(+) = en.name and en.name = 'db file single write'"
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            print i[0]

    def dbprllwrite(self):
        '''DB file parallel write'''
        sql="select to_char(time_waited, 'FM99999999999999990') retvalue \
                 from v$system_event se, v$event_name en \
                 where se.event(+) = en.name and en.name = 'db file parallel write'"
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            if i[0] == None:
                print 0
            else:
                print i[0]

    def directread(self):
        '''Direct path read'''
        sql="select to_char(time_waited, 'FM99999999999999990') retvalue \
                 from v$system_event se, v$event_name en \
                 where se.event(+) = en.name and en.name = 'direct path read'"
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            print i[0]

    def directwrite(self):
        '''Direct path write'''
        sql="select to_char(time_waited, 'FM99999999999999990') retvalue \
                 from v$system_event se, v$event_name en \
                 where se.event(+) = en.name and en.name = 'direct path write'"
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            print i[0]

    def latchfree(self):
        '''latch free.'''
        sql="select to_char(time_waited, 'FM99999999999999990') retvalue \
                 from v$system_event se, v$event_name en \
                 where se.event(+) = en.name and en.name = 'latch free'"
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            print i[0]

    def tablespace(self, name):
        """Get tablespace usage"""
        #sql = '''SELECT df.tablespace_name "TABLESPACE", ROUND ( (df.bytes - \
        #      SUM (fs.bytes)) * 100 / df.bytes, 2) "USED" FROM   \
        #      sys.sm$ts_free fs, (  SELECT tablespace_name, SUM (bytes) \
        #      bytes FROM sys.sm$ts_avail GROUP BY tablespace_name) df WHERE \
        #      fs.tablespace_name(+) = df.tablespace_name and df.tablespace_name \
        #      = '{0}' GROUP BY df.tablespace_name, df.bytes ORDER BY 1'''.format(name)
        sql='''SELECT DF.TABLESPACE_NAME "TABLESPACE", ROUND(SUM((NVL(DF.MAX_SIZE_MB,0)-\
              (NVL(F.FREE_MB,0)+(NVL(DF.MAX_SIZE_MB,0) - \
              NVL(DF.SIZE_MB,0)))))/SUM(NVL(MAX_SIZE_MB,0)),4)*100 AS USER_PCT
              FROM (SELECT FILE_ID,FILE_NAME,TABLESPACE_NAME, TRUNC(BYTES/1024/1024) \
              AS SIZE_MB, TRUNC(GREATEST(BYTES,MAXBYTES)/1024/1024) AS MAX_SIZE_MB
              FROM SYS.DBA_DATA_FILES WHERE autoextensible = 'YES' and \
              TABLESPACE_NAME='{0}') DF,(SELECT TRUNC(SUM(BYTES)/1024/1024) \
              AS FREE_MB,FILE_ID \
              FROM DBA_FREE_SPACE \
              GROUP BY FILE_ID) F \
              WHERE DF.FILE_ID = F.FILE_ID (+) \
              GROUP BY DF.TABLESPACE_NAME'''.format(name)
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            print i[1]

    def tablespace_abs(self, name):
        """Get tablespace in use"""
        sql = '''SELECT df.tablespace_name "TABLESPACE", (df.totalspace - \
              tu.totalusedspace) "FREEMB" from (select tablespace_name, \
              sum(bytes) TotalSpace from dba_data_files group by tablespace_name) \
              df ,(select sum(bytes) totalusedspace,tablespace_name from dba_segments \
              group by tablespace_name) tu WHERE tu.tablespace_name = \
              df.tablespace_name and df.tablespace_name = '{0}' '''.format(name)
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            print i[1]

    def show_tablespaces(self):
        """List tablespace names in a JSON like format for Zabbix use"""
        sql = "SELECT tablespace_name FROM dba_tablespaces ORDER BY 1"
        self.cur.execute(sql)
        res = self.cur.fetchall()
        key = ['{#TABLESPACE}']
        lst = []
        for i in res:
            d = dict(zip(key, i))
            lst.append(d)
        print json.dumps({'data': lst})

    def show_tablespaces_temp(self):
        """List temporary tablespace names in a JSON like
        format for Zabbix use"""
        sql = "SELECT TABLESPACE_NAME FROM DBA_TABLESPACES WHERE \
              CONTENTS='TEMPORARY'"
        self.cur.execute(sql)
        res = self.cur.fetchall()
        key = ['{#TABLESPACE_TEMP}']
        lst = []
        for i in res:
            d = dict(zip(key, i))
            lst.append(d)
        print json.dumps({'data': lst})

    def show_asm_volumes(self):
        """List als ASM volumes in a JSON like format for Zabbix use"""
        sql = "select NAME from v$asm_diskgroup_stat ORDER BY 1"
        self.cur.execute(sql)
        res = self.cur.fetchall()
        key = ['{#ASMVOLUME}']
        lst = []
        for i in res:
            d = dict(zip(key, i))
            lst.append(d)
        print json.dumps({'data': lst})

    def asm_volume_use(self, name):
        """Get ASM volume usage"""
        sql = "select round(((TOTAL_MB-FREE_MB)/TOTAL_MB*100),2) from \
              v$asm_diskgroup_stat where name = '{0}'".format(name)
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            print i[0]

    def tablespace_temp(self, name):
        """Query temporary tablespaces"""
        sql = "SELECT round(((TABLESPACE_SIZE-FREE_SPACE)/TABLESPACE_SIZE)*100,2) \
              PERCENTUAL FROM dba_temp_free_space where \
              tablespace_name='{0}'".format(name)
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            print i[0]

    def query_sysmetrics(self, name):
        """Query v$sysmetric parameters"""
        sql = "select value from v$sysmetric where METRIC_NAME ='{0}' and \
              rownum <=1 order by INTSIZE_CSEC".format(name.replace('_', ' '))
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            print i[0]

    def fra_use(self):
        """Query the Fast Recovery Area usage"""
        sql = "select round((SPACE_LIMIT-(SPACE_LIMIT-SPACE_USED))/ \
              SPACE_LIMIT*100,2) FROM V$RECOVERY_FILE_DEST"
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            print i[0]

    def show_users(self):
        """Query the list of users on the instance"""
        sql = "SELECT username FROM dba_users ORDER BY 1"
        self.cur.execute(sql)
        res = self.cur.fetchall()
        key = ['{#DBUSER}']
        lst = []
        for i in res:
            d = dict(zip(key, i))
            lst.append(d)
        print json.dumps({'data': lst})

    def user_status(self, dbuser):
        """Determines whether a user is locked or not"""
        sql = "SELECT account_status FROM dba_users WHERE username='{0}'" \
            .format(dbuser)
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            print i[0]
    def check_archive(self,archive):
        '''List archive used'''
        sql = "select trunc((total_mb-free_mb)*100/(total_mb)) PCT from v$asm_diskgroup_stat where name='{0}' ORDER BY 1".format(archive)
        self.cur.execute(sql)
        res = self.cur.fetchall()
        if len(res) == 0:
            print 0
            return 0
        for i in res:
            print i[0]

    def archive_RaceConditionQuery(self):
        sql="select value from v$parameter where name='log_archive_start'"
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            print i[0]

    def query_lock(self):
        '''Query lock 2'''
        sql = "SELECT count(*) FROM gv$lock l WHERE  block=1"
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            print i[0]

    def query_redologs(self):
        '''Redo logs'''
        sql = "select COUNT(*) from v$LOG WHERE STATUS='ACTIVE'"
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            print i[0]

    def query_rollbacks(self):
        '''Rollback'''
        sql = "select nvl(trunc(sum(used_ublk*4096)/1024/1024),0) from gv$transaction t,gv$session s where ses_addr = saddr"
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            print i[0]

    def query_sessions(self):
        '''Sessions'''
        sql = "select count(*) from gv$session where username is not null and status='ACTIVE'"
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            print i[0]

    def query_temp(self):
        '''Query temp'''
        sql = "select nvl(sum(blocks*8192)/1024/1024,0) from gv$session s, gv$sort_usage u where s.saddr = u.session_addr"
        self.cur.execute(sql)
        res = self.cur.fetchall()
        for i in res:
            print i[0]

class Main(Checks):
    def __init__(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('--username')
        parser.add_argument('--password')
        parser.add_argument('--address')
        parser.add_argument('--database')

        subparsers = parser.add_subparsers()

        for name in dir(self):
            if not name.startswith("_"):
                p = subparsers.add_parser(name)
                method = getattr(self, name)
                argnames = inspect.getargspec(method).args[1:]
                for argname in argnames:
                    p.add_argument(argname)
                p.set_defaults(func=method, argnames=argnames)
        self.args = parser.parse_args()

    def db_connect(self):
        a = self.args
        username = a.username
        password = a.password
        address = a.address
        port = a.port
        database = a.database
        #self.db = cx_Oracle.connect("{0}/{1}@{2}/{3}".format(
        #   username, password, address, database))
        self.db = cx_Oracle.connect('''{0}/{1}@{2}:{3}/{4}'''.format(username,password,address,port,database))
        self.cur = self.db.cursor()

    def db_close(self):
        self.db.close()

    def __call__(self):
        try:
            a = self.args
            callargs = [getattr(a, name) for name in a.argnames]
            self.db_connect()
            try:
                return self.args.func(*callargs)
            finally:
                self.db_close()
        except Exception, err:
            print 0
            print str(err)

if __name__ == "__main__":
    main = Main()
    main()
