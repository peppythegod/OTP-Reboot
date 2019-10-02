"""
 * Copyright (C) Caleb Marshall - All Rights Reserved
 * Written by Caleb Marshall <anythingtechpro@gmail.com>, August 17th, 2017
 * Licensing information can found in 'LICENSE', which is part of this source code package.
"""

CLIENTAGENT_CHANNEL = 1000
STATESERVER_CHANNEL = 1001
DATABASE_CHANNEL = 1002

UD_CHANNEL = 400000000

CONTROL_MESSAGE = 1
CONTROL_SET_CHANNEL = 2002
CONTROL_REMOVE_CHANNEL = 2003
CONTROL_SET_CON_NAME = 2004
CONTROL_SET_CON_URL = 2005
CONTROL_ADD_RANGE = 2006
CONTROL_REMOVE_RANGE = 2007
CONTROL_ADD_POST_REMOVE = 2008
CONTROL_CLEAR_POST_REMOVE = 2009

CLIENT_GO_GET_LOST = 4
CLIENT_OBJECT_UPDATE_FIELD = 24
CLIENT_OBJECT_UPDATE_FIELD_RESP = 24
CLIENT_OBJECT_DISABLE_RESP = 25
CLIENT_OBJECT_DELETE_RESP = 27
CLIENT_SET_ZONE = 29
CLIENT_SET_SHARD = 31
CLIENT_CREATE_OBJECT_REQUIRED = 34
CLIENT_CREATE_OBJECT_REQUIRED_OTHER = 35
CLIENT_HEARTBEAT = 52
CLIENT_LOGIN = 1
CLIENT_LOGIN_RESP = 2
CLIENT_GET_AVATARS = 3
CLIENT_GET_AVATARS_RESP = 5
CLIENT_CREATE_AVATAR = 6
CLIENT_CREATE_AVATAR_RESP = 7
CLIENT_GET_SHARD_LIST = 8
CLIENT_GET_SHARD_LIST_RESP = 9
CLIENT_GET_FRIEND_LIST = 10
CLIENT_GET_FRIEND_LIST_RESP = 11
CLIENT_GET_FRIEND_DETAILS = 12
CLIENT_GET_FRIEND_DETAILS_RESP = 13
CLIENT_GET_AVATAR_DETAILS = 14
CLIENT_GET_AVATAR_DETAILS_RESP = 15
CLIENT_LOGIN_2 = 16
CLIENT_LOGIN_2_RESP = 17
CLIENT_SET_AVATAR = 32
CLIENT_DISCONNECT = 37
CLIENT_CHANGE_IP_ADDRESS_RESP = 45
CLIENT_GET_STATE = 46
CLIENT_GET_STATE_RESP = 47
CLIENT_DONE_SET_ZONE_RESP = 48
CLIENT_DELETE_AVATAR = 49
CLIENT_DELETE_AVATAR_RESP = 5
CLIENT_HEARTBEAT = 52
CLIENT_FRIEND_ONLINE = 53
CLIENT_FRIEND_OFFLINE = 54
CLIENT_REMOVE_FRIEND = 56
CLIENT_SERVER_UP = 57
CLIENT_SERVER_DOWN = 58
CLIENT_CHANGE_PASSWORD = 65
CLIENT_SET_NAME_PATTERN = 67
CLIENT_SET_NAME_PATTERN_ANSWER = 68
CLIENT_SET_WISHNAME = 70
CLIENT_SET_WISHNAME_RESP = 71
CLIENT_SET_WISHNAME_CLEAR = 72
CLIENT_SET_SECURITY = 73
CLIENT_LOGIN_2_GREEN = 1
CLIENT_LOGIN_2_PLAY_TOKEN = 2
CLIENT_LOGIN_2_BLUE = 3
CLIENT_LOGIN_TOONTOWN = 125
CLIENT_LOGIN_TOONTOWN_RESP = 126
CLIENT_LOGIN_3_DISL_TOKEN = 4  # SSL encoded blob from DISL system.
CLIENT_ADD_INTEREST = 97
CLIENT_REMOVE_INTEREST = 99
CLIENT_DONE_INTEREST_RESP = 48
CLIENT_OBJECT_LOCATION = 102

