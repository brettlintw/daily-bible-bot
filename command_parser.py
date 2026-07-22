def parse_command(text):
    text = text.strip()

    if text == "推播":
        return ("push", None)

    if text.startswith("主題 "):
        arg = text[len("主題 "):].strip()
        return ("theme", arg) if arg else (None, None)

    if text == "歷史" or text.startswith("歷史 "):
        rest = text[len("歷史"):].strip()
        if rest == "":
            return ("history", 5)
        if rest.isdigit() and int(rest) > 0:
            return ("history", int(rest))
        return ("history_error", None)

    if text == "下載":
        return ("download", None)

    if text == "選單":
        return ("menu", None)

    if text == "我的ID":
        return ("whoami", None)

    return (None, None)
