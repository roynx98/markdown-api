def get_format(url):
    if "docx" in url:
        return 'docx'
    if "msword" in url:
        return 'doc'

    return 'md'
