#!/usr/bin/env python3
"""
TLD Database - Organized by theme
"""

TLD_DATABASE = {
    '⭐ Premium': [
        '.com', '.io', '.app', '.dev', '.tech', '.ai', '.co', '.org', '.net'
    ],
    '🔥 Popular': [
        '.info', '.biz', '.name', '.pro', '.mobi', '.tel', '.travel'
    ],
    '🏢 Business': [
        '.academy', '.agency', '.associates', '.business', '.capital',
        '.company', '.consulting', '.enterprises', '.executive', '.finance',
        '.financial', '.industries', '.insure', '.investments', '.management',
        '.market', '.marketing', '.markets', '.mba', '.partner', '.partners',
        '.properties', '.property', '.ventures'
    ],
    '💻 Technology': [
        '.app', '.cloud', '.code', '.codes', '.computer', '.data', '.digital',
        '.dev', '.engineer', '.engineering', '.host', '.hosting', '.io',
        '.network', '.online', '.site', '.software', '.systems', '.tech',
        '.technology', '.web', '.website'
    ],
    '🏠 Home & Living': [
        '.apartments', '.builders', '.casa', '.construction', '.design',
        '.garden', '.homes', '.house', '.kitchen', '.land', '.maison',
        '.realestate', '.realty', '.renovations'
    ],
    '🎨 Creative': [
        '.art', '.design', '.diamonds', '.fashion', '.gallery', '.graphics',
        '.music', '.photo', '.photography', '.photos', '.pics', '.pictures',
        '.studio', '.video', '.watch', '.wiki'
    ],
    '🛍️ Shopping': [
        '.bargains', '.blackfriday', '.buy', '.camera', '.cards', '.cash',
        '.christmas', '.clothing', '.coupons', '.deals', '.direct', '.discount',
        '.furniture', '.gift', '.gifts', '.jewelry', '.loan', '.loans',
        '.ltd', '.pizza', '.plumbing', '.promo', '.purchase', '.recipes',
        '.restaurant', '.rich', '.salon', '.sarl', '.shoes', '.shop',
        '.shopping', '.store', '.tires', '.toys', '.trading', '.watch',
        '.wedding', '.wine'
    ],
    '📰 Media': [
        '.blog', '.book', '.click', '.com', '.digital', '.email', '.events',
        '.exposed', '.express', '.help', '.info', '.link', '.live',
        '.media', '.news', '.online', '.press', '.publishing', '.review',
        '.reviews', '.search', '.social', '.stream', '.tel', '.today',
        '.video', '.vip', '.website', 'world'
    ],
    '🎮 Entertainment': [
        '.actor', '.art', '.band', '.bar', '.bingo', '.casino', '.ceo',
        '.chat', '.club', '.coffee', '.cool', '.cruises', '.dance',
        '.dating', '.download', '.events', '.expert', '.fail', '.fans',
        '.flights', '.flowers', '.football', '.forsale', '.fun', '.game',
        '.games', '.golf', '.guru', '.hiphop', '.hockey', '.holiday',
        '.horse', '.immobilien', '.jetzt', '.lol', '.love', '.men',
        '.moda', '.movie', '.ninja', '.pics', '.pink', '.pizza', '.poker',
        '.porn', '.racing', '.restaurant', '.run', '.sexy', '.show',
        '.soccer', '.tattoo', '.tennis', '.theater', '.tours', '.town',
        '.training', '.travel', '.vacations', '.vet', '.villas', '.vision',
        '.voyage', '.wtf', '.xyz'
    ],
    '🏛️ Professional': [
        '.accountant', '.attorney', '.consulting', '.doctor', '.expert',
        '.health', '.healthcare', '.legal', '.life', '.lawyer', '.support',
        '.surgery', '.university'
    ],
    '🌍 Country': [
        '.us', '.uk', '.ca', '.au', '.de', '.fr', '.jp', '.cn', '.in', '.br',
        '.mx', '.it', '.es', '.nl', '.se', '.no', '.fi', '.dk', '.ch', '.at',
        '.be', '.pl', '.ru', '.za', '.kr', '.sg', '.nz', '.ie', '.eu',
        '.ac', '.ad', '.ae', '.af', '.ag', '.al', '.am', '.ao', '.aq', '.ar',
        '.as', '.aw', '.ax', '.az', '.ba', '.bb', '.bd', '.bf', '.bg', '.bh',
        '.bi', '.bj', '.bm', '.bn', '.bo', '.bs', '.bt', '.bv', '.bw', '.by',
        '.bz', '.cc', '.cd', '.cf', '.cg', '.ci', '.ck', '.cl', '.cm', '.cr',
        '.cu', '.cv', '.cw', '.cx', '.cy', '.cz', '.dj', '.dm', '.do', '.dz',
        '.ec', '.ee', '.eg', '.eh', '.er', '.et', '.fj', '.fk', '.fm', '.fo',
        '.ga', '.gd', '.ge', '.gf', '.gg', '.gh', '.gi', '.gl', '.gm', '.gn',
        '.gp', '.gq', '.gr', '.gs', '.gt', '.gu', '.gw', '.gy', '.hk', '.hm',
        '.hn', '.hr', '.ht', '.hu', '.id', '.ie', '.il', '.im', '.iq', '.ir',
        '.is', '.je', '.jm', '.jo', '.ke', '.kg', '.kh', '.ki', '.km', '.kn',
        '.kp', '.kw', '.ky', '.kz', '.la', '.lb', '.lc', '.li', '.lk', '.lr',
        '.ls', '.lt', '.lu', '.lv', '.ly', '.ma', '.mc', '.md', '.me', '.mg',
        '.mh', '.mk', '.ml', '.mm', '.mn', '.mo', '.mp', '.mq', '.mr', '.ms',
        '.mt', '.mu', '.mv', '.mw', '.my', '.mz', '.na', '.nc', '.ne', '.nf',
        '.ng', '.ni', '.np', '.nr', '.nu', '.nz', '.om', '.pa', '.pe', '.pf',
        '.pg', '.ph', '.pk', '.pl', '.pm', '.pn', '.pr', '.ps', '.pt', '.pw',
        '.py', '.qa', '.re', '.ro', '.rs', '.ru', '.rw', '.sa', '.sb', '.sc',
        '.sd', '.se', '.sh', '.si', '.sj', '.sk', '.sl', '.sm', '.sn', '.so',
        '.sr', '.ss', '.st', '.su', '.sv', '.sx', '.sy', '.sz', '.tc', '.td',
        '.tf', '.tg', '.th', '.tj', '.tk', '.tl', '.tm', '.tn', '.to', '.tp',
        '.tr', '.tt', '.tv', '.tw', '.tz', '.ua', '.ug', '.uy', '.uz', '.va',
        '.vc', '.ve', '.vg', '.vi', '.vn', '.vu', '.wf', '.ws', '.ye', '.yt',
        '.zm', '.zw'
    ]
}

# Flatten for checking
ALL_TLDS = []
for category_tlds in TLD_DATABASE.values():
    ALL_TLDS.extend(category_tlds)

# Remove duplicates while preserving order
ALL_TLDS = list(dict.fromkeys(ALL_TLDS))
