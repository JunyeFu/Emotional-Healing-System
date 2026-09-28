# Debug callback — writes to file to confirm execution
import json

def onHTTPRequest(webServerDat, request, response):
    response['statusCode'] = 200
    response['mimeType'] = 'application/json'
    response['data'] = json.dumps({'ok': True, 'msg': 'TD Bridge working'})

# Confirm script loaded by writing a file
with open('C:/Users/fujunye/Desktop/_td_loaded.txt', 'w') as f:
    f.write('WebServer callbacks loaded OK')
