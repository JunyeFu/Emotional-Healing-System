
def onHTTPRequest(webServerDAT, request, response):
    response['statusCode'] = 200
    response['data'] = 'OK-minimal'
    return response
