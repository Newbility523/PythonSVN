
def is_string(content):
    """
    是否为非空白的字符串
    :param content:
    :return: Bool
    """
    if content is None:
        return False

    if len(content) == 0:
        return False

    return not content.isspace()
