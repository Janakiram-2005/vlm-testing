# LIVE WEB SCENARIO BANK
# Curated, reproducible, non-destructive real-world web benchmarking scenarios.
# Expanded to 15 diverse, login-free, high-traffic platforms across distinct UI paradigms.

LIVE_SCENARIO_BANK = {
    'Amazon': {
        'url': 'https://www.amazon.com',
        'tier': 'guest',
        'normal': [
            "Type 'wireless mouse' into the top search bar and press Enter",
            "Click the 4 Stars & Up customer review filter on the left sidebar",
            "Click the search icon button next to the search input bar"
        ],
        'difficult': [
            "Type 'mechanical keyboard' into search bar, press Enter, AND then click the first product card title"
        ]
    },
    'Wikipedia': {
        'url': 'https://www.wikipedia.org',
        'tier': 'guest',
        'normal': [
            "Type 'Artificial Intelligence' in the search input and click Search",
            "Click the English language link to navigate to the English main page",
            "Click on the search button with the magnifying glass icon"
        ],
        'difficult': [
            "Type 'Quantum Computing' in search, click Search, AND then click 'History' in the Table of Contents"
        ]
    },
    'YouTube': {
        'url': 'https://www.youtube.com',
        'tier': 'guest',
        'normal': [
            "Type 'nature documentary 4k' into the search input and click Search",
            "Click on the first video thumbnail in the feed",
            "Click the search button with the magnifying glass icon"
        ],
        'difficult': [
            "Type 'classical music' in search, press Enter, AND then click the first video title in search results"
        ]
    },
    'GitHub': {
        'url': 'https://github.com/explore',
        'tier': 'guest',
        'normal': [
            "Type 'vision language models' in the top search bar and press Enter",
            "Click the 'Trending' navigation tab at the top",
            "Click on the 'Topics' navigation link"
        ],
        'difficult': [
            "Type 'deep learning' in search bar, press Enter, AND then click the 'Repositories' filter on the left"
        ]
    },
    'Online_Spreadsheet': {
        'url': 'https://ethercalc.net/test_vlm_sandbox',
        'tier': 'guest',
        'normal': [
            "Click on cell C3 and type 'Q3 Profit'",
            "Click the Bold icon (B) on the top formatting toolbar",
            "Click on cell B2 and type '1000'"
        ],
        'difficult': [
            "Click on cell C3, type 'Revenue', AND then click cell D3 and type '50000'"
        ]
    },
    'DuckDuckGo': {
        'url': 'https://duckduckgo.com',
        'tier': 'guest',
        'normal': [
            "Type 'autonomous AI agents' in search bar and click Search",
            "Click the Settings hamburger menu icon on the top right",
            "Type 'weather forecast' in search input and press Enter"
        ],
        'difficult': [
            "Type 'deep learning' in search bar, press Enter, AND then click the 'Images' tab"
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
            "Click the 'Innovation' or 'Tech' navigation tab in the top header",
            "Click on the 'Business' category link in the menu bar",
            "Click on the primary headline title on the homepage"
        ],
        'difficult': [
            "Click the 'Sport' navigation tab, AND then click the first featured match report headline"
        ]
    },
    'MDN_Docs': {
        'url': 'https://developer.mozilla.org',
        'tier': 'guest',
        'normal': [
            "Type 'Array filter' into the top search bar and press Enter",
            "Click on the 'References' navigation menu at the top",
            "Type 'fetch API' in the search input and press Enter"
        ],
        'difficult': [
            "Type 'Promise' into search input, press Enter, AND then click the first search result link"
        ]
    },
    'IMDb': {
        'url': 'https://www.imdb.com',
        'tier': 'guest',
        'normal': [
            "Type 'Interstellar' into the top search bar and click Search",
            "Click the 'Menu' button next to the IMDb logo",
            "Type 'Oppenheimer' into search bar and press Enter"
        ],
        'difficult': [
            "Type 'The Dark Knight' into search bar, press Enter, AND then click the first movie card title"
        ]
    },
    'Desmos_Calculator': {
        'url': 'https://www.desmos.com/scientific',
        'tier': 'guest',
        'normal': [
            "Click the number button '7', click the '+' button, click '8', and click '='",
            "Click the number button '9', click the '×' multiplication button, and click '5'",
            "Click the 'clear' or 'clear all' button on the keypad"
        ],
        'difficult': [
            "Click button '2', click button '5', click button '×', click button '4', AND then click '='"
        ]
    },
    'Internet_Archive': {
        'url': 'https://archive.org',
        'tier': 'guest',
        'normal': [
            "Type 'https://google.com' in the Wayback Machine search input bar and press Enter",
            "Click on the 'Books' icon in the top media collection bar",
            "Click on the 'Audio' icon in the top media category bar"
        ],
        'difficult': [
            "Type 'NASA archives' into the main search box, press Enter, AND then click the first collection item"
        ]
    },
    'Worldometers': {
        'url': 'https://www.worldometers.info',
        'tier': 'guest',
        'normal': [
            "Click on the 'World Population' section link",
            "Scroll down to view the Current World Population counter",
            "Click on the 'Coronavirus' statistical link"
        ],
        'difficult': [
            "Click on 'World Population', scroll down 600 pixels, AND then click the 'Countries in the world' link"
        ]
    },
    'W3Schools': {
        'url': 'https://www.w3schools.com',
        'tier': 'guest',
        'normal': [
            "Click on the 'HTML' tutorial card on the homepage",
            "Type 'CSS Flexbox' in the search bar and press Enter",
            "Click on the 'Tutorials' dropdown button in the navigation bar"
        ],
        'difficult': [
            "Click on 'Python' tutorial, AND then click the green 'Try it Yourself' button"
        ]
    },
    'ArXiv': {
        'url': 'https://arxiv.org',
        'tier': 'guest',
        'normal': [
            "Type 'vision language models' in the search input and click Search",
            "Click on the 'Computer Science' link under subject categories",
            "Click the 'Advanced Search' link next to the search input"
        ],
        'difficult': [
            "Type 'reinforcement learning' in the search bar, click Search, AND then click the first paper's 'pdf' link"
        ]
    }
}
