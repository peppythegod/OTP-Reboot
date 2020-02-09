"""
 * Copyright (C) Caleb Marshall - All Rights Reserved
 * Written by Caleb Marshall <anythingtechpro@gmail.com>, August 17th, 2017
 * Licensing information can found in 'LICENSE', which is part of this source code package.
"""

CLIENTAGENT_CHANNEL = 1000
STATESERVER_CHANNEL = 1001
DATABASE_CHANNEL = 1002

UD_CHANNEL = 400000000

# Broadcast Channels
CHANNEL_CLIENT_BROADCAST = 4014
OTP_CHANNEL_AI_AND_UD_BROADCAST = 4602
OTP_CHANNEL_UD_BROADCAST = 4603
OTP_CHANNEL_AI_BROADCAST = 4604

# Custom Internal Control Messages
CONTROL_MESSAGE = 1
CONTROL_SET_CHANNEL = 2002
CONTROL_REMOVE_CHANNEL = 2003
CONTROL_SET_CON_NAME = 2004
CONTROL_SET_CON_URL = 2005
CONTROL_ADD_RANGE = 2006
CONTROL_REMOVE_RANGE = 2007
CONTROL_ADD_POST_REMOVE = 2008
CONTROL_CLEAR_POST_REMOVE = 2009

CLIENT_LOGIN = 1
CLIENT_LOGIN_RESP = 2
CLIENT_GET_AVATARS = 3
CLIENT_GO_GET_LOST = 4
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
CLIENT_OBJECT_UPDATE_FIELD = 24
CLIENT_OBJECT_UPDATE_FIELD_RESP = 24
CLIENT_OBJECT_DISABLE = 25
CLIENT_OBJECT_DISABLE_RESP = 25
CLIENT_OBJECT_DISABLE_OWNER = 26
CLIENT_OBJECT_DISABLE_OWNER_RESP = 26
CLIENT_OBJECT_DELETE = 27
CLIENT_OBJECT_DELETE_RESP = 27
CLIENT_SET_ZONE = 29 # Same thing as CLIENT_SET_ZONE_CMU?
CLIENT_SET_ZONE_CMU = 29
CLIENT_REMOVE_ZONE = 30
CLIENT_SET_SHARD = 31
CLIENT_SET_AVATAR = 32
CLIENT_CREATE_OBJECT_REQUIRED = 34
CLIENT_CREATE_OBJECT_REQUIRED_RESP = 34
CLIENT_CREATE_OBJECT_REQUIRED_OTHER = 35
CLIENT_CREATE_OBJECT_REQUIRED_OTHER_RESP = 35
CLIENT_CREATE_OBJECT_REQUIRED_OTHER_OWNER = 36
CLIENT_CREATE_OBJECT_REQUIRED_OTHER_OWNER_RESP = 36
CLIENT_REQUEST_GENERATES = 36
CLIENT_DISCONNECT = 37
CLIENT_CHANGE_IP_ADDRESS_RESP = 45
CLIENT_GET_STATE = 46
CLIENT_GET_STATE_RESP = 47
CLIENT_DONE_INTEREST_RESP = 48
CLIENT_DONE_SET_ZONE_RESP = 48 # CMU Only?
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
CLIENT_SET_DOID_RANGE = 74
CLIENT_GET_AVATARS_RESP2 = 75
CLIENT_CREATE_AVATAR2 = 76
CLIENT_SYSTEM_MESSAGE = 78
CLIENT_SET_AVTYPE = 80
CLIENT_GET_PET_DETAILS = 81
CLIENT_GET_PET_DETAILS_RESP = 82
CLIENT_ADD_INTEREST = 97
CLIENT_REMOVE_INTEREST = 99
CLIENT_OBJECT_LOCATION = 102
CLIENT_LOGIN_3 = 111
CLIENT_LOGIN_3_RESP = 110
CLIENT_GET_FRIEND_LIST_EXTENDED = 115
CLIENT_GET_FRIEND_LIST_EXTENDED_RESP = 116
CLIENT_SET_FIELD_SENDABLE = 120
CLIENT_SYSTEMMESSAGE_AKNOWLEDGE = 123
CLIENT_CHANGE_GENERATE_ORDER = 124
CLIENT_LOGIN_TOONTOWN = 125
CLIENT_LOGIN_TOONTOWN_RESP = 126

