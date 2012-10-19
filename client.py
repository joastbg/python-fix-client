#! /usr/bin/env python

#	Copyright 2012 Johan Astborg
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import asyncore, socket
import os
import datetime
import time
from optparse import OptionParser

SOH = '\x01'

TAGS = {
	8: 'BeginString',
	9: 'BodyLength',
	35: 'MsgType',
	49: 'SenderCompID',
	56: 'TargetCompID',
	34: 'MsgSeqNum',
	52: 'SendingTime',
	10: 'CheckSum',
	98: 'EncryptMethod',
	108: 'HeartBtInt'
}

TAGSR = {
	'BeginString': 8,
	'BodyLength': 9,
	'MsgType': 35,
	'SenderCompID': 49,
	'TargetCompID': 56,
	'MsgSeqNum': 34,
	'SendingTime': 52,
	'CheckSum': 10,
	'EncryptMethod': 98,
	'HeartBtInt': 108
}


MSGTYPES = {
	'A': 'Logon',
	'0': 'HeartBeat',
	'1': 'Test Request',
	'2': 'Resend Request',
	'4': 'Sequence Reset',
	'5': 'Logout',
	'8': 'ExecutionReport'
}

MSGTYPESR = {
	'Logon': 'A',
	'HeartBeat':'0',
	'Test Request':'1',
	'Resend Request':'2',
	'Sequence Reset':'4',
	'Logout':'5',
	'ExecutionReport':'8'
}

HEADER = [
	'SenderCompID', 
	'TargetCompID', 
	'MsgSeqNum', 
	'SendingTime',
]

class FIXclient(asyncore.dispatcher):

    def __init__(self, host, port):
		self.host = host
		self.port = port
		asyncore.dispatcher.__init__(self)
		self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
		self.connect((host, port))
		self.buffer = logon_message()

    def handle_connect(self):
		# connection succeeded
		#self.send(self.buffer)
		pass

    def handle_close(self):
		self.close()
		print 'Connection closed, reconnecting...'
		time.sleep(5)
		self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
		self.connect((self.host, self.port))
	
    def handle_read(self):
		print "----------INBOUND----------"
		msg = self.recv(8192)
		msgs = parse(msg)
		print msgs
		if msgs['MsgType'] == 'HeartBeat':
			self.buffer = heartbt_message() 
			#self.send(self.buffer)
	
    def writable(self):
        return (len(self.buffer) > 0)

	def handl_expt(self):
		# connection failed
		print 'exception'
		#self.handle_error()

	def handle_error(self):
		print "Error"

    def handle_write(self):
		print "----------OUTBOUND----------"
		parse(self.buffer)
		sent = self.send(self.buffer)
		self.buffer = self.buffer[sent:]
		print 'REST: ', len(self.buffer)
		pass

def current_datetime():
	return datetime.datetime.utcnow().strftime("%Y%m%d-%H:%M:%S.%f")[:-3]

def make_tag(tag, value):
	print "%s=%s" % (TAGSR[tag], value)

def pack(msgs):
	
	# Create body
	body = []

	if 'SenderCompID' not in msgs:
		print 'ERROR'
		return
	else:
		body.append("%i=%s" % (TAGSR['SenderCompID'], msgs['SenderCompID']))

	if 'TargetCompID' not in msgs:
		print 'ERROR'
		return
	else:
		body.append("%i=%s" % (TAGSR['TargetCompID'], msgs['TargetCompID']))

	if 'MsgSeqNum' not in msgs:
		print 'ERROR'
		return
	else:
		body.append("%i=%s" % (TAGSR['MsgSeqNum'], msgs['MsgSeqNum']))

	if 'SendingTime' not in msgs:
		print 'ERROR'
		return
	else:
		body.append("%i=%s" % (TAGSR['SendingTime'], msgs['SendingTime']))

	if 'EncryptMethod' in msgs:
		body.append("%i=%s" % (TAGSR['EncryptMethod'], msgs['EncryptMethod']))

	if 'HeartBtInt' in msgs:
		body.append("%i=%s" % (TAGSR['HeartBtInt'], msgs['HeartBtInt']))

	# Enable easy change when debugging
	SEP = SOH
	
	body = SEP.join(body) + SEP

	# Create header
	header = []
	header.append("%s=%s" % (TAGSR['BeginString'], 'FIX.4.2'))
	header.append("%s=%i" % (TAGSR['BodyLength'], len(body) + 5))
	header.append("%s=%s" % (TAGSR['MsgType'],  MSGTYPESR[msgs['MsgType']]))

	fixmsg = SEP.join(header) + SEP + body
	cksum = sum([ord(i) for i in list(fixmsg)]) % 256
	
	if cksum < 10:
		fixmsg = fixmsg + "%i=00%s" % (TAGSR['CheckSum'], cksum)
	elif cksum < 100:
		fixmsg = fixmsg + "%i=0%s" % (TAGSR['CheckSum'], cksum)
	else:
		fixmsg = fixmsg + "%i=%s" % (TAGSR['CheckSum'], cksum)
	return fixmsg + SEP
	
def parse(rawmsg):
	
	msg = rawmsg.rstrip(os.linesep).split(SOH)
	msg = msg[:-1]
	msgs = {}

	print "|".join(msg)

	for m in msg:
		tag, value = m.split('=', 1)
		if int(tag) not in TAGS:
			print "Not valid: %s" % (tag)
		else:
			t = TAGS[int(tag)]
			if t == 'CheckSum':
				cksum = ((sum([ord(i) for i in list(SOH.join(msg[:-1]))]) + 1) % 256)
				if cksum == int(value):
					print "CheckSum\t%s (OK)" % (int(value))
				else:
					print "CheckSum\t%s (INVALID)" % (int(value))
			elif t == 'MsgType':
				msgs[t] = MSGTYPES[value]
				print "MsgType\t\t%s" % msgs[t]
			else:
				msgs[t] = value
	return msgs

def heartbt_message():
	msgs = {}
	msgs['SendingTime'] = current_datetime()
	msgs['SenderCompID'] = "BANZAI"
	msgs['TargetCompID'] = "FIXIMULATOR"
	msgs['MsgSeqNum'] = 5
	msgs['MsgType'] = 'HeartBeat'
	#msgs['HeartBtInt'] = 30
	return pack(msgs)

def logon_message():
	msgs = {}
	msgs['SendingTime'] = current_datetime()
	msgs['SenderCompID'] = "BANZAI"
	msgs['TargetCompID'] = "FIXIMULATOR"
	msgs['MsgSeqNum'] = 4
	msgs['EncryptMethod'] = 0
	msgs['MsgType'] = 'Logon'
	msgs['HeartBtInt'] = 30
	return pack(msgs)

def main():

	# Command line args
	usage = "usage: %prog [options] arg"
	parser = OptionParser(usage)
	parser.add_option("-s", "--server", dest="server", help="FIX server to connect to")
	parser.add_option("-p", "--port", dest="port", help="FIX server port")
		
	(options, args) = parser.parse_args()

	if options.server == None and options.port == None:
		print "invalid arguments"
		exit(1)

	# Start FIX client
	client = FIXclient(options.server, int(options.port))
  	asyncore.loop()

if __name__ == "__main__":
    main()
