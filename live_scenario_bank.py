# LIVE WEB SCENARIO BANK
# Curated, reproducible, non-destructive real-world web benchmarking scenarios.

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
    }
}
