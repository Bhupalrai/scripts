#Author: Bhupal Rai
#Verison : 1.0.1
#Date : 05/26/2016
#Updated: 07/12/2016

import sys
import os
import subprocess
import shlex
import time
import getpass
import re

#GLOBAL VARIABLES
DROP_LIST_FNAME = 'schema_drop_list.txt'
DB_NAME = ' '
LOGIN_USER_USERNAME = ' '
LOGIN_USER_PASSWORD = ' '
LOG_FILE = './logs/drop_script.log'
ALL_SQL_FILE_LOC = './sql_files'
ALL_LOG_FILE_LOC = './logs'
HISTORY_FILES = './history_files/'

INFO = 'INFO'
WARN = 'WARN'
ERRO = 'ERRO'
DEBG = 'DEBG'

SET_ROLE_ALL = 'SET ROLE ALL;'
DYNAMIC_DROP_TABLE_CMD_SQL = """\"{1:s} select 'drop table '||table_schema||'.'||table_name||' cascade ; ' from tables where table_schema ilike '{0:s}'\""""
TIMESTAMP_SNAPSHOT = ' '



def filterLoggingMsg(log_msg):

	#We remove pwd para, if log_msg is vsql cmd
	if 'vsql ' in log_msg:		
		# ?, You got to improve this re !!!
		match = re.search(r' -w \s*(\w+)', log_msg)
		
		if match : 
			return re.sub(  ' -w '+match.group(1), '', log_msg)
		return log_msg # ?, verify for dead code
	return log_msg



def writeToLog(log_msg, msg_category, absolute_log_file):
	try:
		file = open(absolute_log_file, 'a')
		file.write(str(time.strftime("%Y-%m-%d %H:%M:%S ")) + str(msg_category)+ ' ' +filterLoggingMsg(str(log_msg))+ '\n')
		file.close()
	except Exception, e:
		print('Exception in writeToLog module. Msg: \n'+str(e))
 

 
def runOsCmd(cmd):

	screen_output = []
	screen_error  = []
	
	writeToLog('executing: ' + str(cmd), INFO, LOG_FILE)
	runCmd = subprocess.Popen(shlex.split(cmd), stderr=subprocess.STDOUT, stdin=subprocess.PIPE, stdout=subprocess.PIPE)

	if runCmd.stdout:
		for line in runCmd.stdout:
			screen_output.append(str(line))
	if runCmd.stderr:
		for line in runCmd.stderr:
			screen_error.append(str(line))
	
	runCmd.communicate()
	exit_code = runCmd.wait()

	if exit_code != 0 :
		print('Error msg : ' + ' '.join(screen_output))
		writeToLog('Error occured on execting command', ERRO, LOG_FILE)		
		writeToLog('Error msg : ' + ' '.join(screen_output), ERRO, LOG_FILE)
		return 0
	return 1
	


def scrubSchemaList(schema_dropt_list):
	s0 = schema_dropt_list
	s1 = map(str.strip, s0)
	return map(str.upper, s1)


def importSchemaList() :
	global DROP_LIST_FNAME

	try:
		schema_dropt_list = [line.rstrip('\n') for line in open(DROP_LIST_FNAME)]
	except Exception, e:
		print e
		writeToLog(str(e), ERRO, LOG_FILE)
		writeToLog('Exiting...', INFO, LOG_FILE)
		raise SystemExit()

	return scrubSchemaList(schema_dropt_list)



def initialize():
	global DB_NAME
	global LOGIN_USER_PASSWORD
	global LOGIN_USER_USERNAME
	
	#Investigate neighbourhood
	if not os.path.exists(ALL_SQL_FILE_LOC): os.makedirs(ALL_SQL_FILE_LOC)
	if not os.path.exists(ALL_LOG_FILE_LOC): os.makedirs(ALL_LOG_FILE_LOC)
	if not os.path.exists(HISTORY_FILES)   : os.makedirs(HISTORY_FILES)

	#Move old files to history folder
	print('Old files moved to : '+HISTORY_FILES)
	os.system('find logs/*.txt -maxdepth 1  -type f -exec mv -f "{}" '+HISTORY_FILES+' \; >/dev/null 2>&1')     #| os cuz wild card not supported by  |
	os.system('find sql_files/*.sql -maxdepth 1 -type f -exec mv -f "{}" '+HISTORY_FILES+' \; >/dev/null 2>&1') #| subprocess and shlex.              |

	DB_NAME = str(raw_input('Database : '))
	LOGIN_USER_USERNAME = str(raw_input('Username : '))
	LOGIN_USER_PASSWORD = getpass.getpass()



