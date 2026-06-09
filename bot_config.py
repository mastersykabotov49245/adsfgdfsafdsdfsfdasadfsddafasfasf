import os

DATA_DIR = "data"
USERS_FILE = os.path.join(DATA_DIR, "users.json")
BLOCKED_NFT_FILE = os.path.join(DATA_DIR, "blocked_nft.json")
TEMPLATES_FILE = os.path.join(DATA_DIR, "templates.json")
USER_SETTINGS_FILE = os.path.join(DATA_DIR, "user_settings.json")
STATS_FILE = os.path.join(DATA_DIR, "stats.json")

if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

BOT_TOKEN = "8634648515:AAGhffesBb4QS3HdwdWizq3Rg4sMdBVNZUo"
ADMINS = [47766426]

REQUIRED_CHANNEL_LINK = "https://t.me/+GT3Dv0_bz-c3NjI1"
REQUIRED_CHANNEL_ID = -1003903354526

SEARCH_LIMIT_OPTIONS = [10, 15, 20, 30, 40, 50]
DEFAULT_SEARCH_LIMIT = 15
MAX_SEARCH_LIMIT = 50

HTTP_TIMEOUT = 2.0
CONCURRENT_REQUESTS = 30
REQUEST_DELAY = 0.01
MAX_SEARCH_TIME = 60
MAX_SEARCH_TIME_GIRLS = 120

ULTRA_FAST_SEARCH_SETTINGS = {
    "max_parallel_requests": 50,
    "wave_size": 100,
    "batch_size": 50,
    "waves_per_search": 20,
    "delay_between_waves": 0.05,
    "timeout": {
        "total": 1.0,
        "connect": 0.2,
        "sock_connect": 0.2,
        "sock_read": 0.3
    }
}

MAX_SEARCH_TIME = 45

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

BANNED_USERNAMES = [
    "giftstoportals", "cryptolordnn", "turbo_ultra", "ballsbank", 
    "giftrelayer", "mrktbank", "rolls_transfer", "sho_tak0e", 
    "@snoopdogg", '@gemsrelayer', "@GiftsDefender", "@gifton_transfer",
    "@gbrelayer", "@giftsstrategy_relayer", "@GameRelayer"
]