CLIENT_DISCONNECT_INVALID_MSGTYPE = 108
CLIENT_DISCONNECT_NO_HEARTBEAT = 345
CLIENT_DISCONNECT_ALREADY_LOGGED_IN = 346
CLIENT_DISCONNECT_BAD_VERSION = 124
CLIENT_DISCONNECT_BAD_DCHASH = 125
CLIENT_DISCONNECT_INVALID_PLAY_TOKEN_TYPE = 284
CLIENT_DISCONNECT_TRUNCATED_DATAGRAM = 109
CLIENT_DISCONNECT_ANONYMOUS_VIOLATION = 113
CLIENT_DISCONNECT_SHARD_CLOSED = 114

CLIENT_DEBUG_SET_NAME = 201
CLIENT_DEBUG_AUTHENTICATE_ADMIN = 202

CLIENTAGENT_DISCONNECT = 1000
CLIENTAGENT_FRIEND_ONLINE = 1001
CLIENTAGENT_FRIEND_OFFLINE = 1002

STATESERVER_OBJECT_GENERATE_WITH_REQUIRED = 2000
STATESERVER_OBJECT_GENERATE_WITH_REQUIRED_OTHER = 2001
STATESERVER_OBJECT_DELETE_RAM = 2002
STATESERVER_OBJECT_ENTER_LOCATION_WITH_REQUIRED = 2041
STATESERVER_OBJECT_ENTER_LOCATION_WITH_REQUIRED_OTHER = 2042
STATESERVER_OBJECT_ENTER_AI_WITH_REQUIRED = 2052
STATESERVER_OBJECT_ENTER_AI_WITH_REQUIRED_OTHER = 2053
STATESERVER_OBJECT_SET_OWNER = 2043
STATESERVER_OBJECT_CHANGING_OWNER = 2044
STATESERVER_OBJECT_UPDATE_FIELD = 2020
STATESERVER_OBJECT_UPDATE_FIELD_MULTIPLE = 2021
STATESERVER_OBJECT_SET_LOCATION = 2040
STATESERVER_OBJECT_CHANGING_LOCATION = 2046
STATESERVER_OBJECT_LOCATION_ACK = 2045
STATESERVER_OBJECT_SET_AI = 2050
STATESERVER_OBJECT_SET_AI_RESP = 2054
STATESERVER_OBJECT_CHANGING_AI = 2051
STATESERVER_OBJECT_SET_ZONE = 2007
STATESERVER_OBJECT_SET_ZONE_RESP = 2008
STATESERVER_OBJECT_CHANGE_ZONE = 2009
STATESERVER_OBJECT_ENTER_OWNER_WITH_REQUIRED = 2062
STATESERVER_OBJECT_ENTER_OWNER_WITH_REQUIRED_OTHER = 2063
STATESERVER_OBJECT_GET_ZONES_OBJECTS = 2064
STATESERVER_OBJECT_GET_ZONES_OBJECTS_RESP = 2065
STATESERVER_OBJECT_GET_ZONES_OBJECTS_2 = 2066
STATESERVER_OBJECT_GET_ZONES_OBJECTS_2_RESP = 2067
STATESERVER_OBJECT_CLEAR_WATCH = 2068
STATESERVER_ADD_SHARD = 2010
STATESERVER_REMOVE_SHARD = 2011
STATESERVER_UPDATE_SHARD = 2012
STATESERVER_GET_SHARD_ALL = 2013
STATESERVER_GET_SHARD_ALL_RESP = 2014

DBSERVER_CREATE_OBJECT = 3000
DBSERVER_CREATE_OBJECT_RESP = 3001
DBSERVER_OBJECT_GET_FIELD = 3002
DBSERVER_OBJECT_GET_FIELD_RESP = 3003
DBSERVER_OBJECT_GET_FIELDS = 3004
DBSERVER_OBJECT_GET_FIELDS_RESP = 3005
DBSERVER_OBJECT_GET_ALL = 3006
DBSERVER_OBJECT_GET_ALL_RESP = 3007
DBSERVER_OBJECT_SET_FIELD = 3008
DBSERVER_OBJECT_SET_FIELDS = 3009
DBSERVER_OBJECT_SET_FIELD_IF_EQUALS = 3010
DBSERVER_OBJECT_SET_FIELD_IF_EQUALS_RESP = 3011
DBSERVER_OBJECT_SET_FIELDS_IF_EQUALS = 3012
DBSERVER_OBJECT_SET_FIELDS_IF_EQUALS_RESP = 3013
DBSERVER_OBJECT_SET_FIELD_IF_EMPTY = 3014
DBSERVER_OBJECT_SET_FIELD_IF_EMPTY_RESP = 3015
DBSERVER_OBJECT_DELETE_FIELD = 3016
DBSERVER_OBJECT_DELETE_FIELDS = 3017
DBSERVER_OBJECT_DELETE = 3018