#--------------------
# SCRIPT ENTRY POINT
#--------------------
if __name__ == '__main__' :

	initialize()

	writeToLog('Script started...', INFO, LOG_FILE)
	print('running...')
	
	#Get drop list
	schema_dropt_list = importSchemaList()	

	for schema in schema_dropt_list:	

		# We generate drop schema table cmd here			
		writeToLog('Generating tables drop cmd...', INFO, LOG_FILE)
		cmd_check_schema = SET_ROLE_ALL + " " + "select user_name from users where upper(user_name) ='{0:s}'".format(schema.upper())
		vsql_cmd_check_schema = 'vsql -d {0:s} -U {1:s} -w {2:s} -c "{3:s}" \
                                          '.format(DB_NAME,  LOGIN_USER_USERNAME, LOGIN_USER_PASSWORD, cmd_check_schema )
		if not runOsCmd(vsql_cmd_check_schema) :
			raise SystemExit('exiting...')

		TIMESTAMP_SNAPSHOT = str(time.strftime("%Y%m%d_%H%M%Ss"))
		
		var_tbl_drop_sql = ALL_SQL_FILE_LOC+'/' + schema.upper()+'_TBL_DROP_'+ TIMESTAMP_SNAPSHOT +'.sql'
		cmd_gen_drop_table_list = 'vsql -d {0:s} -U {1:s} -w {2:s} -c {3:s} -o {4:s} -t \
        	                          '.format(DB_NAME,  LOGIN_USER_USERNAME, LOGIN_USER_PASSWORD, DYNAMIC_DROP_TABLE_CMD_SQL.format(schema.upper(), SET_ROLE_ALL), var_tbl_drop_sql )	
		if( not runOsCmd(cmd_gen_drop_table_list)):
			writeToLog('exiting...', ERRO, LOG_FILE)
			raise SystemExit('exiting...')


		#Execute drop table cmd here
		writeToLog('Executing table drop cmd...', INFO, LOG_FILE)		

		runOsCmd("sed -i '1i {0:s}' {1:s}".format(SET_ROLE_ALL, var_tbl_drop_sql))	# append 'set role all;' @begining
		var_tbl_drop_log = ALL_LOG_FILE_LOC + '/' + schema.upper()+'_TBL_DROP_'+ TIMESTAMP_SNAPSHOT +'.txt'		
		vsql_cmd = 'vsql -d {0:s} -U {1:s} -w {2:s} -f {3:s} -o {4:s} \
                   	   '.format(DB_NAME,  LOGIN_USER_USERNAME, LOGIN_USER_PASSWORD, var_tbl_drop_sql, var_tbl_drop_log)
		runOsCmd(vsql_cmd)

		
		#Drop schema here
		writeToLog('Dropping schema...', INFO, LOG_FILE)
		vsql_cmd = 'vsql -d {0:s} -U {1:s} -w {2:s} -c "{4:s} drop schema {3:s}  cascade" \
						'.format(DB_NAME,  LOGIN_USER_USERNAME, LOGIN_USER_PASSWORD, schema.upper(), SET_ROLE_ALL)

		
		if ( not runOsCmd(vsql_cmd)):
			writeToLog('Schema Drop failed : ' + schema.upper(), ERRO , LOG_FILE)
		else :
			writeToLog('Schema Dropped : ' + schema.upper(), INFO, LOG_FILE)

			
		#Drop user here
		writeToLog('Dropping user...' + schema.upper(), INFO, LOG_FILE)
		vsql_cmd = 'vsql -d {0:s} -U {1:s} -w {2:s} -c "{4:s} drop user {3:s}" \
		           '.format(DB_NAME,  LOGIN_USER_USERNAME, LOGIN_USER_PASSWORD, schema.upper(), SET_ROLE_ALL)		
		
		if ( not runOsCmd(vsql_cmd)) :
			writeToLog('User Drop failed : ' + schema.upper(), ERRO, LOG_FILE)
		else:
			writeToLog('User Dropped :  ' + schema.upper(), INFO, LOG_FILE)

	writeToLog('Script completed !', INFO, LOG_FILE)
	print('Script completed !')