# Login 2 Types
CLIENT_LOGIN_2_GREEN = 1
CLIENT_LOGIN_2_PLAY_TOKEN = 2
CLIENT_LOGIN_2_BLUE = 3

# Custom Internal Disconnect Types
CLIENT_DISCONNECT_INVALID_MSGTYPE = 108
CLIENT_DISCONNECT_NO_HEARTBEAT = 345
CLIENT_DISCONNECT_ALREADY_LOGGED_IN = 346
CLIENT_DISCONNECT_BAD_VERSION = 124
CLIENT_DISCONNECT_BAD_DCHASH = 125
CLIENT_DISCONNECT_INVALID_PLAY_TOKEN_TYPE = 284
CLIENT_DISCONNECT_TRUNCATED_DATAGRAM = 109
CLIENT_DISCONNECT_ANONYMOUS_VIOLATION = 113
CLIENT_DISCONNECT_SHARD_CLOSED = 114

# Debug Stuff
CLIENT_DEBUG_SET_NAME = 201
CLIENT_DEBUG_AUTHENTICATE_ADMIN = 202

# What are these used for?
ACCOUNT_AVATAR_USAGE = 3005
ACCOUNT_ACCOUNT_USAGE = 3006

# Custom CLIENT_AGENT Message Types
CLIENT_AGENT_DISCONNECT = 1000
CLIENT_AGENT_FRIEND_ONLINE = 1001
CLIENT_AGENT_FRIEND_OFFLINE = 1002

CLIENT_AGENT_OPEN_CHANNEL = 3104
CLIENT_AGENT_CLOSE_CHANNEL = 3105
CLIENT_AGENT_SET_INTEREST = 3106
CLIENT_AGENT_REMOVE_INTEREST = 3107

# What is this for?
CHANNEL_PUPPET_ACTION = 4004

# Server Ping.
SERVER_PING = 5002

STATESERVER_OBJECT_GENERATE_WITH_REQUIRED = 2001
STATESERVER_OBJECT_GENERATE_WITH_REQUIRED_OTHER = 2003
STATESERVER_OBJECT_UPDATE_FIELD = 2004
STATESERVER_OBJECT_UPDATE_FIELD_MULTIPLE = 2005
STATESERVER_OBJECT_DELETE_RAM = 2007
STATESERVER_OBJECT_SET_ZONE = 2008
STATESERVER_OBJECT_SET_ZONE_RESP = 2008
STATESERVER_OBJECT_CHANGE_ZONE = 2009
STATESERVER_OBJECT_NOTFOUND = 2015
STATESERVER_QUERY_OBJECT_ALL = 2020
STATESERVER_QUERY_ZONE_OBJECT_ALL = 2021
STATESERVER_OBJECT_LOCATE = 2022
STATESERVER_OBJECT_LOCATE_RESP = 2023
STATESERVER_OBJECT_QUERY_FIELD = 2024
STATESERVER_QUERY_OBJECT_ALL_RESP = 2030
STATESERVER_OBJECT_LEAVING_AI_INTEREST = 2033
STATESERVER_ADD_AI_RECV = 2045
STATESERVER_QUERY_ZONE_OBJECT_ALL_DONE = 2046
STATESERVER_OBJECT_CREATE_WITH_REQUIRED_CONTEXT = 2050
STATESERVER_OBJECT_CREATE_WITH_REQUIR_OTHER_CONTEXT = 2051
STATESERVER_OBJECT_CREATE_WITH_REQUIRED_CONTEXT_RESP = 2052
STATESERVER_OBJECT_CREATE_WITH_REQUIR_OTHER_CONTEXT_RESP = 2053
STATESERVER_OBJECT_DELETE_DISK = 2060
STATESERVER_SHARD_REST = 2061
STATESERVER_OBJECT_QUERY_FIELD_RESP = 2062
STATESERVER_OBJECT_ENTERZONE_WITH_REQUIRED_OTHER = 2066
STATESERVER_OBJECT_ENTER_AI_RECV = 2067
STATESERVER_OBJECT_ENTER_OWNER_RECV = 2068
STATESERVER_OBJECT_CHANGE_OWNER_RECV = 2069
STATESERVER_OBJECT_SET_OWNER_RECV = 2070
STATESERVER_OBJECT_QUERY_FIELDS = 2080
STATESERVER_OBJECT_QUERY_FIELDS_RESP = 2081
STATESERVER_OBJECT_QUERY_FIELDS_STRING = 2082
STATESERVER_OBJECT_QUERY_MANAGING_AI = 2083
STATESERVER_BOUNCE_MESSAGE = 2086
STATESERVER_QUERY_OBJECT_CHILDREN_LOCAL = 2087
STATESERVER_QUERY_OBJECT_CHILDREN_RESP = 2087
STATESERVER_QUERY_OBJECT_CHILDREN_LOCAL_DONE = 2089

