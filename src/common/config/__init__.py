import pymongo
import time
from pymongo.collection import Collection
from collections import defaultdict

from typing import Any, Optional


class BotConfig:
    __config_mongo: Optional[Collection] = None

    @classmethod
    def _get_config_mongo(cls) -> Collection:
        if cls.__config_mongo is None:
            mongo_client = pymongo.MongoClient('127.0.0.1', 27017, w=0)
            mongo_db = mongo_client['PallasBot']
            cls.__config_mongo = mongo_db['config']
            cls.__config_mongo.create_index(name='accounts_index',
                                            keys=[('account', pymongo.HASHED)])
        return cls.__config_mongo

    def __init__(self, bot_id: int, group_id: int = 0) -> None:
        self.bot_id = bot_id
        self.group_id = group_id
        self._mongo_find_key = {
            'account': bot_id
        }
        self.cooldown = 5   # 单位秒

    _cache = {}
    _cache_time = {}
    _cache_time_out = 600

    def _find_key(self, key: str) -> Any:
        if self.bot_id not in BotConfig._cache or \
                self.bot_id not in BotConfig._cache_time or \
                BotConfig._cache_time[self.bot_id] + BotConfig._cache_time_out < time.time():
            # print("refresh bot config from mongodb")
            info = self._get_config_mongo().find_one(self._mongo_find_key)
            BotConfig._cache[self.bot_id] = info
            BotConfig._cache_time[self.bot_id] = time.time()

        if self.bot_id in BotConfig._cache:
            _cache_bot = BotConfig._cache[self.bot_id]
            if _cache_bot and key in _cache_bot:
                return _cache_bot[key]

        return None

    def security(self) -> bool:
        '''
        账号是否安全（不处于风控等异常状态）
        '''
        security = self._find_key('security')
        return True if security else False

    def auto_accept(self) -> bool:
        '''
        是否自动接受加群、加好友请求
        '''
        accept = self._find_key('auto_accept')
        return True if accept else False

    def is_admin(self, user_id: int) -> bool:
        '''
        是否是管理员
        '''
        admins = self._find_key('admins')
        return user_id in admins if admins else False

    def add_admin(self, user_id: int) -> None:
        '''
        添加管理员
        '''
        self._get_config_mongo().update_one(
            self._mongo_find_key,
            {'$push': {'admins': user_id}},
            upsert=True
        )

    _cooldown_data = {}

    def is_cooldown(self, action_type: str) -> bool:
        '''
        是否冷却完成
        '''
        if self.bot_id not in BotConfig._cooldown_data:
            return True

        if self.group_id not in BotConfig._cooldown_data[self.bot_id]:
            return True

        if action_type not in BotConfig._cooldown_data[self.bot_id][self.group_id]:
            return True

        cd = BotConfig._cooldown_data[self.bot_id][self.group_id][action_type]
        return cd + self.cooldown < time.time()

    def refresh_cooldown(self, action_type: str) -> None:
        '''
        刷新冷却时间
        '''
        if self.bot_id not in BotConfig._cooldown_data:
            BotConfig._cooldown_data[self.bot_id] = {}

        if self.group_id not in BotConfig._cooldown_data[self.bot_id]:
            BotConfig._cooldown_data[self.bot_id][self.group_id] = {}

        BotConfig._cooldown_data[self.bot_id][self.group_id][action_type] = time.time(
        )

    _drunk_data = defaultdict(int)          # 醉酒程度，不同群应用不同的数值
    _sleep_until = defaultdict(lambda: defaultdict(int))    # 牛牛起床的时间

    def drink(self) -> None:
        '''
        喝酒功能，增加牛牛的混沌程度（bushi
        '''
        BotConfig._drunk_data[self.group_id] += 1

    def sober_up(self) -> bool:
        '''
        醒酒，降低醉酒程度，返回是否完全醒酒
        '''
        BotConfig._drunk_data[self.group_id] -= 1
        return BotConfig._drunk_data[self.group_id] <= 0

    def drunkenness(self) -> int:
        '''
        获取醉酒程度
        '''
        return BotConfig._drunk_data[self.group_id]

    def is_sleep(self) -> bool:
        '''
        牛牛睡了么？
        '''
        return BotConfig._sleep_until[self.bot_id][self.group_id] > time.time()

    def sleep(self, seconds: int) -> None:
        '''
        牛牛睡觉
        '''
        BotConfig._sleep_until[self.bot_id][self.group_id] = time.time(
        ) + seconds

    @staticmethod
    def completely_sober():
        for key in BotConfig._drunk_data.keys():
            BotConfig._drunk_data[key] = 0


