def _prepare_sequence(sequence):
    symbol_map = {
        '—': '-',
        '“': '«',
        '‘': '«',
        '”': '»',
        '’': '»',
        '😆': '😄',
        '😊': '😄',
        '😑': '😄',
        '😔': '😄',
        '😉': '😄',
        '❗': '😄',
        '🤔': '😄',
        '😅': '😄',
        '⚓': '😄',
        'ε': 'α',
        'ζ': 'α',
        'η': 'α',
        'μ': 'α',
        'δ': 'α',
        'λ': 'α',
        'ν': 'α',
        'β': 'α',
        'γ': 'α',
        'と': '尋',
        'の': '尋',
        '神': '尋',
        '隠': '尋',
        'し': '尋',
        'è': 'e',
        'ĕ': 'e',
        'ç': 'c',
        'ҫ': 'c',
        'ё': 'е',
        'Ё': 'Е',
        u'ú': 'u',
        u'Î': 'I',
        u'Ç': 'C',
        u'Ҫ': 'C',
        '£': '$',
        '₽': '$',
        'ӑ': 'a',
        'Ă': 'A',
    }

    result = []

    for token in sequence.split():

        for key, value in symbol_map.items():
            token = token.replace(key, value)

        for keyword in ['www', 'http']:
            if keyword in token:
                token = '_html_'

        result.append(token)

    return ' '.join(result)
