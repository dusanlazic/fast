class TextStyler:
    COLORS = {
        'black': '30',
        'red': '31',
        'green': '32',
        'yellow': '33',
        'blue': '34',
        'magenta': '35',
        'cyan': '36',
        'white': '37'
    }

    @staticmethod
    def bold(text):
        return f"\033[1m{text}\033[0m"

    @staticmethod
    def italic(text):
        return f"\033[3m{text}\033[0m"

    @staticmethod
    def underline(text):
        return f"\033[4m{text}\033[0m"

    @staticmethod
    def color(text, color):
        color_code = TextStyler.COLORS.get(color.lower(), '39')  # Default to '39' (default color)
        return f"\033[{color_code}m{text}\033[0m"
