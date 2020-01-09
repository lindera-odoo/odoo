from raven import Client


class ravenSingleton:
    class __ravenSingleton:
        def __init__(self, url):
            self.Client = Client(url)
    instance = None
    def __init__(self, url):
        if not ravenSingleton.instance:
            ravenSingleton.instance = ravenSingleton.__ravenSingleton(url)
        else:
            ravenSingleton.instance.val = url
    def __getattr__(self, name):
        return getattr(self.instance, name)
