# Copyright (C) 2022, Wrixte
# Created by Wrixte InfoSec Pvt Ltd. <info@wrixte.co>.
# This program is a free software; you can redistribute it and/or modify it under the terms of GPLv2


async def modify_response_headers(request, response):
    # Delete 'Server' entry
    response.headers.pop('Server', None)