SEARCH_MODES = {
    "easy": {
        "name": "🟢 Легкий режим",
        "description": "Недорогие подарки до 3 TON\nСамые неопытные пользователи",
        "collections": [
            {"name": "BDayCandle", "id_range": (1000, 20000)},
            {"name": "CandyCane", "id_range": (1000, 150000)},
            {"name": "CloverPin", "id_range": (1000, 60000)},
            {"name": "DeskCalendar", "id_range": (1000, 13000)},
            {"name": "FaithAmulet", "id_range": (1000, 60000)},
            {"name": "FreshSocks", "id_range": (1000, 100000)},
            {"name": "GingerCookie", "id_range": (1000, 60000)},
            {"name": "HappyBrownie", "id_range": (1000, 60000)},
            {"name": "HolidayDrink", "id_range": (1000, 60000)},
            {"name": "HomemadeCake", "id_range": (1000, 130000)},
            {"name": "IceCream", "id_range": (1000, 60000)},
            {"name": "InstantRamen", "id_range": (1000, 60000)},
            {"name": "JesterHat", "id_range": (1000, 60000)},
            {"name": "JingleBells", "id_range": (1000, 60000)},
            {"name": "LolPop", "id_range": (1000, 130000)},
            {"name": "LunarSnake", "id_range": (1000, 250000)},
            {"name": "PetSnake", "id_range": (1000, 1000)},
            {"name": "SnakeBox", "id_range": (1000, 55000)},
            {"name": "SnoopDogg", "id_range": (576241, 576241)},
            {"name": "SpicedWine", "id_range": (93557, 93557)},
            {"name": "WhipCupcake", "id_range": (1000, 170000)},
            {"name": "WinterWreath", "id_range": (65311, 65311)},
            {"name": "XmasStocking", "id_range": (177478, 177478)},
        ]
    },
    "medium": {
        "name": "🟡 Средний режим",
        "description": "Хорошие подарки от 3 до 15 TON\nБолее опытные пользователи",
        "collections": [
            {"name": "BerryBox", "id_range": (1000, 60000)},
            {"name": "BigYear", "id_range": (1000, 60000)},
            {"name": "BowTie", "id_range": (1000, 47000)},
            {"name": "BunnyMuffin", "id_range": (1000, 60000)},
            {"name": "CookieHeart", "id_range": (1000, 60000)},
            {"name": "EasterEgg", "id_range": (1000, 60000)},
            {"name": "EternalCandle", "id_range": (1000, 60000)},
            {"name": "EvilEye", "id_range": (1000, 60000)},
            {"name": "HexPot", "id_range": (1000, 50000)},
            {"name": "HypnoLollipop", "id_range": (1000, 60000)},
            {"name": "InputKey", "id_range": (1000, 80000)},
            {"name": "JackInTheBox", "id_range": (1000, 60000)},
            {"name": "JellyBunny", "id_range": (1000, 60000)},
            {"name": "JollyChimp", "id_range": (1000, 25000)},
            {"name": "JoyfulBundle", "id_range": (1000, 60000)},
            {"name": "LightSword", "id_range": (1000, 110000)},
            {"name": "LushBouquet", "id_range": (1000, 60000)},
            {"name": "MousseCake", "id_range": (119126, 119126)},
            {"name": "PartySparkler", "id_range": (161722, 161722)},
            {"name": "RestlessJar", "id_range": (1000, 23000)},
            {"name": "SantaHat", "id_range": (19289, 19289)},
            {"name": "SnoopCigar", "id_range": (1000, 60000)},
            {"name": "SnowGlobe", "id_range": (48029, 48029)},
            {"name": "SnowMittens", "id_range": (64057, 64057)},
            {"name": "SpringBasket", "id_range": (140160, 140160)},
            {"name": "SpyAgaric", "id_range": (84274, 84274)},
            {"name": "StarNotepad", "id_range": (1000, 25000)},
            {"name": "StellarRocket", "id_range": (1000, 35000)},
            {"name": "SwagBag", "id_range": (1000, 5000)},
            {"name": "TamaGadget", "id_range": (95205, 95205)},
            {"name": "ValentineBox", "id_range": (229868, 229868)},
            {"name": "WitchHat", "id_range": (1000, 7000)},
            {"name": "UFCStrike", "id_range": (1000, 56951)},
        ]
    },
    "hard": {
        "name": "🔴 Жирный режим",
        "description": "Дорогие подарки от 15 до 600 TON\nОпытные коллекционеры",
        "collections": [
            {"name": "ArtisanBrick", "id_range": (1000, 7000)},
            {"name": "AstralShard", "id_range": (1000, 60000)},
            {"name": "BondedRing", "id_range": (1000, 3000)},
            {"name": "CupidCharm", "id_range": (1000, 60000)},
            {"name": "DiamondRing", "id_range": (1000, 60000)},
            {"name": "DurovsCap", "id_range": (1000, 60000)},
            {"name": "EternalRose", "id_range": (1000, 60000)},
            {"name": "FlyingBroom", "id_range": (1000, 60000)},
            {"name": "GemSignet", "id_range": (1000, 60000)},
            {"name": "GenieLamp", "id_range": (1000, 60000)},
            {"name": "GustalBall", "id_range": (1000, 60000)},
            {"name": "HeartLocket", "id_range": (1000, 60000)},
            {"name": "HeroicHelmet", "id_range": (1000, 60000)},
            {"name": "IonGem", "id_range": (1000, 60000)},
            {"name": "IonicDryer", "id_range": (1000, 60000)},
            {"name": "KissedFrog", "id_range": (1000, 60000)},
            {"name": "LootBag", "id_range": (1000, 60000)},
            {"name": "LoveCandle", "id_range": (1000, 60000)},
            {"name": "LovePotion", "id_range": (1000, 60000)},
            {"name": "LowRider", "id_range": (1000, 60000)},
            {"name": "MadPumpkin", "id_range": (96227, 96227)},
            {"name": "MagicPotion", "id_range": (4764, 4764)},
            {"name": "MightyArm", "id_range": (150000, 150000)},
            {"name": "MiniOscar", "id_range": (4764, 4764)},
            {"name": "NailBracelet", "id_range": (119126, 119126)},
            {"name": "NekoHelmet", "id_range": (15431, 15431)},
            {"name": "PerfumeBottle", "id_range": (151632, 151632)},
            {"name": "PreciousPeach", "id_range": (2981, 2981)},
            {"name": "RecordPlayer", "id_range": (554, 554)},
            {"name": "ScaredCat", "id_range": (8029, 8029)},
            {"name": "SharpTongue", "id_range": (1000, 16430)},
            {"name": "SignetRing", "id_range": (1000, 16430)},
            {"name": "SkullFlower", "id_range": (1000, 21428)},
            {"name": "SkyStilettos", "id_range": (1000, 47465)},
            {"name": "SleighBell", "id_range": (1000, 48029)},
            {"name": "SwissWatch", "id_range": (1000, 25121)},
            {"name": "TopHat", "id_range": (1000, 32648)},
            {"name": "ToyBear", "id_range": (1000, 60000)},
            {"name": "TrappedHeart", "id_range": (1000, 24656)},
            {"name": "VintageCigar", "id_range": (1000, 18000)},
            {"name": "VoodooDoll", "id_range": (1000, 26658)},
        ]
    }
}

EXCLUDED_NFT = ["PlushPepe"]

SEARCH_ANIMATION = [
    "🔍 ▰▱▱▱▱▱▱▱▱ Поиск NFT...",
    "🔍 ▰▰▱▱▱▱▱▱▱ Поиск NFT...", 
    "🔍 ▰▰▰▱▱▱▱▱▱ Поиск NFT...",
    "🔍 ▰▰▰▰▱▱▱▱▱ Поиск NFT...",
    "🔍 ▰▰▰▰▰▱▱▱▱ Поиск NFT...",
    "🔍 ▰▰▰▰▰▰▱▱▱ Поиск NFT...",
    "🔍 ▰▰▰▰▰▰▰▱▱ Поиск NFT...",
    "🔍 ▰▰▰▰▰▰▰▰▱ Поиск NFT...",
    "🔍 ▰▰▰▰▰▰▰▰▰ Поиск NFT...",
    "🔍 Анализ результатов..."
]