# Custom STATESERVER Message Types
STATESERVER_OBJECT_ENTER_LOCATION_WITH_REQUIRED = 2090
STATESERVER_OBJECT_ENTER_LOCATION_WITH_REQUIRED_OTHER = 2091
STATESERVER_OBJECT_ENTER_AI_WITH_REQUIRED = 2092
STATESERVER_OBJECT_ENTER_AI_WITH_REQUIRED_OTHER = 2093
STATESERVER_OBJECT_SET_OWNER = 2094
STATESERVER_OBJECT_CHANGING_OWNER = 2095
STATESERVER_OBJECT_SET_LOCATION = 2096
STATESERVER_OBJECT_CHANGING_LOCATION = 2097
STATESERVER_OBJECT_LOCATION_ACK = 2098
STATESERVER_OBJECT_SET_AI = 2099
STATESERVER_OBJECT_SET_AI_RESP = 2100
STATESERVER_OBJECT_CHANGING_AI = 2101
STATESERVER_OBJECT_ENTER_OWNER_WITH_REQUIRED = 2102
STATESERVER_OBJECT_ENTER_OWNER_WITH_REQUIRED_OTHER = 2103
STATESERVER_OBJECT_GET_ZONES_OBJECTS = 2104
STATESERVER_OBJECT_GET_ZONES_OBJECTS_RESP = 2105
STATESERVER_OBJECT_GET_ZONES_OBJECTS_2 = 2106
STATESERVER_OBJECT_GET_ZONES_OBJECTS_2_RESP = 2107
STATESERVER_OBJECT_CLEAR_WATCH = 2108
STATESERVER_ADD_SHARD = 2109
STATESERVER_REMOVE_SHARD = 2110
STATESERVER_UPDATE_SHARD = 2111
STATESERVER_GET_SHARD_ALL = 2112
STATESERVER_GET_SHARD_ALL_RESP = 2113

DBSERVER_CREATE_STORED_OBJECT = 1003
DBSERVER_CREATE_STORED_OBJECT_RESP = 1004
DBSERVER_DELETE_STORED_OBJECT = 1008
DBSERVER_GET_STORED_VALUES = 1012
DBSERVER_GET_STORED_VALUES_RESP = 1013
DBSERVER_SET_STORED_VALUES = 1014
DBSERVER_MAKE_FRIENDS = 1017
DBSERVER_MAKE_FRIENDS_RESP = 1031
DBSERVER_REQUEST_SECRET = 1025
DBSERVER_REQUEST_SECRET_RESP = 1026
DBSERVER_SUBMIT_SECRET = 1027
DBSERVER_SUBMIT_SECRET_RESP = 1028

# Custom DBSERVER Message Types
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