class GroupConfig:
    __config_mongo: Optional[Collection] = None

    @classmethod
    def _get_config_mongo(cls) -> Collection:
        if cls.__config_mongo is None:
            mongo_client = pymongo.MongoClient('127.0.0.1', 27017, w=0)
            mongo_db = mongo_client['PallasBot']
            cls.__config_mongo = mongo_db['group_config']
            cls.__config_mongo.create_index(name='group_index',
                                            keys=[('group_id', pymongo.HASHED)])
        return cls.__config_mongo

    def __init__(self, group_id: int) -> None:
        self.group_id = group_id
        self._mongo_find_key = {
            'group_id': group_id
        }

    _cache = {}
    _cache_time = {}
    _cache_time_out = 600

    def _find_key(self, key: str) -> Any:
        if self.group_id not in GroupConfig._cache or \
                self.group_id not in GroupConfig._cache_time or \
                GroupConfig._cache_time[self.group_id] + GroupConfig._cache_time_out < time.time():
            # print("refresh group config from mongodb")
            info = self._get_config_mongo().find_one(self._mongo_find_key)
            GroupConfig._cache[self.group_id] = info
            GroupConfig._cache_time[self.group_id] = time.time()

        if self.group_id in GroupConfig._cache:
            _cache_group = GroupConfig._cache[self.group_id]
            if _cache_group and key in _cache_group:
                return _cache_group[key]

        return None

    _roulette_mode = {}    # 0 踢人 1 禁言

    def roulette_mode(self) -> int:
        '''
        获取轮盘模式

        :return: 0 踢人 1 禁言
        '''
        if self.group_id not in GroupConfig._roulette_mode:
            mode = self._find_key('roulette_mode')
            GroupConfig._roulette_mode[self.group_id] = mode if mode is not None else 0

        return GroupConfig._roulette_mode[self.group_id]

    def set_roulette_mode(self, mode: int) -> None:
        '''
        设置轮盘模式

        :param mode: 0 踢人 1 禁言
        '''
        GroupConfig._roulette_mode[self.group_id] = mode
        self._get_config_mongo().update_one(
            self._mongo_find_key,
            {'$set': {'roulette_mode': mode}},
            upsert=True
        )

    _ban_cache = {}

    def ban(self) -> None:
        '''
        拉黑该群
        '''
        GroupConfig._ban_cache[self.group_id] = True

        self._get_config_mongo().update_one(
            self._mongo_find_key,
            {'$set': {'banned': True}},
            upsert=True
        )

    def is_banned(self) -> bool:
        '''
        群是否被拉黑
        '''
        if self.group_id not in GroupConfig._ban_cache:
            banned = self._find_key('banned')
            GroupConfig._ban_cache[self.group_id] = True if banned else False

        return GroupConfig._ban_cache[self.group_id]


class UserConfig:
    __config_mongo: Optional[Collection] = None

    @classmethod
    def _get_config_mongo(cls) -> Collection:
        if cls.__config_mongo is None:
            mongo_client = pymongo.MongoClient('127.0.0.1', 27017, w=0)
            mongo_db = mongo_client['PallasBot']
            cls.__config_mongo = mongo_db['user_config']
            cls.__config_mongo.create_index(name='user_index',
                                            keys=[('user_id', pymongo.HASHED)])
        return cls.__config_mongo

    def __init__(self, user_id: int) -> None:
        self.user_id = user_id
        self._mongo_find_key = {
            'user_id': user_id
        }

    _cache = {}
    _cache_time = {}
    _cache_time_out = 600

    def _find_key(self, key: str) -> Any:
        if self.user_id not in UserConfig._cache or \
                self.user_id not in UserConfig._cache_time or \
                UserConfig._cache_time[self.user_id] + UserConfig._cache_time_out < time.time():
            # print("refresh group config from mongodb")
            info = self._get_config_mongo().find_one(self._mongo_find_key)
            UserConfig._cache[self.user_id] = info
            UserConfig._cache_time[self.user_id] = time.time()

        if self.user_id in UserConfig._cache:
            _cache_user = UserConfig._cache[self.user_id]
            if _cache_user and key in _cache_user:
                return _cache_user[key]

        return None

    _ban_cache = {}

    def ban(self) -> None:
        '''
        拉黑这个人
        '''
        UserConfig._ban_cache[self.user_id] = True

        self._get_config_mongo().update_one(
            self._mongo_find_key,
            {'$set': {'banned': True}},
            upsert=True
        )

    def is_banned(self) -> bool:
        '''
        是否被拉黑
        '''
        if self.user_id not in UserConfig._ban_cache:
            banned = self._find_key('banned')
            UserConfig._ban_cache[self.user_id] = True if banned else False

        return UserConfig._ban_cache[self.user_id]
