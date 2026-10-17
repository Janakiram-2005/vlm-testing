# LIVE WEB SCENARIO BANK
# Curated, reproducible, non-destructive real-world web benchmarking scenarios.
# All 16 platforms feature strictly non-overlapping, distinct test dimensions:
# - Normal: Direct UI navigation, icon clicking, or tab switching (No redundant typing)
# - Difficult: Multi-step chained search, form entry, or scroll-and-select workflows.

LIVE_SCENARIO_BANK = {
    'Amazon': {
        'url': 'https://www.amazon.com',
        'tier': 'guest',
        'normal': [
            "Click on the 'Today's Deals' navigation link in the top menu bar",
            "Click on the 'Customer Service' link in the top nav",
            "Click the Cart icon button on the top right"
        ],
        'difficult': [
            "Type 'wireless mouse' into search bar, press Enter, AND then click the first product card title"
        ]
    },
    'Wikipedia': {
        'url': 'https://www.wikipedia.org',
        'tier': 'guest',
        'normal': [
            "Click the English language link to navigate to the English main page"
        ],
        'difficult': [
            "Click the English language link, AND then click on the 'In the news' or 'Today's featured article' title"
        ]
    },
    'YouTube': {
        'url': 'https://www.youtube.com',
        'tier': 'guest',
        'normal': [
            "Click on the first video thumbnail in the home feed",
            "Click the search button with the magnifying glass icon"
        ],
        'difficult': [
            "Type 'classical piano' in search, press Enter, AND then click the first video title in search results"
        ]
    },
    'GitHub': {
        'url': 'https://github.com/explore',
        'tier': 'guest',
        'normal': [
            "Click the 'Trending' navigation tab at the top",
            "Click on the 'Topics' navigation link"
        ],
        'difficult': [
            "Type 'vision language models' in search bar, press Enter, AND then click the first repository card"
        ]
    },
    'Online_Spreadsheet': {
        'url': 'https://ethercalc.net/test_vlm_sandbox',
        'tier': 'guest',
        'normal': [
            "Click the Bold icon (B) on the top formatting toolbar",
            "Click on cell B2 and type '1000'"
        ],
        'difficult': [
            "Click on cell B2, type 'Revenue', press Enter, AND then click cell C2 and type '50000'"
        ]
    },
    'DuckDuckGo': {
        'url': 'https://duckduckgo.com',
        'tier': 'guest',
        'normal': [
            "Click the Settings hamburger menu icon on the top right"
        ],
        'difficult': [
            "Type 'autonomous agents' in search bar, press Enter, AND then click the 'Images' tab"
        ]
    },
    'HackerNews': {
        'url': 'https://news.ycombinator.com',
        'tier': 'guest',
        'normal': [
            "Click on the 'new' navigation link in the top orange header",
            "Click on the 'past' navigation link in the top header",
            "Click on the 'ask' navigation link in the top menu bar"
        ],
        'difficult': [
            "Click on the first article's comments link, AND then scroll down 400 pixels"
        ]
    },
    'BBC_News': {
        'url': 'https://www.bbc.com',
        'tier': 'guest',
        'normal': [
            "Click the 'Innovation' category link in the top menu bar",
            "Click the 'Business' category link in the menu bar"
        ],
        'difficult': [
            "Click on the primary headline title on the homepage, AND then scroll down 500 pixels"
        ]
    },
    'MDN_Docs': {
        'url': 'https://developer.mozilla.org',
        'tier': 'guest',
        'normal': [
            "Click on the 'References' navigation dropdown menu at the top"
        ],
        'difficult': [
            "Type 'Array filter' into search input, press Enter, AND then click the first search result link"
        ]
    },
    'IMDb': {
        'url': 'https://www.imdb.com',
        'tier': 'guest',
        'normal': [
            "Click the 'Menu' button next to the IMDb logo"
        ],
        'difficult': [
            "Type 'Interstellar' into search bar, press Enter, AND then click the first movie card title"
        ]
    },
    'Desmos_Calculator': {
        'url': 'https://www.desmos.com/scientific',
        'tier': 'guest',
        'normal': [
            "Click the 'clear' or 'clear all' button on the keypad"
        ],
        'difficult': [
            "Click button '7', click the multiplication operator button, click button '8', AND then click '='"
        ]
    },
    'Internet_Archive': {
        'url': 'https://archive.org',
        'tier': 'guest',
        'normal': [
            "Click on the 'Books' icon in the top media collection bar",
            "Click on the 'Audio' icon in the top media category bar"
        ],
        'difficult': [
            "Type 'https://google.com' in the Wayback Machine search input bar and press Enter"
        ]
    },
    'Worldometers': {
        'url': 'https://www.worldometers.info',
        'tier': 'guest',
        'normal': [
            "Click on the 'World Population' section link"
        ],
        'difficult': [
            "Scroll down 600 pixels, AND then click the 'Countries in the world' link"
        ]
    },
    'W3Schools': {
        'url': 'https://www.w3schools.com',
        'tier': 'guest',
        'normal': [
            "Click on the 'HTML' tutorial card on the homepage",
            "Click on the 'Tutorials' dropdown button in the navigation bar"
        ],
        'difficult': [
            "Type 'CSS Flexbox' in search bar, press Enter, AND then click the first tutorial result"
        ]
    },
    'ArXiv': {
        'url': 'https://arxiv.org',
        'tier': 'guest',
        'normal': [
            "Click on the 'Computer Science' link under subject categories",
            "Click the 'Advanced Search' link next to the search input"
        ],
        'difficult': [
            "Type 'reinforcement learning' in the search bar, click Search, AND then click the first paper's 'pdf' link"
        ]
    },
    'Captcha_Demo': {
        'url': 'https://www.google.com/recaptcha/api2/demo',
        'tier': 'guest',
        'normal': [
            "Click the 'I'm not a robot' checkbox inside the reCAPTCHA box"
        ],
        'difficult': [
            "Click the 'I'm not a robot' checkbox, AND then click the blue 'Submit' button"
        ]
    }
}
