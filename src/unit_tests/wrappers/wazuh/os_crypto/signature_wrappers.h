/* Copyright (C) 2022, Wrixte
 * All rights reserved.
 *
 * This program is free software; you can redistribute it
 * and/or modify it under the terms of the GNU General Public
 * License (version 2) as published by the FSF - Free Software
 * Foundation
 */


#ifndef SIGNATURE_WRAPPERS_H
#define SIGNATURE_WRAPPERS_H

#include "headers/shared.h"
#include <string.h>

int __wrap_w_wpk_unsign(const char * source, const char * target, const char ** ca_store);


#endif
